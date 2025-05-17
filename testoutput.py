import requests
import threading
import time
import json
from uuid import uuid4

# 配置
BASE_URL = "http://gpu.rbdjob.com:54055"  # 替换为实际地址
TEST_ERROR_DESCRIPTIONS = [
    "二次方程问题：忘记考虑判别式",
    "几何问题：辅助线构造错误"
]

def send_request(description, user_id, request_id, delay=0):
    """发送分析请求（可设置延迟）"""
    if delay > 0:
        time.sleep(delay)
    
    payload = {
        "error_description": description,
        "user_id": user_id,
        "request_id": request_id
    }
    
    print(f"\n[线程 {threading.current_thread().name}] 发送请求 {request_id}")
    print(f"时间: {time.strftime('%H:%M:%S')}")
    print("请求载荷:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(
            f"{BASE_URL}/full-analysis/",
            json=payload,
            timeout=300
        )
        
        print(f"\n[线程 {threading.current_thread().name}] 响应状态码: {response.status_code}")
        if response.status_code == 200:
            print("响应摘要:", response.text[:10000] + "...")
        else:
            print("错误响应:", response.text[:200])
            
    except Exception as e:
        print(f"请求失败: {str(e)}")

if __name__ == "__main__":
    print(f"=== 开始并发测试 ===")
    print(f"目标服务: {BASE_URL}\n")
    
    # 创建两个线程（请求1立即发送，请求2延迟15秒）
    t1 = threading.Thread(
        target=send_request,
        args=(TEST_ERROR_DESCRIPTIONS[0], f"user_{uuid4().hex[:8]}", f"req_{uuid4().hex[:8]}", 0)
    )
    
    t2 = threading.Thread(
        target=send_request,
        args=(TEST_ERROR_DESCRIPTIONS[1], f"user_{uuid4().hex[:8]}", f"req_{uuid4().hex[:8]}", 15)
    )
    
    # 启动线程
    t1.start()
    t2.start()
    
    # 等待完成
    t1.join()
    t2.join()
    
    print("\n=== 测试完成 ===")