"""lab2 State 与 Reducer（状态定义、add_messages）

目标：掌握 State 的定义方式与 Reducer 合并语义——
1. 无 Annotated 字段：默认「覆盖」
2. Annotated[list, add_messages]：消息专用 reducer，按 id 追加/合并
3. Annotated[list[str], add]：自定义 reducer，用 operator.add 拼接
不调用任何 LLM，纯本地运行：`uv run langgraph-agent`
"""

from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# 同一份 State，三种字段有三种合并语义：
# 1. answer：无 Annotated —— 节点返回新值直接「覆盖」旧值
# 2. messages：add_messages —— 消息专用 reducer，按消息 id「追加/合并」
# 3. steps：operator.add —— 自定义 reducer，对两个列表做「拼接」
class State(TypedDict):
    answer: str
    messages: Annotated[list, add_messages]
    steps: Annotated[list[str], add]


def node_a(state: State) -> dict:
    # 部分更新约定：只返回要改的字段，LangGraph 按 reducer 合并进总 state
    return {
        "answer": "来自 node_a",
        "messages": [HumanMessage(content="你好")],
        "steps": ["node_a 完成"],
    }


def node_b(state: State) -> dict:
    return {
        "answer": "来自 node_b（覆盖了 node_a 的值）",
        "messages": [AIMessage(content="你好，这是图的回复")],
        "steps": ["node_b 完成"],
    }


def build_graph():
    builder = StateGraph(State)
    builder.add_node("node_a", node_a)
    builder.add_node("node_b", node_b)

    builder.add_edge(START, "node_a")
    builder.add_edge("node_a", "node_b")
    builder.add_edge("node_b", END)

    return builder.compile()


def main() -> None:
    graph = build_graph()
    result = graph.invoke({"answer": "", "messages": [], "steps": []})

    print("最终 State:")
    for key, value in result.items():
        print(f"  {key}: {value}")

    # 观察三种语义的差异：
    # - answer   被覆盖：只剩 node_b 的值
    # - steps    被拼接：node_a 和 node_b 各留一条
    # - messages 被追加：两条消息都在列表里
    graph.get_graph().print_ascii()


if __name__ == "__main__":
    main()
