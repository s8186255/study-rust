# lab10 长期记忆（Store、跨 thread 的用户画像）

用 Store 实现跨 thread 的长期记忆，与 lab4 的 checkpointer（thread 内短期记忆）形成对照。
模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab10
uv sync
uv run langgraph-agent
```

## 预期输出

- thread-A：用户自我介绍，助手回应
- thread-B：全新会话（无对话历史），但助手能答出「Andrew / Python」——画像来自 Store
- 最后打印 Store 内容：`namespace=("users","andrew") key=profile`

## 关键点

- **两种记忆对照**：checkpointer 存「对话历史」（thread 隔离），Store 存「用户画像等事实」（跨 thread 共享）
- **Store 三件套**：`put(namespace, key, value)` 写、`get(namespace, key)` 读、`search(namespace)` 列出
- **namespace 层级**：`("users", USER_ID)` —— 第一层是记忆类型，第二层是用户 ID，天然支持多租户隔离
- **注入方式**：节点内 `get_store()` 取 Store，把画像拼进 system prompt；编译时 `compile(store=...)` 注入
- **生产替换**：`InMemoryStore` 换成 `PostgresStore` 即持久化；语义记忆（向量搜索）用 `store.search(query=...)`
- 本 lab 的画像抽取是关键词规则，生产用 LLM 结构化抽取后写入
