# KnowledgeManager

一个基于大模型的轻量级智能知识库管理与检索组件，面向智能客服、产品问答、内部知识助手等 RAG 场景。

当前开发分支：**V2 验证增强版**

V1.1 在 V1.0 MVP 主链路基础上修复了 `.env` 配置加载问题，并将默认模型配置切换为 BigModel 官方的 `GLM-4.7-Flash`。

## 已实现能力

- 知识入库：`KnowledgeManager.addKnowledge(text, metadata?)`
- 智能分类：调用 LLM 生成业务域、知识类型、重要程度、过期时间、标签、摘要、置信度
- 文档存储：SQLite 保存原文、元数据、状态和版本
- 向量存储：本地 JSON 保存 embedding 向量
- 混合检索：关键词检索 + 向量检索
- 智能检索增强：查询改写、结果重排
- Prompt 组装：返回带来源、分数、上下文的下游 LLM Prompt
- 版本管理：同一 `logical_id` 支持多版本
- 过期过滤：过期知识默认不参与检索
- 基础可观测性：记录分类置信度、检索耗时、Prompt token 估算
- 本地 fallback：无 API Key 或 API 失败时仍可用规则分类和哈希向量跑通 Demo

## 目录结构

```text
.
├── src/knowledge_base/
│   ├── manager.py                  # KnowledgeManager 对外入口
│   ├── models.py                   # 文档、元数据、检索结果模型
│   ├── config.py                   # 环境变量和运行配置
│   ├── llm/                        # LLM/Embedding API 与 Prompt 模板
│   ├── storage/                    # SQLite 文档库、向量库、关键词索引
│   ├── retrieval/                  # 混合检索、重排、Prompt 组装
│   └── observability/              # 指标记录
├── data/samples/                   # 24 条样本文档
├── scripts/                        # 入库、查询、评估脚本
├── docs/                           # 方案设计和验证报告
├── .env.example                    # BigModel 配置模板
└── requirements.txt
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

KB_DB_PATH=data/kb.sqlite
KB_VECTOR_PATH=data/vectors.json
KB_VECTOR_DIMENSIONS=256
KB_TOP_K=5
KB_PROMPT_TOKEN_LIMIT=1800
KB_VECTOR_WEIGHT=0.65
KB_KEYWORD_WEIGHT=0.35
```

说明：

- `LLM_MODEL` 固定使用 `glm-4.7-flash`。
- `LLM_BASE_URL` 使用 BigModel OpenAI-compatible API 地址。
- `EMBEDDING_MODEL` 使用 `embedding-3`。
- `EMBEDDING_DIMENSIONS` 为空时使用服务商默认维度；设置数值时会随 embedding 请求传入。
- `.env` 已被 `.gitignore` 忽略，避免提交 API Key。

不配置 `.env` 也可以运行，系统会自动使用 fallback 模式。

## 快速运行

入库样本文档：

```bash
python scripts/demo_add.py
```

查询知识库：

```bash
python scripts/demo_query.py "API 返回 401 应该怎么处理？"
```

运行检索评估：

```bash
python scripts/evaluate.py
```

评估脚本会重建本地 `data/kb.sqlite` 和 `data/vectors.json`，导入 24 条样本文档，并输出 Hit@1、Hit@3、查询耗时和 Top-K 来源。结果会写入 `data/eval_results/retrieval_eval.json`。

运行分类准确率评估：

```bash
python scripts/evaluate_classification.py --fallback
```

运行批量性能测试：

```bash
python scripts/benchmark.py --copies 20
```

生成 RAG 对比实验模板：

```bash
python scripts/rag_comparison_template.py
```

说明：`evaluate_classification.py` 不带 `--fallback` 时会使用 `.env` 中的大模型 API。`benchmark.py` 默认使用 fallback，只有显式传入 `--use-api` 才会调用真实 API，避免批量测试消耗过多调用额度。

这些脚本都会重建本地 `data/kb.sqlite` 和 `data/vectors.json`，请顺序运行，不要并行执行。

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

### 入库流程

```text
text
 -> LLM 分类 / fallback 分类
 -> 合并人工 metadata
 -> SQLite 保存文档版本
 -> Embedding API / fallback 向量
 -> 本地向量库 upsert
```

### 查询流程

```text
question
 -> LLM 查询改写 / 原问题 fallback
 -> 向量检索
 -> 关键词检索
 -> 混合分数合并
 -> LLM 重排 / 分数排序 fallback
 -> Token 上限控制
 -> 组装 Prompt
```

混合分数：

```text
final_score = 0.65 * vector_score + 0.35 * keyword_score
```

## 当前验证结果

在 fallback 模式下运行 `python scripts/evaluate.py`，当前样本集结果：

| 指标 | 结果 |
| --- | --- |
| 文档数 | 24 |
| 查询数 | 6 |
| Hit@1 | 1.0 |
| Hit@3 | 1.0 |

详细验证说明见 [docs/validation_report.md](docs/validation_report.md)。

## 版本规划

### V1.0 MVP

- 完成知识入库、分类、存储、向量化、混合检索、Prompt 组装主链路。
- 提供样本文档、Demo 和基础评估脚本。

### V1.1 当前版本

- 修复 `.env` 配置加载时机问题。
- 默认配置切换为 BigModel `glm-4.7-flash`。
- README 改为真实项目运行说明。
- API 调用失败时保留 fallback 路径，便于本地演示。

### V2 当前分支

- 增加分类准确率评估脚本。
- 增加检索评估结果落盘。
- 增加批量入库性能测试和 Token 控制边界测试。
- 将指标输出为 JSON。
- 增加纯 LLM 直接回答 vs RAG 回答对比实验模板。
- 保留真实 API 验证入口，但批量测试默认走 fallback。

### V3 计划

- 增加知识冲突检测。
- 增加 HyDE 检索增强。
- 支持动态分类规则和人工反馈闭环。
- 可选增加 FastAPI 服务接口。

## 提交物对应

- 方案设计：`docs/design.md`
- 验证报告：`docs/validation_report.md`
- 核心源码：`src/knowledge_base/`
- 样本文档：`data/samples/sample_documents.json`
- Demo：`scripts/demo_add.py`、`scripts/demo_query.py`
- 评估：`scripts/evaluate.py`
