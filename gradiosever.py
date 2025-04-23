import gradio as gr
from maindouble import LearningAssistantSystem, ErrorAnalysisAssistant, ExerciseRecommendationAssistant

# 初始化助手系统
system = LearningAssistantSystem()
error_analyzer = ErrorAnalysisAssistant()
exercise_recommender = ExerciseRecommendationAssistant()

def analyze_error_interface(error_description):
    """错题分析界面函数（真正的流式输出）"""
    full_response = ""
    for chunk in error_analyzer.analyze_error(error_description):
        full_response += chunk
        yield full_response  # 逐步返回累积的完整响应

def recommend_exercises_interface(error_analysis=None, knowledge_points=None):
    """题目推荐界面函数（真正的流式输出）"""
    full_response = ""
    for chunk in exercise_recommender.recommend_exercises(error_analysis, knowledge_points):
        full_response += chunk
        yield full_response

def full_analysis_interface(error_description):
    """完整分析流程界面函数（真正的流式输出）"""
    full_response = ""
    for chunk in system.full_analysis_pipeline(error_description):
        full_response += chunk
        yield full_response

# 创建Gradio界面
with gr.Blocks(title="学习助手系统", theme=gr.themes.Soft()) as demo:
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
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=free_port,
        share=True,
        show_error=True
    )