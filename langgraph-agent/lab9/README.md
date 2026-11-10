# lab9 检索增强生成 RAG（crag、self-rag 工作流）

用图编排 CRAG-lite 工作流：检索 → 文档相关性评分 → 不合格则改写查询再检索 → 生成回答。
模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab9
uv sync
uv run langgraph-agent
```

## 预期输出

- 检索日志：`[retrieve] query=... -> N 篇文档`
- 评分日志：`[grade] 模型判定: YES/NO`
- 命中时直接生成；未命中时出现 `[rewrite]` 日志并回到 retrieve（回路）
- 两个问题分别命中 doc1/doc2 与 doc4

## 关键点

- **CRAG 思想**：检索质量把关（grade）不过关就「改写查询再检索」，而不是拿烂上下文硬答
- **回路**：`grade -> rewrite -> retrieve -> grade` 这条环是链式结构做不到的，必须用图
- **兜底**：`MAX_RETRIES` 超限后强制进入 generate，避免无限循环——工作流必须有出口
- **检索器**：本 lab 用关键词打分模拟，接口与向量检索一致（输入 query、输出 docs），生产替换为向量库即可
- **Self-RAG 扩展**：在 generate 后再加一个「回答质量自评」节点，不合格就重来，即 Self-RAG 的自查思想
