"""lab6 Human-in-the-loop（interrupt、人工审核与恢复）

目标：
1. 用 compile(interrupt_before=[...]) 在「敏感工具」执行前暂停整张图
2. 人工审批两种结果：批准 → invoke(None) 原地恢复；拒绝 → update_state 回填拒绝 ToolMessage
3. 理解 checkpointer 是 HITL 的前提：没有持久化，暂停后无从恢复

对接配置：本 lab 目录下的 `config.json`（与 lab4 相同约定）
运行：uv run langgraph-agent
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


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


# ---------- 工具：安全类 vs 敏感类 ----------


@tool
def get_weather(city: str) -> str:
    """查询指定城市今天的天气。"""
    return {"北京": "晴，12°C", "上海": "多云，16°C"}.get(city, f"{city}：暂无数据")


@tool
def send_email(to: str, content: str) -> str:
    """发送一封邮件。对外发送属于敏感操作。"""
    return f"邮件已发送给 {to}：{content[:30]}..."


SAFE_TOOLS = [get_weather]
SENSITIVE_TOOLS = [send_email]
ALL_TOOLS = SAFE_TOOLS + SENSITIVE_TOOLS
SENSITIVE_NAMES = {t.name for t in SENSITIVE_TOOLS}


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def agent_node(state: State) -> dict:
    llm = make_llm().bind_tools(ALL_TOOLS)
    return {"messages": [llm.invoke(state["messages"])]}


def route_tools(state: State) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    """按 tool_calls 的名字分流：敏感工具进专用节点（它才是被暂停的对象）"""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        names = {c["name"] for c in last.tool_calls}
        return "sensitive_tools" if names & SENSITIVE_NAMES else "safe_tools"
    return END


def build_graph():
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("safe_tools", ToolNode(SAFE_TOOLS))
    builder.add_node("sensitive_tools", ToolNode(SENSITIVE_TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_tools)
    builder.add_edge("safe_tools", "agent")
    builder.add_edge("sensitive_tools", "agent")

    # 关键：sensitive_tools 之前暂停，等人工审批
    return builder.compile(
        checkpointer=InMemorySaver(),
        interrupt_before=["sensitive_tools"],
    )


def pending_tool_calls(graph, config) -> list[dict]:
    """被暂停时，取回模型想执行但还没执行的 tool_calls"""
    state = graph.get_state(config)
    return getattr(state.values["messages"][-1], "tool_calls", [])


def demo() -> None:
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")
    graph = build_graph()

    # 1) 安全工具：不触发中断，直接跑完
    config = {"configurable": {"thread_id": "t1"}}
    r = graph.invoke({"messages": [("user", "上海天气怎么样？")]}, config)
    print(f"[Q1 天气] {r['messages'][-1].content}\n")

    # 2) 敏感工具：中断 → 人工批准 → 恢复
    config = {"configurable": {"thread_id": "t2"}}
    graph.invoke({"messages": [("user", "请给 bob@example.com 发邮件，内容：明天开会")]}, config)
    calls = pending_tool_calls(graph, config)
    print(f"[Q2 发邮件] 已暂停，待审批: {[(c['name'], c['args']) for c in calls]}")
    print("[人工] 批准 → invoke(None) 恢复执行")
    r = graph.invoke(None, config)
    print(f"[Q2 结果] {r['messages'][-1].content}\n")

    # 3) 敏感工具：中断 → 人工拒绝 → 回填拒绝 ToolMessage 后恢复
    config = {"configurable": {"thread_id": "t3"}}
    graph.invoke({"messages": [("user", "给 alice@example.com 发邮件，内容：密码重置")]}, config)
    calls = pending_tool_calls(graph, config)
    print(f"[Q3 发邮件] 已暂停，待审批: {[(c['name'], c['args']) for c in calls]}")
    print("[人工] 拒绝 → update_state 回填拒绝消息 → 恢复")
    graph.update_state(
        config,
        {"messages": [ToolMessage(content="用户拒绝了此操作，请改用其他方式。", tool_call_id=calls[0]["id"])]},
    )
    r = graph.invoke(None, config)
    print(f"[Q3 结果] {r['messages'][-1].content}")


if __name__ == "__main__":
    demo()
