import json
import requests
from typing import List, Dict, Generator
import logging

class StreamingLLMClient:
    """支持全链路流式处理的LLM客户端"""
    
    def __init__(self, api_key: str, api_url: str, model: str):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = 60

    def stream_response(self, messages: List[Dict]) -> Generator[str, None, None]:
        """流式响应生成器"""
        try:
            with requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                
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
                                    yield data['choices'][0]['delta']['content']
                            except:
                                continue
        except Exception as e:
            logging.error(f"流式请求失败: {str(e)}")
            raise

    def stream_pipeline(self, prompt: str) -> Generator[str, None, None]:
        """流式处理管道"""
        messages = [{"role": "user", "content": prompt}]
        for chunk in self.stream_response(messages):
            yield chunk