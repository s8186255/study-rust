"""lab8 多智能体协作（supervisor、swarm、handoff）

目标：
1. 实现 supervisor 模式：调度者智能体看消息、决定「交给哪个专家」
2. 用 handoff 工具（transfer_to_xxx）表达控制权移交
3. 理解多智能体的本质：多个「各有系统提示词和工具集」的 LLM 节点 + 路由回路
对接配置：本 lab 目录下的 `config.json`（与 lab4 相同约定）
运行：uv run langgraph-agent
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


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


def make_llm(temperature: float | None = None):
    from langchain_openai import ChatOpenAI

    cfg = LlmConfig.load()
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.effective_key(),
        base_url=cfg.base_url,
        temperature=temperature if temperature is not None else cfg.temperature,
    )


# ---------- State：所有智能体共享同一条消息流 ----------


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    next_agent: str  # supervisor 写入的路由决定


# ---------- handoff 工具：模型用它「表达」移交意向 ----------


@tool
def transfer_to_tech() -> str:
    """当用户的问题是编程、软件、技术相关时，移交给技术专家处理。"""
    return "移交技术专家"


@tool
def transfer_to_general() -> str:
    """当用户的问题是闲聊、生活、非技术类问题时，移交通用助手处理。"""
    return "移交通用助手"


@tool
def finish() -> str:
    """当专家已完成回答、任务结束时调用。"""
    return "任务完成"


HANDOFF_TOOLS = [transfer_to_tech, transfer_to_general, finish]


# ---------- 节点：supervisor 与两个专家 ----------


def supervisor_node(state: State) -> dict:
    """调度者：不直接回答问题，只决定 next_agent"""
    system = (
        "你是调度员。查看对话历史，用 transfer_to_tech / transfer_to_general 把任务"
        "移交给合适的专家；若任务已完成（历史里已有专家的最终回答），调用 finish。"
        "每次只调用一个工具。"
    )
    llm = make_llm(temperature=0.0).bind_tools(HANDOFF_TOOLS)
    reply = llm.invoke([("system", system)] + state["messages"])
    return {"messages": [reply]}


def tech_expert_node(state: State) -> dict:
    llm = make_llm().bind_tools([])  # 专家不带 handoff 工具，专心回答
    system = "你是资深技术专家，用中文简洁准确地回答技术问题。"
    reply = llm.invoke([("system", system)] + state["messages"])
    return {"messages": [reply]}


def general_expert_node(state: State) -> dict:
    llm = make_llm().bind_tools([])
    system = "你是一个风趣的通用助手，用中文轻松地回答非技术问题。"
    reply = llm.invoke([("system", system)] + state["messages"])
    return {"messages": [reply]}


# ---------- 路由：解析 supervisor 的 handoff 意图 ----------


def route_after_supervisor(state: State) -> Literal["handoff_tools", "__end__"]:
    last = state["messages"][-1]
    calls = getattr(last, "tool_calls", []) or []
    # 移交工具必须先经 ToolNode 执行（回填 ToolMessage），否则消息流里
    # 会出现「带 tool_calls 的 AI 消息悬空」，很多 OpenAI 兼容服务端会报 400
    return "handoff_tools" if calls else END


def route_after_handoff(state: State) -> Literal["tech", "general", "__end__"]:
    """看刚执行的移交工具是哪个，决定去哪个专家；finish 则结束"""
    last = state["messages"][-1]  # 是 handoff 工具的 ToolMessage
    name = getattr(last, "name", "")
    return {"transfer_to_tech": "tech", "transfer_to_general": "general"}.get(name, END)


def route_after_expert(state: State) -> Literal["supervisor", "__end__"]:
    """专家答完回 supervisor 复核"""
    return "supervisor"


def build_graph():
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("tech", tech_expert_node)
    builder.add_node("general", general_expert_node)
    builder.add_node("handoff_tools", ToolNode(HANDOFF_TOOLS))

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges("supervisor", route_after_supervisor)
    builder.add_conditional_edges("handoff_tools", route_after_handoff)
    builder.add_edge("tech", "supervisor")  # 专家答完 → 回调度员复核
    builder.add_edge("general", "supervisor")

    return builder.compile(checkpointer=InMemorySaver())


def main() -> None:
    # Windows GBK 控制台打不出 emoji 等字符，改为容错替换，避免程序崩溃
    sys.stdout.reconfigure(errors="replace")
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")
    graph = build_graph()

    for i, q in enumerate(["用 Python 怎么读 CSV 文件？", "给我讲个程序员笑话"]):
        config = {"configurable": {"thread_id": f"demo-{i}"}}
        print(f"[用户] {q}")
        result = graph.invoke({"messages": [("user", q)]}, config)
        # 打印调度轨迹：谁被移交给谁
        for m in result["messages"]:
            if getattr(m, "tool_calls", None):
                print(f"  [supervisor] 决定: {[c['name'] for c in m.tool_calls]}")
        print(f"  [最终回答] {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
