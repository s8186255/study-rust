# lab8 多智能体协作（supervisor、swarm、handoff）

实现 supervisor 模式：调度员用 handoff 工具把任务移交给专家智能体，专家答完回调度员复核。
模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab8
uv sync
uv run langgraph-agent
```

## 预期输出

- 技术问题 → `[supervisor] 决定: [transfer_to_tech]` → 技术专家的专业回答
- 闲聊问题 → `[supervisor] 决定: [transfer_to_general]` → 通用助手的轻松回答
- 专家回答后回调度员，调度员 `finish` 结束

## 关键点

- **共享消息流**：所有智能体读写同一个 `messages`（`add_messages`），这是 lab2 reducer 的直接应用
- **handoff 工具**：`transfer_to_xxx` 本身不干活（ToolNode 执行只返回一句话），真正的作用是让调度员用「函数调用」这个结构化接口表达路由意图，路由函数解析 `tool_calls` 后决定下一节点
- **专家不握手**：专家 `bind_tools([])`，只回答不移交，控制权回收交给 supervisor——职责清晰
- **温度策略**：调度员用 `temperature=0`（路由要稳定），专家用默认温度（回答要有个性）
- supervisor / swarm / handoff 是多智能体三种常见拓扑，本 lab 是 supervisor；swarm（专家间直接移交）在 lab8 基础上给专家也配上 handoff 工具即可
