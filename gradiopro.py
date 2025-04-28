import gradio as gr
from maindouble import LearningAssistantSystem, ErrorAnalysisAssistant, ExerciseRecommendationAssistant
from mainpptnew import generate_ppt_from_topic  # 导入PPT生成函数
import os
import logging

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

def analyze_error_interface(error_description):
    """错题分析界面函数（真正的流式输出）"""
    if not error_description.strip():
        yield "请输入有效的错题描述"
        return
        
    full_response = ""
    try:
        for chunk in error_analyzer.analyze_error(error_description):
            full_response += chunk
            yield full_response
    except Exception as e:
        logger.error(f"错题分析出错: {e}")
        yield f"错题分析时出错: {str(e)}"

def recommend_exercises_interface(error_analysis=None, knowledge_points=None):
    """题目推荐界面函数（真正的流式输出）"""
    if not (error_analysis or knowledge_points):
        yield "请至少提供知识点描述或错题分析结果"
        return
        
    full_response = ""
    try:
        for chunk in exercise_recommender.recommend_exercises(error_analysis, knowledge_points):
            full_response += chunk
            yield full_response
    except Exception as e:
        logger.error(f"题目推荐出错: {e}")
        yield f"题目推荐时出错: {str(e)}"

def full_analysis_interface(error_description):
    """完整分析流程界面函数（真正的流式输出）"""
    if not error_description.strip():
        yield "请输入有效的错题描述"
        return
        
    full_response = ""
    try:
        for chunk in system.full_analysis_pipeline(error_description):
            full_response += chunk
            yield full_response
    except Exception as e:
        logger.error(f"完整分析出错: {e}")
        yield f"完整分析时出错: {str(e)}"

def generate_ppt_interface(topic, bg_image=None, transparency=0.95):
    """PPT生成界面函数"""
    if not topic.strip():
        raise gr.Error("请输入PPT主题内容")
    
    try:
        # 确保输出目录存在
        os.makedirs("data/ppt/pptresults", exist_ok=True)
        
        # 处理背景图片
        bg_image_path = None
        if bg_image:
            bg_image_path = bg_image.name
        else:
            bg_image_path = "assets/qh.jpg"
            if not os.path.exists(bg_image_path):
                logger.warning(f"默认背景图片不存在: {bg_image_path}")
                bg_image_path = None
        
        # 生成PPT并返回文件路径
        ppt_path = generate_ppt_from_topic(
            topic=topic,
            bg_image=bg_image_path,
            bg_transparency=transparency,
            output_dir="data/ppt/pptresults"
        )
        
        if not os.path.exists(ppt_path):
            raise gr.Error("PPT生成失败，文件未创建")
            
        return ppt_path
    except Exception as e:
        logger.error(f"生成PPT时出错: {e}")
        raise gr.Error(f"生成PPT时出错: {str(e)}")

# 创建Gradio界面
with gr.Blocks(title="学习助手系统", theme=gr.themes.Soft(), css=".gradio-container {max-width: 1200px !important}") as demo:
    gr.Markdown("# 🎓 智能学习助手系统")
    gr.Markdown("这是一个专业的错题分析和题目推荐系统，可以帮助学生更好地理解错误并提高学习效率。")
    
    with gr.Tabs():
        with gr.TabItem("错题分析", id="error_analysis"):
            with gr.Row():
                with gr.Column():
                    error_input = gr.Textbox(
                        label="请输入错题描述",
                        placeholder="请包含题目内容、学生答案和错误原因...",
                        lines=5
                    )
                    analyze_btn = gr.Button("开始分析", variant="primary")
                    
                    # 错题分析示例
                    with gr.Accordion("示例输入", open=False):
                        gr.Examples(
                            examples=[[
                                """
题目：一个质量为2kg的物体在水平面上受到10N的水平拉力作用，物体与水平面间的动摩擦因数为0.3。求物体的加速度。
学生答案：a = F/m = 10/2 = 5 m/s²
错误原因：忽略了摩擦力
学生思路：直接用牛顿第二定律F=ma计算，忘记考虑摩擦力影响
                                """
                            ]],
                            inputs=error_input,
                            label="物理错题示例"
                        )
                    
                with gr.Column():
                    error_output = gr.Textbox(
                        label="错题分析结果",
                        lines=15,
                        interactive=False
                    )
            analyze_btn.click(
                fn=analyze_error_interface,
                inputs=error_input,
                outputs=error_output
            )
        
        with gr.TabItem("题目推荐", id="exercise_recommend"):
            with gr.Row():
                with gr.Column():
                    knowledge_input = gr.Textbox(
                        label="知识点描述",
                        placeholder="请输入需要练习的知识点...",
                        lines=3
                    )
                    with gr.Accordion("可选：提供错题分析结果", open=False):
                        analysis_input = gr.Textbox(
                            label="错题分析结果",
                            placeholder="如果有错题分析结果，可以粘贴在这里...",
                            lines=5
                        )
                    recommend_btn = gr.Button("开始推荐", variant="primary")
                    
                    # 题目推荐示例
                    with gr.Accordion("示例输入", open=False):
                        gr.Examples(
                            examples=[[
                                "函数极值与最值的求解",
                                """
错因归类：极值点判断错误
涉及知识点：导数应用、极值判定定理
知识漏洞分析：未能正确理解一阶导数与二阶导数的关系
                                """
                            ]],
                            inputs=[knowledge_input, analysis_input],
                            label="数学知识点示例"
                        )
                    
                with gr.Column():
                    exercise_output = gr.Textbox(
                        label="推荐题目",
                        lines=15,
                        interactive=False
                    )
            recommend_btn.click(
                fn=recommend_exercises_interface,
                inputs=[analysis_input, knowledge_input],
                outputs=exercise_output
            )
        
        with gr.TabItem("完整分析流程", id="full_analysis"):
            with gr.Row():
                with gr.Column():
                    full_error_input = gr.Textbox(
                        label="请输入错题描述",
                        placeholder="请包含题目内容、学生答案和错误原因...",
                        lines=5
                    )
                    full_analyze_btn = gr.Button("开始完整分析", variant="primary")
                    
                    # 完整分析示例
                    with gr.Accordion("示例输入", open=False):
                        gr.Examples(
                            examples=[[
                                """
题目：已知函数f(x)=x³-3x²+4，求f(x)在区间[-1,3]上的最大值和最小值。
学生答案：最大值f(3)=4，最小值f(-1)=-6
错误原因：忽略了临界点x=0和x=2
学生思路：只计算了端点值，没有求导找极值点
                                """
                            ]],
                            inputs=full_error_input,
                            label="数学错题完整分析示例"
                        )
                    
                with gr.Column():
                    full_output = gr.Textbox(
                        label="分析结果",
                        lines=15,
                        interactive=False
                    )
            full_analyze_btn.click(
                fn=full_analysis_interface,
                inputs=full_error_input,
                outputs=full_output
            )

        with gr.TabItem("PPT生成", id="ppt_generation"):
            with gr.Row():
                with gr.Column():
                    ppt_topic = gr.Textbox(
                        label="PPT主题内容",
                        placeholder="请输入PPT主题和内容要求...",
                        lines=5,
                        value="结合以下内容生成20页ppt，我们某某团队，实现的功能有..."
                    )
                    
                    with gr.Accordion("高级设置", open=False):
                        bg_image = gr.File(
                            label="上传背景图片(可选)",
                            file_types=["image"],
                            type="filepath"
                        )
                        transparency = gr.Slider(
                            label="背景透明度",
                            minimum=0,
                            maximum=1,
                            step=0.05,
                            value=0.95
                        )
                    
                    ppt_generate_btn = gr.Button("生成PPT", variant="primary")
                    
                    # PPT生成示例
                    with gr.Accordion("示例输入", open=False):
                        gr.Examples(
                            examples=[[
                                """
结合以下内容生成20页ppt，我们是清华大学的ai教育助手团队，
我们的ai教育助手实现了很多功能，1本地向量数据库构建，设置中文停用词做文本清洗，
结合jieba分词与语义分割高质量分割文本，构建向量数据库使用多路召回混合检索重排输出结果，
2结合输入查询改写通过动态提示工程生成优质提示词，3错题分析与题目推荐，调用优质提示词结合本地题目向量数据库与知识向量数据库，
实现对用户输入错题的错因分析与新题目推荐；4aippt生成，调用大模型输出结构化数据，调用自编程实现的ppt模板，减少教师压力
                                """
                            ]],
                            inputs=ppt_topic,
                            label="教育主题PPT示例"
                        )
                    
                with gr.Column():
                    ppt_status = gr.Textbox(
                        label="生成状态",
                        lines=2,
                        interactive=False
                    )
                    ppt_download = gr.File(
                        label="生成的PPT文件",
                        interactive=False,
                        visible=False
                    )
            
            ppt_generate_btn.click(
                fn=lambda: gr.update(value="正在生成PPT，请稍候..."),
                outputs=ppt_status
            ).then(
                fn=generate_ppt_interface,
                inputs=[ppt_topic, bg_image, transparency],
                outputs=ppt_download,
                api_name="generate_ppt"
            ).then(
                fn=lambda: gr.update(value="PPT生成完成，请点击下方下载按钮"),
                outputs=ppt_status
            ).then(
                fn=lambda: gr.update(visible=True),
                outputs=ppt_download
            )

if __name__ == "__main__":
    import socket
    from contextlib import closing
    
    def find_free_port(start_port=7860, end_port=7870):
        """自动寻找可用端口"""
        for port in range(start_port, end_port + 1):
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                try:
                    s.bind(("", port))
                    return port
                except OSError:
                    continue
        return None
    
    free_port = find_free_port() or 7861
    
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=free_port,
            share=True,
            show_error=True,
            favicon_path="favicon.ico" if os.path.exists("favicon.ico") else None
        )
    except Exception as e:
        logger.error(f"启动应用失败: {e}")
        raise