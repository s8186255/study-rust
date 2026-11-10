# lab12 容错与工程化（重试、fallback、并发控制、LangSmith 观测）

用 fake 模型离线演示三大工程能力：节点重试、模型 fallback、超步并行。
无 LLM 依赖，纯本地运行。

## 运行方式

```powershell
cd langgraph-agent\lab12
uv sync
uv run langgraph-agent
```

## 预期输出

- 重试：`flaky_node` 第 1、2 次抛错，第 3 次成功（RetryPolicy 自动退避重试）
- fallback：主模型抛错，日志可见异常被捕获，最终输出备用模型的回答
- 并行：`branch_a` / `branch_b` 在同一超步执行，两份结果都写入 state

## 关键点

- **RetryPolicy**：`add_node("x", fn, retry=RetryPolicy(max_attempts=3, initial_interval=0.1))`，
  指数退避，只重试可重试的异常类型（默认不含 ValueError 等，可配 `retry_on`）
- **with_fallbacks**：`primary.with_fallbacks([backup])`，按顺序尝试；与 RetryPolicy 互补——
  重试解决「瞬时故障」，fallback 解决「整个服务不可用」
- **超步（superstep）**：LangGraph 的执行单元。无依赖的节点在同一超步内并发；
  同一超步内两个节点写同一个无 reducer 字段 → `InvalidUpdateError`，必须加 reducer（呼应 lab2）
- **LangSmith**：设 `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` 即自动上报每次 run 的
  完整轨迹（节点输入输出、token 消耗、延迟），无需改代码
