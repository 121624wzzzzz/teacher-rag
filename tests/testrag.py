# testrag.py - RAG流程测试脚本
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置镜像源
import sys


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import logging
from huggingface_hub import snapshot_download
from utils.rag_retriever import RAGRetriever

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def download_rerank_model():
    """通过镜像下载重排序模型"""
    try:
        logging.info("开始下载重排序模型...")
        model_path = snapshot_download(
            repo_id="BAAI/bge-reranker-base",
            local_dir="./model/reranker",
            resume_download=True
        )
        logging.info(f"模型下载成功：{model_path}")
        return model_path
    except Exception as e:
        logging.error(f"模型下载失败: {str(e)}")
        return None

def test_rag_pipeline():
    """测试RAG全流程"""
    # 初始化检索器
    retriever = RAGRetriever(
        vector_db_path="./data/vector_db",
        embedding_model_path="./model/embeddingmodel",
        rerank_model_name="./model/reranker",  # 使用本地路径
        device="cpu"
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
            
            # 多路召回
            multi_results = retriever.multi_retrieval(query, top_k=3)
            print("\n[多路召回结果]")
            for method, results in multi_results.items():
                print(f"{method.upper()} 结果:")
                for doc, score in results[:2]:  # 显示前2个
                    print(f"  [{score:.2f}] {doc[:50]}...")
            
            # 混合检索
            fused_results = retriever.hybrid_search(multi_results)
            print("\n[混合检索结果]")
            for doc, score in fused_results[:3]:
                print(f"  [{score:.4f}] {doc[:50]}...")
            
            # 重排序
            candidate_docs = [doc for doc, _ in fused_results[:5]]
            reranked = retriever.rerank(query, candidate_docs)
            print("\n[重排序结果]")
            for doc, score in reranked:
                print(f"  [{score:.2f}] {doc[:50]}...")
                
        except Exception as e:
            logging.error(f"处理查询失败: {str(e)}")

if __name__ == "__main__":
    # 下载模型（首次运行需要）
    if not os.path.exists("./model/reranker"):
        download_rerank_model()
    
    # 运行测试流程
    test_rag_pipeline()
    print("\n✅ 测试完成！请检查输出结果是否符合预期")