import os
import json
import logging
from typing import Dict, List, Optional, Generator, Union, Any
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

# 环境配置
load_dotenv()
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 配置日志
logging.basicConfig(level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s")

@dataclass
class LLMConfig:
    """LLM配置数据类"""
    api_key: str = os.getenv("DEEPSEEK_API_KEY")
    api_url: str = os.getenv("API_URL")
    model_name: str = os.getenv("MODEL_NAME")
    temperature: float = 0.7
    timeout: int = 1000

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