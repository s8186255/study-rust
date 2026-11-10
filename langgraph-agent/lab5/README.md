# lab5 工具调用与 ReAct 智能体（ToolNode、tool calling）

用 `@tool` 定义工具、`bind_tools` 绑定模型，手写 ReAct 循环，并对照预构建的 `create_react_agent`。
模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab5
uv sync
uv run langgraph-agent           # 脚本化演示：手写 ReAct 解决两道题
uv run langgraph-agent --chat    # 交互式 ReAct 对话（输入 q 退出）
```

## 预期输出（demo 模式）

- `3 + 5 再乘以 12`：模型先调 `add(3,5)` 再调 `multiply(8,12)`，最终回答 96
- `北京天气`：调 `get_weather("北京")`，回答晴 12°C
- 对照组：`create_react_agent` 对同类问题给出一致结果

## 关键点

- `@tool` 的 docstring 是给模型看的「使用说明书」，写清楚何时用、参数含义
- `bind_tools` 只是把工具 schema 发给模型；模型返回 `AIMessage.tool_calls`（想调用），**执行权在图里的 ToolNode**
- `tools_condition`：有 tool_calls → `tools` 节点；没有 → `END`
- `tools → agent` 的回边就是 ReAct 的「回路」：工具结果以 `ToolMessage` 追加进消息流，模型继续推理
- `create_react_agent` = 手写 ReAct 的预打包版本（agent 节点 + ToolNode + 条件边 + 提示词模板）
