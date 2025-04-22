import logging
from typing import Generator
from src.llm.dynamic import DynamicPromptEngine, get_default_configs

class ErrorAnalysisAssistant:
    """错题分析助手"""
    
    def __init__(self):
        # 获取默认配置
        llm_config, rag_config, prompt_rag_config = get_default_configs()
        
        # 初始化动态提示引擎
        self.engine = DynamicPromptEngine(
            llm_config=llm_config,
            rag_config=rag_config,
            prompt_rag_config=prompt_rag_config,
            stream_output=True
        )
        
        # 预设的系统提示 (专业错题分析模板)
        self.system_prompt = """你是一位经验丰富的学科教育专家，专门负责分析学生的错题。请按照以下要求进行分析：
        
1. **错因诊断**：分析错误的具体原因（概念混淆、计算错误、理解偏差等）
2. **知识点定位**：指出题目涉及的核心知识点及关联知识图谱
3. **深层分析**：挖掘学生知识体系中的薄弱环节和思维误区
4. **改进建议**：提供针对性的学习建议和练习题推荐
5. **联系拓展**：展示该知识点在知识体系中的位置及与其他概念的联系

请用清晰的结构化格式回答，包含以下部分：
- 错因归类
- 涉及知识点
- 知识漏洞分析
- 学习建议
- 相关拓展"""

    def analyze_error(self, error_description: str) -> Generator[str, None, None]:
        """
        分析错题的主方法
        
        参数:
            error_description: 学生的错题描述（题目+错误答案+学生思路）
            
        返回:
            生成器，流式输出分析结果
        """
        # 1. 设置预设的系统提示
        self.engine.current_enhanced_prompt = self.system_prompt
        self.engine.is_first_query = False  # 跳过提示生成阶段
        
        # 2. 构建完整的用户输入
        user_input = f"""请分析以下错题：
        
【错题描述】
{error_description}

请按照要求进行专业分析："""
        
        # 3. 开始对话并流式返回结果
        try:
            response_generator = self.engine.start_conversation(
                original_query=user_input,
                verbose=True
            )
            
            # 添加处理标记
            yield "\n【错题分析开始】\n"
            for chunk in response_generator:
                yield chunk
            yield "\n【分析完成】\n"
            
        except Exception as e:
            logging.error(f"错题分析失败: {str(e)}")
            yield "抱歉，分析过程中出现错误，请稍后再试。"

# 使用示例
if __name__ == "__main__":
    assistant = ErrorAnalysisAssistant()
    
    # 示例错题 (实际使用时可以从文件/输入获取)
    sample_error = """
题目：求函数f(x) = x³ - 3x² + 2在区间[-1,3]上的最大值。
学生答案：f(3) = 2
错误原因：只计算了端点值，没有检查临界点
学生思路：我认为最大值出现在区间端点，所以只计算了f(-1)和f(3)的值
"""
    
    print("正在分析错题...\n")
    for response in assistant.analyze_error(sample_error):
        print(response, end="", flush=True)