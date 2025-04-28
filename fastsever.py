from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from maindouble import LearningAssistantSystem, ErrorAnalysisAssistant, ExerciseRecommendationAssistant
from mainpptnew import generate_ppt_from_topic
import os
import logging
from typing import Optional
import uuid
import asyncio

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化助手系统
try:
    system = LearningAssistantSystem()
    error_analyzer = ErrorAnalysisAssistant()
    exercise_recommender = ExerciseRecommendationAssistant()
except Exception as e:
    logger.error(f"初始化助手系统失败: {e}")
    raise

app = FastAPI(
    title="学习助手系统API",
    description="这是一个专业的错题分析和题目推荐系统API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保输出目录存在
os.makedirs("data/ppt/pptresults", exist_ok=True)

async def stream_generator(generator):
    """将生成器转换为异步流"""
    try:
        for chunk in generator:
            yield f"data: {chunk}\n\n"
            await asyncio.sleep(0.01)  # 添加小延迟避免客户端过载
    except Exception as e:
        logger.error(f"流生成出错: {e}")
        yield f"data: 处理过程中出错: {str(e)}\n\n"

@app.post("/api/analyze-error/")
async def analyze_error(error_description: str = Form(...)):
    """错题分析API端点"""
    if not error_description.strip():
        raise HTTPException(status_code=400, detail="请输入有效的错题描述")
    
    try:
        generator = error_analyzer.analyze_error(error_description)
        return StreamingResponse(
            stream_generator(generator),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"错题分析出错: {e}")
        raise HTTPException(status_code=500, detail=f"错题分析时出错: {str(e)}")

@app.post("/api/recommend-exercises/")
async def recommend_exercises(
    error_analysis: Optional[str] = Form(None),
    knowledge_points: Optional[str] = Form(None)
):
    """题目推荐API端点"""
    if not (error_analysis or knowledge_points):
        raise HTTPException(status_code=400, detail="请至少提供知识点描述或错题分析结果")
    
    try:
        generator = exercise_recommender.recommend_exercises(error_analysis, knowledge_points)
        return StreamingResponse(
            stream_generator(generator),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"题目推荐出错: {e}")
        raise HTTPException(status_code=500, detail=f"题目推荐时出错: {str(e)}")

@app.post("/api/full-analysis/")
async def full_analysis(error_description: str = Form(...)):
    """完整分析流程API端点"""
    if not error_description.strip():
        raise HTTPException(status_code=400, detail="请输入有效的错题描述")
    
    try:
        generator = system.full_analysis_pipeline(error_description)
        return StreamingResponse(
            stream_generator(generator),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"完整分析出错: {e}")
        raise HTTPException(status_code=500, detail=f"完整分析时出错: {str(e)}")

@app.post("/api/generate-ppt/")
async def generate_ppt(
    topic: str = Form(...),
    transparency: float = Form(0.95),
    bg_image: Optional[UploadFile] = File(None)
):
    """PPT生成API端点"""
    if not topic.strip():
        raise HTTPException(status_code=400, detail="请输入PPT主题内容")
    
    try:
        # 处理背景图片
        bg_image_path = None
        if bg_image:
            # 保存上传的图片
            file_ext = os.path.splitext(bg_image.filename)[1]
            bg_image_path = f"data/ppt/temp_bg_{uuid.uuid4()}{file_ext}"
            with open(bg_image_path, "wb") as buffer:
                buffer.write(bg_image.file.read())
        else:
            bg_image_path = "assets/qh.jpg"
            if not os.path.exists(bg_image_path):
                logger.warning(f"默认背景图片不存在: {bg_image_path}")
                bg_image_path = None
        
        # 生成PPT
        ppt_path = generate_ppt_from_topic(
            topic=topic,
            bg_image=bg_image_path,
            bg_transparency=transparency,
            output_dir="data/ppt/pptresults"
        )
        
        # 清理临时背景图片
        if bg_image and bg_image_path and os.path.exists(bg_image_path):
            os.remove(bg_image_path)
        
        if not os.path.exists(ppt_path):
            raise HTTPException(status_code=500, detail="PPT生成失败，文件未创建")
            
        return FileResponse(
            ppt_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=os.path.basename(ppt_path)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成PPT时出错: {e}")
        raise HTTPException(status_code=500, detail=f"生成PPT时出错: {str(e)}")

@app.get("/")
async def root():
    """根端点，提供API文档链接"""
    return {
        "message": "欢迎使用学习助手系统API",
        "documentation": "/docs",
        "endpoints": {
            "/api/analyze-error/": "错题分析",
            "/api/recommend-exercises/": "题目推荐",
            "/api/full-analysis/": "完整分析流程",
            "/api/generate-ppt/": "PPT生成"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)