from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import traceback
from maindouble import LearningAssistantSystem
import uuid
from typing import Dict, Callable
from functools import wraps
from contextlib import asynccontextmanager
import socket

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 替换原有的生命周期事件处理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理
    """
    # 启动时执行
    logger.info("学习助手API服务启动")
    yield
    # 关闭时执行
    logger.info("学习助手API服务关闭")

# 使用新的生命周期管理器
app = FastAPI(
    title="学习助手API",
    description="提供错题分析和题目推荐功能的API服务",
    version="1.0.0",
    lifespan=lifespan
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化助手系统和用户会话存储
try:
    system = LearningAssistantSystem()
    logger.info("学习助手系统初始化成功")
except Exception as e:
    logger.error(f"学习助手系统初始化失败: {str(e)}")
    raise

user_sessions: Dict[str, dict] = {}  # 存储用户会话的字典，键为用户ID

class FullAnalysisRequest(BaseModel):
    error_description: str
    user_id: str = None  # 可选字段，如果未提供将自动生成

# 异常处理装饰器
def handle_exceptions(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API错误: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")
    return wrapper

@app.post("/full-analysis/")
@handle_exceptions
async def full_analysis(request: FullAnalysisRequest):
    """
    完整分析流程接口（错题分析+题目推荐）
    
    参数:
    - error_description: 学生的错题描述
    - user_id: (可选) 用户唯一标识符，如果未提供将自动生成
    
    返回:
    - 完整的分析结果
    - 包含用户ID的头部信息（如果是新用户）
    """
    if not request.error_description:
        raise HTTPException(status_code=400, detail="错题描述不能为空")

    # 处理用户ID
    user_id = request.user_id or str(uuid.uuid4())
    logger.info(f"接收到分析请求 - 用户ID: {user_id}")
    
    # 准备响应头
    headers = {}
    
    # 如果是新用户，在响应头中返回用户ID
    if not request.user_id:
        headers["X-User-ID"] = user_id
        logger.info(f"创建新用户ID: {user_id}")
    
    # 将用户ID与当前分析关联
    if user_id not in user_sessions:
        user_sessions[user_id] = {"current_analysis": None}
        logger.info(f"创建新用户会话: {user_id}")
    
    try:
        logger.info(f"开始为用户 {user_id} 分析错题")
        user_sessions[user_id]["current_analysis"] = request.error_description
        
        # 获取完整分析结果
        analysis_result = list(system.full_analysis_pipeline(request.error_description))
        full_result = "".join(str(chunk) for chunk in analysis_result)
        response_data = {
            "user_id": user_id,
            "analysis_result": full_result,
            "status": "completed"
        }
        
        # 从FastAPI返回响应时包含headers
        from fastapi.responses import JSONResponse
        return JSONResponse(content=response_data, headers=headers)
    except Exception as e:
        error_msg = f"分析失败: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # 分析完成后更新用户状态
        if user_id in user_sessions:
            user_sessions[user_id]["current_analysis"] = None
            logger.info(f"用户 {user_id} 的分析已完成")

@app.get("/user/{user_id}/status")
@handle_exceptions
async def get_user_status(user_id: str):
    """
    获取用户当前状态
    
    参数:
    - user_id: 用户唯一标识符
    
    返回:
    - 用户状态信息
    """
    logger.info(f"查询用户状态: {user_id}")
    if user_id in user_sessions:
        return {
            "user_id": user_id,
            "status": "active" if user_sessions[user_id]["current_analysis"] else "idle",
            "current_analysis": user_sessions[user_id]["current_analysis"]
        }
    return {"user_id": user_id, "status": "unknown", "message": "用户未找到"}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    logger.debug("健康检查请求")
    return {"status": "healthy", "service": "learning_assistant_api"}

def find_available_port(start_port, max_attempts=10):
    """查找可用的端口"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                logger.info(f"找到可用端口: {port}")
                return port
            except socket.error:
                logger.warning(f"端口 {port} 已被占用，尝试下一个端口")
    
    # 如果所有尝试的端口都被占用，则使用随机端口
    logger.warning(f"无法找到可用端口，将使用随机端口")
    return 0  # 0表示随机端口

if __name__ == "__main__":
    import uvicorn
    
    # 初始端口
    default_port = 8000
    
    # 查找可用端口
    port = find_available_port(default_port)
    
    logger.info(f"启动服务器 - 监听 0.0.0.0:{port}")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        logger.error(traceback.format_exc())