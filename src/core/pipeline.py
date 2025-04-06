import logging
import os
from . import document_processor as dp
from . import chunk_processor as cp
from . import vector_db as vp

logger = logging.getLogger(__name__)

class DocumentPipeline:
    """文档处理全流程封装"""
    
    def __init__(self, embedding_model_path="./model/embeddingmodel", device="cpu"):
        self.embedding_model_path = embedding_model_path
        self.device = device
    
    def save_chunks(self, chunks, output_dir):
        """保存分块结果到指定目录"""
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"创建目录: {output_dir}")
            
            for idx, chunk in enumerate(chunks, start=1):
                chunk_file = os.path.join(output_dir, f"chunk_{idx}.txt")
                with open(chunk_file, "w", encoding="utf-8") as f:
                    f.write(chunk)
                logger.debug(f"分块 {idx} 已保存到 {chunk_file}")
            
            logger.info(f"成功保存 {len(chunks)} 个分块到目录: {output_dir}")
            return True
        except Exception as e:
            logger.error(f"保存分块失败: {e}")
            raise
    
    def process(self, input_dir, cleaned_output_dir, chunks_output_dir, vector_db_output_dir):
        """执行完整文档处理流程"""
        try:
            # 1. 加载文档
            logger.info("开始加载文档...")
            documents = dp.load_documents(input_dir)
            
            # 2. 清洗文档
            logger.info("开始清洗文档...")
            cleaned_docs = dp.clean_documents(documents)
            
            # 3. 保存清洗后的文档
            logger.info("保存清洗后的文档...")
            dp.save_cleaned_documents(cleaned_docs, cleaned_output_dir)
            
            # 4. 读取合并后的清洗文本
            cleaned_file_path = os.path.join(cleaned_output_dir, "cleaned_output.txt")
            with open(cleaned_file_path, "r", encoding="utf-8") as f:
                combined_text = f.read()
            
            # 5. 分块处理
            logger.info("开始分块处理...")
            splitter = cp.OptimizedHybridSplitter()
            chunks = splitter.split_text(combined_text)
            logger.info(f"生成 {len(chunks)} 个分块")
            
            # 6. 保存分块结果
            logger.info("保存分块结果...")
            self.save_chunks(chunks, chunks_output_dir)
            
            # 7. 读取所有分块文件内容
            chunks_list = []
            for chunk_file in os.listdir(chunks_output_dir):
                if chunk_file.endswith(".txt"):
                    file_path = os.path.join(chunks_output_dir, chunk_file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        chunks_list.append(f.read())
            
            if not chunks_list:
                logger.error("没有分块内容可用于构建向量数据库")
                return False
            
            # 8. 构建向量数据库
            vdb = vp.VectorDB(
                model_path=self.embedding_model_path,
                device=self.device,
                db_path=vector_db_output_dir
            )
            
            if vdb.process_chunks(chunks_list):
                vdb.save_index()
                logger.info("✅ 向量数据库构建完成！")
                return True
            else:
                logger.error("❌ 向量数据库构建失败")
                return False
                
        except Exception as e:
            logger.error(f"文档处理流程出错: {e}")
            raise