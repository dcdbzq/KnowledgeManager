# 验证报告

## 1. 验证目标

本报告验证智能知识库组件是否满足题目要求：

- 自动分类并生成结构化元数据。
- 将文本、元数据、版本和向量持久化保存。
- 对用户查询进行关键词 + 向量混合检索。
- 使用 LLM 完成分类、查询改写、重排等智能检索环节。
- 组装包含来源、分数和上下文的 Prompt。
- 准备 20-30 条样本文档并验证 Top-K 相关性。
- 对比纯 LLM 直接回答和 RAG 回答。
- 测试大量知识入库后的查询性能和 Token 控制效果。

## 2. 样本数据

样本文件：`data/samples/sample_documents.json`

当前包含 24 条知识，覆盖客服售后、产品功能、HR、财务、技术接口、销售合同、运营活动和安全合规等领域。

## 3. 验证脚本

| 脚本 | 目标 | 默认是否调用真实 API | 输出 |
| --- | --- | --- | --- |
| `scripts/evaluate.py --fallback` | 检索 Hit@K 和耗时 | 否 | `data/eval_results/retrieval_eval.json` |
| `scripts/evaluate_classification.py --fallback` | 分类准确率 | 否 | `classification_eval.json` |
| `scripts/benchmark.py --copies N` | 批量入库和查询性能 | 否 | `benchmark.json` |
| `scripts/api_smoke_test.py` | 真实 API 小样本链路验证 | 是 | `api_smoke_test.json` |
| `scripts/rag_comparison.py --sleep 5` | 纯 LLM vs RAG 对比 | 是 | `rag_comparison.json` |
| `scripts/rag_comparison_template.py` | 生成手工评分模板 | 否 | `rag_comparison_template.json` |

批量 benchmark 默认关闭真实 API，避免一次测试触发大量 LLM/Embedding 调用。

## 4. 检索验证

固定查询集：

| 查询 | 期望命中文档 |
| --- | --- |
| 大额纸质专票多久寄出？ | sample-004 |
| API 返回 401 应该怎么处理？ | sample-005 |
| 客户忘记管理员密码怎么办？ | sample-015 |
| 免费版接口限流是多少？ | sample-024 |
| 合同到期前什么时候提醒客户经理？ | sample-014 |
| 数据库连接超时怎么排查？ | sample-012 |

运行：

```bash
python scripts/evaluate.py --fallback
```

结果：

| 指标 | 结果 |
| --- | --- |
| 文档数 | 24 |
| 查询数 | 6 |
| Hit@1 | 1.0 |
| Hit@3 | 1.0 |
| Prompt 估算 token | 约 448-501 |

结论：混合检索可在当前样本集上稳定召回期望知识，Top1 命中所有固定查询。

## 5. 分类验证

运行：

```bash
python scripts/evaluate_classification.py --fallback
```

结果：

| 指标 | 结果 |
| --- | --- |
| 文档数 | 24 |
| 业务域准确率 | 0.958 |
| 标注类型准确率 | 1.0 |
| 需人工复核样本 | sample-017 |

说明：fallback 分类器将 `sample-017` 的权限管理说明归为 `general`，并设置 `needs_review=true`，符合低置信度进入人工复核的设计。

## 6. 边界性能测试

运行：

```bash
python scripts/benchmark.py --copies 20
python scripts/benchmark.py --copies 42
```

结果：

| 数据规模 | 入库总耗时 | 平均入库耗时 | 平均查询耗时 | 最大查询耗时 |
| --- | --- | --- | --- | --- |
| 480 条 | 45.720 s | 95.249 ms/条 | 109.942 ms | 116.100 ms |
| 1008 条 | 177.834 s | 176.423 ms/条 | 272.018 ms | 461.390 ms |

结论：

- 千级数据下本地 JSON 向量库仍可完成演示级查询。
- 入库耗时随数据规模增长明显，主要原因是 JSON 向量库每次写入都会保存整个向量文件。
- 后续工程化建议替换为 Chroma、FAISS 或 Milvus。

## 7. 真实 API Smoke Test

运行：

```bash
python scripts/api_smoke_test.py
```

结果摘要：

| 项 | 结果 |
| --- | --- |
| 模型 | `glm-4.7-flash` |
| Embedding | `embedding-3` |
| LLM 是否启用 | true |
| 分类结果 | technical / troubleshooting |
| 分类置信度 | 1.0 |
| 查询改写 | `HTTP 401 未授权错误处理方法` |
| Top1 来源 | api-smoke-001 |
| 入库耗时 | 约 26.893 s |
| 查询耗时 | 约 27.775 s |

结论：GLM-4.7-Flash 接入路径可用，真实 API 已完成分类、Embedding、查询改写和检索链路验证。

## 8. 纯 LLM vs RAG 对比实验

运行：

```bash
python scripts/rag_comparison.py --sleep 5
```

结果摘要：

| 问题 | 直接 LLM | RAG 回答 | 说明 |
| --- | --- | --- | --- |
| 大额纸质专票多久寄出？ | 表示信息不可用 | 受 429 限流失败 | 已召回 sample-004 |
| API 返回 401 应该怎么处理？ | 给出通用处理流程 | 准确回答内部知识：重新获取 token 并检查 Authorization 格式 | RAG 更贴近内部文档 |
| 合同到期前什么时候提醒客户经理？ | 表示信息不可用 | 受 429 限流失败 | 已召回 sample-014 |

结论：

- 当 RAG 回答调用成功时，回答能严格基于内部知识库，事实更贴近样本文档。
- 直接 LLM 对内部专有知识通常无法回答，或只能给出通用经验。
- BigModel 免费模型存在明显限流，RAG 对比实验中 2 条回答被 `429` 阻断。

## 9. 可观测性

当前记录并可导出的指标包括：

- 入库耗时。
- 分类置信度。
- 是否需要人工复核。
- 是否检测到冲突。
- 查询耗时。
- 命中文档数量。
- Prompt 估算 token 数。

指标通过 `MetricsRecorder.export_json()` 写入 `data/eval_results/*.json`。

## 10. 风险与改进

| 风险 | 当前处理 | 后续建议 |
| --- | --- | --- |
| BigModel 免费模型限流 | API 失败时 fallback；脚本控制请求规模 | 增加更长退避、错峰运行，或切换付费/稳定模型 |
| JSON 向量库写入慢 | 当前满足千级演示 | 替换为 Chroma/FAISS |
| Token 控制为估算 | 使用保守上限 | 接入真实 tokenizer |
| 关键词索引每次查询重建 | 千级可接受 | 增量索引或持久化索引 |

## 11. 最终结论

当前 V2 已完成题目要求的核心交付：

- 方案设计文档。
- 完整源码与 README。
- `KnowledgeManager` 核心接口。
- LLM 分类、Embedding、查询改写、结果重排。
- 本地存储、版本管理、过期过滤。
- 混合检索和 Prompt 组装。
- 24 条样本文档。
- Demo、功能验证、对比实验和边界测试。
- 可观测性基础指标。
- HyDE 和知识冲突检测作为加分能力已接入，可通过配置开关启用。

仍建议在最终展示时说明：BigModel `glm-4.7-flash` 可用，但免费模型存在限流和耗时波动，因此项目保留 fallback 模式以保证本地可复现。
