"""lab9 检索增强生成 RAG（CRAG-lite 工作流）

目标：
1. 用图编排 RAG 全流程：retrieve → grade（文档评分）→ rewrite（查询改写）→ generate
2. 实现 CRAG 的核心思想：检索质量不高时「改写查询再检索」，而不是硬答
3. 体会图 vs 链：带回路、带分支的 RAG 流程只能用图表达
说明：检索器用关键词打分模拟（不依赖向量库/embedding 服务），生产环境换成向量检索即可。
对接配置：本 lab 目录下的 `config.json`
运行：uv run langgraph-agent
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


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


# ---------- 知识库：4 篇小文档 ----------

DOCS = {
    "doc1": "LangGraph 是 LangChain 团队推出的智能体编排框架，核心抽象是状态图（StateGraph），节点共享状态，支持条件边和回路。",
    "doc2": "LangGraph 的 checkpointer 机制可以把每一步的状态持久化，是实现多轮记忆和人工中断的基础。",
    "doc3": "Python 的 GIL（全局解释器锁）使同一时刻只有一个线程执行字节码，CPU 密集任务建议用 multiprocessing。",
    "doc4": "Rust 没有垃圾回收，通过所有权和借用检查在编译期保证内存安全。",
}


def retrieve(query: str, k: int = 2) -> list[str]:
    """关键词打分检索（模拟向量检索）：按查询词在各文档中的命中数排序取 top-k"""
    words = [w for w in query.replace("？", "").split() if w]
    scored = []
    for doc_id, text in DOCS.items():
        score = sum(text.count(w) for w in words)
        scored.append((score, doc_id, text))
    scored.sort(reverse=True)
    return [f"[{doc_id}] {text}" for _, doc_id, text in scored[:k]]


# ---------- State ----------


class State(TypedDict):
    question: str
    documents: list[str]
    rewritten: str  # 改写后的查询（空串 = 未改写）
    retries: int
    answer: str


# ---------- 节点 ----------


def retrieve_node(state: State) -> dict:
    query = state.get("rewritten") or state["question"]
    docs = retrieve(query)
    print(f"  [retrieve] query={query!r} -> {len(docs)} 篇文档")
    return {"documents": docs}


def grade_documents_node(state: State) -> dict:
    """CRAG 核心：让模型判断检索文档与问题是否相关"""
    llm = make_llm().bind_tools([])
    docs_desc = "\n".join(state["documents"])
    prompt = (
        f"问题：{state['question']}\n\n候选文档：\n{docs_desc}\n\n"
        "判断这些文档是否包含回答该问题所需的信息。只回答 YES 或 NO。"
    )
    verdict = llm.invoke(prompt).content.strip().upper()
    relevant = "YES" in verdict
    print(f"  [grade] 模型判定: {verdict} -> {'进入生成' if relevant else '改写查询再检索'}")
    return {"retries": state.get("retries", 0) + (0 if relevant else 1)}


def rewrite_node(state: State) -> dict:
    llm = make_llm()
    prompt = (
        f"原始问题「{state['question']}」检索效果不佳。"
        "请改写为更适合检索的关键词组合（只输出改写后的问题，不要解释）。"
    )
    rewritten = llm.invoke(prompt).content.strip()
    print(f"  [rewrite] -> {rewritten!r}")
    return {"rewritten": rewritten, "documents": []}


def generate_node(state: State) -> dict:
    llm = make_llm()
    context = "\n".join(state["documents"])
    prompt = f"根据以下资料回答问题。\n\n资料：\n{context}\n\n问题：{state['question']}"
    answer = llm.invoke(prompt).content.strip()
    return {"answer": answer}


# ---------- 路由 ----------

MAX_RETRIES = 1


def route_after_grade(state: State) -> Literal["generate", "rewrite"]:
    if state.get("retries", 0) > MAX_RETRIES:
        return "generate"  # 改写过仍不相关，兜底硬答
    last_docs_relevant = state.get("retries", 0) == 0
    return "generate" if last_docs_relevant else "rewrite"


def route_after_rewrite(state: State) -> Literal["retrieve", "generate"]:
    # 改写后回去重检索（回路！）；重试次数已超限时直接生成
    return "retrieve" if state.get("retries", 0) <= MAX_RETRIES else "generate"


def build_graph():
    builder = StateGraph(State)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("grade", grade_documents_node)
    builder.add_node("rewrite", rewrite_node)
    builder.add_node("generate", generate_node)

    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", route_after_grade)
    builder.add_conditional_edges("rewrite", route_after_rewrite)
    builder.add_edge("generate", END)
    return builder.compile()


def main() -> None:
    sys.stdout.reconfigure(errors="replace")
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")

    graph = build_graph()
    for q in [
        "LangGraph 的记忆功能是怎么实现的？",
        "什么是所有权和借用检查？",
    ]:
        print(f"[问题] {q}")
        result = graph.invoke(
            {"question": q, "documents": [], "rewritten": "", "retries": 0, "answer": ""}
        )
        print(f"[回答] {result['answer'][:300]}\n")


if __name__ == "__main__":
    main()
