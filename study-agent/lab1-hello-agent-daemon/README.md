# Lab1-daemon：交互式 Agent（D1-M2）

在 [lab1-hello-agent](../lab1-hello-agent) 基础上演进：

- `system`（系统提示词）配置在 `config.json`，改配置即改人设，无需重编译
- 运行后进入终端交互循环：`you>` 输入 → `assistant>` 回答 → 继续输入
- 退出：输入 `exit` / `quit` / `q` / `退出`，或 Ctrl+Z（回车）/ Ctrl+D（EOF）

## 步骤

```bash
cargo run -p lab1-hello-agent-daemon
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

1. 每轮对话之间有记忆吗？（没有——每轮独立请求；多轮记忆是扩展练习）
2. `system` 和用户输入有什么区别？（一个随 config 固定，一个每轮由用户给）
3. `temperature=0` 能保证输出完全一样吗？

## 扩展练习

- 改 `config.json` 的 `system` 为中文人设，观察风格变化
- 多轮对话：把上一轮问答存入 history 传给下一轮（见 main.rs 课堂练习）
- 直连 DashScope 等其它 OpenAI 兼容服务：只改 `base_url` / `model` / `api_key`
