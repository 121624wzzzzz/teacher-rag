# maindouble.py 全过程主程序
import logging
from typing import Generator, Optional
from src.llm.dynamic import DynamicPromptEngine, get_knowledge_configs, get_exercise_configs

class ErrorAnalysisAssistant:
    """错题分析助手"""
    
    def __init__(self):
        # 获取默认配置
        llm_config, knowledge_rag_config, prompt_rag_config = get_knowledge_configs()
        
        # 初始化动态提示引擎
        self.engine = DynamicPromptEngine(
            llm_config=llm_config,
            rag_config=knowledge_rag_config,
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


class ExerciseRecommendationAssistant:
    """题目推荐助手"""
    
    def __init__(self):
        # 获取默认配置
        llm_config, exercise_rag_config, prompt_rag_config = get_exercise_configs()
        
        # 初始化动态提示引擎
        self.engine = DynamicPromptEngine(
            llm_config=llm_config,
            rag_config=exercise_rag_config,
            prompt_rag_config=prompt_rag_config,
            stream_output=True
        )
        
        # 预设的系统提示 (题目推荐模板)
        self.system_prompt = """你是一位专业的题目推荐专家，能够根据学生的知识漏洞和错题分析结果，推荐最适合的练习题。请遵循以下原则：
        
1. **针对性**：题目要精准匹配学生的知识漏洞
2. **渐进性**：从基础到提高，形成递进式训练
3. **多样性**：包含不同题型和难度
4. **关联性**：题目之间要有知识关联性

推荐格式要求：
- 题目分类（基础/巩固/提高）
- 题目来源（教材/真题/模拟）
- 题目难度（★☆☆～★★★）
- 推荐理由（与知识漏洞的关联）"""

    def recommend_exercises(self, 
                        error_analysis: Optional[str] = None,
                        knowledge_points: Optional[str] = None) -> Generator[str, None, None]:
        """
        推荐练习题的主方法
        
        参数:
            error_analysis: 错题分析结果（可选）
            knowledge_points: 知识点描述（可选）
            
        返回:
            生成器，流式输出推荐结果
        """
        # 设置预设的系统提示
        self.engine.current_enhanced_prompt = self.system_prompt
        self.engine.is_first_query = False
        
        # 构建用户输入
        if error_analysis and knowledge_points:
            user_input = f"""基于以下错题分析和知识点，推荐最适合的练习题：
            
【错题分析】
{error_analysis}

【知识点】
{knowledge_points}

请按照要求推荐题目："""
        elif knowledge_points:
            user_input = f"""根据以下知识点推荐练习题：
            
【知识点】
{knowledge_points}

请按照要求推荐题目："""
        else:
            user_input = """请推荐一些适合高中学生的综合练习题：
            
请按照要求推荐题目："""
        
        # 开始对话并流式返回结果
        try:
            response_generator = self.engine.start_conversation(
                original_query=user_input,
                verbose=True
            )
            
            yield "\n【题目推荐开始】\n"
            for chunk in response_generator:
                yield chunk
            yield "\n【推荐完成】\n"
            
        except Exception as e:
            logging.error(f"题目推荐失败: {str(e)}")
            yield "抱歉，推荐过程中出现错误，请稍后再试。"


class LearningAssistantSystem:
    """学习助手系统（整合两个助手）"""
    
    def __init__(self):
        self.error_analyzer = ErrorAnalysisAssistant()
        self.exercise_recommender = ExerciseRecommendationAssistant()
    
    def full_analysis_pipeline(self, error_description: str) -> Generator[str, None, None]:
        """
        完整的分析流程：错题分析 -> 题目推荐
        
        参数:
            error_description: 学生的错题描述
            
        返回:
            生成器，流式输出分析结果和推荐
        """
        # 第一阶段：错题分析
        analysis_result = []
        yield "\n=== 第一阶段：错题分析 ===\n"
        for chunk in self.error_analyzer.analyze_error(error_description):
            analysis_result.append(chunk)
            yield chunk
        
        # 提取知识点用于推荐（简化处理，实际中可以更智能地提取）
        knowledge_points = self._extract_knowledge_points("".join(analysis_result))
        
        # 第二阶段：题目推荐
        yield "\n=== 第二阶段：题目推荐 ===\n"
        for chunk in self.exercise_recommender.recommend_exercises(
            error_analysis="".join(analysis_result),
            knowledge_points=knowledge_points
        ):
            yield chunk
    
    def _extract_knowledge_points(self, analysis_text: str) -> str:
        """从分析文本中提取知识点（简化版）"""
        # 这里可以添加更复杂的文本处理逻辑
        if "涉及知识点" in analysis_text:
            return analysis_text.split("涉及知识点")[-1].split("知识漏洞分析")[0].strip()
        return "未明确提取到知识点，基于整体分析推荐题目"


# 使用示例
if __name__ == "__main__":
    system = LearningAssistantSystem()
    
    # 示例错题
    sample_error = """
题目：一个质量为2kg的物体在水平面上受到10N的水平拉力作用，物体与水平面间的动摩擦因数为0.3。求物体的加速度。
学生答案：a = F/m = 10/2 = 5 m/s²
错误原因：忽略了摩擦力
学生思路：直接用牛顿第二定律F=ma计算，忘记考虑摩擦力影响
"""
    
    print("正在执行完整分析流程...\n")
    
    # 方式1：独立使用错题分析
    # for response in system.error_analyzer.analyze_error(sample_error):
    #     print(response, end="", flush=True)
    
    # 方式2：独立使用题目推荐
    # for response in system.exercise_recommender.recommend_exercises(
    #     knowledge_points="函数极值与最值的求解"
    # ):
    #     print(response, end="", flush=True)
    
    # 方式3：完整分析流程（错题分析+题目推荐）
    for response in system.full_analysis_pipeline(sample_error):
        print(response, end="", flush=True)