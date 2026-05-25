# KnowledgeManager

一个基于大模型的轻量级智能知识库管理与检索组件，面向智能客服、产品问答、内部知识助手等 RAG 场景。

当前版本：**V2 最终提交版**。V2 在 V1.0/V1.1 主链路基础上补齐了验证脚本、真实 API smoke test、RAG 对比实验、HyDE、知识冲突检测、指标落盘和边界性能测试。

## 已实现能力

- 知识入库：`KnowledgeManager.addKnowledge(text, metadata?)`
- 智能分类：LLM 生成业务域、知识类型、重要程度、过期时间、标签、摘要、置信度
- 文档存储：SQLite 保存原文、元数据、状态和版本
- 向量存储：本地 JSON 保存 embedding 向量
- 混合检索：关键词检索 + 向量检索
- 智能检索增强：查询改写、结果重排、可选 HyDE
- 知识冲突检测：可选启用，入库时提示相似知识冲突
- Prompt 组装：返回带来源、分数、上下文的下游 LLM Prompt
- 版本管理和过期过滤
- 指标落盘：分类置信度、检索耗时、Prompt token 估算等
- 本地 fallback：无 API Key 或 API 失败时仍可运行 Demo

## 目录结构

```text
src/knowledge_base/              # 核心组件源码
data/samples/                    # 24 条样本文档
scripts/                         # Demo、评估、benchmark、RAG 对比脚本
docs/                            # 方案设计和验证报告
.env.example                     # BigModel 配置模板
```

## 环境要求

- Python 3.10+
- Git
- 可选：BigModel API Key

当前代码只使用 Python 标准库，`requirements.txt` 暂无强制第三方依赖。

## 配置大模型 API

复制配置模板：

```bash
copy .env.example .env
```

在 `.env` 中填写你的 API Key：

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

`.env` 已被 `.gitignore` 忽略，避免提交 API Key。`ENABLE_HYDE` 和 `ENABLE_CONFLICT_CHECK` 默认关闭，避免额外 API 调用；需要展示加分项时可改为 `true`。

## 快速运行

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

真实 RAG 对比实验：

```bash
python scripts/rag_comparison.py --sleep 5
```

说明：`evaluate_classification.py` 不带 `--fallback` 时会调用真实 API。`benchmark.py` 默认使用 fallback，只有传入 `--use-api` 才会批量调用真实 API。

## 代码使用示例

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

## 核心流程

入库：

```text
text -> LLM/fallback 分类 -> 冲突检测(可选) -> SQLite 存储 -> Embedding/fallback 向量 -> 向量库
```

查询：

```text
question -> 查询改写 -> HyDE(可选) -> 向量检索 + 关键词检索 -> 混合排序 -> LLM 重排 -> Prompt 组装
```

混合分数：

```text
final_score = 0.65 * vector_score + 0.35 * keyword_score
```

## 当前验证结果

| 验证项 | 结果 |
| --- | --- |
| 样本文档数 | 24 |
| 检索评估 | Hit@1=1.0，Hit@3=1.0 |
| 分类评估 | 业务域准确率=0.958，标注类型准确率=1.0 |
| 480 条 benchmark | 平均查询耗时约 110 ms |
| 1008 条 benchmark | 平均查询耗时约 272 ms |
| 真实 API smoke test | GLM-4.7-Flash 分类、Embedding、查询改写、检索链路成功 |
| RAG 对比 | 3 条问题中 1 条 RAG 回答成功，2 条受 429 限流影响 |

详细验证说明见 [docs/validation_report.md](docs/validation_report.md)。

## 版本说明

- V1.0：完成知识入库、分类、存储、向量化、混合检索、Prompt 组装主链路。
- V1.1：修复 `.env` 配置加载问题，默认配置切换为 BigModel `glm-4.7-flash`。
- V2：补齐评估脚本、真实 API 验证、RAG 对比、指标落盘、HyDE、知识冲突检测和边界测试。

## 提交物对应

- 方案设计：`docs/design.md`
- 验证报告：`docs/validation_report.md`
- 核心源码：`src/knowledge_base/`
- 样本文档：`data/samples/sample_documents.json`
- Demo：`scripts/demo_add.py`、`scripts/demo_query.py`
- 评估：`scripts/evaluate.py`、`scripts/evaluate_classification.py`、`scripts/benchmark.py`、`scripts/api_smoke_test.py`、`scripts/rag_comparison.py`
