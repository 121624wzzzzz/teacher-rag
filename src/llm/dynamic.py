import logging
from typing import Dict, List, Optional, Generator, Any
from dataclasses import dataclass
from .llm_core import LLMClient, LLMConfig, RAGConfig

class DynamicPromptEngine:
    """动态提示工程主类"""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        rag_config: RAGConfig,
        prompt_rag_config: RAGConfig,
        stream_output: bool = True
    ):
        """
        初始化动态提示引擎
        
        参数:
            llm_config: LLM配置
            rag_config: 知识库RAG配置
            prompt_rag_config: 提示模板RAG配置
            stream_output: 是否流式输出
        """
        self.llm = LLMClient(llm_config)
        self.stream_output = stream_output
        
        # 延迟导入以避免不必要的依赖
        from src.core.rag_retriever import RAGRetriever
        
        # 初始化知识库检索器
        self.retriever = RAGRetriever(**rag_config.__dict__)
        
        # 初始化提示模板检索器
        self.prompt_retriever = RAGRetriever(**prompt_rag_config.__dict__)
        
        # 上下文管理
        self.conversation_history: List[Dict[str, str]] = []
        self.current_enhanced_prompt: Optional[str] = None
        self.is_first_query: bool = True
    
    def rewrite_query(self, original_query: str) -> Generator[str, None, None]:
        """LLM1: 流式查询改写"""
        prompt = f"""请将以下用户查询改写为更适合信息检索的形式，保持原意但更明确具体：
        
原始查询: {original_query}

改写后的查询:（需要注意你只给我改写为结果而不用无关信息，之后我将直接将你的输出用来查询）"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.query(messages, stream=True)
        
        full_response = []
        if isinstance(response, Generator):
            for chunk in response:
                full_response.append(chunk)
                yield chunk
            return "".join(full_response)
        else:
            yield response
            return response
    
    def retrieve_prompt_template(self, query: str) -> str:
        """从RAG检索提示模板"""
        try:
            result = self.prompt_retriever.full_retrieval(
                query, 
                retrieval_top_k=5, 
                rerank_top_k=3
            )
            
            if result["status"] == "success":
                # 获取最佳匹配的提示模板
                top_templates = [doc for doc, _ in result["results"]["reranked"][:3]]
                return "\n\n---\n\n".join(top_templates)
            else:
                logging.warning(f"检索失败: {result['message']}")
                return ""
        except Exception as e:
            logging.error(f"检索提示模板失败: {str(e)}")
            return ""
        
    def retrieve_knowledge(self, query: str) -> str:
        """从RAG检索相关知识"""
        try:
            result = self.retriever.full_retrieval(
                query, 
                retrieval_top_k=5,  # 知识库可以取更多结果
                rerank_top_k=3       # 最终保留3个最相关片段
            )
            
            if result["status"] == "success":
                # 格式化检索结果
                knowledge_snippets = [
                    f"【知识片段 {i+1}】\n{doc}"
                    for i, (doc, score) in enumerate(result["results"]["reranked"][:3])
                ]
                return "\n\n".join(knowledge_snippets)
            else:
                logging.warning(f"知识检索失败: {result['message']}")
                return ""
        except Exception as e:
            logging.error(f"知识检索过程中发生异常: {str(e)}")
            return ""
        
    def generate_enhanced_prompt(self, original_query: str, retrieved_template: str) -> Generator[str, None, None]:
        """LLM2: 流式生成增强提示词"""
        prompt = f"""基于以下原始查询和检索到的提示模板，生成一个优化的LLM提示词:

    原始查询: {original_query}
    检索到的提示模板: {retrieved_template}

    请生成一个结合两者优点的最终提示词，确保它:
    1. 清晰明确地表达用户意图
    2. 包含适当的上下文和约束条件
    3. 优化了信息检索和回答质量
    4. 不要过分细化，要保持一定的提示词的泛用性

    生成的最终提示词:（需要注意你只给我最终提示词不用无关信息，之后我将直接将你输出赋给其他大模型作为他的systemprompt）"""
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.query(messages, stream=True)
        
        # 修改这里：直接返回生成器，不拼接完整响应
        if isinstance(response, Generator):
            return response
        else:
            # 将非流式响应转换为生成器
            def gen():
                yield response
            return gen()

    def generate_response(
        self,
        original_query: str,
        enhanced_prompt: str,
        knowledge: str
    ) -> Generator[str, None, None]:
        """LLM3: 流式生成最终回复"""
        try:
            # 构建系统提示（核心提示工程）
            system_prompt = enhanced_prompt
            
            # 构建完整的消息历史
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history
            ]
            
            # 调用LLM生成响应
            response = self.llm.query(messages, stream=self.stream_output)
            
            # 流式处理
            if isinstance(response, Generator):
                return response
            else:
                # 非流式响应适配为生成器
                def wrapper():
                    yield response
                return wrapper()
                
        except Exception as e:
            logging.error(f"回复生成失败: {str(e)}")
            def error_generator():
                yield "抱歉，生成回复时出现错误，请稍后再试。"
            return error_generator()

    def generate_prompt(
        self,
        original_query: str,
        verbose: bool = False
    ) -> Generator[str, None, None]:
        """
        生成增强提示词的流程
        
        参数:
            original_query: 用户原始查询
            verbose: 是否输出详细日志
            
        返回:
            生成器，流式输出提示词生成过程的内容
        """
        if verbose:
            logging.info("开始生成提示词...")
        
        if self.is_first_query:
            if verbose:
                logging.info("首次查询，执行完整提示生成流程...")
            
            # 步骤1: 流式查询改写
            if verbose:
                logging.info("步骤1: 查询改写...")
                print("\n[查询改写]: ", end="", flush=True)
            rewritten_query_chunks = []
            for chunk in self.rewrite_query(original_query):
                rewritten_query_chunks.append(chunk)
                yield chunk
            rewritten_query = "".join(rewritten_query_chunks)
            if verbose:
                print("\n", end="")
                logging.info(f"改写后的查询: {rewritten_query}")
            
            # 步骤2: 检索提示模板
            if verbose:
                logging.info("步骤2: 检索提示模板...")
                print("\n[检索提示模板]: 进行中...", flush=True)
            prompt_template = self.retrieve_prompt_template(rewritten_query)
            if verbose:
                logging.info(f"检索到的提示模板: {prompt_template[:100]}...")
                print(f"\n[检索到的提示模板]:\n{prompt_template[:200]}...\n", flush=True)
            
            # 步骤3: 流式生成增强提示
            if verbose:
                logging.info("步骤3: 生成增强提示...")
                print("\n[生成增强提示]: ", end="", flush=True)
            enhanced_prompt_chunks = []
            for chunk in self.generate_enhanced_prompt(original_query, prompt_template):
                enhanced_prompt_chunks.append(chunk)
                yield chunk
            enhanced_prompt = "".join(enhanced_prompt_chunks)
            if verbose:
                print("\n", end="")
                logging.info(f"生成的增强提示: {enhanced_prompt[:100]}...")
                print(f"\n[最终增强提示]:\n{enhanced_prompt}\n", flush=True)
            
            self.current_enhanced_prompt = enhanced_prompt
            self.is_first_query = False
        else:
            if verbose:
                logging.info("非首次查询，复用已有提示模板...")
                print("\n[复用提示模板]: 使用之前生成的增强提示", flush=True)
            
            # 只需改写查询用于知识检索
            if verbose:
                logging.info("改写查询用于知识检索...")
                print("\n[查询改写]: ", end="", flush=True)
            rewritten_query_chunks = []
            for chunk in self.rewrite_query(original_query):
                rewritten_query_chunks.append(chunk)
                yield chunk
            rewritten_query = "".join(rewritten_query_chunks)
            if verbose:
                print("\n", end="")
                logging.info(f"改写后的查询: {rewritten_query}")

    def start_conversation(
        self,
        original_query: str,
        verbose: bool = False
    ) -> Generator[str, None, None]:
        """
        使用设置好的的提示词开始对话
        
        参数:
            original_query: 用户原始查询
            verbose: 是否输出详细日志
            
        返回:
            生成器，流式输出对话内容
        """
        if verbose:
            logging.info("开始对话流程...")
        
        # 改写查询用于知识检索
        rewritten_query_chunks = []
        for chunk in self.rewrite_query(original_query):
            rewritten_query_chunks.append(chunk)
        rewritten_query = "".join(rewritten_query_chunks)
        
        # 步骤4: 检索相关知识
        if verbose:
            logging.info("检索相关知识...")
            print("\n[知识检索]: 进行中...", flush=True)
        knowledge = self.retrieve_knowledge(rewritten_query)
        user_content_with_knowledge = f"""用户查询: {original_query}
        相关背景知识:
        {knowledge}"""
        self.conversation_history.append({"role": "user", "content": user_content_with_knowledge})
        if verbose:
            logging.info(f"检索到的知识: {knowledge[:100]}...")
            print(f"\n[检索到的知识]:\n{knowledge[:200]}...\n", flush=True)
        
        # 步骤5: 生成并流式输出最终回复
        if verbose:
            logging.info("生成最终回复...")
            print("\n[生成最终回复]: ", end="", flush=True)
        
        full_response = []
        response_generator = self.generate_response(original_query, self.current_enhanced_prompt, knowledge)
        for chunk in response_generator:
            full_response.append(chunk)
            yield chunk
        
        # 更新对话历史
        self.conversation_history.append({"role": "assistant", "content": "".join(full_response)})
        # if verbose:
        #     print("\n=== 完整对话历史 ===")
        #     for i, msg in enumerate(self.conversation_history):
        #         print(f"[{i}] {msg['role']}: {msg['content'][:1000]}...")

    def process_query(
        self,
        original_query: str,
        verbose: bool = False
    ) -> Generator[str, None, None]:
        """
        完整处理流程（整合生成提示词和开始对话）
        
        参数:
            original_query: 用户原始查询
            verbose: 是否输出详细日志
            
        返回:
            生成器，流式输出响应内容
        """
        if verbose:
            logging.info("开始处理查询...")
        
        # 生成提示词部分
        prompt_generator = self.generate_prompt(original_query, verbose)
        for chunk in prompt_generator:
            yield chunk
        
        # 开始对话部分
        conversation_generator = self.start_conversation(original_query, verbose)
        for chunk in conversation_generator:
            yield chunk
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []
        self.current_enhanced_prompt = None
        self.is_first_query = True

def get_default_configs() -> tuple:
    """获取默认配置"""
    # LLM配置
    llm_config = LLMConfig()
    
    # 知识库RAG配置
    rag_config = RAGConfig(
        vector_db_path="data/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    # 提示模板RAG配置
    prompt_rag_config = RAGConfig(
        vector_db_path="data/prompts/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    return llm_config, rag_config, prompt_rag_config

def get_knowledge_configs() -> tuple:
    """获取默认知识库配置"""
    # LLM配置
    llm_config = LLMConfig()
    
    # 知识库RAG配置
    knowledge_rag_config = RAGConfig(
        vector_db_path="data/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    # 提示模板RAG配置
    prompt_rag_config = RAGConfig(
        vector_db_path="data/prompts/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    return llm_config, knowledge_rag_config, prompt_rag_config

def get_exercise_configs() -> tuple:
    """获取默认配置"""
    # LLM配置
    llm_config = LLMConfig()
    
    # 知识库RAG配置
    exercise_rag_config = RAGConfig(
        vector_db_path="data/exercise/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    # 提示模板RAG配置
    prompt_rag_config = RAGConfig(
        vector_db_path="data/prompts/vector_db",  # 直接相对路径
        embedding_model_path="model/embeddingmodel",
        rerank_model_name="model/reranker"
    )
    
    return llm_config, exercise_rag_config, prompt_rag_config