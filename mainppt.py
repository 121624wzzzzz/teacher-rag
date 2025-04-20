#mainppt.py
import json
import os
from pptgenerate.testend import generate_ppt_from_content
from datetime import datetime

def save_json_to_file(json_data: dict, filename: str = None) -> str:
    """
    将JSON数据保存到文件
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ppt_content_{timestamp}.json"
    
    os.makedirs("data/ppt_content", exist_ok=True)
    filepath = os.path.join("data/ppt_content", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return filepath

def generate_ppt_from_topic(topic: str, stream: bool = False) -> str:
    """
    从主题生成PPT的完整流程
    """
    from pptgenerate.generate import generate_and_validate_json
    
    # 1. 生成JSON内容
    print(f"\n正在为主题 '{topic}' 生成内容结构...")
    json_data = generate_and_validate_json(topic, stream=stream)
    
    if not json_data:
        raise ValueError("无法生成有效的JSON内容")
    
    # 2. 保存JSON内容供调试
    json_file = save_json_to_file(json_data)
    print(f"内容结构已保存到: {json_file}")
    
    # 3. 调整JSON结构以匹配PPT生成器期望的格式
    # 注意: 这里假设json_generator生成的格式是{"slides_template": [...]}
    # 而ppt_generator期望的格式是{"slides": [...]}
    ppt_content = {
        "slides": json_data["slides_template"]
    }
    
    # 4. 生成PPT
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ppt_filename = f"{topic.replace(' ', '_')}_{timestamp}.pptx"
    ppt_path = os.path.join("data/pptresults", ppt_filename)
    
    print("\n正在生成PPT演示文稿...")
    generated_path = generate_ppt_from_content(
        content=ppt_content,
        output_path=ppt_path,
        bg_image="assets/qh.jpg",
        bg_transparency=0.95
    )
    
    print(f"\n✓ PPT生成完成: {generated_path}")
    return generated_path

if __name__ == "__main__":
    # 用户输入主题
    topic = input("请输入PPT主题: ").strip()
    if not topic:
        topic = "人工智能在医疗领域的应用"  # 默认主题
    
    # 用户选择是否启用流式输出
    stream_input = input("是否启用流式输出？(y/n): ").strip().lower()
    stream_enabled = stream_input == 'y'
    
    try:
        # 执行完整流程
        ppt_path = generate_ppt_from_topic(topic, stream=stream_enabled)
        
        # 可选: 打开生成的PPT文件
        if os.name == 'nt':  # Windows
            os.startfile(ppt_path)
        elif os.name == 'posix':  # macOS/Linux
            os.system(f'open "{ppt_path}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{ppt_path}"')
    except Exception as e:
        print(f"\n✗ 生成PPT时出错: {e}")