# lab13 部署（langgraph dev、LangGraph Platform、API 服务化）

把 StateGraph 服务化为 HTTP API，理解「状态外置」的部署架构。图用 echo 离线可跑。

## 运行方式

```powershell
cd langgraph-agent\lab13
uv sync

# 方式 1：自测（TestClient 完整走一遍 HTTP 流程，无需起进程）
uv run langgraph-agent

# 方式 2：起真实服务
uv run uvicorn langgraph_agent.main:app --port 8123
# 然后访问 http://127.0.0.1:8123/docs 看 Swagger，或：
# curl -X POST http://127.0.0.1:8123/chat -H "Content-Type: application/json" -d '{"message":"hi","thread_id":"t1"}'
```

## 预期输出（自测模式）

- `POST /chat #1`：reply=`echo: 你好`，message_count=2
- `POST /chat #2`（同 thread）：message_count=4——checkpointer 记住了历史
- `GET /threads/t1`：返回完整消息历史
- `POST /chat`（新 thread）：message_count=2——线程隔离生效

## 关键点

- **无状态服务**：API 进程不存任何会话状态；状态全在 checkpointer。水平扩容时把
  `InMemorySaver` 换成 `PostgresSaver`/`RedisSaver` 即可多实例共享
- **thread_id 由客户端传**：服务端只按 thread_id 读写状态，与登录态解耦
- **langgraph dev**：本目录含 `langgraph.json`，安装 `langgraph-cli[inmem]` 后
  `uv run langgraph dev` 可启动官方开发服务器（Studio 可视化调试，零代码部署 API）
- **LangGraph Platform**：生产托管方案，提供 threads/runs/assistants API、持久化、定时任务；
  自建时本 lab 的 FastAPI 骨架即等价物的起点
