from langchain_text_splitters import RecursiveCharacterTextSplitter
from nltk.tokenize import TextTilingTokenizer
import re
import jieba
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch
from functools import lru_cache

# 初始化模型
tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-bert-wwm-ext")
model = AutoModel.from_pretrained("hfl/chinese-bert-wwm-ext").eval()
torch.set_grad_enabled(False)

# 内置基础中文停用词
BASIC_CHINESE_STOPWORDS = {
    '的', '了', '是', '在', '和', '有', '就', '这', '为', '与',
    '也', '要', '对', '都', '而', '及', '等', '可以', '我', '我们',
    '他们', '这', '那', '你', '您', '吧', '啊', '哦', '呀', '啦',
    '吗', '嗯', '唉', '之', '者', '或', '日', '月', '年', '个',
    '中', '上', '下', '左', '右', '前', '后', '时', '很', '太',
    '最', '更', '非常', '会', '没有', '不', '无', '未', '非', '并',
    '但', '已', '由', '被', '让', '把', '向', '去', '又', '再'
}

class OptimizedHybridSplitter:
    def __init__(self):
        # 一级分割器配置
        self.base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=150,
            separators=[
                r"\n{2,}",
                r"(?<=\n\n)",
                r"[。！？][”]*",
                r";+",
                r"，{2,}"
            ],
            keep_separator=True
        )
        
        # 二级分割参数
        self.topic_threshold = 0.68
        self.min_section_length = 120
        
        # 修复TextTilingTokenizer参数问题
        self.tt = TextTilingTokenizer(
            w=20,  # 正确参数名为w而不是words_per_block
            stopwords=list(BASIC_CHINESE_STOPWORDS)  # 需要转换为list类型
        )
        
        self.similarity_cache = {}
    
    # 以下方法保持不变，与之前版本相同
    def _preprocess_text(self, text):
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[！？]', '。', text)
        text = re.sub(r'([，；])\1+', r'\1', text)
        text = re.sub(r'([a-zA-Z])([\u4e00-\u9fa5])', r'\1 \2', text)
        return text.strip()

    @lru_cache(maxsize=5000)
    def _bert_embedding(self, text):
        inputs = tokenizer(text, 
                          return_tensors="pt", 
                          max_length=512, 
                          truncation=True)
        outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).numpy()

    def _text_similarity(self, text1, text2):
        key = (text1[:100], text2[:100])
        if key not in self.similarity_cache:
            emb1 = self._bert_embedding(text1)
            emb2 = self._bert_embedding(text2)
            sim = np.dot(emb1, emb2.T) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            self.similarity_cache[key] = sim.item()
        return self.similarity_cache[key]

    def _chinese_texttiling(self, text):
        words = ["|".join(jieba.cut(sent)) for sent in text.split('\n')]
        return self.tt.tokenize('\n'.join(words))

    def _dynamic_split(self, chunk):
        if re.search(r'(^|\n)(\d+\.|[-*+])\s', chunk):
            return re.split(r'\n(?=\d+\.|[-*+]\s)', chunk)
            
        try:
            if len(chunk) > 800:
                tiles = self._chinese_texttiling(chunk)
                if len(tiles) > 1:
                    return tiles
        except Exception as e:
            pass
            
        sentences = self.base_splitter.split_text(chunk)
        if len(sentences) < 3:
            return [chunk]
            
        window_size = 2
        split_points = []
        for i in range(window_size, len(sentences)-window_size):
            prev = "".join(sentences[i-window_size:i])
            next_ = "".join(sentences[i:i+window_size])
            if self._text_similarity(prev, next_) < self.topic_threshold:
                split_points.append(i)
                
        merged_points = []
        prev = -1
        for p in sorted(split_points):
            if p - prev > window_size*2:
                merged_points.append(p)
                prev = p
                
        chunks = []
        start = 0
        for point in merged_points:
            chunks.append("".join(sentences[start:point]))
            start = point
        chunks.append("".join(sentences[start:]))
        
        return [c for c in chunks if len(c) >= self.min_section_length]

    def split_text(self, text):
        processed_text = self._preprocess_text(text)
        base_chunks = self.base_splitter.split_text(processed_text)
        
        final_chunks = []
        for chunk in base_chunks:
            if len(chunk) > 600:
                refined = self._dynamic_split(chunk)
                final_chunks.extend(refined)
            else:
                final_chunks.append(chunk)
                
        merged = []
        buffer = ""
        for c in final_chunks:
            if len(buffer) + len(c) < 300:
                buffer += "\n" + c
            else:
                if buffer:
                    merged.append(buffer)
                buffer = c
        if buffer:
            merged.append(buffer)
            
        return merged

# 测试代码保持不变
def test_hybrid_chunker():
    splitter = OptimizedHybridSplitter()
    
    test_text = """
《金铲铲之战》4.3版本更新公告

第一章 核心机制调整

1.1 经济系统重构

本次更新彻底重做经济系统，关键改动包括：
• 基础金币收益从5/回合 → 6/回合
• 新增利息倍率机制：
  - 等级5以下：每10金币+1/回合
  - 等级6-8：每10金币+2/回合
  - 等级9：每10金币+3/回合
• 连胜/连败奖励公式调整：
  公式：奖励 = 基础值 × (1 + 0.2×回合数)
  示例：3连胜时获得 2×1.6=3.2金币（向下取整）

1.2 装备合成系统

新增装备合成异常检测机制，解决以下问题：
1. 当同时存在【暴风大剑+女神泪】和【女神泪+暴风大剑】时
2. 合成优先级问题（修复时间戳冲突BUG）
3. 视觉特效与实际效果不同步问题

第二章 英雄与羁绊

2.1 英雄数值调整表

英雄名称 | 费用 | 生命值 | 技能伤害
-------|-----|-------|---------
阿狸   | 4   | 850 → 800 | 350/500/800 → 320/480/750
李青   | 2   | 750 → 800 | 眩晕时间1.2s → 1.5s
索尔   | 5   | 1000 → 950 | 黑洞范围+15%

2.2 羁绊效果重做

【神谕者】效果变更：
旧：全体+40魔抗
新：每3秒回复10/20/35法力值

【法师】效果增强：
法术强度加成从20/45/80% → 25/50/90%

第三章 玩家生态

3.1 社区反馈分析

从50万局对战数据中发现：
- 阿狸使用率下降22%，但胜率提升4.3%
- 新经济系统使平均升9级时间提前1.2回合
- 装备异常反馈减少78%

玩家"云顶魔术师"评论：
"新的利息机制让运营策略更有深度，但李青的增强让前期阵容过于强势，
建议将生命值回调到780左右保持平衡。"

3.2 赛事体系升级

2024全球总决赛赛制更新：
1. 小组赛阶段：
   - BO3双败制
   - 禁用英雄池系统
2. 决赛阶段新增「巅峰对决」模式：
   双方使用完全相同随机阵容

技术团队透露正在开发：
- 实时胜率预测系统（基于LSTM神经网络）
- 跨平台对战功能（预计2024Q2上线）
"""

    chunks = splitter.split_text(test_text)
    
    print("\n🔍 深度测试分块结果：")
    print(f"总字符数：{len(test_text)}")
    print(f"最终分块数：{len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\n▇▇ 块{i+1} ({len(chunk)}字符) ▇▇")
        print(chunk[:100] + "..." if len(chunk) > 100 else chunk)


if __name__ == "__main__":
    test_hybrid_chunker()