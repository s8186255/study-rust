# lab7 子图（subgraph）与状态组合复用

把编译后的图当节点嵌入父图，理解「图即节点」的组合方式。不调用 LLM，纯本地运行。

## 运行方式

```powershell
cd langgraph-agent\lab7
uv run langgraph-agent
```

## 预期输出

- 子图 1（clean）打印清洗后的文本
- 父图最终 State：`text` 被清洗、`char_count`/`word_count` 来自子图 2
- 父图拓扑只显示 `clean / stats` 两个节点（子图内部结构对父图不可见）

## 关键点

- **方式 1（同名状态）**：子图 State 与父图有同名字段（`text`）时，编译后的子图可直接 `add_node`，状态自动透传
- **方式 2（schema 映射）**：子图字段名不同（`content`）时，用普通节点函数包一层，手工搬运进/出子图
- 子图可单独测试、单独复用；lab1 的 `build_graph()` 封装正是为此准备
- 复杂系统的推荐拆法：每个子图负责一件事，父图只管编排
