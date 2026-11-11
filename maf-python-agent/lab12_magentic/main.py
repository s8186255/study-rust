# Lab 12：Magentic 磁控调度（MAF 招牌，源自 Magentic-One）
# 对应 maf-csharp-agent/lab12-magnetic
# Orchestrator 负责任务规划 + 进度账本（Ledger），动态决定"下一步谁来做、是否重规划、何时完成"
# 与 Group Chat 的差异：Group Chat 靠轮转规则，Magentic 靠目标驱动的动态编排
#
# 注意：编排历史含连续 assistant 消息，部分 OpenAI 兼容端点（本地 vLLM + gemma
# chat template）会报 400 "Cannot have 2 or more assistant messages"；
# Azure OpenAI / OpenAI 官方服务不受影响。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework.orchestrations import MagenticBuilder, StandardMagenticManager


async def main():
    client, _ = get_client()

    orchestrator = client.as_agent(name="Orchestrator", instructions="你是任务编排者，负责规划与调度。")
    researcher = client.as_agent(name="Researcher", instructions="你是研究员，负责检索与整理事实要点，回答不超过 4 句。")
    coder = client.as_agent(name="Coder", instructions="你是程序员，负责编写或修正代码片段，只输出代码与一句说明。")
    reviewer = client.as_agent(name="Reviewer", instructions="你是评审员，检查产出是否满足任务目标，回答不超过 3 句。")

    # Magentic 工作流：StandardMagenticManager（LLM 编排器）+ 参与者 + 防失控参数
    workflow = (
        MagenticBuilder(
            participants=[researcher, coder, reviewer],
            manager=StandardMagenticManager(agent=orchestrator),
            max_round_count=10,   # 防失控：编排轮数上限
            max_stall_count=3,    # 连续停滞次数上限
        )
        .build()
    )

    try:
        result = await workflow.run("写一个把 CSV 的前 3 行转成 Markdown 表格的 Python 方法，并做自检")
        for event in result:
            if event.type == "output":
                print(f"[Magentic 输出]\n{event.data}")
    except Exception as ex:
        print(f"[调用失败] {ex}")
        print("（本地兼容端点可能不支持编排的连续 assistant 消息，见文件头说明）")

    # ---- 课堂练习 ----
    # 1. 监听 magentic_orchestrator 事件（stream=True），观察 Ledger（任务清单/事实/进度）如何推进
    # 2. 人为让 Coder 指令改成"总是输出错误代码"，观察 Orchestrator 的重规划能力

asyncio.run(main())
