import json
import re
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class LLMConfig:
    """LLM配置数据类"""
    api_key: str = os.getenv("SILICONFLOW_API_KEY")
    api_url: str = os.getenv("API_URL")
    model_name: str = os.getenv("MODEL_NAME")
    temperature: float = 0.7
    timeout: int = 300
    stream: bool = False  # 新增流式输出开关

def get_expected_structure() -> Dict[str, Any]:
    """从外部JSON文件加载模板结构"""
    template_path = os.path.join("pptgenerate", "slide_prompt_template.json")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：模板文件未找到 - {template_path}")
        return {"slides_template": []}  # 返回空结构避免崩溃
    except json.JSONDecodeError as e:
        print(f"模板文件格式错误: {e}")
        return {"slides_template": []}

def llm(prompt: str, config: Optional[LLMConfig] = None) -> str:
    """
    模拟LLM调用函数，支持流式输出
    """
    if config is None:
        config = LLMConfig()
    
    # 这里应该是调用实际的LLM API
    import requests
    try:
        response = requests.post(
            config.api_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": config.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.temperature,
                "stream": config.stream  # 传递流式参数
            },
            timeout=config.timeout,
            stream=config.stream  # 启用流式响应
        )
        response.raise_for_status()
        
        if config.stream:
            # 处理流式响应
            full_response = ""
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith("data:"):
                        chunk_data = chunk_str[5:].strip()
                        if chunk_data == "[DONE]":
                            break
                        try:
                            chunk_json = json.loads(chunk_data)
                            content = chunk_json["choices"][0]["delta"].get("content", "")
                            print(content, end="", flush=True)  # 实时输出
                            full_response += content
                        except json.JSONDecodeError:
                            continue
            print()  # 换行
            return full_response
        else:
            # 普通响应处理
            return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"\nLLM调用失败: {e}")
        return "模拟LLM响应，实际应用中请替换为真实API调用"

def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    从LLM响应中提取JSON内容
    """
    try:
        # 尝试从响应中提取JSON部分
        json_pattern = r'```(?:json)?\s*(.*?)\s*```'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_content = matches.group(1)
            try:
                return json.loads(json_content)
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"提取的JSON内容: {json_content[:200]}...")
                return None
        
        # 如果没有特定格式，尝试直接解析整个响应
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print("无法直接解析响应为JSON")
            print(f"原始响应: {response[:200]}...")
            return None
            
    except Exception as e:
        print(f"解析过程出现错误: {e}")
        print(f"原始响应: {response[:200]}...")
        return None

def generate_and_validate_json(topic: str, stream: bool = False) -> Optional[Dict[str, Any]]:
    """
    使用LLM生成JSON内容并验证其结构
    """
    # 获取预期的JSON结构
    expected_structure = get_expected_structure()
    
    # 获取LLM配置
    llm_config = LLMConfig(stream=stream)
    
    # 构建提示词
    expected_structure_str = json.dumps(expected_structure, ensure_ascii=False, indent=2)
    
    prompt = f"""
    作为一个专业的演示文稿内容创作者，请你为我创建一个关于"{topic}"的结构化内容。
    
    请严格按照以下JSON格式输出，确保内容逻辑清晰、结构合理：
    
    {expected_structure_str}
    
    请根据此结构，为主题"{topic}"创建内容。
    请确保内容准确、专业，围绕"{topic}"进行全面阐述。
    JSON格式必须严格遵守，不要出现格式错误，这非常重要。
    每个幻灯片必须包含type字段，键名不要随意更改。
    常见的幻灯片类型有: cover（封面）, toc（目录）, section（章节）, content（内容）, timeline（时间线）, comparison（比较）, thank_you（感谢）等,
    其中cover（封面）, toc（目录），thank_you（感谢）等是全文的，
    section（章节）, content（内容）, timeline（时间线）, comparison（比较）则是用来讲述各个模块内容的组成页。
    """
    
    # 调用LLM生成内容
    print(f"正在为主题 '{topic}' 生成结构化内容...")
    if stream:
        print("\n=== 流式输出开始 ===")
    
    response = llm(prompt, llm_config)
    
    if stream:
        print("\n=== 流式输出结束 ===")
    
    # 解析JSON响应
    json_data = extract_json_from_response(response)
    
    if not json_data:
        print("✗ 无法从响应中提取有效的JSON数据")
        return None
    
    # 验证结构
    is_valid, validation_errors = validate_template_structure(json_data)
    if not is_valid:
        print("\n✗ JSON结构验证失败:")
        for error in validation_errors:
            print(f"  - {error}")
        return None
    
    return json_data

def validate_template_structure(json_data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    验证生成的JSON是否符合结构要求
    返回验证结果和错误信息列表
    """
    errors = []
    
    if not json_data:
        errors.append("JSON数据为空")
        return False, errors
    
    # 检查是否有slides_template字段
    if 'slides_template' not in json_data:
        errors.append("缺少'slides_template'字段")
    
    # 检查slides是否为列表
    if not isinstance(json_data.get('slides_template', None), list):
        errors.append("'slides_template'字段不是列表类型")
    
    # 检查每个slide是否有type字段
    slides = json_data.get('slides_template', [])
    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            errors.append(f"第{i+1}个幻灯片不是字典类型")
            continue
        
        if 'type' not in slide:
            errors.append(f"第{i+1}个幻灯片缺少'type'字段")
        
        # 检查type是否有效
        slide_type = slide.get('type')
        valid_types = {'cover', 'toc', 'section', 'content', 'timeline', 'comparison', 'thank_you'}
        if slide_type and slide_type not in valid_types:
            errors.append(f"第{i+1}个幻灯片的类型'{slide_type}'无效，应为{valid_types}之一")
        
        # 根据类型检查必要字段
        if slide_type == 'cover' and 'title' not in slide:
            errors.append(f"第{i+1}个幻灯片(封面)缺少'title'字段")
        elif slide_type == 'section' and 'level1' not in slide:
            errors.append(f"第{i+1}个幻灯片(章节)缺少'level1'字段")
    
    return len(errors) == 0, errors

def print_json_structure(json_data: Dict[str, Any]) -> None:
    """
    打印JSON结构概览
    """
    if 'slides_template' not in json_data:
        return
    
    slides = json_data['slides_template']
    
    print("\n=== JSON结构概览 ===")
    print(f"幻灯片数量: {len(slides)}")
    print("幻灯片类型列表:")
    
    for i, slide in enumerate(slides):
        slide_type = slide.get('type', '未知类型')
        title = None
        
        if 'title' in slide:
            title = slide['title']
        elif slide_type == 'section' and 'level1' in slide:
            title = slide['level1']
        
        title_info = f"(标题: {title})" if title else ""
        print(f"  {i+1}. {slide_type} {title_info}")
    
    # 打印第一个幻灯片的详细信息作为示例
    if slides:
        print("\n第一个幻灯片详细信息（示例）:")
        print(json.dumps(slides[0], ensure_ascii=False, indent=2))
    
    print("\n=== JSON结构验证完成 ===")

if __name__ == "__main__":
    # 设置主题
    topic = "人工智能在医疗领域的应用"
    print(f"主题: {topic}")
    
    # 用户选择是否启用流式输出
    stream_input = input("是否启用流式输出？(y/n): ").strip().lower()
    stream_enabled = stream_input == 'y'
    
    # 生成并验证JSON
    json_data = generate_and_validate_json(topic, stream=stream_enabled)
    
    if json_data:
        print("\n✓ 成功生成并验证JSON内容")
        
        # 打印JSON结构概览
        print_json_structure(json_data)
        
        # 可选: 输出完整JSON
        print("\n完整JSON内容:")
        print(json.dumps(json_data, ensure_ascii=False, indent=2))
    else:
        print("\n✗ JSON生成或验证失败")