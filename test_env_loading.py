from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件
api_url = os.getenv("API_URL")
print(api_url)  # 检查输出是否为 "https://api.siliconflow.cn/v1/chat/completions"