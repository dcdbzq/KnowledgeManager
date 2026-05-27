# KnowledgeManager

基于大模型的智能知识库管理与检索组件，面向智能客服、产品问答、内部知识助手等 RAG 场景。

## 功能概览

- 知识入库：`KnowledgeManager.addKnowledge(text, metadata?)`
- 智能分类：LLM 生成业务域、知识类型、重要程度、过期时间、标签、摘要、置信度
- 存储管理：SQLite 保存原文、元数据、状态和版本
- 向量检索：Embedding 向量化后写入本地向量库
- 混合检索：关键词检索 + 向量检索
- 智能检索增强：查询改写、结果重排、可选 HyDE
- 知识冲突检测：可选启用，入库时提示相似知识冲突
- Prompt 组装：返回带来源、分数、上下文的下游 LLM Prompt
- 验证脚本：分类准确率、检索 Hit@K、边界性能、RAG 对比实验

## 目录结构

```text
src/knowledge_base/              # 核心组件源码
data/samples/                    # 24 条样本文档
scripts/                         # Demo、评估、benchmark、RAG 对比脚本
docs/                            # 方案设计、验证报告、最终提交文档
.env.example                     # BigModel 配置模板
requirements.txt                 # 依赖说明
```

## 环境要求

- Python 3.10+
- 可选：BigModel API Key

当前实现只使用 Python 标准库，`requirements.txt` 暂无强制第三方依赖。

## API Key 配置

复制配置模板：

```bash
copy .env.example .env
```

在 `.env` 中填写 API Key：

```env
LLM_API_KEY=your_bigmodel_api_key_here
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_MODEL=glm-4.7-flash
EMBEDDING_MODEL=embedding-3
EMBEDDING_DIMENSIONS=
ENABLE_LLM=true
ENABLE_EMBEDDING_API=true
ENABLE_QUERY_REWRITE=true
ENABLE_RERANK=true
ENABLE_HYDE=false
ENABLE_CONFLICT_CHECK=false
API_RETRY_ATTEMPTS=2
API_RETRY_BACKOFF_SECONDS=2.0
KB_DB_PATH=data/kb.sqlite
KB_VECTOR_PATH=data/vectors.json
KB_VECTOR_DIMENSIONS=256
KB_TOP_K=5
KB_PROMPT_TOKEN_LIMIT=1800
KB_VECTOR_WEIGHT=0.65
KB_KEYWORD_WEIGHT=0.35
```

`.env` 已加入 `.gitignore`，不会提交 API Key。未配置 API Key 时，系统会使用本地 fallback 模式运行。

## 本地运行

入库样本文档：

```bash
python scripts/demo_add.py
```

查询知识库：

```bash
python scripts/demo_query.py "API 返回 401 应该怎么处理？"
```

检索评估：

```bash
python scripts/evaluate.py --fallback
```

分类准确率评估：

```bash
python scripts/evaluate_classification.py --fallback
```

批量性能测试：

```bash
python scripts/benchmark.py --copies 20
```

真实 API smoke test：

```bash
python scripts/api_smoke_test.py
```

RAG 对比实验：

```bash
python scripts/rag_comparison.py --sleep 5
```

## 测试数据

样本文档位于：

```text
data/samples/sample_documents.json
```

当前包含 24 条知识，覆盖客服售后、产品功能、HR、财务、技术接口、销售合同、运营活动和安全合规等领域。

## 使用示例

```python
from knowledge_base import KnowledgeManager

manager = KnowledgeManager()

added = manager.addKnowledge(
    "API接口返回401通常表示访问令牌无效或已过期。",
    metadata={"source_id": "manual-001"},
)

result = manager.query("接口返回401怎么办？")

print(result["hits"])
print(result["prompt"])
```

## 验证结果摘要

| 验证项 | 结果 |
| --- | --- |
| 样本文档数 | 24 |
| 检索评估 | Hit@1=1.0，Hit@3=1.0 |
| 分类评估 | 业务域准确率=0.958，标注类型准确率=1.0 |
| 480 条 benchmark | 平均查询耗时约 110 ms |
| 1008 条 benchmark | 平均查询耗时约 272 ms |
| 真实 API smoke test | GLM-4.7-Flash 分类、Embedding、查询改写、检索链路成功 |
| RAG 对比 | 3 条问题中 1 条 RAG 回答成功，2 条受 429 限流影响 |

## 提交物

- 方案设计：`docs/design.md`
- 验证报告：`docs/validation_report.md`
- 最终提交文档：`docs/final_submission.md`
- 核心源码：`src/knowledge_base/`
- 样本文档：`data/samples/sample_documents.json`
- Demo：`scripts/demo_add.py`、`scripts/demo_query.py`
- 评估脚本：`scripts/evaluate.py`、`scripts/evaluate_classification.py`、`scripts/benchmark.py`、`scripts/api_smoke_test.py`、`scripts/rag_comparison.py`
