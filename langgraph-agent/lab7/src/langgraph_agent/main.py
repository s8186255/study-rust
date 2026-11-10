"""lab7 子图（subgraph）与状态组合复用

目标：
1. 把一个编译后的图当节点嵌入父图（同名状态字段自动透传）
2. 父子图 schema 不同时，用包装函数做状态映射
3. 理解「图即节点」：复杂工作流 = 小图的层层组合
不调用 LLM，纯本地运行：uv run langgraph-agent
"""

from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph


# ---------- 子图 1：清洗（与父图同名状态字段，直接嵌入） ----------


class TextState(TypedDict):
    text: str


def clean_node(state: TextState) -> dict:
    text = state["text"].strip().lower()
    print(f"  [子图1 clean] {text!r}")
    return {"text": text}


def build_clean_subgraph():
    g = StateGraph(TextState)
    g.add_node("clean", clean_node)
    g.add_edge(START, "clean")
    g.add_edge("clean", END)
    return g.compile()  # 编译后的图就是一个可当节点用的 Runnable


# ---------- 子图 2：统计（自有 schema，嵌入时需要映射） ----------


class StatsState(TypedDict):
    content: str
    char_count: int
    word_count: int


def count_node(state: StatsState) -> dict:
    content = state["content"]
    return {
        "char_count": len(content),
        "word_count": len(content.split()),
    }


def build_stats_subgraph():
    g = StateGraph(StatsState)
    g.add_node("count", count_node)
    g.add_edge(START, "count")
    g.add_edge("count", END)
    return g.compile()


# ---------- 父图：组合两个子图 ----------


class ParentState(TypedDict):
    text: str
    char_count: int
    word_count: int


def call_stats(state: ParentState) -> dict:
    """schema 映射：父图字段 text -> 子图字段 content，再把结果搬回来"""
    result = stats_subgraph.invoke({"content": state["text"]})
    return {"char_count": result["char_count"], "word_count": result["word_count"]}


clean_subgraph = build_clean_subgraph()
stats_subgraph = build_stats_subgraph()


def build_parent_graph():
    builder = StateGraph(ParentState)

    # 方式 1：同名状态直接把编译后的子图当节点
    builder.add_node("clean", clean_subgraph)
    # 方式 2：schema 不同，用普通节点函数包一层做映射
    builder.add_node("stats", call_stats)

    builder.add_edge(START, "clean")
    builder.add_edge("clean", "stats")
    builder.add_edge("stats", END)
    return builder.compile()


def main() -> None:
    graph = build_parent_graph()
    result = graph.invoke({"text": "  Hello LangGraph SubGraph  "})
    print("\n最终 State:")
    for k, v in result.items():
        print(f"  {k}: {v!r}")
    print("\n父图拓扑（子图在节点内部，父图只见 clean/stats 两个节点）:")
    graph.get_graph().print_ascii()


if __name__ == "__main__":
    main()
