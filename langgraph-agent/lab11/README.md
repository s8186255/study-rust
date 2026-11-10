# lab11 流式输出（stream tokens、stream events、自定义事件）

掌握 `graph.stream()` 的三种流式模式，实现打字机输出与节点内进度上报。
模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab11
uv sync
uv run langgraph-agent
```

## 预期输出

- 模式 1 `updates`：`节点 chat 完成，产出 1 条消息`（节点级，一次一条）
- 模式 2 `messages`：回答逐 token 打出（打字机效果）
- 模式 3 `custom`：`[自定义事件] {'progress': '开始思考...'}` 等

## 关键点

- **updates**：粒度=节点。每个节点执行完，吐出 `{节点名: 增量state}`，适合做「执行轨迹」展示
- **messages**：粒度=token。yield `(消息片段, 元数据)`；用 `meta["langgraph_node"]` 过滤来源节点，实现打字机
- **custom**：节点内 `get_stream_writer()` 拿发射器，`writer(任意json)` 上报进度（如「正在检索…」「已读 3/10 篇」），前端可做进度条
- 三种模式可同时开：`stream_mode=["updates", "messages", "custom"]`，每条流带模式标签
- `invoke()` 是 `stream()` 的「全部吃完」版本；生产 API 用 SSE/WebSocket 把流转发给前端
