"""lab11 流式输出（stream tokens、stream events、自定义事件）

目标：
1. 掌握 graph.stream() 的三种模式：updates（节点级）/ messages（token 级）/ custom（节点内自定义事件）
2. 实现打字机式输出
3. 用 get_stream_writer() 从节点内部发进度事件
对接配置：本 lab 目录下的 `config.json`
运行：uv run langgraph-agent
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# ---------- 配置（与 lab4 相同） ----------


@dataclass
class LlmConfig:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.7

    @classmethod
    def load(cls) -> "LlmConfig":
        path = Path(__file__).resolve().parents[2] / "config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            base_url=data["base_url"],
            model=data["model"],
            api_key=data.get("api_key", ""),
            temperature=data.get("temperature", 0.7),
        )

    def effective_key(self) -> str:
        return self.api_key if self.api_key.strip() else "not-needed"


def make_llm():
    from langchain_openai import ChatOpenAI

    cfg = LlmConfig.load()
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.effective_key(),
        base_url=cfg.base_url,
        temperature=cfg.temperature,
    )


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def chat_node(state: State) -> dict:
    writer = get_stream_writer()  # 节点内拿「自定义事件发射器」
    writer({"progress": "开始思考..."})
    time.sleep(0.5)
    writer({"progress": "调用模型中..."})

    reply = make_llm().invoke(state["messages"])
    return {"messages": [reply]}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    return builder.compile()


QUESTION = "用三句话介绍一下 LangGraph 的核心概念。"


def demo_updates() -> None:
    """模式 1：updates —— 每个节点执行完吐一次（节点级粒度）"""
    print("=== 模式 1: stream_mode='updates'（节点级） ===")
    graph = build_graph()
    for chunk in graph.stream(
        {"messages": [("user", QUESTION)]},
        {"configurable": {"thread_id": "s1"}},
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            print(f"  节点 {node} 完成，产出 {len(update.get('messages', []))} 条消息")
    print()


def demo_messages() -> None:
    """模式 2：messages —— LLM 的 token 逐个流出（打字机效果）"""
    print("=== 模式 2: stream_mode='messages'（token 级打字机） ===")
    graph = build_graph()
    print("  [AI] ", end="", flush=True)
    for chunk, meta in graph.stream(
        {"messages": [("user", QUESTION)]},
        {"configurable": {"thread_id": "s2"}},
        stream_mode="messages",
    ):
        # 只打印我们 chat 节点里 LLM 的 token（过滤掉其它来源）
        if chunk.content and meta.get("langgraph_node") == "chat":
            print(chunk.content, end="", flush=True)
    print("\n")


def demo_custom() -> None:
    """模式 3：custom —— 节点内 writer() 发的自定义事件"""
    print("=== 模式 3: stream_mode='custom'（节点内自定义事件） ===")
    graph = build_graph()
    for event in graph.stream(
        {"messages": [("user", QUESTION)]},
        {"configurable": {"thread_id": "s3"}},
        stream_mode="custom",
    ):
        print(f"  [自定义事件] {event}")
    print()


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")
    demo_updates()
    demo_messages()
    demo_custom()


if __name__ == "__main__":
    main()
