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
from typing import Dict, Optional, List, Union
from maindouble import LearningAssistantSystem
import uvicorn
import asyncio
from concurrent.futures import ProcessPoolExecutor
import os
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 全局进程池
process_pool = ProcessPoolExecutor()

# 应用程序生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期"""
    logger.info("🚀 学习助手API服务启动中...")
    try:
        # 初始化系统
        app.state.system = LearningAssistantSystem()
        logger.info("✅ 学习助手系统初始化成功")
        yield
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {str(e)}")
        raise
    finally:
        logger.info("🛑 学习助手API服务关闭")
        process_pool.shutdown(wait=True)

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

# 用户会话存储
user_sessions: Dict[str, dict] = {}

# 工具函数
def generate_id(prefix: str = "") -> str:
    """生成带前缀的唯一ID"""
    return f"{prefix}{uuid.uuid4().hex}"

def check_port(port: int, host: str = "0.0.0.0") -> bool:
    """检查端口是否可用"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) != 0

def find_available_port(base_port: int = 8000, max_tries: int = 10) -> int:
    """自动寻找可用端口"""
    for port in range(base_port, base_port + max_tries):
        if check_port(port):
            return port
    raise OSError(f"没有可用的端口 (尝试范围: {base_port}-{base_port + max_tries - 1})")

def run_analysis_pipeline(system: LearningAssistantSystem, error_description: str):
    """包装同步的pipeline函数，用于进程池执行"""
    return list(system.full_analysis_pipeline(error_description))

# 核心API
@app.post("/v1/analyze", response_class=StreamingResponse)
async def full_analysis_stream(request: AnalysisRequest):
    """
    完整分析流程接口 (流式+完整返回)
    使用进程池并行处理CPU密集型任务
    """
    # 请求标识处理
    request_id = request.request_id or generate_id("req_")
    user_id = request.user_id or generate_id("user_")
    
    # 验证输入
    if not request.error_description.strip():
        raise HTTPException(status_code=400, detail="错题描述不能为空")
    
    # 初始化用户会话
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_analysis": request.error_description[:100] + "...",
            "request_count": 0
        }
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
            
            # 将CPU密集型任务放入进程池执行
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                process_pool,
                run_analysis_pipeline,
                app.state.system,
                request.error_description
            )
            
            # 流式返回结果
            for chunk in chunks:
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

@app.post("/full-analysis/", response_model=AnalysisResponse) 
async def full_analysis_sync(request: AnalysisRequest):
    """
    完整分析流程接口 (仅返回最终结果)
    使用进程池并行处理CPU密集型任务
    """
    # 请求标识处理
    request_id = request.request_id or generate_id("req_")
    user_id = request.user_id or generate_id("user_")
    
    # 验证输入
    if not request.error_description.strip():
        raise HTTPException(status_code=400, detail="错题描述不能为空")
    
    # 初始化用户会话
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "current_analysis": request.error_description[:100] + "...",
            "request_count": 0
        }
    user_sessions[user_id]["request_count"] += 1
    
    logger.info(f"📩 收到同步分析请求 [user={user_id}, req={request_id}]")

    try:
        # 执行分析流程并收集完整结果
        import time
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(
            process_pool,
            run_analysis_pipeline,
            app.state.system,
            request.error_description
        )
        
        full_response = "".join(chunks)
        processing_time = int((time.time() - start_time) * 1000)  # 转换为毫秒
        
        logger.info(f"✅ 同步分析完成 [user={user_id}, req={request_id}, bytes={len(full_response)}, time={processing_time}ms]")
        
        return AnalysisResponse(
            content=full_response,
            request_id=request_id,
            user_id=user_id,
            status="completed",
            processing_time_ms=processing_time
        )
            
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
        user_sessions[user_id]["current_analysis"] = None

# 辅助API
@app.get("/health")
async def health_check():
    """服务健康检查"""
    return {
        "status": "healthy",
        "version": app.version,
        "system": "available" if hasattr(app.state, "system") else "unavailable",
        "process_pool": "running" if not process_pool._shutdown else "shutdown"
    }

@app.get("/users/{user_id}/status")
async def get_user_status(user_id: str):
    """获取用户状态"""
    if user_id in user_sessions:
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
        logger.info(f"🌐 启动服务器 0.0.0.0:{port}")
        
        # 使用模块导入方式启动
        uvicorn.run(
            "teachersever:app",  # 模块名:应用变量名
            host="0.0.0.0", 
            port=port,
            workers=4,
            reload=False,  # 生产环境设为False
            loop="asyncio",
            timeout_keep_alive=60
        )
    except Exception as e:
        logger.critical(f"💥 服务器启动失败: {str(e)}")
        raise