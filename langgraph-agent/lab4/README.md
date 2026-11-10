# lab4 Chatbot 与短期记忆（checkpointer、thread、多轮对话）

接入第一个 LLM，用 checkpointer 让图拥有多轮对话记忆，理解 thread_id 的会话隔离。

## 模型配置

本 lab 目录下的 `config.json`（与 rig `study-agent/lab1-hello-agent` 同一约定）：

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "temperature": 0.7
}
```

- `api_key` 可留空（服务端未启用鉴权时代码自动用占位值）
- 改 `base_url` / `model` 即可切换模型服务，代码不动

## 运行方式

```powershell
cd langgraph-agent\lab4
uv sync
uv run langgraph-agent           # 脚本化演示：同一 thread 连续三轮，验证记忆
uv run langgraph-agent --chat    # 交互式多轮对话（输入 q 退出）
```

## 预期输出（demo 模式）

- 第 1 轮：告知姓名和喜欢的数字
- 第 2 轮：AI 能答出「Andrew」——记忆生效
- 第 3 轮：AI 能算出「420」——更早的历史仍在

## 关键点

- `compile(checkpointer=InMemorySaver())` 是记忆的开关：去掉它，每轮 invoke 都从零开始
- `thread_id` 在 `config["configurable"]` 里传入；换一个 thread_id 就是一个全新会话
- 记忆的载体是 State 里的 `messages`（`add_messages` 追加），checkpointer 负责每步之后持久化/恢复
- `InMemorySaver` 只活在进程内；换成 `SqliteSaver` / `PostgresSaver` 即可跨进程持久化
