import logging
import os
from src.core import (
    document_processor as dp,
    chunk_processor as cp,
    vector_db as vp
)
# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def save_chunks(chunks, output_dir):
    """保存分块结果到指定目录，每个分块一个文件"""
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"创建目录: {output_dir}")
        
        # 保存每个分块为单独的文件
        for idx, chunk in enumerate(chunks, start=1):
            chunk_file = os.path.join(output_dir, f"chunk_{idx}.txt")
            with open(chunk_file, "w", encoding="utf-8") as f:
                f.write(chunk)
            logging.debug(f"分块 {idx} 已保存到 {chunk_file}")
        
        logging.info(f"成功保存 {len(chunks)} 个分块到目录: {output_dir}")
    except Exception as e:
        logging.error(f"保存分块失败: {e}")
        raise

def main(input_dir, cleaned_output_dir, chunks_output_dir,vector_db_output_dir):
    """主流程：加载文档 → 清洗 → 分块 → 保存→ 构建向量数据库"""
    try:
        # 加载文档
        logging.info("开始加载文档...")
        documents = dp.load_documents(input_dir)
        
        # 清洗文档
        logging.info("开始清洗文档...")
        cleaned_docs = dp.clean_documents(documents)
        
        # 保存清洗后的文档（合并为一个文件）
        logging.info("保存清洗后的文档...")
        dp.save_cleaned_documents(cleaned_docs, cleaned_output_dir)
        
        # 读取合并后的清洗文本
        cleaned_file_path = os.path.join(cleaned_output_dir, "cleaned_output.txt")
        with open(cleaned_file_path, "r", encoding="utf-8") as f:
            combined_text = f.read()
        
        # 初始化分块器
        splitter = cp.OptimizedHybridSplitter()
        
        # 分块处理
        logging.info("开始分块处理...")
        chunks = splitter.split_text(combined_text)
        logging.info(f"生成 {len(chunks)} 个分块")
        
        # 保存分块结果
        logging.info("保存分块结果...")
        save_chunks(chunks, chunks_output_dir)
        
# 读取所有分块文件内容
        chunks_list = []
        for chunk_file in os.listdir(chunks_output_dir):
            if chunk_file.endswith(".txt"):
                file_path = os.path.join(chunks_output_dir, chunk_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    chunks_list.append(f.read())
        
        if not chunks_list:
            logging.error("没有分块内容可用于构建向量数据库")
            return
        
        # 初始化向量数据库
        vdb = vp.VectorDB(
            model_path="./model/embeddingmodel",  # 确保模型路径正确
            device="cpu",
            db_path=vector_db_output_dir
        )
        
        # 处理分块并保存索引
        if vdb.process_chunks(chunks_list):
            vdb.save_index()
            logging.info("✅ 向量数据库构建完成！")
        else:
            logging.error("❌ 向量数据库构建失败")
    except Exception as e:
        logging.error(f"主流程执行出错: {e}")
        raise

if __name__ == "__main__":
    # 配置路径（根据实际情况修改）
    input_dir = "./data/prompts/raw"         # 原始PDF文档所在目录
    cleaned_output_dir = "./data/prompts/cleaned" # 清洗后文档保存目录
    chunks_output_dir = "./data/prompts/chunks"   # 分块结果保存目录
    vector_db_output_dir = "./data/prompts/vector_db"# 向量数据库保存目录
    main(input_dir, cleaned_output_dir, chunks_output_dir,vector_db_output_dir)