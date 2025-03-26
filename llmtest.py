import requests

# 配置信息 → 替换为你的真实API密钥
API_KEY = "sk-hhvdtdrjucpieeklquumgwihnzohplwcndcpfyqtfujznowo"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V3"  # 确认模型名称正确

def simple_chat():
    history = []
    
    while True:
        # 用户输入
        user_input = input("\n你的问题（输入exit退出）: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # 构造请求
        history.append({"role": "user", "content": user_input})
        
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": history,
                "temperature": 0.7
            },
            timeout=300  # 10秒超时
        )
        
        # 处理响应
        if response.status_code == 200:
            reply = response.json()['choices'][0]['message']['content']
            print("\nAI回复:", reply)
            history.append({"role": "assistant", "content": reply})
        else:
            print(f"请求失败 (状态码 {response.status_code}): {response.text}")

if __name__ == "__main__":
    simple_chat()