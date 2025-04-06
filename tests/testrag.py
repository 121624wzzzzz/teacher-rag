import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置镜像源
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

import logging
from src.core.rag_retriever import RAGRetriever

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def test_rag_pipeline():
    """测试RAG全流程"""
    # 初始化检索器 - 使用相对于项目根目录的路径
    retriever = RAGRetriever(
        vector_db_path=str(PROJECT_ROOT / "data" / "vector_db"),
        embedding_model_path=str(PROJECT_ROOT / "model" / "embeddingmodel"),
        rerank_model_name=str(PROJECT_ROOT / "model" / "reranker"),
        device="cpu",
        download_mirror="https://hf-mirror.com"
    )
    
    # 测试查询
    test_queries = [
        "概率论与数理统计",
        "大数定律",
        "古典概型"
    ]
    
    for query in test_queries:
        try:
            print(f"\n=== 测试查询: '{query}' ===")
            
            # 执行完整RAG流程
            result = retriever.full_retrieval(query, retrieval_top_k=3, rerank_top_k=3)
            
            if result["status"] == "success":
                # 打印多路召回结果
                print("\n[多路召回结果]")
                for method, results in result["results"]["multi_retrieval"].items():
                    print(f"{method.upper()} 结果:")
                    for doc, score in results[:2]:  # 显示前2个
                        print(f"  [{score:.2f}] {doc[:50]}...")
                
                # 打印混合检索结果
                print("\n[混合检索结果]")
                for doc, score in result["results"]["hybrid_search"][:3]:
                    print(f"  [{score:.4f}] {doc[:50]}...")
                
                # 打印重排序结果
                print("\n[重排序结果]")
                for doc, score in result["results"]["reranked"]:
                    print(f"  [{score:.2f}] {doc[:50]}...")
            else:
                print(f"查询失败: {result['message']}")
                
        except Exception as e:
            logging.error(f"处理查询失败: {str(e)}")

if __name__ == "__main__":
    # 运行测试流程
    test_rag_pipeline()
    print("\n✅ 测试完成！请检查输出结果是否符合预期")