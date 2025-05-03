from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging
from maindouble import LearningAssistantSystem
import asyncio

app = FastAPI(
    title="学习助手流式API",
    description="提供错题分析和题目推荐功能的流式API服务",
    version="1.0.0"
)

# 设置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化助手系统
system = LearningAssistantSystem()

class FullAnalysisRequest(BaseModel):
    error_description: str

async def generate_stream(error_description: str):
    """生成流式响应的生成器函数"""
    try:
        generator = system.full_analysis_pipeline(error_description)
        for chunk in generator:
            # 确保chunk是字符串
            chunk_str = str(chunk)
            # 使用SSE格式
            yield f"data: {chunk_str}\n\n"
            await asyncio.sleep(0.01)  # 避免阻塞
    except Exception as e:
        logging.error(f"流式分析失败: {str(e)}")
        yield "data: 抱歉，分析过程中出现错误\n\n"

@app.post("/stream-full-analysis/")
async def stream_full_analysis(request: FullAnalysisRequest):
    """
    完整分析流程流式接口（错题分析+题目推荐）
    
    参数:
    - error_description: 学生的错题描述
    
    返回:
    - Server-Sent Events (SSE) 流式响应
    """
    return StreamingResponse(
        generate_stream(request.error_description),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)