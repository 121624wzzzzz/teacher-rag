import pytest
import requests
import json
from uuid import uuid4
from time import time

# 测试配置
BASE_URL = "http://gpu.rbdjob.com:54055"  # 根据你的实际服务地址修改
TEST_ERROR_DESCRIPTION = "我在解二次方程时总是忘记考虑判别式的情况，导致答案不完整"

@pytest.fixture(scope="module")
def test_user_id():
    """生成测试用户ID"""
    return f"test_user_{uuid4().hex[:8]}"

def test_health_check():
    """测试健康检查接口"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_full_analysis_sync(test_user_id):
    """测试同步分析接口"""
    request_id = f"req_{uuid4().hex[:8]}"
    
    payload = {
        "error_description": TEST_ERROR_DESCRIPTION,
        "user_id": test_user_id,
        "request_id": request_id
    }
    
    start_time = time()
    response = requests.post(
        f"{BASE_URL}/full-analysis/",
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["request_id"] == request_id
    assert data["user_id"] == test_user_id
    assert data["status"] == "completed"
    assert data["processing_time_ms"] > 0
    assert len(data["content"]) > 0
    
    print(f"\n同步分析完成 (耗时: {data['processing_time_ms']}ms)")
    print(f"响应长度: {len(data['content'])} 字符")

def test_user_status(test_user_id):
    """测试用户状态接口"""
    # 先确保有用户活动记录
    requests.post(
        f"{BASE_URL}/full-analysis/",
        json={
            "error_description": TEST_ERROR_DESCRIPTION,
            "user_id": test_user_id
        }
    )
    
    response = requests.get(f"{BASE_URL}/users/{test_user_id}/status")
    assert response.status_code == 200
    data = response.json()
    
    assert data["user_id"] == test_user_id
    assert data["request_count"] > 0
    assert data["status"] == "idle"  # 因为请求已完成

def test_invalid_input():
    """测试无效输入"""
    response = requests.post(
        f"{BASE_URL}/v1/analyze",
        json={"error_description": ""}
    )
    assert response.status_code == 400