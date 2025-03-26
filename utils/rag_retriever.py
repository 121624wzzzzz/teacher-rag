# rag_retriever.py - RAG检索模块（多路召回+混合检索+重排序）
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置镜像源

import logging
from typing import List, Dict, Tuple
import numpy as np
from pathlib import Path

# 第三方库
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class RAGRetriever:
    """RAG检索器（支持多路召回、混合检索、重排序）"""
    
    def __init__(
        self,
        vector_db_path: str,
        embedding_model_path: str = "./model/embeddingmodel",
        rerank_model_name: str = "BAAI/bge-reranker-base",
        device: str = "cpu"
    ):
        """
        初始化检索器
        :param vector_db_path: 向量数据库路径
        :param embedding_model_path: 本地嵌入模型路径
        :param rerank_model_name: 重排序模型名称
        :param device: 计算设备
        """
        self.device = device
        self._init_logging()
        
        # 初始化基础组件
        self._load_embedding_model(embedding_model_path)
        self._load_vector_db(vector_db_path)
        self._load_rerank_model(rerank_model_name)
        
        # 初始化BM25
        self._init_bm25()

    def _init_logging(self):
        """配置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
        )
    
    def _load_embedding_model(self, model_path: str):
        """加载本地嵌入模型"""
        try:
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={'device': self.device},
                encode_kwargs={'normalize_embeddings': False}
            )
            logging.info("✅ 嵌入模型加载成功")
        except Exception as e:
            logging.error(f"❌ 嵌入模型加载失败: {str(e)}")
            raise
    
    def _load_vector_db(self, db_path: str):
        """加载向量数据库"""
        try:
            self.vector_db = FAISS.load_local(
                folder_path=db_path,
                embeddings=self.embedding_model,
                allow_dangerous_deserialization=True
            )
            logging.info(f"✅ 向量数据库加载成功（{self.vector_db.index.ntotal}条数据）")
        except Exception as e:
            logging.error(f"❌ 向量数据库加载失败: {str(e)}")
            raise
    
    def _load_rerank_model(self, model_name: str):
        """加载重排序模型"""
        try:
            self.rerank_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.rerank_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.rerank_model.to(self.device)
            logging.info(f"✅ 重排序模型加载成功: {model_name}")
        except Exception as e:
            logging.error(f"❌ 重排序模型加载失败: {str(e)}")
            raise
    
    def _init_bm25(self):
        """初始化BM25索引"""
        try:
            all_texts = [doc.page_content for doc in self.vector_db.docstore._dict.values()]
            self.bm25_index = BM25Okapi([doc.split() for doc in all_texts])
            self.all_texts = all_texts
            logging.info(f"✅ BM25索引构建成功（{len(all_texts)}条数据）")
        except Exception as e:
            logging.error(f"❌ BM25索引构建失败: {str(e)}")
            raise

    def multi_retrieval(self, query: str, top_k: int = 10) -> Dict[str, List[Tuple[str, float]]]:
        """
        多路召回检索
        :param query: 查询文本
        :param top_k: 每路召回数量
        :return: 各路的检索结果字典
        """
        results = {}
        
        # 向量检索
        vector_results = self.vector_db.similarity_search_with_score(query, k=top_k)
        results["vector"] = [(doc.page_content, score) for doc, score in vector_results]
        
        # BM25检索
        tokenized_query = query.split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_indices = np.argsort(bm25_scores)[::-1][:top_k]
        results["bm25"] = [(self.all_texts[i], bm25_scores[i]) for i in bm25_indices]
        
        logging.info(f"🔍 多路召回完成：向量召回 {len(results['vector'])} 条，BM25召回 {len(results['bm25'])} 条")
        return results

    def hybrid_search(self, retrieval_results: Dict[str, List[Tuple[str, float]]], 
                      weights: Dict[str, float] = None) -> List[Tuple[str, float]]:
        """
        混合检索（加权融合）
        :param retrieval_results: 多路召回结果
        :param weights: 各检索方法的权重（默认：向量0.6，BM25 0.4）
        :return: 融合后的结果列表
        """
        # 设置默认权重
        default_weights = {"vector": 0.6, "bm25": 0.4}
        weights = weights or default_weights
        
        # 结果融合
        fused_results = {}
        for method, docs in retrieval_results.items():
            for doc, score in docs:
                # 分数归一化处理
                norm_score = 1 / (1 + np.exp(-score)) if method == "vector" else score
                fused_score = norm_score * weights.get(method, 0)
                if doc in fused_results:
                    fused_results[doc] += fused_score
                else:
                    fused_results[doc] = fused_score
        
        # 排序并返回
        sorted_results = sorted(fused_results.items(), key=lambda x: x[1], reverse=True)
        logging.info(f"🧬 混合检索完成：融合 {len(sorted_results)} 条结果")
        return sorted_results

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        重排序
        :param query: 查询文本
        :param documents: 待排序文档列表
        :param top_k: 返回结果数量
        :return: 重排序后的结果列表
        """
        try:
            # 准备输入数据
            pairs = [[query, doc] for doc in documents]
            
            # 模型推理
            with torch.no_grad():
                inputs = self.rerank_tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    return_tensors='pt',
                    max_length=512
                ).to(self.device)
                
                scores = self.rerank_model(**inputs).logits.view(-1).float().cpu().numpy()
            
            # 组合结果并排序
            scored_docs = list(zip(documents, scores))
            sorted_results = sorted(scored_docs, key=lambda x: x[1], reverse=True)[:top_k]
            logging.info(f"📊 重排序完成：处理 {len(documents)} 条文档")
            return sorted_results
        except Exception as e:
            logging.error(f"❌ 重排序失败: {str(e)}")
            return []

# ---------------------------- 测试代码 ----------------------------
if __name__ == "__main__":
    # 测试配置
    test_query = "什么是机器学习？"
    vector_db_path = "./data/vector_db"  # 需提前构建好的向量库路径
    
    # 初始化检索器
    retriever = RAGRetriever(
        vector_db_path=vector_db_path,
        embedding_model_path="./model/embeddingmodel",
        rerank_model_name="BAAI/bge-reranker-base",
        device="cpu"
    )
    
    # 多路召回测试
    print("\n=== 多路召回测试 ===")
    multi_results = retriever.multi_retrieval(test_query, top_k=3)
    for method in multi_results:
        print(f"\n{method.upper()}结果：")
        for doc, score in multi_results[method][:2]:  # 展示前2个结果
            print(f"[{score:.2f}] {doc[:60]}...")
    
    # 混合检索测试
    print("\n=== 混合检索测试 ===")
    fused_results = retriever.hybrid_search(multi_results)
    for doc, score in fused_results[:3]:
        print(f"[{score:.4f}] {doc[:60]}...")
    
    # 重排序测试
    print("\n=== 重排序测试 ===")
    candidate_docs = [doc for doc, _ in fused_results[:6]]  # 取前6个候选文档
    reranked_results = retriever.rerank(test_query, candidate_docs)
    for doc, score in reranked_results:
        print(f"[{score:.2f}] {doc[:60]}...")