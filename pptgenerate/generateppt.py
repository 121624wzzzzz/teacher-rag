from pptx.util import Inches
from .pptslides import Presentation, SlideDesigner, BackgroundDesign

def generate_ppt_from_content(content, output_path="output.pptx", bg_image="assets/qh.jpg", bg_transparency=0.95):
    """
    根据内容生成PPT演示文稿
    
    参数:
        content (dict): 包含幻灯片数据的字典，格式如下:
            {
                "slides": [
                    {
                        "type": "cover",
                        "title": "主标题",
                        "subtitle": "副标题",
                        "company": "公司信息"
                    },
                    # 其他幻灯片数据...
                ]
            }
        output_path (str): 输出PPT文件路径
        bg_image (str): 背景图片路径
        bg_transparency (float): 背景透明度(0-1)
    """
    # 验证内容格式
    if not isinstance(content, dict) or "slides" not in content:
        raise ValueError("内容格式不正确，必须包含'slides'键")
    
    # 设置PPT幻灯片
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    
    designer = SlideDesigner(prs)
    
    # 按顺序生成幻灯片
    for slide_data in content["slides"]:
        slide_type = slide_data["type"]
        slide = None
        
        # 根据幻灯片类型调用相应的方法
        if slide_type == "cover":
            slide = designer.add_cover_slide(
                title=slide_data["title"],
                subtitle=slide_data["subtitle"],
                company=slide_data["company"]
            )
        
        elif slide_type == "toc":
            slide = designer.add_toc_slide(
                title=slide_data["title"],
                items=slide_data["items"]
            )
        
        elif slide_type == "section":
            params = {
                "level1": slide_data["level1"],
                "level2": slide_data.get("level2"),
            }
            if "level3" in slide_data:
                params["level3"] = slide_data["level3"]
                
            slide = designer.add_section_slide(**params)
            
        elif slide_type == "content":
            slide = designer.add_content_slide(
                title=slide_data["title"],
                contents=slide_data["contents"]
            )
        
        elif slide_type == "timeline":
            # 转换时间线项目格式
            timeline_items = [(item[0], item[1]) for item in slide_data["items"]]
            slide = designer.add_timeline_slide(
                title=slide_data["title"],
                timeline_items=timeline_items
            )
        
        elif slide_type == "comparison":
            slide = designer.add_comparison_slide(
                title=slide_data["title"],
                left_title=slide_data["left_title"],
                right_title=slide_data["right_title"],
                left_content=slide_data["left_content"],
                right_content=slide_data["right_content"]
            )
        
        elif slide_type == "thank_you":
            slide = designer.add_thank_you_slide(
                text=slide_data["text"],
                contact_info=slide_data["contact"]
            )
        else:
            raise ValueError(f"未知的幻灯片类型: {slide_type}")
        
        # 为所有幻灯片设置统一背景
        if slide:
            # 封面页和感谢页使用默认透明度
            if slide_type in ["cover", "thank_you"]:
                BackgroundDesign.set_background_image(slide, bg_image, transparency=bg_transparency)
            # 分节页使用稍低的透明度，使内容更突出
            elif slide_type == "section":
                BackgroundDesign.set_background_image(slide, bg_image, transparency=bg_transparency)
            # 其他页面可以选择是否设置背景
            else:
                BackgroundDesign.set_background_image(slide, bg_image, transparency=bg_transparency)
    
    prs.save(output_path)
    return output_path

def test_presentation_workflow():
    """测试完整演示文稿工作流（内置JSON内容版）"""
    # 内置的文字内容（相当于JSON内置在py文件中）
    # 按照实际PPT生成顺序排列的结构化JSON
    CONTENT = {
        "slides": [
            {
                "type": "cover",
                "title": "人工智能发展趋势分析",
                "subtitle": "从大语言模型看AI的未来",
                "company": "AI研究院 2023"
            },
            {
                "type": "toc",
                "title": "报告大纲",
                "items": [
                    "AI历史发展回顾",
                    "大语言模型的技术突破",
                    "当前应用场景分析",
                    "面临的挑战与局限",
                    "未来发展预测"
                ]
            },
            {
                "type": "section",
                "level1": "第一部分",
                "level2": "AI历史发展回顾",
                "level3": "从规则系统到深度学习"
            },
            {
                "type": "timeline",
                "title": "AI关键发展节点",
                "items": [
                    ["1950s", "图灵测试提出"],
                    ["1980s", "专家系统流行"],
                    ["2000s", "统计机器学习"],
                    ["2012", "深度学习兴起"],
                    ["2022", "大语言模型爆发"]
                ]
            },
            {
                "type": "section",
                "level1": "第二部分",
                "level2": "大语言模型的技术突破"
            },
            {
                "type": "content",
                "title": "核心技术创新",
                "contents": [
                    "预训练自然语言模型的规模化",
                    "Transformer架构的改进与优化",
                    "自监督学习的广泛应用",
                    "强化学习和人类反馈的引入",
                    "多模态能力的整合"
                ]
            },
            {
                "type": "section",
                "level1": "第三部分",
                "level2": "当前应用场景分析"
            },
            {
                "type": "content",
                "title": "主要应用领域",
                "contents": [
                    "内容创作与辅助",
                    "编程与软件开发",
                    "教育辅助和个性化学习",
                    "客户服务与智能问答",
                    "专业领域辅助决策"
                ]
            },
            {
                "type": "section",
                "level1": "第四部分",
                "level2": "面临的挑战与局限"
            },
            {
                "type": "comparison",
                "title": "大语言模型的优势与局限",
                "left_title": "主要优势",
                "right_title": "关键局限",
                "left_content": [
                    "强大的语言理解能力",
                    "零样本学习和少样本学习",
                    "多任务适应性",
                    "持续进化的潜力"
                ],
                "right_content": [
                    "事实准确性难以保证",
                    "存在偏见和伦理问题",
                    "推理能力有限",
                    "环境适应性不足",
                    "计算资源需求大"
                ]
            },
            {
                "type": "section",
                "level1": "第五部分",
                "level2": "未来发展预测"
            },
            {
                "type": "content",
                "title": "未来五年可能的发展方向",
                "contents": [
                    "多模态理解与生成的进一步融合",
                    "具备更强规划和推理能力的模型",
                    "领域专精模型与通用模型的协同",
                    "适应性和持续学习能力的增强",
                    "更高效的训练和推理范式"
                ]
            },
            {
                "type": "thank_you",
                "text": "感谢您的关注！",
                "contact": "联系我们：research@aiinstitute.org"
            }
        ]
    }

    output_path = generate_ppt_from_content(
        content=CONTENT,
        output_path="data/pptresults/ai_trends_presentation.pptx",
        bg_image="assets/qh.jpg",
        bg_transparency=0.95
    )
    
    print(f"演示文稿已生成：{output_path}")

if __name__ == "__main__":
    test_presentation_workflow()