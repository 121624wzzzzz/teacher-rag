以下是完全保留 **除 `chunks/` 和 `model/` 目录下具体文件** 外的完整结构，其他文件路径均原样呈现的 Markdown 格式目录树：

```markdown
# 项目目录结构

```
├── **data**  
│   ├── **chunks** - 文本分块目录（共 541 个 `.txt` 文件，命名格式 `chunk_{num}.txt`）  
│   ├── **cleaned**  
│   │   └── `cleaned_output.txt`  
│   ├── **raw**  
│   │   └── `[HIT教材]概率论与数理统计第三版(OCR).pdf`  
│   └── **vector_db**  
│       ├── `index.faiss`  
│       └── `index.pkl`  

├── **environment.yml**  
├── **llmtest2.py**  
├── **llmtest.py**  
├── **main2.py**  
├── **model**  
│   ├── **embeddingmodel** - 嵌入模型（含配置文件、权重等）  
│   ├── **reranker** - 重排序模型（含 `safetensors`、分词器等）  
│   └── **rerankmodel** - 空目录  

├── **requirements.txt**  
├── **src**  
│   ├── **core**  
│   │   ├── `chunk_processor.py`  
│   │   ├── `document_processor.py`  
│   │   ├── `__init__.py`  
│   │   ├── `__pycache__`  
│   │   ├── `rag_retriever.py`  
│   │   └── `vector_db.py`  
│   ├── `__init__.py`  
│   ├── `__pycache__`  
│   │   └── `__init__.cpython-310.pyc`  
│   └── **sub_utils**  
│       ├── `hello.py`  
│       ├── `__init__.py`  
│       └── `__pycache__`  

└── **tests**  
    ├── `llmtest3.py`  
    ├── `testqianru.py`  
    └── `testrag.py`  
```

### 调整说明
1. **保留所有文件路径**：除明确忽略的 `chunks/` 下具体文件和 `model/` 下的文件内容外，其余文件（包括 `__pycache__`、空目录 `rerankmodel`）均完整列出。
2. **隐藏细节的文件**：对 `chunks/` 和 `model/` 仅保留目录名和关键文件类型说明，避免冗余。
3. **格式优化**：使用 **加粗** 标注一级目录和关键文件，保持可读性。

如需进一步调整（如隐藏 `__pycache__` 或补充特定文件说明），可随时告知。