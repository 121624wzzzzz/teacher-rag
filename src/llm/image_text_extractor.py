import os
import re
import cv2
from paddleocr import PaddleOCR
import time

class ImageTextExtractor:
    """图片文本提取器：提取图片中的文本和数学公式，生成适合大模型的Markdown格式内容"""
    
    def __init__(self, use_gpu=False, lang='ch', conf_threshold=0.5, verbose=False):
        """
        初始化图片文本提取器
        
        参数:
            use_gpu: 是否使用GPU加速OCR
            lang: OCR使用的语言，默认中文
            conf_threshold: 置信度阈值，低于此值的结果被过滤
            verbose: 是否输出详细日志
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self.conf_threshold = conf_threshold
        self.verbose = verbose
        self.ocr = None
        
    def _log(self, message):
        """打印日志信息"""
        if self.verbose:
            print(message)
    
    def _init_ocr(self):
        """初始化OCR引擎（延迟加载，节省资源）"""
        if self.ocr is None:
            self._log("初始化OCR引擎...")
            start_time = time.time()
            self.ocr = PaddleOCR(
                use_angle_cls=True, 
                lang=self.lang, 
                use_gpu=self.use_gpu, 
                show_log=False,
                rec_algorithm="CRNN",  # 使用基础识别算法
                det_algorithm="DB",    # 使用基础检测算法
                # 禁用预处理中的数据增强功能
                det_db_unclip_ratio=1.5,
                use_dilation=False,
                # 直接使用预训练模型，避免训练相关依赖
                use_space_char=True
            )
            self._log(f"OCR引擎初始化完成，耗时: {time.time() - start_time:.2f}秒")
    
    def _is_formula(self, text):
        """判断文本是否为公式"""
        # 数学符号集
        math_symbols = set('+-*/=<>^()[]{}∑∏∫√∂∆πθλμ∞≠≈≤≥±×÷')
        
        # 计算数学符号密度
        symbol_count = sum(1 for char in text if char in math_symbols)
        symbol_density = symbol_count / len(text) if text else 0
        
        # 检查常见的数学表达式模式
        formula_patterns = [
            r'[\^\d\_]',           # 上标下标
            r'[a-zA-Z]_\d',        # 下标表示
            r'[a-zA-Z]\^\d',       # 上标表示
            r'\d+[/]\d+',          # 分数形式
            r'[√∑∏∫]',             # 数学运算符
            r'\([a-zA-Z0-9+\-*/]+\)' # 括号表达式
        ]
        
        # 检查是否符合公式模式
        for pattern in formula_patterns:
            if re.search(pattern, text):
                return True
        
        # 根据符号密度做最终判断
        return symbol_density > 0.15  # 如果数学符号占比超过15%，认为是公式
    
    def _format_to_latex(self, text):
        """将识别出的文本转换为 LaTeX 格式"""
        # 替换常见的数学符号和表达式
        replacements = [
            (r'(\d+)/(\d+)', r'\\frac{\1}{\2}'),  # 分数
            (r'(\w+)_(\d+)', r'\1_{\\2}'),         # 下标
            (r'(\w+)\^(\d+)', r'\1^{\2}'),         # 上标
            ('×', r'\\times'),
            ('÷', r'\\div'),
            ('±', r'\\pm'),
            ('∞', r'\\infty'),
            ('≠', r'\\neq'),
            ('≈', r'\\approx'),
            ('≤', r'\\leq'),
            ('≥', r'\\geq'),
            ('π', r'\\pi'),
            ('θ', r'\\theta'),
            ('λ', r'\\lambda'),
            ('μ', r'\\mu'),
            ('∑', r'\\sum'),
            ('∏', r'\\prod'),
            ('∫', r'\\int'),
            ('√', r'\\sqrt'),
            ('∂', r'\\partial'),
            ('∆', r'\\Delta')
        ]
        
        result = text
        for old, new in replacements:
            result = re.sub(old, new, result)
        
        return result
    
    def process_image(self, image_path):
        """
        处理图片，识别文本和公式
        
        参数:
            image_path: 图片路径
            
        返回:
            包含识别结果的字典
        """
        result = {
            'text_blocks': [],
            'formulas': []
        }
        
        try:
            self._init_ocr()
            
            self._log(f"处理图片: {image_path}")
            start_time = time.time()
            
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                result['error'] = f"无法读取图片: {image_path}"
                return result
            
            # 进行OCR识别
            self._log("正在识别图片文字...")
            ocr_result = self.ocr.ocr(image_path, cls=True)
            
            # 提取识别结果
            if ocr_result and len(ocr_result) > 0 and ocr_result[0]:
                for line in ocr_result[0]:
                    bbox, (text, conf) = line
                    
                    # 过滤低置信度的结果
                    if conf < self.conf_threshold:
                        continue
                    
                    # 判断是否为公式
                    if self._is_formula(text):
                        latex_text = self._format_to_latex(text)
                        result['formulas'].append({
                            'text': text,
                            'latex': latex_text,
                            'confidence': float(conf)
                        })
                    else:
                        result['text_blocks'].append({
                            'text': text,
                            'confidence': float(conf)
                        })
            
            # 按置信度排序
            result['text_blocks'].sort(key=lambda x: x['confidence'], reverse=True)
            result['formulas'].sort(key=lambda x: x['confidence'], reverse=True)
            
            process_time = time.time() - start_time
            result['process_time'] = process_time
            self._log(f"处理完成，文本: {len(result['text_blocks'])}项，公式: {len(result['formulas'])}项，耗时: {process_time:.2f}秒")
            
        except Exception as e:
            result['error'] = f"处理图片时出错: {str(e)}"
            self._log(f"错误: {str(e)}")
        
        return result
    
    def get_content_for_llm(self, image_path):
        """
        提取图片内容，生成适合大模型的Markdown格式文本
        
        参数:
            image_path: 图片路径
            
        返回:
            适合大模型的Markdown格式内容
        """
        result = self.process_image(image_path)
        
        if 'error' in result:
            return f"# 图片处理错误\n\n{result['error']}"
        
        # 构建给大模型的Markdown内容
        filename = os.path.basename(image_path)
        lines = [f"# 图片内容: {filename}"]
        
        # 处理并添加文本内容
        if result['text_blocks']:
            lines.append("\n## 以下是提取到的文本内容")
            
            # 尝试将文本块组织成有意义的段落
            paragraphs = []
            current_paragraph = []
            
            for item in result['text_blocks']:
                text = item['text'].strip()
                if not text:  # 跳过空文本
                    continue
                    
                # 判断段落结束标志
                if text.endswith('.') or text.endswith('。') or text.endswith('!') or text.endswith('?') or text.endswith('！') or text.endswith('？'):
                    current_paragraph.append(text)
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
                else:
                    current_paragraph.append(text)
            
            # 处理剩余内容
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            # 添加段落到输出
            for paragraph in paragraphs:
                lines.append(f"\n{paragraph}")
        
        # 添加公式内容
        if result['formulas']:
            lines.append("\n## 数学公式")
            
            for i, formula in enumerate(result['formulas']):
                lines.append(f"\n### 公式 {i+1}")
                lines.append(f"{formula['text']}")
                lines.append("")
                lines.append("LaTeX格式:")
                lines.append(f"```latex")
                lines.append(formula['latex'])
                lines.append("```")
                lines.append("")
                lines.append("渲染后的公式:")
                lines.append(f"$${formula['latex']}$$")
        
        return "\n".join(lines)


# 简单使用示例
if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            image_path = filedialog.askopenfilename(
                title="选择图片文件",
                filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp")]
            )
            if not image_path:
                print("未选择图片，程序退出")
                sys.exit(0)
        except ImportError:
            print("错误: 请提供图片路径作为命令行参数")
            sys.exit(1)
    else:
        image_path = sys.argv[1]
    
    # 创建提取器并处理图片
    extractor = ImageTextExtractor(verbose=True)
    content = extractor.get_content_for_llm(image_path)
    
    # 输出结果
    print("\n" + "=" * 40 + " 提取结果 " + "=" * 40 + "\n")
    print(content)

'''使用方法
from image_text_extractor import ImageTextExtractor

# 创建一个实例
extractor = ImageTextExtractor(
    use_gpu=False,  # 是否使用GPU
    lang='ch',      # 语言选择，'ch'为中文，'en'为英文
    conf_threshold=0.5,  # 置信度阈值
    verbose=True    # 是否打印详细日志
)

# 处理单个图像并获取Markdown格式结果
image_path = "path/to/your/image.jpg"
markdown_content = extractor.get_content_for_llm(image_path)

# 打印或使用结果
print(markdown_content)

# 或者将结果保存到文件
with open("output.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)
    '''