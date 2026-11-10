# lab6 Human-in-the-loop（interrupt、人工审核与恢复）

敏感操作前暂停整张图，等人工审批后再恢复或拒绝。模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab6
uv sync
uv run langgraph-agent
```

## 预期输出（demo 模式，三问三答）

- Q1 查天气：安全工具，不中断，直接回答
- Q2 发邮件：在 `sensitive_tools` 前暂停 → 打印待审批的 tool_calls → 模拟批准 → `invoke(None)` 恢复 → 邮件「已发送」
- Q3 发邮件：暂停 → 模拟拒绝 → `update_state` 回填拒绝 `ToolMessage` → 恢复 → 模型改口给出替代方案

## 关键点

- `compile(checkpointer=..., interrupt_before=["sensitive_tools"])`：暂停点必须配 checkpointer，恢复靠持久化的断点
- `graph.invoke(None, config)`：传 None 表示「从中断处继续」，不注入新输入
- 分流设计：安全工具走 `safe_tools` 节点不受影响，只有 `sensitive_tools` 被设为中断点——审批粒度是节点级
- 拒绝的标准姿势：用 `update_state` 手动补一条 `ToolMessage(tool_call_id=...)`，让消息流保持成对，模型才能继续推理
