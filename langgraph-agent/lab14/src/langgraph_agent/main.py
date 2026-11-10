"""lab14 综合实验：个人AI分身（多智能体 + 工具 + HITL + 双记忆 + 流式）

场景：用户的「个人 AI 分身」，能算账、查知识库；对外发邮件前必须人工审批。

综合能力对照：
  lab2  add_messages reducer          -> State
  lab3  条件边路由                    -> 工具分流（安全/敏感）
  lab4  checkpointer 短期记忆         -> compile(checkpointer=...)
  lab5  ReAct 工具调用                -> agent + ToolNode 回路
  lab6  interrupt 人工审批            -> interrupt_before=["sensitive_tools"]
  lab10 Store 长期记忆                -> 记住用户名字，跨 thread 可见
  lab11 流式输出                      -> stream_mode="messages"

对接配置：本 lab 目录下的 `config.json`
运行：uv run langgraph-agent
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_store
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
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


# ---------- 工具集：计算（安全）、查知识库（安全）、发周报（敏感） ----------

KB = {
    "langgraph": "LangGraph 是状态图智能体编排框架，支持回路、条件边、checkpoint 与人工中断。",
    "python": "Python 是解释型高级语言，生态丰富，广泛用于数据科学与 AI 工程。",
}


@tool
def calculate(expression: str) -> str:
    """计算一个四则运算表达式，如 '3+5*12'。所有数学计算必须用本工具。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "表达式含非法字符"
    return str(eval(expression))  # noqa: S307 教学演示，输入已过滤


@tool
def lookup_kb(keyword: str) -> str:
    """在内部知识库中查询关键词（支持：langgraph、python）。"""
    return KB.get(keyword.lower(), f"知识库中没有关于 {keyword} 的条目")


@tool
def send_report(to: str, content: str) -> str:
    """把一段总结以邮件形式发送给指定收件人。对外发送属于敏感操作。"""
    return f"周报已发送给 {to}（正文 {len(content)} 字）"


SAFE_TOOLS = [calculate, lookup_kb]
SENSITIVE_TOOLS = [send_report]
ALL_TOOLS = SAFE_TOOLS + SENSITIVE_TOOLS
SENSITIVE_NAMES = {t.name for t in SENSITIVE_TOOLS}


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# ---------- 节点 ----------


def agent_node(state: State) -> dict:
    store = get_store()
    profile = [f"- {i.key}: {i.value}" for i in store.search(("users", "andrew"))]
    system = "你是用户的个人 AI 分身，用中文简洁回答。"
    if profile:
        system += f"\n你长期记住的用户信息：\n" + "\n".join(profile)
    reply = make_llm().bind_tools(ALL_TOOLS).invoke([("system", system)] + state["messages"])

    # 长期记忆：首次自我介绍时记录（生产用 LLM 结构化抽取）
    text = state["messages"][-1].content
    if not profile and "我叫" in text:
        store.put(("users", "andrew"), "名字", {"自我介绍": text[:40]})
    return {"messages": [reply]}


def route_tools(state: State) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    last = state["messages"][-1]
    calls = getattr(last, "tool_calls", []) or []
    if not calls:
        return END
    names = {c["name"] for c in calls}
    return "sensitive_tools" if names & SENSITIVE_NAMES else "safe_tools"


def build_graph():
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("safe_tools", ToolNode(SAFE_TOOLS))
    builder.add_node("sensitive_tools", ToolNode(SENSITIVE_TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_tools)
    builder.add_edge("safe_tools", "agent")
    builder.add_edge("sensitive_tools", "agent")

    # 三件套一次配齐：短期记忆 + 敏感操作人工审批 + 长期记忆
    return builder.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=["sensitive_tools"],
        store=InMemoryStore(),
    )


def pending_tool_calls(g, config) -> list[dict]:
    return getattr(g.get_state(config).values["messages"][-1], "tool_calls", [])


def run_streaming(g, text: str, config: RunnableConfig) -> None:
    """流式执行：token 级打字机（lab11），结束时返回最终 state"""
    print(f"[用户] {text}")
    print("[AI] ", end="", flush=True)
    last = None
    for chunk, meta in g.stream({"messages": [("user", text)]}, config, stream_mode="messages"):
        if chunk.content and meta.get("langgraph_node") == "agent":
            print(chunk.content, end="", flush=True)
    print()
    last = g.get_state(config).values["messages"][-1]
    return last


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")

    g = build_graph()
    config = {"configurable": {"thread_id": "capstone-1"}}

    # 第 1 轮：自我介绍 -> 写入长期记忆（Store）
    run_streaming(g, "你好，我叫 Andrew，是我的分身，请记住我。", config)
    print()

    # 第 2 轮：ReAct 两跳工具调用（安全工具）
    run_streaming(g, "帮我算一下 3+5 再乘以 12", config)
    print()

    # 第 3 轮：知识库 + 敏感操作 -> 人工审批
    last = run_streaming(g, "查一下 langgraph 是什么，然后把简介发给 bob@example.com", config)
    print()

    calls = pending_tool_calls(g, config)
    if calls:
        print(f"[暂停] 敏感操作待审批: {[(c['name'], c['args']) for c in calls]}")
        print("[人工] 批准 -> invoke(None) 恢复")
        result = g.invoke(None, config)
        print(f"[AI] {result['messages'][-1].content}\n")

    # 第 4 轮：验证短期记忆（同 thread 历史仍在）
    run_streaming(g, "我刚才让你算的那道题，结果是多少？", config)
    print()

    # 验证长期记忆：换一个全新 thread
    config2 = {"configurable": {"thread_id": "capstone-2"}}
    run_streaming(g, "我叫什么名字？", config2)
    print()


if __name__ == "__main__":
    main()
