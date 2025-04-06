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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

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
            
            return (
                self._handle_stream_response(response) 
                if stream 
                else self._handle_non_stream_response(response)
            )
                
        except Exception as e:
            logging.error(f"LLM查询失败: {str(e)}")
            raise

    def _handle_stream_response(self, response: requests.Response) -> Generator[str, None, None]:
        """处理流式响应"""
        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode('utf-8').strip()
                if chunk_str.startswith('data: '):
                    json_str = chunk_str[6:]
                    if json_str == "[DONE]":
                        return
                    try:
                        data = json.loads(json_str)
                        if content := data['choices'][0]['delta'].get('content'):
                            yield content
                    except Exception as parse_error:
                        logging.warning(f"解析错误: {parse_error}")

    def _handle_non_stream_response(self, response: requests.Response) -> str:
        """处理非流式响应"""
        try:
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except KeyError:
            logging.error("响应格式异常")
            return ""

class DynamicPromptEngine:
    """动态提示工程主类"""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        rag_config: RAGConfig,
        prompt_rag_config: RAGConfig,
        stream_output: bool = True
    ):
        self.llm = LLMClient(llm_config)
        self.stream_output = stream_output
        
        # 延迟导入以避免不必要的依赖
        from src.core.rag_retriever import RAGRetriever
        
        self.retriever = RAGRetriever(**rag_config.__dict__)
        self.prompt_retriever = RAGRetriever(**prompt_rag_config.__dict__)
        
        self.conversation_history: List[Dict[str, str]] = []
        self.current_enhanced_prompt: Optional[str] = None
        self.is_first_query: bool = True

    def rewrite_query(self, original_query: str) -> Generator[str, None, None]:
        """LLM1: 流式查询改写"""
        prompt = f"""请将以下用户查询改写为更适合信息检索的形式，保持原意但更明确具体：
原始查询: {original_query}
改写后的查询:"""
        
        try:
            response = self.llm.query([{"role": "user", "content": prompt}], stream=True)
            for chunk in response:
                yield chunk
        except Exception as e:
            logging.error(f"查询改写失败: {str(e)}")
            yield "[错误] 查询改写失败"

    def retrieve_prompt_template(self, query: str) -> str:
        """从RAG检索提示模板"""
        try:
            result = self.prompt_retriever.full_retrieval(
                query, 
                retrieval_top_k=5, 
                rerank_top_k=3
            )
            
            if result["status"] == "success":
                top_templates = [doc for doc, _ in result["results"]["reranked"][:3]]
                return "\n\n---\n\n".join(top_templates) or "默认提示模板"
            return "默认提示模板"
        except Exception as e:
            logging.error(f"模板检索失败: {str(e)}")
            return "默认提示模板"

    def generate_enhanced_prompt(
        self, 
        original_query: str, 
        retrieved_template: str
    ) -> Generator[str, None, None]:
        """LLM2: 流式生成增强提示词"""
        prompt = f"""基于以下信息生成优化提示词：
原始查询: {original_query}
检索模板: {retrieved_template}

生成要求:
1. 明确用户意图
2. 包含必要上下文
3. 优化检索结构

最终提示词:"""
        
        try:
            response = self.llm.query(
                [{"role": "user", "content": prompt}], 
                stream=True
            )
            for chunk in response:
                yield chunk
        except Exception as e:
            logging.error(f"提示生成失败: {str(e)}")
            yield "[错误] 增强提示生成失败"

    def process_query(
        self,
        original_query: str,
        verbose: bool = False
    ) -> Generator[str, None, None]:
        """
        完整处理流程
        """
        try:
            self.conversation_history.append({"role": "user", "content": original_query})
            
            if self.is_first_query:
                # 首次查询完整流程
                rewritten_query = []
                for chunk in self.rewrite_query(original_query):
                    rewritten_query.append(chunk)
                    yield chunk
                rewritten_query = "".join(rewritten_query)
                
                prompt_template = self.retrieve_prompt_template(rewritten_query)
                if not prompt_template:
                    raise ValueError("未检索到有效提示模板")
                
                enhanced_prompt = []
                for chunk in self.generate_enhanced_prompt(original_query, prompt_template):
                    enhanced_prompt.append(chunk)
                    yield chunk
                self.current_enhanced_prompt = "".join(enhanced_prompt)
                self.is_first_query = False
            else:
                # 后续查询复用模板
                for chunk in self.rewrite_query(original_query):
                    yield chunk
            
            # 知识检索（假设已实现）
            knowledge = "相关上下文信息..."
            
            # 生成最终回复
            final_response = self.llm.query(
                messages=[
                    {"role": "system", "content": self.current_enhanced_prompt},
                    {"role": "user", "content": f"{original_query}\n\n相关知识:{knowledge}"}
                ],
                stream=self.stream_output
            )
            
            if isinstance(final_response, Generator):
                for chunk in final_response:
                    yield chunk
            else:
                yield final_response
                
        except Exception as e:
            logging.error(f"处理流程异常: {str(e)}")
            yield "[系统错误] 处理请求失败"

def get_default_configs(project_root: Path) -> tuple:
    """获取默认配置"""
    return (
        LLMConfig(),
        RAGConfig(
            vector_db_path=str(project_root/"data/vector_db"),
            embedding_model_path=str(project_root/"model/embedding"),
            rerank_model_name="BAAI/bge-reranker-base"
        ),
        RAGConfig(
            vector_db_path=str(project_root/"data/prompts_db"),
            embedding_model_path=str(project_root/"model/embedding"),
            rerank_model_name="BAAI/bge-reranker-base"
        )
    )

def main():
    """命令行交互主函数"""
    project_root = Path(__file__).parent.parent.parent
    sys.path.append(str(project_root))
    
    llm_config, rag_config, prompt_rag_config = get_default_configs(project_root)
    
    engine = DynamicPromptEngine(
        llm_config=llm_config,
        rag_config=rag_config,
        prompt_rag_config=prompt_rag_config
    )
    
    print("动态提示系统已启动 (输入exit退出)")
    while True:
        try:
            user_input = input("\n你的问题: ").strip()
            if user_input.lower() in ('exit', 'quit'):
                break
                
            print("\nAI回复: ", end="", flush=True)
            for chunk in engine.process_query(user_input, verbose=True):
                print(chunk, end="", flush=True)
            print("\n" + "="*50)
            
        except KeyboardInterrupt:
            print("\n操作已取消")
            break
        except Exception as e:
            logging.error(f"运行时错误: {str(e)}")

if __name__ == "__main__":
    main()