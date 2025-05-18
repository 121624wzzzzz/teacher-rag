# maindop.py 全过程主程序
import logging
import os
from typing import Generator, Optional, List
from src.llm.dynamic import DynamicPromptEngine, get_knowledge_configs, get_exercise_configs
from src.llm.image_text_extractor import ImageTextExtractor

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
        # 初始化图像文本提取器
        self.image_extractor = ImageTextExtractor(
            use_gpu=False,  # 根据实际情况调整
            lang='ch',
            conf_threshold=0.5,
            verbose=False
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

    def extract_text_from_images(self, image_paths: List[str]) -> str:
        """
        从图片中提取文本
        
        参数:
            image_paths: 图片路径列表
            
        返回:
            提取的文本内容
        """
        if not image_paths:
            return ""
        
        extracted_texts = []
        
        for img_path in image_paths:
            try:
                # 使用图像提取器处理图片
                content = self.image_extractor.get_content_for_llm(img_path)
                extracted_texts.append(content)
                
            except Exception as e:
                logging.error(f"处理图片失败 {img_path}: {str(e)}")
                extracted_texts.append(f"图片 {os.path.basename(img_path)} 处理失败: {str(e)}")
        
        # 组合所有提取的文本
        return "\n\n".join(extracted_texts)

    def analyze_error(self, error_description: str, image_paths: Optional[List[str]] = None) -> Generator[str, None, None]:
        """
        分析错题的主方法
        
        参数:
            error_description: 学生的错题描述（题目+错误答案+学生思路）
            image_paths: 错题图片路径列表（可选）

        返回:
            生成器，流式输出分析结果
        """
        # 1. 设置预设的系统提示
        self.engine.current_enhanced_prompt = self.system_prompt
        self.engine.is_first_query = False  # 跳过提示生成阶段
        
        # 2. 如果提供了图片，处理并提取文本
        image_content = ""
        if image_paths and len(image_paths) > 0:
            try:
                yield "正在处理图片，提取题目内容...\n"
                image_content = self.extract_text_from_images(image_paths)
            except Exception as e:
                logging.error(f"图片处理失败: {str(e)}")
                yield f"图片处理时出错: {str(e)}\n"
        
        # 3. 构建完整的用户输入
        user_input = f"""请分析以下错题：
        
【错题描述】
{error_description}"""

        # 如果有图片内容，添加到输入中
        if image_content:
            user_input += f"""

【图片中识别的内容】
{image_content}"""

        user_input += "\n\n请按照要求进行专业分析："
        
        # 4. 开始对话并流式返回结果
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
    
    def full_analysis_pipeline(self, error_description: str, image_paths: Optional[List[str]] = None) -> Generator[str, None, None]:
        """
        完整的分析流程：错题分析 -> 题目推荐
        
        参数:
            error_description: 学生的错题描述
            image_paths: 错题图片路径列表（可选）
            
        返回:
            生成器，流式输出分析结果和推荐
        """
        # 第一阶段：错题分析
        analysis_result = []
        yield "\n=== 第一阶段：错题分析 ===\n"
        for chunk in self.error_analyzer.analyze_error(error_description, image_paths):
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
以下是我不会的知识点
"""
    
    # 示例图片路径（可选）
    sample_images = ["false.png"]  # 例如 ["path/to/image1.jpg", "path/to/image2.jpg"]
    
    print("正在执行完整分析流程...\n")
    
    # 方式1：独立使用错题分析（带图片）
    # for response in system.error_analyzer.analyze_error(sample_error, sample_images):
    #     print(response, end="", flush=True)
    
    # 方式2：独立使用题目推荐
    # for response in system.exercise_recommender.recommend_exercises(
    #     knowledge_points="函数极值与最值的求解"
    # ):
    #     print(response, end="", flush=True)
    
    # 方式3：完整分析流程（错题分析+题目推荐，带图片）
    for response in system.full_analysis_pipeline(sample_error, sample_images):
        print(response, end="", flush=True)