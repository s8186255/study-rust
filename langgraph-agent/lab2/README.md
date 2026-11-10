# lab2 State 与 Reducer（状态定义、add_messages）

理解 State 字段的三种 Reducer 合并语义：默认覆盖、`add_messages` 追加、自定义 reducer 拼接。
不调用任何 LLM，纯本地运行。

## 运行方式

### 方式 1：命令入口（推荐）

```powershell
cd langgraph-agent\lab2
uv run langgraph-agent
```

### 方式 2：直接运行文件

```powershell
cd langgraph-agent\lab2
uv run python src/langgraph_agent/main.py
```

> 首次运行或依赖变更后，先执行 `uv sync`（`uv run` 通常会自动处理）。

## 预期输出

- `answer` 被覆盖：只剩 node_b 的值
- `steps` 被拼接：node_a、node_b 各留一条
- `messages` 被追加：两条消息都在列表里
- 图拓扑：`__start__ -> node_a -> node_b -> __end__`
