import requests
import json
import sys

API_KEY = "sk-hhvdtdrjucpieeklquumgwihnzohplwcndcpfyqtfujznowo"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V3"

def generate_dynamic_prompt(history, user_input):
    """调用LLM生成动态系统提示"""
    try:
        # 构造临时对话历史（包含当前用户输入）
        temp_history = history.copy()
        temp_history.append({"role": "user", "content": user_input})
        
        # 将对话历史转换为文本格式
        conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in temp_history])
        
        # 构造生成提示的请求
        prompt = f"""根据以下对话历史和用户的最新问题，生成一个系统提示，用于指导AI助手给出最佳回答。提示应明确回答方向和重点要求。

对话历史：
{conversation}

请生成一个针对最新问题的系统提示："""
        
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 150
            },
            timeout=150
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"\n动态提示生成失败: {str(e)}，使用默认提示")
        return "请提供清晰、详细的解答，并给出具体示例。"

def stream_chat():
    history = []
    
    while True:
        user_input = input("\n你的问题（输入exit退出）: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue

        # 生成动态系统提示
        system_prompt = generate_dynamic_prompt(history, user_input)
        
        # 构造完整的消息列表（系统提示 + 历史记录 + 当前问题）
        request_messages = [{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": user_input}
        ]

        try:
            # 流式请求
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": request_messages,
                    "temperature": 0.7,
                    "stream": True
                },
                stream=True,
                timeout=30
            )
            
            response.raise_for_status()
            
            # 处理流式响应
            print(f"\n系统提示: {system_prompt}")  # 显示生成的系统提示
            print("\nAI回复: ", end="", flush=True)
            full_reply = []
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:]
                        if json_str == "[DONE]":
                            break
                        try:
                            data = json.loads(json_str)
                            if 'content' in data['choices'][0]['delta']:
                                content = data['choices'][0]['delta']['content']
                                print(content, end="", flush=True)
                                full_reply.append(content)
                        except:
                            continue
            
            # 更新对话历史
            if full_reply:
                history.append({"role": "user", "content": user_input})
                history.append({
                    "role": "assistant",
                    "content": "".join(full_reply)
                })
            print("\n" + "-"*50)
            
        except requests.exceptions.RequestException as e:
            print(f"\n请求失败: {str(e)}")
            if history and history[-1]["role"] == "user":
                history.pop()

if __name__ == "__main__":
    try:
        stream_chat()
    except KeyboardInterrupt:
        print("\n对话已终止")
        sys.exit(0)