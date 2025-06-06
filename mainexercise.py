import logging
from src.core.pipeline import DocumentPipeline

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    # 配置路径
    input_dir = "./data/exercise/raw"
    cleaned_output_dir = "./data/exercise/cleaned"
    chunks_output_dir = "./data/exercise/chunks"
    vector_db_output_dir = "./data/exercise/vector_db"
    
    # 创建并执行管道
    pipeline = DocumentPipeline()
    pipeline.process(
        input_dir=input_dir,
        cleaned_output_dir=cleaned_output_dir,
        chunks_output_dir=chunks_output_dir,
        vector_db_output_dir=vector_db_output_dir
    )