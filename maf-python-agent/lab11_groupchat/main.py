# Lab 11：多智能体协作 —— Group Chat（群聊）
# 对应 maf-csharp-agent/lab11-groupchat
# GroupChat 编排多个 Agent 轮流发言（程序员 + 评审员），按终止条件停止
#
# 注意：群聊历史天然含连续 assistant 消息，部分 OpenAI 兼容端点（本地 vLLM + gemma
# chat template）会报 400 "Cannot have 2 or more assistant messages"；
# Azure OpenAI / OpenAI 官方服务不受影响。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework.orchestrations import GroupChatBuilder


async def main():
    client, _ = get_client()

    writer = client.as_agent(
        name="Writer",
        instructions="你是程序员，负责写出简短的代码思路（不超过 5 行）。",
    )
    reviewer = client.as_agent(
        name="Reviewer",
        instructions="你是评审员。若思路合格，回复以 APPROVED 开头并说明理由；否则给出修改意见。",
    )

    # 轮转调度：按发言顺序在参与者之间轮换（也可用 orchestrator_agent 让 LLM 当主持人）
    def round_robin(state) -> str:
        last_author = state.conversation[-1].author_name if state.conversation else None
        return "Reviewer" if last_author == "Writer" else "Writer"

    # 终止条件：最后一条消息以 APPROVED 开头（也可用 max_rounds 兜底防死循环）
    def approved(messages) -> bool:
        return bool(messages) and str(messages[-1].text).startswith("APPROVED")

    workflow = (
        GroupChatBuilder(
            participants=[writer, reviewer],
            selection_func=round_robin,
            termination_condition=approved,
            max_rounds=8,
        )
        .build()
    )

    try:
        result = await workflow.run("写一个判断字符串是否回文的函数思路")
        for event in result:
            if event.type == "output":
                print(f"[群聊输出] {event.data}")
    except Exception as ex:
        print(f"[调用失败] {ex}")
        print("（本地兼容端点可能不支持群聊的连续 assistant 消息，见文件头说明）")

    # ---- 课堂练习 ----
    # 1. 换成 orchestrator_agent（LLM 主持人）观察动态调度
    # 2. 自定义 selection_func 实现"评审不合格则重写"的策略

asyncio.run(main())
