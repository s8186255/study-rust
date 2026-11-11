# Lab 10：多智能体协作 —— Handoff（交接）
# 对应 maf-csharp-agent/lab10-handoff
# 分流 Agent 根据用户问题把控制权"交接"给专业 Agent，上下文随交接转移
#
# 注意：交接后上下文可能出现连续 assistant 消息，部分 OpenAI 兼容端点
# （如本地 vLLM + gemma chat template）会报 400；Azure OpenAI / OpenAI 官方服务不受影响。
# 遇到 400 时换用支持该特性的模型服务，或调整 agent instructions 减少转接轮次。
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework.orchestrations import HandoffBuilder


async def main():
    client, _ = get_client()

    # Handoff 编排要求参与者开启本地历史持久化（保证交接时上下文一致）
    triage = client.as_agent(
        name="Triage",
        instructions="你是客服分流员。判断问题属于'订单'还是'技术支持'，立即把控制权交给对应专员。",
        require_per_service_call_history_persistence=True,
    )
    order = client.as_agent(
        name="OrderSupport",
        instructions="你是订单专员，负责查订单、退换货，回答不超过 3 句。",
        require_per_service_call_history_persistence=True,
    )
    tech = client.as_agent(
        name="TechSupport",
        instructions="你是技术支持，负责排查登录、报错问题，回答不超过 3 句。",
        require_per_service_call_history_persistence=True,
    )

    # Handoff 工作流：triage 是入口，可把控制权交给 order / tech；专员之间可互转
    workflow = (
        HandoffBuilder(participants=[triage, order, tech])
        .with_start_agent(triage)
        .add_handoff(triage, [order, tech])
        .add_handoff(order, [tech])
        .add_handoff(tech, [order])
        .build()
    )

    for question in (
        "我的订单三天了还没发货",
        "登录 APP 一直报 500 错误",
    ):
        print(f"\n=== 用户: {question} ===")
        try:
            result = await workflow.run(question)
            for event in result:
                if event.type == "output":
                    print(f"[响应] {event.data}")
        except Exception as ex:
            print(f"[调用失败] {ex}")
            print("（本地兼容端点可能不支持交接后的连续 assistant 消息，见文件头说明）")

    # ---- 课堂练习 ----
    # 1. 加一个"投诉专员"，观察分流与交接
    # 2. 打印全部事件（去掉 if 过滤），观察 handoff_sent 事件如何流转

asyncio.run(main())
