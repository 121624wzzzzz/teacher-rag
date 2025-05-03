from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import traceback
import uuid
import json
import socket
from contextlib import asynccontextmanager, closing
from typing import Dict, Optional, List, Union, Any
from maindouble import LearningAssistantSystem
import uvicorn
import asyncio
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 并发控制设置
MAX_CONCURRENT_REQUESTS = 100  # 最大并发请求数
REQUEST_TIMEOUT = 300  # 请求超时时间(秒)

# 应用程序生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期"""
    logger.info("🚀 学习助手API服务启动中...")
    try:
        # 初始化系统
        app.state.system = LearningAssistantSystem()
        # 初始化并发控制
        app.state.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        # 初始化请求锁
        app.state.request_locks = defaultdict(asyncio.Lock)
        logger.info("✅ 学习助手系统初始化成功")
        yield
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {str(e)}")
        raise
    finally:
        logger.info("🛑 学习助手API服务关闭")

# 创建FastAPI应用
app = FastAPI(
    title="智能学习助手API",
    description="提供完整的错题分析和学习建议生成服务",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class AnalysisRequest(BaseModel):
    error_description: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None

class AnalysisResponse(BaseModel):
    """分析结果响应模型"""
    content: str
    request_id: str
    user_id: str
    status: str = "completed"
    processing_time_ms: Optional[int] = None

# 用户会话存储 - 使用线程安全的数据结构
user_sessions: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "current_analysis": None,
    "request_count": 0,
    "lock": asyncio.Lock()
})

# 工具函数
def generate_id(prefix: str = "") -> str:
    """生成带前缀的唯一ID"""
    return f"{prefix}{uuid.uuid4().hex}"

def check_port(port: int, host: str = "0.0.0.0") -> bool:
    """检查端口是否可用"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        try:
            result = sock.connect_ex((host, port))
            return result != 0  # 返回True表示端口可用，False表示端口被占用
        except socket.error as e:
            logger.error(f"检查端口时出错: {e}")
            return False

def find_available_port(base_port: int = 8000, max_tries: int = 10) -> int:
    """自动寻找可用端口"""
    logger.info(f"正在查找可用端口，从 {base_port} 开始，尝试 {max_tries} 次")
    for attempt in range(max_tries):
        port = base_port + attempt
        if check_port(port):
            logger.info(f"找到可用端口: {port}")
            return port
        else:
            logger.warning(f"端口 {port} 已被占用，尝试下一个")
    
    logger.error(f"没有找到可用端口 (尝试范围: {base_port}-{base_port + max_tries - 1})")
    raise OSError(f"没有可用的端口 (尝试范围: {base_port}-{base_port + max_tries - 1})")

# 核心API
@app.post("/v1/analyze", response_class=StreamingResponse)
async def full_analysis_stream(request: AnalysisRequest):
    """
    完整分析流程接口 (流式+完整返回)
    """
    logger.info(f"收到流式分析请求: {request.dict()}")
    # 请求标识处理
    request_id = request.request_id or generate_id("req_")
    user_id = request.user_id or generate_id("user_")
    
    # 验证输入
    if not request.error_description.strip():
        raise HTTPException(status_code=400, detail="错题描述不能为空")
    
    # 获取用户会话锁
    user_lock = user_sessions[user_id]["lock"]
    
    async with app.state.semaphore, user_lock:
        try:
            # 更新用户会话状态
            async with user_lock:
                user_sessions[user_id]["current_analysis"] = request.error_description[:100] + "..."
                user_sessions[user_id]["request_count"] += 1
            
            logger.info(f"📩 收到分析请求 [user={user_id}, req={request_id}]")

            async def analysis_generator():
                """分析结果生成器"""
                full_response = ""
                try:
                    # 初始元数据
                    yield json.dumps({
                        "meta": {
                            "request_id": request_id,
                            "user_id": user_id,
                            "status": "started",
                            "phase": "initializing"
                        }
                    }) + "\n"
                    
                    # 执行分析流程
                    for chunk in app.state.system.full_analysis_pipeline(request.error_description):
                        full_response += chunk
                        yield json.dumps({
                            "data": chunk,
                            "meta": {
                                "status": "streaming",
                                "bytes_received": len(full_response)
                            }
                        }) + "\n"
                    
                    # 最终完整结果
                    yield json.dumps({
                        "data": full_response,
                        "meta": {
                            "status": "completed",
                            "bytes_total": len(full_response),
                            "analysis_complete": True
                        }
                    }) + "\n"
                    
                    logger.info(f"✅ 分析完成 [user={user_id}, req={request_id}, bytes={len(full_response)}]")
                    
                except Exception as e:
                    logger.error(f"❌ 分析失败 [user={user_id}, req={request_id}]: {str(e)}")
                    logger.error(traceback.format_exc())
                    yield json.dumps({
                        "error": {
                            "code": 500,
                            "message": "分析过程中发生错误",
                            "details": str(e)
                        },
                        "meta": {
                            "request_id": request_id,
                            "status": "error"
                        }
                    }) + "\n"
                finally:
                    # 更新用户会话状态
                    async with user_lock:
                        user_sessions[user_id]["current_analysis"] = None

            return StreamingResponse(
                analysis_generator(),
                media_type="application/x-ndjson",
                headers={
                    "X-Request-ID": request_id,
                    "X-User-ID": user_id,
                    "Cache-Control": "no-cache"
                }
            )
            
        except asyncio.TimeoutError:
            logger.error(f"⏱️ 请求超时 [user={user_id}, req={request_id}]")
            raise HTTPException(status_code=504, detail="请求处理超时")
        except Exception as e:
            logger.error(f"❌ 请求处理错误 [user={user_id}, req={request_id}]: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/full-analysis/", response_model=AnalysisResponse) 
async def full_analysis_sync(request: AnalysisRequest):
    """
    完整分析流程接口 (仅返回最终结果)
    """
    logger.info(f"收到同步分析请求: {request.dict()}")
    # 请求标识处理
    request_id = request.request_id or generate_id("req_")
    user_id = request.user_id or generate_id("user_")
    
    # 验证输入
    if not request.error_description.strip():
        raise HTTPException(status_code=400, detail="错题描述不能为空")
    
    # 获取用户会话锁
    user_lock = user_sessions[user_id]["lock"]
    
    async with app.state.semaphore, user_lock:
        try:
            # 更新用户会话状态
            async with user_lock:
                user_sessions[user_id]["current_analysis"] = request.error_description[:100] + "..."
                user_sessions[user_id]["request_count"] += 1
            
            logger.info(f"📩 收到同步分析请求 [user={user_id}, req={request_id}]")

            # 执行分析流程并收集完整结果
            import time
            start_time = time.time()
            
            full_response = ""
            for chunk in app.state.system.full_analysis_pipeline(request.error_description):
                full_response += chunk
                
            processing_time = int((time.time() - start_time) * 1000)  # 转换为毫秒
            
            logger.info(f"✅ 同步分析完成 [user={user_id}, req={request_id}, bytes={len(full_response)}, time={processing_time}ms]")
            
            return AnalysisResponse(
                content=full_response,
                request_id=request_id,
                user_id=user_id,
                status="completed",
                processing_time_ms=processing_time
            )
                
        except asyncio.TimeoutError:
            logger.error(f"⏱️ 同步请求超时 [user={user_id}, req={request_id}]")
            raise HTTPException(status_code=504, detail="请求处理超时")
        except Exception as e:
            logger.error(f"❌ 同步分析失败 [user={user_id}, req={request_id}]: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "分析过程中发生错误",
                    "details": str(e),
                    "request_id": request_id
                }
            )
        finally:
            # 更新用户会话状态
            async with user_lock:
                user_sessions[user_id]["current_analysis"] = None

# 辅助API
@app.get("/health")
async def health_check():
    """服务健康检查"""
    logger.info("收到健康检查请求")
    result = {
        "status": "healthy",
        "version": app.version,
        "system": "available" if hasattr(app.state, "system") else "unavailable",
        "concurrent_requests": MAX_CONCURRENT_REQUESTS - app.state.semaphore._value if hasattr(app.state, "semaphore") else 0,
        "max_concurrent_requests": MAX_CONCURRENT_REQUESTS
    }
    logger.info(f"健康检查返回: {result}")
    return result

@app.get("/users/{user_id}/status")
async def get_user_status(user_id: str):
    """获取用户状态"""
    if user_id in user_sessions:
        async with user_sessions[user_id]["lock"]:
            return {
                "user_id": user_id,
                "status": "active" if user_sessions[user_id]["current_analysis"] else "idle",
                "request_count": user_sessions[user_id]["request_count"],
                "current_analysis": user_sessions[user_id]["current_analysis"]
            }
    raise HTTPException(status_code=404, detail="用户未找到")

if __name__ == "__main__":
    try:
        port = find_available_port(8000)
        logger.info(f"🌐 服务器将在 0.0.0.0:{port} 启动")
        
        # 使用模块导入字符串形式
        uvicorn.run(
            "fastsever4:app",  # 改为模块名:应用变量名
            host="0.0.0.0", 
            port=port,
            workers=4,
            limit_concurrency=MAX_CONCURRENT_REQUESTS,
            timeout_keep_alive=REQUEST_TIMEOUT,
            log_level="info",  # 确保日志级别设置为info
            reload=True  # 如果需要热重载可以添加这个
        )
    except Exception as e:
        logger.critical(f"💥 服务器启动失败: {str(e)}")
        raise