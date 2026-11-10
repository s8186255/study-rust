# lab3 节点与边（顺序边、条件边、START/END）

掌握动态路由的两种写法：`add_conditional_edges`（边上路由）与 `Command(goto=...)`（节点内路由）。
不调用任何 LLM（用关键词规则模拟分类器），纯本地运行。

## 运行方式

### 方式 1：命令入口（推荐）

```powershell
cd langgraph-agent\lab3
uv run langgraph-agent
```

### 方式 2：直接运行文件

```powershell
cd langgraph-agent\lab3
uv run python src/langgraph_agent/main.py
```

> 首次运行或依赖变更后，先执行 `uv sync`（`uv run` 通常会自动处理）。

## 预期输出

- 两个查询分别路由到 tech / general 线路，图 1 与图 2 结果一致
- 图拓扑：`__start__ -> classify -> (tech | general) -> __end__`
