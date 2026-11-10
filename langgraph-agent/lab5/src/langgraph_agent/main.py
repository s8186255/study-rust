"""lab5 工具调用与 ReAct 智能体（ToolNode、tool calling）

目标：
1. 用 @tool 定义工具，bind_tools 绑定到模型（模型只「决定调用」，执行权在图里）
2. 手写 ReAct 循环：agent 节点 → tools_condition 条件边 → ToolNode → 回到 agent
3. 对照预构建的 create_react_agent，理解它替你做了什么

对接配置：本 lab 目录下的 `config.json`（与 lab4 相同约定）
运行：
  uv run langgraph-agent           # 脚本化演示：手写 ReAct 解决两道题
  uv run langgraph-agent --chat    # 交互式（create_react_agent 版本）
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition


# ---------- 配置：与 lab4 相同的 config.json 约定 ----------


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


# ---------- 1. 定义工具：docstring 就是给模型看的「使用说明书」 ----------


@tool
def add(a: float, b: float) -> float:
    """计算两个数的和。需要做加法时必须使用本工具，不要心算。"""
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """计算两个数的乘积。需要做乘法时必须使用本工具，不要心算。"""
    return a * b


@tool
def get_weather(city: str) -> str:
    """查询指定城市今天的天气。仅支持北京、上海、深圳。"""
    fake = {"北京": "晴，12°C", "上海": "多云，16°C", "深圳": "阵雨，24°C"}
    return fake.get(city, f"{city}：暂无数据")


TOOLS = [add, multiply, get_weather]


# ---------- 2. 手写 ReAct：State + agent 节点 + 工具回路 ----------


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def agent_node(state: State) -> dict:
    # bind_tools：把工具 schema 随请求发给模型；模型的 tool_calls 出现在 AIMessage 里
    llm = make_llm().bind_tools(TOOLS)
    return {"messages": [llm.invoke(state["messages"])]}


def build_react_graph():
    builder = StateGraph(State)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(TOOLS))  # 预构建节点：执行 tool_calls，回填 ToolMessage

    builder.add_edge(START, "agent")
    # 条件边：模型有 tool_calls → 去 tools；没有 → 结束
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")  # 工具结果回给模型，继续推理（这就是 ReAct 的「回路」）
    builder.add_edge("agent", END)  # tools_condition 为 end 时直接走这条

    return builder.compile(checkpointer=InMemorySaver())


# ---------- 3. 对照组：预构建的 create_react_agent ----------


def build_prebuilt_graph():
    return create_react_agent(
        make_llm(),
        TOOLS,
        checkpointer=InMemorySaver(),
        prompt="你是一个严谨的助手，计算必须调用工具完成。",
    )


def show_flow(result: dict) -> None:
    """打印消息流，看清 ReAct 每一步"""
    for m in result["messages"]:
        role = m.type
        if role == "ai" and m.tool_calls:
            print(f"  [ai] 想调用工具: {[(c['name'], c['args']) for c in m.tool_calls]}")
        elif role == "tool":
            print(f"  [tool] {m.name} -> {m.content}")
        elif role == "ai":
            print(f"  [ai] 最终回答: {m.content}")


def demo() -> None:
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")

    graph = build_react_graph()
    config = {"configurable": {"thread_id": "demo-1"}}

    print("=== 手写 ReAct ===")
    for i, q in enumerate(["帮我算一下 3 + 5 再乘以 12 等于多少", "北京今天天气怎么样？"]):
        print(f"[用户] {q}")
        # 每个问题独立 thread，消息流互不干扰（想验证跨轮记忆可改成同一个）
        config = {"configurable": {"thread_id": f"demo-q{i}"}}
        result = graph.invoke({"messages": [("user", q)]}, config)
        show_flow(result)
        print()

    print("=== 对照：create_react_agent ===")
    prebuilt = build_prebuilt_graph()
    result = prebuilt.invoke(
        {"messages": [("user", "上海天气如何？")]},
        {"configurable": {"thread_id": "demo-2"}},
    )
    print(f"  最终回答: {result['messages'][-1].content}")


def chat() -> None:
    graph = build_react_graph()
    config = {"configurable": {"thread_id": "interactive-1"}}
    print("ReAct 交互对话（输入 q 退出）")
    while True:
        text = input("\n[用户] ").strip()
        if not text or text.lower() == "q":
            break
        result = graph.invoke({"messages": [("user", text)]}, config)
        print(f"[AI  ] {result['messages'][-1].content}")


def main() -> None:
    if "--chat" in sys.argv:
        chat()
    else:
        demo()


if __name__ == "__main__":
    main()
