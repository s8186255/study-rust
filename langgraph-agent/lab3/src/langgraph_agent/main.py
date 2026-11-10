"""lab3 节点与边（顺序边、条件边、START/END）

目标：掌握动态路由的两种写法——
1. add_conditional_edges：路由函数 + 映射表，在「边」上决定去向
2. Command(goto=...)：在「节点内部」直接决定下一节点并顺带更新 state
不调用任何 LLM（用关键词规则模拟分类器），纯本地运行：`uv run langgraph-agent`
"""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


# ---------- 图 1：add_conditional_edges（路由逻辑放在「边」上） ----------


class State(TypedDict):
    query: str
    route: str
    result: str


def classify(state: State) -> dict:
    """分类节点：只负责更新 state，不决定去向"""
    tech_words = ("python", "rust", "langgraph", "代码", "程序")
    route = "tech" if any(w in state["query"].lower() for w in tech_words) else "general"
    return {"route": route}


def tech_agent(state: State) -> dict:
    return {"result": f"[技术线路] 处理：{state['query']}"}


def general_agent(state: State) -> dict:
    return {"result": f"[通用线路] 处理：{state['query']}"}


def route_by_state(state: State) -> Literal["tech", "general"]:
    """路由函数：读 state，返回目标节点名（或节点名列表）"""
    return state["route"]  # type: ignore[no-any-return]


def build_graph_v1():
    builder = StateGraph(State)
    builder.add_node("classify", classify)
    builder.add_node("tech", tech_agent)
    builder.add_node("general", general_agent)

    builder.add_edge(START, "classify")
    # 条件边：classify 执行完后，调 route_by_state 决定走哪条边
    builder.add_conditional_edges(
        "classify",
        route_by_state,
        {"tech": "tech", "general": "general"},  # 映射表：返回值 -> 节点名
    )
    builder.add_edge("tech", END)
    builder.add_edge("general", END)

    return builder.compile()


# ---------- 图 2：Command（路由逻辑放在「节点内部」） ----------


def classify_and_route(state: State) -> Command[Literal["tech", "general"]]:
    """同一个节点：既更新 state，又用 goto 决定下一跳"""
    tech_words = ("python", "rust", "langgraph", "代码", "程序")
    route = "tech" if any(w in state["query"].lower() for w in tech_words) else "general"
    return Command(
        update={"route": route},  # 更新 state
        goto=route,               # 决定下一节点
    )


def build_graph_v2():
    builder = StateGraph(State)
    builder.add_node("classify", classify_and_route)
    builder.add_node("tech", tech_agent)
    builder.add_node("general", general_agent)

    builder.add_edge(START, "classify")
    builder.add_edge("tech", END)
    builder.add_edge("general", END)

    return builder.compile()


def main() -> None:
    queries = ["帮我写一段 python 代码", "今天天气怎么样"]

    print("=== 图 1：add_conditional_edges ===")
    graph1 = build_graph_v1()
    for q in queries:
        result = graph1.invoke({"query": q})
        print(f"  query={q!r} -> route={result['route']}, {result['result']}")

    print("=== 图 2：Command(goto=...) ===")
    graph2 = build_graph_v2()
    for q in queries:
        result = graph2.invoke({"query": q})
        print(f"  query={q!r} -> route={result['route']}, {result['result']}")

    graph1.get_graph().print_ascii()


if __name__ == "__main__":
    main()
