"""lab4 Chatbot 与短期记忆（checkpointer、thread、多轮对话）

目标：
1. 接入第一个 LLM（OpenAI 兼容接口）
2. 用 InMemorySaver 做 checkpointer，让图「记住」当前 thread 的历史
3. 理解 thread_id：同一 thread 多轮对话有记忆，换 thread 互不干扰

对接配置：本 lab 目录下的 `config.json`（与 rig study-agent/lab1-hello-agent 同一约定）
  - base_url：OpenAI 兼容服务地址（须带 /v1）
  - api_key：可填可不填（留空 = 服务端未启用鉴权，用占位值）
  - model：模型 Id（如 gemma-4-26B-A4B）
  - temperature：可选，默认 0.7
改配置文件即可切换模型服务，代码不动。

运行：
  uv run langgraph-agent           # 脚本化演示（同一 thread 连续三轮，验证记忆）
  uv run langgraph-agent --chat    # 交互式多轮对话（输入 q 退出）
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


# 1. State：只有 messages 一个字段，用 add_messages 做 reducer
#    checkpointer 恢复 state 时，新消息会「追加」到历史之后——这就是记忆的载体
class State(TypedDict):
    messages: Annotated[list, add_messages]


# 2. 配置：对应 config.json；除 base_url / model 外其余字段均可省略
@dataclass
class LlmConfig:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.7

    @classmethod
    def load(cls) -> "LlmConfig":
        # 用 main.py 自身位置定位 lab 根目录，无论从哪里启动都能找到 config.json
        path = Path(__file__).resolve().parents[2] / "config.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            base_url=data["base_url"],
            model=data["model"],
            api_key=data.get("api_key", ""),
            temperature=data.get("temperature", 0.7),
        )

    def effective_key(self) -> str:
        # key 可用可不用：留空时返回占位值（服务端未启用鉴权即可）
        return self.api_key if self.api_key.strip() else "not-needed"


# 3. LLM：OpenAI 兼容客户端，POST {base_url}/chat/completions
def make_llm() -> ChatOpenAI:
    cfg = LlmConfig.load()
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.effective_key(),
        base_url=cfg.base_url,
        temperature=cfg.temperature,
    )


# 4. 节点：把完整历史交给模型，返回的回复由 add_messages 追加进 state
def chatbot(state: State) -> dict:
    reply = make_llm().invoke(state["messages"])
    return {"messages": [reply]}


# 5. 组图：唯一亮点是 compile(checkpointer=...)——没有它，图是「无记忆」的
def build_graph():
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=InMemorySaver())


# 6. 脚本化演示：同一 thread_id 连续三轮，第三轮问第一轮的信息，验证记忆
def demo() -> None:
    cfg = LlmConfig.load()
    print(f"配置: base_url={cfg.base_url} model={cfg.model}\n")

    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-1"}}

    turns = [
        "我叫 Andrew，我最喜欢的数字是 42。请记住。",
        "我叫什么名字？",
        "把我喜欢的数字乘以 10 等于多少？",
    ]
    for text in turns:
        print(f"[用户] {text}")
        result = graph.invoke({"messages": [("user", text)]}, config)
        print(f"[AI  ] {result['messages'][-1].content}\n")


# 7. 交互式对话：每轮都带同一个 thread_id，模型能看见全部历史
def chat() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "interactive-1"}}
    print("交互式对话（输入 q 退出）")
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
