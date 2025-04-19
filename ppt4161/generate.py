import json
import re
import os
from dataclasses import dataclass

@dataclass
class LLMConfig:
    """LLM配置数据类"""
    api_key: str = os.getenv("SILICONFLOW_API_KEY")
    api_url: str = os.getenv("API_URL")
    model_name: str = os.getenv("MODEL_NAME")
    temperature: float = 0.7
    timeout: int = 300

def get_expected_structure():
    """从外部JSON文件加载模板结构"""
    template_path = os.path.join("ppt4161", "slide_prompt_template.json")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：模板文件未找到 - {template_path}")
        return {"slides_template": []}  # 返回空结构避免崩溃
    except json.JSONDecodeError as e:
        print(f"模板文件格式错误: {e}")
        return {"slides_template": []}

def llm(prompt, config=None):
    """
    模拟LLM调用函数，实际项目中应替换为真实的API调用
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
                "temperature": config.temperature
            },
            timeout=config.timeout
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return "模拟LLM响应，实际应用中请替换为真实API调用"

def generate_and_validate_json(topic):
    """
    使用LLM生成JSON内容并验证其结构
    """
    # 获取预期的JSON结构
    expected_structure = get_expected_structure()
    
    # 获取LLM配置
    llm_config = LLMConfig()
    
    # 构建提示词
    expected_structure_str = json.dumps(expected_structure, ensure_ascii=False, indent=2)
    
    prompt = f"""
    作为一个专业的演示文稿内容创作者，请你为我创建一个关于"{topic}"的结构化内容。
    
    请严格按照以下JSON格式输出，确保内容逻辑清晰、结构合理：
    
    {expected_structure_str}
    
    请根据此结构，为主题"{topic}"创建内容。
    请确保内容准确、专业，围绕"{topic}"进行全面阐述。
    JSON格式必须严格遵守，不要出现格式错误。
    每个幻灯片必须包含type字段。
    常见的幻灯片类型有: cover（封面）, toc（目录）, section（章节）, content（内容）, 
    timeline（时间线）, comparison（比较）, thank_you（感谢）等,其中cover（封面）, toc（目录），thank_you（感谢）等是全文的
    section（章节）, content（内容）, timeline（时间线）, comparison（比较）则是用来讲述各个模块内容的组成页。
    """
    
    # 调用LLM生成内容
    print(f"正在为主题 '{topic}' 生成结构化内容...")
    response = llm(prompt, llm_config)
    
    # 解析JSON响应
    try:
        # 尝试从响应中提取JSON部分
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.search(json_pattern, response, re.DOTALL)
        
        if matches:
            json_content = matches.group(1)
            try:
                json_data = json.loads(json_content)
                return json_data
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"提取的JSON内容: {json_content[:200]}...")
                return None
        else:
            # 如果没有特定格式，尝试直接解析整个响应
            try:
                json_data = json.loads(response)
                return json_data
            except json.JSONDecodeError:
                print("无法直接解析响应为JSON")
                print(f"原始响应: {response[:200]}...")
                return None
            
    except Exception as e:
        print(f"解析过程出现错误: {e}")
        print(f"原始响应: {response[:200]}...")
        return None

def validate_template_structure(json_data):
    """
    验证生成的JSON是否符合结构要求
    """
    if not json_data:
        return False
    
    # 检查是否有slides_template字段
    if 'slides_template' not in json_data:
        print("缺少'slides_template'字段")
        return False
    
    # 检查slides是否为列表
    if not isinstance(json_data['slides_template'], list):
        print("'slides_template'字段不是列表类型")
        return False
    
    # 检查每个slide是否有type字段
    for i, slide in enumerate(json_data['slides_template']):
        if not isinstance(slide, dict):
            print(f"第{i+1}个幻灯片不是字典类型")
            return False
        
        if 'type' not in slide:
            print(f"第{i+1}个幻灯片缺少'type'字段")
            return False
    
    return True

def print_json_structure(json_data):
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
        elif slide_type == 'cover' and 'title' in slide:
            title = slide['title']
        elif slide_type == 'section' and 'level1' in slide:
            title = slide['level1']
        
        title_info = f"(标题: {title})" if title else ""
        print(f"  {i+1}. {slide_type} {title_info}")
    
    # 打印第一个幻灯片的详细信息作为示例
    if slides:
        print("\n第一个幻灯片详细信息（示例）:")
        print(json.dumps(slides, ensure_ascii=False, indent=2))
    
    print("\n=== JSON结构验证完成 ===")

if __name__ == "__main__":
    # 设置主题
    topic = "人工智能在医疗领域的应用"
    print(f"主题: {topic}")
        
    # 生成并验证JSON
    json_data = generate_and_validate_json(topic)
    
    if json_data:
        print("\n✓ 成功生成JSON内容")
        
        # 验证结构
        is_valid = validate_template_structure(json_data)
        if is_valid:
            print("✓ JSON结构符合要求")
            
            # 打印JSON结构概览
            print_json_structure(json_data)
            
            # 可选: 输出完整JSON
            print("\n完整JSON内容:")
            # print(json.dumps(json_data, ensure_ascii=False, indent=2))
        else:
            print("✗ JSON结构不符合要求")
    else:
        print("\n✗ JSON生成失败")