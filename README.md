**我的理解**

这个项目要做的不是“调用大模型回答问题”，而是实现一个轻量级 RAG 知识库组件。核心价值在于：把文本知识自动分类、结构化入库、向量化存储，然后在用户提问时做混合检索、重排和 Prompt 组装，给下游大模型提供可靠上下文，减少幻觉。

最终交付要包含三类东西：

1. **方案设计文档/PDF**
2. **可运行源码 + README + Demo**
3. **验证报告：分类、检索、对比实验、边界测试**

当前目录里还没有源码工程，只有题目文件和空的 `plans` 目录，所以建议先从工程骨架和方案文档同步开始。

**推荐项目结构**

建议用 Python，理由是 RAG、Embedding、向量库、Demo 验证生态更轻，2 周内交付风险更低。

```text
zhaoshang/
  README.md
  requirements.txt
  .env.example

  src/
    knowledge_base/
      __init__.py
      manager.py              # KnowledgeManager 对外入口
      models.py               # Knowledge、Metadata、QueryResult 等数据结构
      config.py               # API Key、模型、TopK、Token 上限配置

      llm/
        client.py             # LLM/Embedding API 适配
        prompts.py            # 分类、查询改写、重排 Prompt 模板

      storage/
        document_store.py     # 文档 CRUD、版本、过期
        vector_store.py       # 向量存储与相似度检索
        keyword_index.py      # 关键词/BM25/简单倒排索引

      retrieval/
        hybrid_retriever.py   # 关键词 + 向量混合检索
        reranker.py           # LLM 重排，可先简化
        prompt_builder.py     # 上下文 Prompt 组装和 Token 控制

      observability/
        metrics.py            # 指标记录，加分项

  data/
    samples/                  # 20-30 条样本文档
    kb.sqlite                 # 文档/元数据存储
    vectors.json 或 chroma/    # 向量存储

  scripts/
    demo_add.py               # 入库 Demo
    demo_query.py             # 查询 Demo
    evaluate.py               # 验证脚本

  docs/
    design.md                 # 方案设计文档草稿
    validation_report.md      # 验证报告
```

**核心目标**

必须完成的目标有三个：

1. **智能分类与入库**
   - 输入 Markdown/纯文本。
   - 调用 LLM 生成结构化分类 JSON。
   - 分类维度至少包括：业务域、知识类型、重要程度、过期时间、关键词/标签、摘要、置信度。
   - 低置信度时保留 `needs_review=true`，而不是强行分类。

2. **存储与管理**
   - 保存原始文本、分类元数据、版本号、创建时间、更新时间、过期时间、状态。
   - 文本向量化后存入向量库。
   - 支持新增、更新、删除、查询、过期过滤。
   - 版本管理可以先用“同一个 logical_id 多个 version”的方式实现。

3. **智能检索与 Prompt 组装**
   - 用户问题进入后，先做查询改写，或者至少生成检索关键词。
   - 同时做关键词检索和向量检索。
   - 合并结果后按分数排序，必要时用 LLM 重排。
   - 最后按 Token 上限组装上下文 Prompt，返回给下游 LLM。

**约束**

题目中的硬约束是：

- 语言推荐 Java 或 Python。
- 必须使用大模型 API 做分类和智能检索相关环节。
- 可以用 Chroma、FAISS 或内存向量库。
- 只处理纯文本/Markdown，不做 PDF、Word 解析。
- 核心逻辑要自己实现，尤其是分类 Prompt、检索编排、Prompt 组装。

我的建议是：

- **Python + SQLite + 简易向量存储/Chroma**
- 第一版用本地json向量库实现(第一版可以先用内存/JSON 向量库，方便展示；如果想显得更工程化，用 Chroma)。
- 文档元数据用 SQLite，结构清楚，也方便写 Schema。
- LLM API 做成 OpenAI-compatible 接口，后续可接 OpenAI、通义、智谱、DeepSeek、硅基流动等。

**验收标准**

我会按下面这些标准判断项目是否完成：

1. 能运行 `KnowledgeManager.addKnowledge(text, metadata?)`。
2. 能自动分类并生成结构化元数据。
3. 能保存文本、版本、过期时间、向量。
4. 能运行 `KnowledgeManager.query(question)`。
5. 查询结果来自混合检索，而不是只靠 LLM 编答案。
6. 能返回检索到的知识片段、分数、来源、最终 Prompt。
7. 有 20-30 条样本文档。
8. 有 Demo 脚本展示端到端流程。
9. 有验证报告，包含 Top-K 命中、分类结果、RAG vs 纯 LLM 对比。
10. README 能让别人配置 API Key 后跑起来。

**必要优先级**

第一优先级，必须做：

- 工程骨架
- `KnowledgeManager`
- LLM 分类 Prompt
- Embedding 调用
- 文档存储
- 向量检索
- 关键词检索
- 混合检索
- Prompt 组装
- Demo 脚本
- 设计文档和 README

这些是题目明确要求的主线，缺一个都会影响验收。

第二优先级，建议做：

- 查询改写
- 简单 LLM 重排
- 版本管理
- 过期过滤
- Token 长度控制
- 验证脚本
- 指标记录

这些会让项目从“能跑”变成“像一个组件”。

第三优先级，加分项：

- HyDE
- 动态分类规则
- 知识冲突检测
- 聚类重分类
- 更完整可观测性
- Web/API 服务
- 更漂亮的报告图表

这些不是第一版必要项，但适合放进设计文档的“后续优化”，或者在时间充裕时实现其中 1-2 个。

**建议实施步骤**

1. **先写最小工程骨架**
   - 必要。
   - 理由：后续所有代码都要围绕 `KnowledgeManager` 展开，先定入口可以避免散乱脚本。

2. **定义数据模型和存储 Schema**
   - 必要。
   - 理由：分类、检索、版本、过期都依赖统一的数据结构。

3. **实现 LLM 分类模块**
   - 必要。
   - 理由：题目重点之一就是“利用大模型做智能分类”，不能只写人工 metadata。

4. **实现 Embedding 和向量存储**
   - 必要。
   - 理由：语义检索是 RAG 的基础，也是题目硬要求。

5. **实现关键词检索**
   - 必要。
   - 理由：题目要求“关键词 + 向量混合检索”；关键词检索还能补足专有名词、产品名、规章编号等场景。

6. **实现混合召回和排序**
   - 必要。
   - 理由：这是检索质量的核心。第一版可以用加权分数：`final_score = 0.65 * vector_score + 0.35 * keyword_score`。

7. **实现 Prompt 组装和 Token 控制**
   - 必要。
   - 理由：RAG 最后交付给下游 LLM 的不是裸结果，而是受控上下文。

8. **准备样本文档和 Demo**
   - 必要。
   - 理由：验收需要可展示的端到端流程。

9. **写验证报告**
   - 必要。
   - 理由：题目明确要求功能验证、对比实验、边界测试。

10. **再补查询改写、重排、指标**
   - 推荐。
   - 理由：这几项能明显体现“大模型参与智能检索”，也适合作为加分点。

**当前推荐技术选择理由**

我建议第一版这样选：

- **Python**：实现快，RAG 生态成熟，便于 2 周内完成。
- **SQLite**：足够表达文档表、版本表、元数据、过期状态，轻量且好验收。
- **本地 JSON 向量库**：用本地内存实现。
- **OpenAI-compatible LLM Client**：避免绑定某一家模型，README 里只需配置 `BASE_URL`、`API_KEY`、`MODEL`、`EMBEDDING_MODEL`。
- **Prompt**：都交给你来帮我写。
- **先实现规则分数重排，再补 LLM 重排**：这样基础功能稳定，LLM 重排作为增强，不会卡住主流程。

**建议从哪里开始**

第一步我建议直接创建：

1. `docs/design.md`：把架构、流程、Schema、Prompt、检索策略先落下来。
2. `src/knowledge_base/manager.py`：定义 `KnowledgeManager` 的两个核心接口。
3. `src/knowledge_base/models.py`：定义数据结构。
4. `data/samples/`：准备样本文档。

也就是说，不要一开始就纠结 UI 或高级加分项。先把“入库 -> 分类 -> 存储 -> 检索 -> Prompt”的主链路跑通。这个主链路跑通后，项目就有骨架了，后面所有加分项都能自然挂上去。