import os
from dotenv import load_dotenv

print("Loading .env file...")
load_dotenv()

print("\nEnvironment variables after loading:")
print(f"API_URL = {os.getenv('API_URL')}")
print(f"SILICONFLOW_API_KEY = {os.getenv('SILICONFLOW_API_KEY')}")
print(f"MODEL_NAME = {os.getenv('MODEL_NAME')}")

# 检查是否有奇怪的变量被加载
print("\nChecking for unexpected variables:")
for key, value in os.environ.items():
    if "filepath" in key.lower() or "silicon" in key.lower() or "api" in key.lower() or "model" in key.lower():
        print(f"{key} = {value}")
