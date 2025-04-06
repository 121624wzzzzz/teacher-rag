
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 3. 导入嵌入模块
from langchain_huggingface import HuggingFaceEmbeddings

# 4. 初始化嵌入模型（这里展示多个模型选择示例）
model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 推荐多语言模型

# 创建嵌入实例
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs={'device': 'cpu'},  # 使用CPU，如有GPU可改为 'cuda'
    encode_kwargs={'normalize_embeddings': False}
)

# 5. 生成嵌入测试
texts = [
    "Hello, world!", 
    "机器学习很有趣。",
    "The quick brown fox jumps over the lazy dog."
]

try:
    # 生成嵌入向量
    embedded_data = embeddings.embed_documents(texts)
    
    # 打印结果
    print(f"成功生成 {len(embedded_data)} 个嵌入向量")
    print(f"第一个文本的嵌入维度：{len(embedded_data[0])}")
    print("样例嵌入（前5个维度）:", embedded_data[0][:5])
    
except Exception as e:
    print(f"发生错误：{str(e)}")
    print("请检查：")
    print("1. 网络连接是否正常")
    print("2. 模型名称是否正确（访问 https://hf-mirror.com/models 验证）")
    print("3. 是否已安装sentence-transformers库")