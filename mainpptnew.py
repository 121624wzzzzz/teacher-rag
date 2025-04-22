# mainpptnew.py (新的主函数)
import argparse
from pptgenerate.pipeline import generate_ppt_from_topic  # 假设你将函数移动到这里

def main():
    # 设置参数解析
    parser = argparse.ArgumentParser(description="PPT生成工具")
    parser.add_argument("topic", nargs="?", default="人工智能在医疗领域的应用", 
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