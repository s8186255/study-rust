# lab1 环境搭建与第一个图（Hello World）

跑通第一个 `StateGraph`，理解「State -> 节点 -> 边 -> compile -> invoke」五步。
不调用任何 LLM，纯本地运行。

## 运行方式

### 方式 1：命令入口（推荐）

`pyproject.toml` 的 `[project.scripts]` 已定义入口，安装后即可作为命令调用：

```powershell
cd langgraph-agent\lab1
uv run langgraph-agent
```

### 方式 2：直接运行文件

`main.py` 未使用相对导入，可直接以文件路径执行：

```powershell
cd langgraph-agent\lab1
uv run python src/langgraph_agent/main.py
```

> 首次运行或依赖变更后，先执行 `uv sync`（`uv run` 通常会自动处理）。

## 预期输出

- 最终 State：`{'message': 'Hello, langgraph!', 'word_count': 2}`
- 图拓扑：`__start__ -> greet -> count_words -> __end__`（ASCII 图）

## 说明

- 方式 1 依赖 `pyproject.toml` 的入口声明，包结构调整不受影响；
  方式 2 依赖「文件内没有相对导入」，代码引入相对导入后会失效，故优先方式 1。
