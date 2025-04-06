import logging
import os
from llama_index.core import SimpleDirectoryReader
from cleantext import clean

# 设置日志格式
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_documents(directory: str, verbose: bool = False):
    """ 加载指定目录中的文档 """
    try:
        # 读取目录中的所有文档
        documents = SimpleDirectoryReader(directory).load_data()
        
        if not documents:
            raise ValueError("未找到任何文档")
        
        logging.info(f"成功加载 {len(documents)} 个文档")

        # 仅打印第一个文档信息（避免过多日志）
        if verbose and documents:
            doc = documents[0]
            print("\n--- 示例文档信息 ---")
            print(f"元信息: {doc.metadata}")
            print(f"内容（前500字符）: {doc.text[:1000]}...\n")
        
        return documents
    except Exception as e:
        logging.error(f"文档加载失败: {e}")
        raise

def clean_paragraphs(paragraphs):
    cleaned = []
    for text in paragraphs:
        # 清洗步骤：修复Unicode/移除URL/邮箱/处理空格等
        processed = clean(
            text,
            fix_unicode=True,        # 修正乱码字符（如 â€“ → —）
            to_ascii=False,          # 保留非ASCII字符（如中文）
            lower=False,             # 不转为小写
            no_urls=True,            # 移除URL
            no_emails=True,          # 移除邮箱
            no_line_breaks=False,    # 保留换行符
            replace_with_url="",    # URL替换为空白
            replace_with_email=""    # 邮箱替换为空白
        )
        # 额外处理：去除首尾多余空格
        processed = processed.strip()
        cleaned.append(processed)
    return cleaned

def clean_documents(documents):
    """ 清洗文档内容 """
    try:
        cleaned_docs = []
        for doc in documents:
            # 清洗文档内容
            cleaned_text = clean_paragraphs([doc.text])[0]
            # 创建新的文档对象，保留元数据
            cleaned_doc = type(doc)(text=cleaned_text, metadata=doc.metadata)
            cleaned_docs.append(cleaned_doc)
        
        logging.info(f"成功清洗 {len(cleaned_docs)} 个文档")
        return cleaned_docs
    except Exception as e:
        logging.error(f"文档清洗失败: {e}")
        raise

def save_cleaned_documents(cleaned_docs, output_dir: str, output_file: str = "cleaned_output.txt"):
    """ 将所有清洗后的文档内容合并并保存到一个文件中 """
    try:
        # 如果目录不存在，则创建
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"创建目录: {output_dir}")
        
        # 合并所有文档内容
        combined_text = "\n\n".join(doc.text for doc in cleaned_docs)
        
        # 文件保存路径
        file_path = os.path.join(output_dir, output_file)
        
        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(combined_text)
        logging.info(f"保存合并后的文件: {file_path}")
        
        logging.info(f"成功保存 {len(cleaned_docs)} 个清洗后的文档内容")
    except Exception as e:
        logging.error(f"保存清洗后的文档失败: {e}")
        raise