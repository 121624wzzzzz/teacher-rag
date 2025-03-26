import requests
import json
import sys

API_KEY = "sk-hhvdtdrjucpieeklquumgwihnzohplwcndcpfyqtfujznowo"
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL = "deepseek-ai/DeepSeek-V3"

def stream_chat():
    history = []
    
    while True:
        # 用户输入
        user_input = input("\n你的问题（输入exit退出）: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue
            
        # 添加用户消息到历史
        history.append({"role": "user", "content": user_input})
        
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
                    "messages": history,
                    "temperature": 0.7,
                    "stream": True  # 启用流式
                },
                stream=True,  # 保持连接开放
                timeout=30  # 整个流的超时时间
            )
            
            response.raise_for_status()
            
            # 解析流式数据
            print("\nAI回复: ", end="", flush=True)
            full_reply = []
            for chunk in response.iter_lines():
                if chunk:
                    # 解码数据块
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        json_str = chunk_str[6:]  # 去除'data: '前缀
                        if json_str == "[DONE]":
                            break
                            
                        try:
                            data = json.loads(json_str)
                            delta = data['choices'][0]['delta']
                            if 'content' in delta:
                                content = delta['content']
                                print(content, end="", flush=True)
                                full_reply.append(content)
                        except json.JSONDecodeError:
                            print(" [JSON解析错误] ", end="", flush=True)
                        except KeyError:
                            print(" [数据格式异常] ", end="", flush=True)
            
            # 保存完整回复
            if full_reply:
                history.append({
                    "role": "assistant",
                    "content": "".join(full_reply)
                })
            print("\n" + "-"*50)
            
        except requests.exceptions.RequestException as e:
            print(f"\n请求失败: {str(e)}")
            # 移除非成功的对话历史
            if history[-1]["role"] == "user":
                history.pop()

if __name__ == "__main__":
    try:
        stream_chat()
    except KeyboardInterrupt:
        print("\n\n对话已终止")
        sys.exit(0)