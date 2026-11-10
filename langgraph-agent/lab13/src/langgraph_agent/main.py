"""lab13 部署（langgraph dev、LangGraph Platform、API 服务化）

目标：
1. 用 FastAPI 把图包装成 HTTP 服务：POST /chat（对话）、GET /threads/{id}（历史）
2. 理解服务化的三个要素：全局图实例 + checkpointer（thread 隔离）+ config 传递
3. README 说明 langgraph.json + `langgraph dev` 的官方开发服务器路径
图用无 LLM 的 echo 图，保证离线可运行；换 chatbot 图即成真实服务。
运行：
  uv run langgraph-agent            # 自测（TestClient 调用 HTTP 接口，无需起进程）
  uv run uvicorn langgraph_agent.main:app --port 8123   # 起真实服务
"""

from typing import Annotated, TypedDict

from fastapi import FastAPI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel


# ---------- 图：echo chatbot（离线可跑；生产换成带 LLM 的图） ----------


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot(state: State) -> dict:
    last = state["messages"][-1].content
    return {"messages": [{"role": "assistant", "content": f"echo: {last}"}]}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    # 全局唯一 checkpointer：thread 隔离靠 thread_id，不是靠多个图实例
    return builder.compile(checkpointer=InMemorySaver())


graph = build_graph()

# ---------- HTTP 服务 ----------

app = FastAPI(title="langgraph lab13", description="把 StateGraph 服务化为 API")


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    message_count: int


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """对话接口：thread_id 决定会话归属，服务端无会话状态（状态在 checkpointer 里）"""
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke({"messages": [("user", req.message)]}, config)
    return ChatResponse(
        thread_id=req.thread_id,
        reply=result["messages"][-1].content,
        message_count=len(result["messages"]),
    )


@app.get("/threads/{thread_id}")
def history(thread_id: str) -> dict:
    """会话历史：直接从 checkpointer 读，体现「状态外置」的架构"""
    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    msgs = state.values.get("messages", []) if state.values else []
    return {
        "thread_id": thread_id,
        "messages": [{"role": m.type, "content": m.content} for m in msgs],
    }


# ---------- 自测：不起进程，用 TestClient 走完整 HTTP 流程 ----------


def selftest() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r1 = client.post("/chat", json={"message": "你好", "thread_id": "t1"})
    print("POST /chat #1:", r1.json())

    r2 = client.post("/chat", json={"message": "我上一句说了什么？", "thread_id": "t1"})
    print("POST /chat #2:", r2.json(), "（message_count=4 说明同一 thread 有记忆）")

    r3 = client.get("/threads/t1")
    print("GET  /threads/t1:", r3.json())

    r4 = client.post("/chat", json={"message": "新会话", "thread_id": "t2"})
    print("POST /chat（新 thread）:", r4.json(), "（message_count=2 说明线程隔离）")


def main() -> None:
    selftest()


if __name__ == "__main__":
    main()
