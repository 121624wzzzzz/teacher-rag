# mainpptnew.py (新的主函数)
import argparse
from pptgenerate.pipeline import generate_ppt_from_topic  # 假设你将函数移动到这里

def main():
    # 设置参数解析
    parser = argparse.ArgumentParser(description="PPT生成工具")
    parser.add_argument("topic", nargs="?", default="结合以下内容生成20页ppt，我们是清华大学的ai教育助手团队，我们的ai教育助手实现了很多功能，1本地向量数据库构建，设置中文停用词做文本清洗，结合jieba分词与语义分割高质量分割文本，构建向量数据库使用多路召回混合检索重排输出结果，2结合输入查询改写通过动态提示工程生成优质提示词3错题分析与题目推荐，调用优质提示词结合本地题目向量数据库与知识向量数据库，实现对用户输入错题的错因分析与新题目推荐；4aippt生成，调用大模型输出结构化数据，调用自编程实现的ppt模板，减少教师压力，", 
                    help="PPT主题内容")
    parser.add_argument("--stream", action="store_true", 
                    help="启用流式输出模式")
    parser.add_argument("--bg_image", default="assets/qh.jpg", 
                    help="背景图片路径")
    parser.add_argument("--transparency", type=float, default=0.95,
                    help="背景透明度(0-1)")
    parser.add_argument("--output_dir", default="data/ppt/pptresults",
                    help="输出目录路径")
    
    args = parser.parse_args()
    
    try:
        # 执行生成流程
        ppt_path = generate_ppt_from_topic(
            topic=args.topic,
            stream=args.stream,
            bg_image=args.bg_image,
            bg_transparency=args.transparency,
            output_dir=args.output_dir
        )
        print(f"\n✓ PPT生成完成: {ppt_path}")
    
    except Exception as e:
        print(f"\n✗ 生成PPT时出错: {e}")
        raise

if __name__ == "__main__":
    main()