import sys
import logging
from src.llm.dynamic import DynamicPromptEngine, get_default_configs
from src.llm.dynamic import DynamicPromptEngine, get_default_configs

def main():
    """命令行交互主函数"""
    # 获取配置
    llm_config, rag_config, prompt_rag_config = get_default_configs()
    
    # 初始化引擎
    engine = DynamicPromptEngine(
        llm_config=llm_config,
        rag_config=rag_config,
        prompt_rag_config=prompt_rag_config,
        stream_output=True
    )
    
    print("动态提示工程系统已启动 (输入exit退出)")
    while True:
        user_input = input("\n你的问题: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        if not user_input:
            continue
            
        try:
            print("\nAI回复: ", end="", flush=True)
            for chunk in engine.process_query(user_input, verbose=True):
                print(chunk, end="", flush=True)
            print("\n" + "="*50)
        except Exception as e:
            logging.error(f"处理查询时出错: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n对话已终止")
        sys.exit(0)