# pptgenerate/pipeline.py (新的pipeline模块)
import os
import json
from datetime import datetime
from .generate import generate_and_validate_json
from .testend import generate_ppt_from_content

def save_json_to_file(json_data: dict, filename: str = None) -> str:
    """将JSON数据保存到文件"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ppt_content_{timestamp}.json"
    
    os.makedirs("data/ppt_content", exist_ok=True)
    filepath = os.path.join("data/ppt_content", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return filepath

def generate_ppt_from_topic(
    topic: str, 
    stream: bool = False,
    bg_image: str = "assets/qh.jpg",
    bg_transparency: float = 0.95,
    output_dir: str = "data/pptresults"
) -> str:
    """从主题生成PPT的完整流程"""
    # 1. 生成JSON内容
    print(f"\n正在为主题 '{topic}' 生成内容结构...")
    json_data = generate_and_validate_json(topic, stream=stream)
    
    if not json_data:
        raise ValueError("无法生成有效的JSON内容")
    
    # 2. 保存JSON内容供调试
    json_file = save_json_to_file(json_data)
    print(f"内容结构已保存到: {json_file}")
    
    # 3. 调整JSON结构
    ppt_content = {"slides": json_data["slides_template"]}
    
    # 4. 生成PPT
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ppt_filename = f"{topic.replace(' ', '_')}_{timestamp}.pptx"
    ppt_path = os.path.join(output_dir, ppt_filename)
    
    print("\n正在生成PPT演示文稿...")
    generated_path = generate_ppt_from_content(
        content=ppt_content,
        output_path=ppt_path,
        bg_image=bg_image,
        bg_transparency=bg_transparency
    )
    
    print(f"\n✓ PPT生成完成: {generated_path}")
    return generated_path