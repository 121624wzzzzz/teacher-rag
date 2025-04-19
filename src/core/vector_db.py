
#vector_db.py - 本地文本向量化及索引管理模块
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'  # 优先使用镜像

from pathlib import Path
import logging
from typing import List
import numpy as np

# 第三方库导入
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

class VectorDB:
    """向量数据库管理类"""
    
    def __init__(
        self,
        model_path: str = "./model/embeddingmodel",
        device: str = "cpu",
        db_path: str = "./vector_db",
        chunk_size: int = 32
    ):
        """
        初始化向量数据库
        :param model_path: 本地模型路径
        :param device: 计算设备 (cpu/cuda)
        :param db_path: 向量数据库存储路径
        :param chunk_size: 批处理大小
        """
        self._setup_logging()
        self.model_path = Path(model_path)
        self.db_path = Path(db_path)
        self.chunk_size = chunk_size
        
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=str(self.model_path.absolute()),
                model_kwargs={'device': device},
                encode_kwargs={
                    'batch_size': chunk_size,
                    'normalize_embeddings': False
                }
            )
            self.vector_db = None
            logging.info("✅ 嵌入模型初始化成功")
        except Exception as e:
            logging.error(f"❌ 模型加载失败: {str(e)}")
            raise

    def _setup_logging(self):
        """配置日志格式"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(module)s - %(message)s"
        )

    def process_chunks(self, chunks: List[str]) -> bool:
        """
        处理文本块生成向量索引
        :param chunks: 文本块列表
        :return: 处理结果
        """
        try:
            if not chunks:
                logging.warning("⚠️ 接收到空文本列表")
                return False

            # 创建或更新向量数据库
            self.vector_db = FAISS.from_texts(
                texts=chunks,
                embedding=self.embeddings
            )
            logging.info(f"🎯 成功生成 {len(chunks)} 个向量")
            return True
            
        except Exception as e:
            logging.error(f"❌ 向量生成失败: {str(e)}")
            return False

    def save_index(self) -> bool:
        """保存向量索引到本地"""
        if not self.vector_db:
            logging.error("❌ 请先执行 process_chunks 生成索引")
            return False
            
        try:
            self.db_path.mkdir(parents=True, exist_ok=True)
            self.vector_db.save_local(self.db_path)
            logging.info(f"💾 索引已保存至 {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"❌ 保存失败: {str(e)}")
            return False

    def load_existing_index(self) -> bool:
        """加载已有向量索引"""
        try:
            if not (self.db_path / "index.faiss").exists():
                logging.warning("⚠️ 未找到已有索引")
                return False
                
            self.vector_db = FAISS.load_local(
                folder_path=self.db_path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True  # 允许加载未经验证的文件
            )
            logging.info("🔍 成功加载已有索引")
            return True
        except Exception as e:
            logging.error(f"❌ 索引加载失败: {str(e)}")
            return False

# ---------------------------- 测试代码 ----------------------------
if __name__ == "__main__":
    # 测试配置
    test_chunks = [
        "量子计算利用量子比特实现并行计算",
        "Transformer模型在NLP领域广泛应用",
        "联邦学习保护用户数据隐私",
        "LangChain简化了AI应用开发流程"
    ]

    # 初始化数据库
    try:
        vdb = VectorDB(
            model_path="./model/embeddingmodel",
            device="cpu",
            db_path="./test_vector_db"
        )
        
        # 处理文本生成向量
        if vdb.process_chunks(test_chunks):
            # 保存索引
            if vdb.save_index():
                # 验证向量维度
                sample_vector = vdb.embeddings.embed_query(test_chunks[0])
                print("\n=== 测试结果 ===")
                print(f"向量维度: {len(sample_vector)}")
                print(f"首向量前5维: {np.round(sample_vector[:5], 4)}")
                
                # 验证索引加载
                if vdb.load_existing_index():
                    print(f"索引文档数: {vdb.vector_db.index.ntotal}")
                
    except Exception as e:
        print(f"❗ 测试过程中发生严重错误: {str(e)}")
        print("故障排查建议：检查模型文件是否完整，确保安装所有依赖库")