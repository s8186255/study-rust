# Lab1-daemon-typer：真·流式输出的交互式 Agent（D1-M2）

在 [lab1-hello-agent-daemon](../lab1-hello-agent-daemon) 基础上演进：

- `agent.prompt(..).stream()` 发起流式请求（`"stream": true`，SSE）
- **LLM 每生成一段 token 就立刻打印**——输出速度完全由模型决定，无人为延时
- 退出：输入 `exit` / `quit` / `q` / `退出`，或 Ctrl+Z（回车）/ Ctrl+D（EOF）

## 步骤

```bash
cargo run -p lab1-hello-agent-daemon-typer
```

## config.json

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "temperature": 0.7,
  "system": "You are a helpful assistant."
}
```

## 检查点（口头验收）

1. 这是「真流式」还是「假动画」？（真的——`stream` 事件流，token 到达即显示；与 daemon 版的长问题首字延迟对比）
2. 流里除了文本还有什么？（工具调用/结果事件、CompletionCall（含 usage）、最后的 FinalResponse）
3. 每轮对话之间有记忆吗？（没有——每轮独立请求）

## 扩展练习

- 用 `CompletionCall` 事件统计本次回答的 token 用量
- 多轮对话：把 FinalResponse 里的消息存入 history 传给下一轮
- 直连 DashScope 等其它 OpenAI 兼容服务：只改 `base_url` / `model` / `api_key`

