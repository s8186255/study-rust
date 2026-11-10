"""lab10 长期记忆（Store、跨 thread 的用户画像）

目标：
1. 区分两种记忆：checkpointer（thread 内短期）vs Store（跨 thread 长期）
2. 掌握 Store 三件套：put（写入）/ get（读取）/ search（搜索）
3. 在节点里读写用户画像：新 thread 的对话也能「记得」用户是谁
对接配置：本 lab 目录下的 `config.json`
运行：uv run langgraph-agent
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_store
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.store.memory import InMemoryStore


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


USER_ID = "andrew"  # 真实系统里来自登录态


# ---------- 节点 ----------


def chat_node(state: State) -> dict:
    """带长期记忆的对话节点：回答前先查用户画像，注入系统提示词"""
    store = get_store()  # 编译时注入的 Store，运行时从上下文取
    namespace = ("users", USER_ID)

    profile = None
    items = list(store.search(namespace))  # search：列出该用户所有记忆
    if items:
        profile = "\n".join(f"- {i.key}: {i.value}" for i in items)

    system = "你是贴心的私人助手。"
    if profile:
        system += f"\n以下是长期记住的用户画像：\n{profile}"
    else:
        system += "\n你还不知道用户的信息，如果用户做了自我介绍，请记住关键信息。"

    reply = make_llm().invoke([("system", system)] + state["messages"])

    # 简单画像抽取：仅当「还没有画像」且命中自我介绍句式时写入（生产用 LLM 结构化抽取）
    text = state["messages"][-1].content
    if not items and "我叫" in text:
        store.put(namespace, "profile", {"自我介绍": text[:80]})

    return {"messages": [reply]}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("chat", chat_node)
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    # 关键差异：Store 是编译参数，与 checkpointer 并列；它不属于任何 thread
    return builder.compile(store=InMemoryStore())


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")
    graph = build_graph()

    # thread A：用户自我介绍（写入长期记忆）
    config_a = {"configurable": {"thread_id": "thread-A"}}
    r = graph.invoke({"messages": [("user", "你好，我叫 Andrew，我最喜欢的语言是 Python。")]}, config_a)
    print(f"[thread-A] {r['messages'][-1].content}\n")

    # thread B：全新会话（thread 内没有历史），但 Store 里有人画像
    config_b = {"configurable": {"thread_id": "thread-B"}}
    r = graph.invoke({"messages": [("user", "猜猜我叫什么名字？喜欢什么语言？")]}, config_b)
    print(f"[thread-B] {r['messages'][-1].content}\n")

    # 直接查看 Store 内容
    print("Store 内容（跨 thread 共享）:")
    for item in graph.store.search(("users", USER_ID)):
        print(f"  namespace={item.namespace} key={item.key} value={item.value}")


if __name__ == "__main__":
    main()
