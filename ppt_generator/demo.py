from builder import PPTBuilder
import pandas as pd
import os

# 初始化生成器
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "advanced_template.pptx")

# 初始化生成器（会自动创建缺失的模板）
builder = PPTBuilder(TEMPLATE_PATH)

# 1. 添加封面页
builder.add_cover_slide(
    title="2024年科技趋势报告",
    subtitle="生成时间：2024年3月",
    logo_path="assets/real_logo.png"
)

# 2. 添加过渡页
builder.add_section_slide("第一部分：市场分析", progress=0.25)

# 3. 添加数据图表页
data = pd.read_excel("data/tech_data.xlsx")
chart_data = {
    "categories": data["categories"].tolist(),
    "series": [
        {"name": "Product A", "values": data["Product A"].tolist()},
        {"name": "Product B", "values": data["Product B"].tolist()}
    ]
}
builder.add_chart_slide("季度销售额对比", chart_data)

# 4. 保存结果
output_path = "output/demo_output.pptx"
os.makedirs("output", exist_ok=True)
builder.save(output_path)
print(f"PPT已生成至:_path")