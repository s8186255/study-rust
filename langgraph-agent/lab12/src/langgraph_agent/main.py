"""lab12 容错与工程化（重试、fallback、并发控制、LangSmith 观测）

目标：
1. RetryPolicy：节点失败自动重试（指数退避），第三次成功
2. with_fallbacks：主模型挂了自动切到备用模型
3. 超步（superstep）并行：无依赖的节点在同一超步内并发执行
4. LangSmith：设环境变量即开启追踪（README 说明，无需代码）
全程离线（用 fake 模型），运行：uv run langgraph-agent
"""

import sys
from typing import Annotated, TypedDict

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy


class State(TypedDict):
    query: str
    result_a: str
    result_b: str
    recovered: str


# ---------- 1. 重试：前两次抛异常，第三次成功 ----------

ATTEMPTS = {"count": 0}


def flaky_node(state: State) -> dict:
    ATTEMPTS["count"] += 1
    print(f"  [flaky_node] 第 {ATTEMPTS['count']} 次尝试")
    if ATTEMPTS["count"] < 3:
        raise RuntimeError(f"模拟故障（第 {ATTEMPTS['count']} 次）")
    return {"recovered": f"第 {ATTEMPTS['count']} 次尝试成功"}


# ---------- 2. fallback：主模型总是失败，备用模型接棒 ----------


class AlwaysFailModel(FakeListChatModel):
    """每次调用都抛错的主模型"""

    def _generate(self, *args, **kwargs):
        raise RuntimeError("主模型服务不可用")


def make_models():
    primary = AlwaysFailModel(responses=[""])
    backup = FakeListChatModel(responses=["这是备用模型的回答：一切正常。"])
    return primary.with_fallbacks([backup])  # 主模型失败自动切备用


def llm_node(state: State) -> dict:
    reply = make_models().invoke(state["query"])
    return {"result_a": reply.content}


# ---------- 3. superstep 并行：两个无依赖节点并发跑 ----------


def branch_a(state: State) -> dict:
    print("  [branch_a] 执行（与 branch_b 同一超步并发）")
    return {"result_a": f"A 处理：{state['query']}"}


def branch_b(state: State) -> dict:
    print("  [branch_b] 执行（与 branch_a 同一超步并发）")
    return {"result_b": f"B 处理：{state['query']}"}


def main() -> None:
    sys.stdout.reconfigure(errors="replace")

    print("=== 1. RetryPolicy：节点失败自动重试 ===")
    builder = StateGraph(State)
    builder.add_node(
        "flaky", flaky_node,
        # retry_on 默认只重试连接类异常，这里显式包含 RuntimeError；
        # max_attempts=3，间隔从 0.1s 指数退避
        retry=RetryPolicy(max_attempts=3, initial_interval=0.1, retry_on=(RuntimeError,)),
    )
    builder.add_edge(START, "flaky")
    builder.add_edge("flaky", END)
    graph = builder.compile()
    result = graph.invoke({"query": "test"})
    print(f"  结果: {result['recovered']}\n")

    print("=== 2. with_fallbacks：主模型挂了自动切换 ===")
    builder = StateGraph(State)
    builder.add_node("llm", llm_node)  # llm_node 内部已配 fallback
    builder.add_edge(START, "llm")
    builder.add_edge("llm", END)
    graph = builder.compile()
    result = graph.invoke({"query": "你好"})
    print(f"  结果: {result['result_a']}\n")

    print("=== 3. 超步并行：START 分叉到两个节点 ===")
    builder = StateGraph(State)
    builder.add_node("a", branch_a)
    builder.add_node("b", branch_b)
    builder.add_edge(START, "a")
    builder.add_edge(START, "b")  # 同一超步的两个分支
    builder.add_edge("a", END)
    builder.add_edge("b", END)
    graph = builder.compile()
    result = graph.invoke({"query": "并行任务"})
    print(f"  结果: {result['result_a']} / {result['result_b']}")
    print("  注意: 同一超步内两个节点若写同一个无 reducer 字段会报 InvalidUpdateError")
    print("  —— 这就是 lab2 强调 reducer 的工程原因")


if __name__ == "__main__":
    main()
