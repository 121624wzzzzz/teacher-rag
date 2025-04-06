import os
import json
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path
import logging
from src.core.rag_retriever import RAGRetriever
from typing import Dict, List, Optional

# 环境配置
load_dotenv()
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format="%(asctime)s - %(levelname)s - %(message)s")

# API配置
API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = os.getenv("API_URL")
MODEL = os.getenv("MODEL_NAME")

class DynamicPromptEngine:
    def __init__(self):
        # 初始化RAG检索器
        self.retriever = RAGRetriever(
            vector_db_path=str(PROJECT_ROOT / "data" / "vector_db"),
            embedding_model_path=str(PROJECT_ROOT / "model" / "embeddingmodel"),
            rerank_model_name=str(PROJECT_ROOT / "model" / "reranker"),
            device="cpu",
            download_mirror="https://hf-mirror.com"
        )
        
        # 提示模板路径
        self.prompt_retriever = RAGRetriever(
            vector_db_path=str(PROJECT_ROOT / "data" / "prompts" / "vector_db"),  # 关键修改点
            embedding_model_path=str(PROJECT_ROOT / "model" / "embeddingmodel"),  # 可以复用同一个embedding模型
            rerank_model_name=str(PROJECT_ROOT / "model" / "reranker"),  # 可以复用同一个reranker
            device="cpu",
            download_mirror="https://hf-mirror.com"
        )
        
        # 流式输出配置
        self.stream_output = True
    
    def query_llm(self, messages: List[Dict], stream: bool = False) -> str:
        """通用LLM查询函数"""
        try:
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": stream
                },
                stream=stream,
                timeout=100
            )
            response.raise_for_status()
            
            if stream:
                full_response = []
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
                                    if self.stream_output:
                                        print(content, end="", flush=True)
                                    full_response.append(content)
                            except:
                                continue
                return "".join(full_response)
            else:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
                
        except Exception as e:
            logging.error(f"LLM查询失败: {str(e)}")
            raise

    def rewrite_query(self, original_query: str) -> str:
        """LLM1: 查询改写"""
        prompt = f"""请将以下用户查询改写为更适合信息检索的形式，保持原意但更明确具体：
        
原始查询: {original_query}

改写后的查询:"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.query_llm(messages)

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

    def generate_enhanced_prompt(self, original_query: str, retrieved_template: str) -> str:
        """LLM2: 生成增强提示词"""
        prompt = f"""基于以下原始查询和检索到的提示模板，生成一个优化的LLM提示词：

原始查询: {original_query}
检索到的提示模板: {retrieved_template}

请生成一个结合两者优点的最终提示词，确保它:
1. 清晰明确地表达用户意图
2. 包含适当的上下文和约束条件
3. 优化了信息检索和回答质量

生成的最终提示词:"""
        
        messages = [{"role": "user", "content": prompt}]
        return self.query_llm(messages)

    def generate_final_response(self, enhanced_prompt: str, original_query: str) -> str:
        """LLM3: 生成最终回复"""
        # 先检索相关知识
        retrieval_result = self.retriever.full_retrieval(
            original_query,
            retrieval_top_k=5,
            rerank_top_k=3
        )
        
        knowledge = ""
        if retrieval_result["status"] == "success":
            knowledge = "\n".join([
                doc[0] for doc in retrieval_result["results"]["reranked"]
            ])
        
        messages = [
            {"role": "system", "content": enhanced_prompt},
            {"role": "user", "content": f"问题: {original_query}\n相关背景知识:\n{knowledge}"}
        ]
        
        return self.query_llm(messages, stream=self.stream_output)

    def process_query(self, original_query: str) -> str:
        """完整处理流程"""
        logging.info("开始处理查询...")
        
        # 步骤1: 查询改写
        logging.info("步骤1: 查询改写...")
        rewritten_query = self.rewrite_query(original_query)
        logging.info(f"改写后的查询: {rewritten_query}")
        
        # 步骤2: 检索提示模板
        logging.info("步骤2: 检索提示模板...")
        prompt_template = self.retrieve_prompt_template(rewritten_query)
        logging.info(f"检索到的提示模板: {prompt_template[:100]}...")
        
        # 步骤3: 生成增强提示
        logging.info("步骤3: 生成增强提示...")
        enhanced_prompt = self.generate_enhanced_prompt(original_query, prompt_template)
        logging.info(f"生成的增强提示: {enhanced_prompt[:100]}...")
        
        # 步骤4: 生成最终回复
        logging.info("步骤4: 生成最终回复...")
        print("\nAI回复: ", end="", flush=True)
        final_response = self.generate_final_response(enhanced_prompt, original_query)
        
        return final_response

def main():
    engine = DynamicPromptEngine()
    
    print("动态提示工程系统已启动 (输入exit退出)")
    while True:
        user_input = input("\n你的问题: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue
            
        try:
            engine.process_query(user_input)
            print("\n" + "="*50)
        except Exception as e:
            logging.error(f"处理查询时出错: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n对话已终止")
        sys.exit(0)