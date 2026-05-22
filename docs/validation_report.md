# 验证报告

## 1. 验证目标

验证智能知识库组件是否完成以下能力：

- 自动分类并生成结构化元数据。
- 将文本和向量持久化保存。
- 对用户查询进行混合检索。
- 组装包含上下文和来源信息的 Prompt。
- 在样本数据上具备可解释的 Top-K 命中结果。

## 2. 样本数据

样本文件：`data/samples/sample_documents.json`

当前包含 24 条知识，覆盖：

- 客服售后
- 产品功能
- HR 制度
- 财务发票/报销
- 技术接口/故障
- 销售合同
- 运营活动
- 安全合规

## 3. 功能验证方法

运行：

```bash
python scripts/evaluate.py
```

脚本会执行：

1. 清空本地 `data/kb.sqlite` 和 `data/vectors.json`。
2. 导入 24 条样本文档。
3. 执行 6 条固定查询。
4. 统计 Hit@1、Hit@3、耗时和 Top 来源。
5. 将检索结果写入 `data/eval_results/retrieval_eval.json`。
6. 将运行指标写入 `data/eval_results/metrics_events.json`。

V2 新增分类准确率验证：

```bash
python scripts/evaluate_classification.py --fallback
```

该脚本会对 24 条样本文档的 `business_domain` 进行准确率统计，并将结果写入 `data/eval_results/classification_eval.json`。

V2 新增批量性能测试：

```bash
python scripts/benchmark.py --copies 20
```

该脚本会将 24 条样本文档复制扩展为 480 条知识，统计批量入库耗时、平均单文档入库耗时、查询平均耗时和 Token 上限配置。

V2 新增 RAG 对比实验模板：

```bash
python scripts/rag_comparison_template.py
```

该脚本生成 `data/eval_results/rag_comparison_template.json`，用于记录纯 LLM 直接回答和 RAG 回答的人工评分。

## 4. 查询集合

| 查询 | 期望命中文档 |
| --- | --- |
| 大额纸质专票多久寄出？ | sample-004 |
| API 返回 401 应该怎么处理？ | sample-005 |
| 客户忘记管理员密码怎么办？ | sample-015 |
| 免费版接口限流是多少？ | sample-024 |
| 合同到期前什么时候提醒客户经理？ | sample-014 |
| 数据库连接超时怎么排查？ | sample-012 |

## 5. 指标说明

- Hit@1：期望文档是否排在第一位。
- Hit@3：期望文档是否出现在前三位。
- elapsed_ms：单次查询耗时。
- used_tokens_estimate：Prompt 估算 token 数。

## 6. 对比实验设计

纯 LLM 直接回答的问题：

- 不一定知道企业内部制度。
- 可能编造处理时效、审批条件或接口限制。
- 无法给出内部知识来源。

通过本组件 RAG 回答：

- 先召回内部文档。
- Prompt 中包含来源、业务域和正文。
- 下游 LLM 被要求只基于上下文回答。
- 对时效、流程、错误码等事实型问题更可靠。

## 7. 当前结论

当前版本完成了题目要求的主链路：

- `addKnowledge(text, metadata?)`
- LLM/本地 fallback 分类
- 文档和向量持久化
- 关键词 + 向量混合检索
- LLM/分数重排
- Prompt 组装和 Token 控制
- Demo 和评估脚本

## 8. 本地验证结果

在未配置 API Key 的 fallback 模式下运行：

```bash
python scripts/evaluate.py
```

结果摘要：

| 指标 | 结果 |
| --- | --- |
| 文档数 | 24 |
| 查询数 | 6 |
| Hit@1 | 1.0 |
| Hit@3 | 1.0 |
| 单次查询耗时 | 约 8-21 ms |
| Prompt 估算 token | 约 458-503 |

Top-K 结果均能在第一位命中期望文档。例如：

| 查询 | Top1 |
| --- | --- |
| 大额纸质专票多久寄出？ | sample-004 |
| API 返回 401 应该怎么处理？ | sample-005 |
| 客户忘记管理员密码怎么办？ | sample-015 |
| 免费版接口限流是多少？ | sample-024 |
| 合同到期前什么时候提醒客户经理？ | sample-014 |
| 数据库连接超时怎么排查？ | sample-012 |

后续接入真实 LLM API 后，可进一步提高分类准确率、查询改写质量和重排效果。

## 9. V2 验证增强

V2 将验证拆成四类：

| 脚本 | 目标 | 默认是否调用真实 API |
| --- | --- | --- |
| `scripts/evaluate.py` | 检索 Hit@K 和耗时 | 取决于 `.env` |
| `scripts/evaluate_classification.py --fallback` | 分类准确率 | 否 |
| `scripts/benchmark.py --copies 20` | 批量入库和查询性能 | 否 |
| `scripts/rag_comparison_template.py` | 生成 RAG 对比实验记录模板 | 否 |

批量 benchmark 默认关闭真实 API，是为了避免一次性能测试触发大量 LLM/Embedding 调用。需要真实 API 测试时，可显式去掉 `--fallback` 或为 benchmark 增加 `--use-api`。

V2 本地 fallback 验证结果：

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| 语法检查 | `python -m compileall src scripts` | 通过 |
| 检索评估 | `python scripts/evaluate.py --fallback` | Hit@1=1.0，Hit@3=1.0 |
| 分类评估 | `python scripts/evaluate_classification.py --fallback` | 业务域准确率=0.958，标注类型准确率=1.0 |
| 性能测试 | `python scripts/benchmark.py --copies 2` | 48 条文档，平均查询耗时约 13.654 ms |
| RAG 对比模板 | `python scripts/rag_comparison_template.py` | 已生成模板 JSON |

注意：上述脚本会重置同一组本地数据库和向量文件，需顺序运行，不能并行执行。
