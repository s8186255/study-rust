"""lab1 环境搭建与第一个图（Hello World）

目标：跑通第一个 StateGraph，理解「State -> 节点 -> 边 -> compile -> invoke」五步。
不调用任何 LLM，纯本地运行：`uv run langgraph-agent`
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# 1. 定义 State：图中所有节点共享的「黑板」
class State(TypedDict):
    message: str
    word_count: int


# 2. 定义节点：接收 state，返回要更新的字段（部分更新）
def greet(state: State) -> dict:
    return {"message": f"Hello, {state['message']}!"}


def count_words(state: State) -> dict:
    return {"word_count": len(state["message"].split())}


# 3-4. 组装并编译：添加节点、用边连接，编译为可执行图
def build_graph():
    builder = StateGraph(State)
    builder.add_node("greet", greet)
    builder.add_node("count_words", count_words)

    builder.add_edge(START, "greet")              # 入口 -> greet
    builder.add_edge("greet", "count_words")      # greet -> count_words
    builder.add_edge("count_words", END)          # count_words -> 出口

    return builder.compile()


# 5. invoke：从入口执行到出口，返回最终 State
def main() -> None:
    graph = build_graph()
    result = graph.invoke({"message": "langgraph"})

    print("最终 State:", result)
    print("message   :", result["message"])
    print("word_count:", result["word_count"])

    # 附：打印图的 ASCII 结构，直观看到拓扑
    graph.get_graph().print_ascii()


if __name__ == "__main__":
    main()
