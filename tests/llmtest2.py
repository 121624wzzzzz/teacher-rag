import os
from dotenv import load_dotenv
from pathlib import Path
import sys
from src.core.rag_retriever import RAGRetriever
from src.llm.client import StreamingLLMClient
from src.llm.prompt_engine import StreamingPromptEngine

def initialize_components():
    """初始化所有组件（修正参数名称）"""
    load_dotenv()
    PROJECT_ROOT = Path(__file__).parent
    
    # 主知识库检索器
    knowledge_retriever = RAGRetriever(
        vector_db_path=str(PROJECT_ROOT / "data" / "vector_db"),
        embedding_model_path=str(PROJECT_ROOT / "model" / "embeddingmodel"),
        rerank_model_name=str(PROJECT_ROOT / "model" / "reranker"),
        device="cpu",
        download_mirror="https://hf-mirror.com"
    )
    
    # 提示模板检索器（独立路径）
    prompt_retriever = RAGRetriever(
        vector_db_path=str(PROJECT_ROOT / "data" / "prompts" / "vector_db"),
        embedding_model_path=str(PROJECT_ROOT / "model" / "embeddingmodel"),
        rerank_model_name=str(PROJECT_ROOT / "model" / "reranker"),
        device="cpu",
        download_mirror="https://hf-mirror.com"
    )
    
    # 初始化LLM客户端
    llm_client = StreamingLLMClient(
        api_key=os.getenv("SILICONFLOW_API_KEY"),
        api_url=os.getenv("API_URL"),
        model=os.getenv("MODEL_NAME")
    )
    
    return StreamingPromptEngine(
        knowledge_retriever=knowledge_retriever,  # 修正参数名称
        prompt_retriever=prompt_retriever,
        llm_client=llm_client
    )

def main():
    engine = initialize_components()
    print("流式处理系统已就绪 (输入exit退出)")
    
    while True:
        query = input("\n你的问题: ").strip()
        if query.lower() in ['exit', 'quit']:
            break
            
        try:
            print()  # 空行分隔
            for chunk in engine.process_query(query):
                print(chunk, end="", flush=True)
            print("\n" + "="*50)
        except Exception as e:
            print(f"\n处理出错: {str(e)}")

if __name__ == "__main__":
    main()