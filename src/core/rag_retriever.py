import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 设置镜像源

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from pathlib import Path
from huggingface_hub import snapshot_download

# 第三方库
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

class RAGRetriever:
    """RAG检索器（支持完整RAG流程：多路召回+混合检索+重排序）"""
    
    def __init__(
        self,
        vector_db_path: str,
        embedding_model_path: str = "./model/embeddingmodel",
        rerank_model_name: str = "./model/reranker",
        device: str = "cpu",
        download_mirror: Optional[str] = None
    ):
        """
        初始化检索器
        :param vector_db_path: 向量数据库路径
        :param embedding_model_path: 本地嵌入模型路径
        :param rerank_model_name: 重排序模型名称或路径
        :param device: 计算设备
        :param download_mirror: 模型下载镜像地址
        """
        self.device = device
        self.download_mirror = download_mirror
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
        """加载重排序模型（自动下载如果不存在）"""
        try:
            # 检查是否为本地路径
            model_path = Path(model_name)
            if not model_path.exists():
                self._download_rerank_model(model_name)
            
            self.rerank_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.rerank_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.rerank_model.to(self.device)
            logging.info(f"✅ 重排序模型加载成功: {model_name}")
        except Exception as e:
            logging.error(f"❌ 重排序模型加载失败: {str(e)}")
            raise
    
    def _download_rerank_model(self, model_name: str):
        """下载重排序模型"""
        try:
            logging.info("开始下载重排序模型...")
            
            # 设置镜像环境变量(如果提供)
            if self.download_mirror:
                os.environ['HF_ENDPOINT'] = self.download_mirror
            
            # 确保模型目录存在
            model_dir = Path(model_name).parent
            model_dir.mkdir(parents=True, exist_ok=True)
            
            snapshot_download(
                repo_id=model_name,
                local_dir=str(model_dir),
                resume_download=True
            )
            logging.info(f"✅ 重排序模型下载完成: {model_name}")
        except Exception as e:
            logging.error(f"❌ 模型下载失败: {str(e)}")
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
    
    def full_retrieval(self, query: str, 
                       retrieval_top_k: int = 10,
                       rerank_top_k: int = 5,
                       weights: Dict[str, float] = None) -> Dict:
        """
        完整RAG检索流程（多路召回→混合检索→重排序）
        :param query: 查询文本
        :param retrieval_top_k: 每路召回数量
        :param rerank_top_k: 重排序返回数量
        :param weights: 混合检索权重
        :return: 包含各阶段结果的字典
        """
        try:
            result = {}
            
            # 1. 多路召回
            multi_results = self.multi_retrieval(query, top_k=retrieval_top_k)
            result["multi_retrieval"] = multi_results
            
            # 2. 混合检索
            fused_results = self.hybrid_search(multi_results, weights=weights)
            result["hybrid_search"] = fused_results
            
            # 3. 重排序
            candidate_docs = [doc for doc, _ in fused_results[:rerank_top_k*2]]  # 取更多候选文档
            reranked = self.rerank(query, candidate_docs, top_k=rerank_top_k)
            result["reranked"] = reranked
            
            return {
                "status": "success",
                "query": query,
                "results": result
            }
        except Exception as e:
            logging.error(f"❌ 完整检索流程失败: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

# ---------------------------- 测试代码 ----------------------------
if __name__ == "__main__":
    # 测试配置
    test_query = "什么是概率论与数理统计？"
    vector_db_path = "./data/vector_db"  # 需提前构建好的向量库路径
    
    # 初始化检索器
    retriever = RAGRetriever(
        vector_db_path=vector_db_path,
        embedding_model_path="./model/embeddingmodel",
        rerank_model_name="./model/reranker",
        device="cpu",
        download_mirror="https://hf-mirror.com"
    )
    
    # 测试完整流程
    print("\n=== 完整RAG流程测试 ===")
    full_result = retriever.full_retrieval(test_query)
    
    if full_result["status"] == "success":
        # 打印多路召回结果
        print("\n[多路召回结果]")
        for method in full_result["results"]["multi_retrieval"]:
            print(f"\n{method.upper()}结果：")
            for doc, score in full_result["results"]["multi_retrieval"][method][:2]:
                print(f"[{score:.2f}] {doc[:60]}...")
        
        # 打印混合检索结果
        print("\n[混合检索结果]")
        for doc, score in full_result["results"]["hybrid_search"][:3]:
            print(f"[{score:.4f}] {doc[:60]}...")
        
        # 打印重排序结果
        print("\n[重排序结果]")
        for doc, score in full_result["results"]["reranked"]:
            print(f"[{score:.2f}] {doc[:60]}...")
    else:
        print(f"❌ 检索失败: {full_result['message']}")