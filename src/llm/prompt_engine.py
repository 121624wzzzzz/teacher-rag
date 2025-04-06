import os
import json
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging
from typing import Dict, List, Optional, Generator, Union, Any
from dataclasses import dataclass

# 环境配置
load_dotenv()
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format="%(asctime)s - %(levelname)s - %(message)s")

@dataclass
class LLMConfig:
    """LLM配置数据类"""
    api_key: str = os.getenv("SILICONFLOW_API_KEY")
    api_url: str = os.getenv("API_URL")
    model_name: str = os.getenv("MODEL_NAME")
    temperature: float = 0.7
    timeout: int = 100

@dataclass
class RAGConfig:
    """RAG配置数据类"""
    vector_db_path: str
    embedding_model_path: str
    rerank_model_name: str
    device: str = "cpu"
    download_mirror: str = "https://hf-mirror.com"

class LLMClient:
    """LLM客户端封装类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def query(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> Union[Generator[str, None, None], str]:
        """
        通用LLM查询函数
        
        参数:
            messages: 消息列表
            stream: 是否流式输出
            
        返回:
            生成器(流式)或字符串(非流式)
        """
        try:
            response = requests.post(
                self.config.api_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": self.config.temperature,
                    "stream": stream
                },
                stream=stream,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return self._handle_non_stream_response(response)
                
        except Exception as e:
            logging.error(f"LLM查询失败: {str(e)}")
            raise
    
    def _handle_stream_response(self, response: requests.Response) -> Generator[str, None, None]:
        """处理流式响应"""
        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8')
                if chunk_str.startswith('data: '):
                    json_str = chunk_str[6:]
                    if json_str == "[DONE]":
                        break
                    try:
                        data = json.loads(json_str)
                        if 'content' in data['choices'][0]['delta']:
                            content = data['choices'][0]['delta']['content']
                            yield content
                    except:
                        continue
    
    def _handle_non_stream_response(self, response: requests.Response) -> str:
        """处理非流式响应"""
        data = response.json()
        return data['choices'][0]['message']['content'].strip()

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

改写后的查询:"""
        
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
    
    def generate_enhanced_prompt(self, original_query: str, retrieved_template: str) -> Generator[str, None, None]:
        """LLM2: 流式生成增强提示词"""
        prompt = f"""基于以下原始查询和检索到的提示模板，生成一个优化的LLM提示词：

    原始查询: {original_query}
    检索到的提示模板: {retrieved_template}

    请生成一个结合两者优点的最终提示词，确保它:
    1. 清晰明确地表达用户意图
    2. 包含适当的上下文和约束条件
    3. 优化了信息检索和回答质量

    生成的最终提示词:"""
        
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

    def process_query(
        self,
        original_query: str,
        verbose: bool = False
    ) -> Generator[str, None, None]:
        """
        完整处理流程
        
        参数:
            original_query: 用户原始查询
            verbose: 是否输出详细日志
            
        返回:
            生成器，流式输出响应内容
        """
        if verbose:
            logging.info("开始处理查询...")
        
        # 更新对话历史
        self.conversation_history.append({"role": "user", "content": original_query})
        
        if self.is_first_query:
            if verbose:
                logging.info("首次查询，执行完整流程...")
            
            # 步骤1: 流式查询改写
            if verbose:
                logging.info("步骤1: 查询改写...")
                print("\n[查询改写]: ", end="", flush=True)
            rewritten_query_chunks = []
            for chunk in self.rewrite_query(original_query):
                rewritten_query_chunks.append(chunk)
                yield chunk  # 将改写结果也流式输出
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
                yield chunk  # 将增强提示也流式输出
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
                yield chunk  # 将改写结果也流式输出
            rewritten_query = "".join(rewritten_query_chunks)
            if verbose:
                print("\n", end="")
                logging.info(f"改写后的查询: {rewritten_query}")
        
        # 步骤4: 检索相关知识
        if verbose:
            logging.info("检索相关知识...")
            print("\n[知识检索]: 进行中...", flush=True)
        knowledge = self.retrieve_knowledge(rewritten_query)
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
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []
        self.current_enhanced_prompt = None
        self.is_first_query = True

def get_default_configs(project_root: Path) -> tuple:
    """获取默认配置"""
    # LLM配置
    llm_config = LLMConfig()
    
    # 知识库RAG配置
    rag_config = RAGConfig(
        vector_db_path=str(project_root / "data" / "vector_db"),
        embedding_model_path=str(project_root / "model" / "embeddingmodel"),
        rerank_model_name=str(project_root / "model" / "reranker")
    )
    
    # 提示模板RAG配置
    prompt_rag_config = RAGConfig(
        vector_db_path=str(project_root / "data" / "prompts" / "vector_db"),
        embedding_model_path=str(project_root / "model" / "embeddingmodel"),
        rerank_model_name=str(project_root / "model" / "reranker")
    )
    
    return llm_config, rag_config, prompt_rag_config

def main():
    """命令行交互主函数"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    
    # 获取配置
    llm_config, rag_config, prompt_rag_config = get_default_configs(project_root)
    
    # 初始化引擎
    engine = DynamicPromptEngine(
        llm_config=llm_config,
        rag_config=rag_config,
        prompt_rag_config=prompt_rag_config,
        stream_output=True
    )
    
    print("动态提示工程系统已启动 (输入exit退出)")
    while True:
        user_input = input("\n你的问题: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue
            
        try:
            print("\nAI回复: ", end="", flush=True)
            for chunk in engine.process_query(user_input, verbose=True):
                print(chunk, end="", flush=True)
            print("\n" + "="*50)
        except Exception as e:
            logging.error(f"处理查询时出错: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n对话已终止")
        sys.exit(0)