# Lab 20：综合实战（毕业项目）—— 智能客服工作台
# 对应 maf-csharp-agent/lab20-final
#
# 流程：意图识别 → 路由到专业 Agent（带工具）→ 危险操作人工审批 → 结果汇总
# 覆盖：Lab 1 统一抽象 / Lab 2 工具 / Lab 3 会话 / Lab 13 HITL / Lab 17 中间件
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import AgentContext, AgentMiddleware, tool


class TelemetryMiddleware(AgentMiddleware):
    """追踪中间件（Lab 17 成果复用）"""

    async def process(self, context: AgentContext, call_next):
        start = time.perf_counter()
        response = await call_next()
        print(f"[遥测] 调用耗时 {time.perf_counter() - start:.2f}s")
        return response


@tool
def get_order(order_id: str) -> str:
    """查询订单状态"""
    return f"订单 {order_id}：已发货（圆通），预计明天送达"


@tool
def refund(order_id: str) -> str:
    """执行退款（危险操作）"""
    return f"订单 {order_id} 已退款"


async def main():
    client, _ = get_client()
    telemetry = TelemetryMiddleware()

    intent = client.as_agent(
        name="Intent",
        instructions="识别用户意图，只输出 Order / Refund / Tech / Other 之一，不要多余文字。",
        middleware=[telemetry],
    )
    order_agent = client.as_agent(
        name="OrderSupport",
        instructions="你是订单专员，先调用工具查订单，再回复。",
        tools=[get_order],
    )
    refund_agent = client.as_agent(
        name="RefundSupport",
        instructions="你是退款专员。确认执行后调用退款工具。",
        tools=[refund],
    )
    fallback = client.as_agent(
        name="General",
        instructions="你是通用客服，简短回答。",
    )

    print("智能客服工作台（输入 q 退出）")
    intent_session = intent.create_session()
    while True:
        question = input("\n用户输入: ").strip()
        if not question or question.lower() in ("q", "quit"):
            break

        # 1. 意图识别（同一会话内多轮）
        intent_text = (await intent.run(question, session=intent_session)).text.strip()
        print(f"[意图识别] {intent_text}")

        # 2. 路由（Handoff 思路）
        target = {"Order": order_agent, "Refund": refund_agent}.get(intent_text, fallback)

        # 3. 危险操作人工审批（HITL）
        if target is refund_agent:
            if input("[人工审批] 允许执行退款? (y/n): ").strip().lower() != "y":
                print("[已拦截] 退款操作已取消，转人工处理。")
                continue

        # 4. 专业 Agent 处理
        try:
            reply = (await target.run(question, session=target.create_session())).text
            print(f"[客服] {reply}")
        except Exception as ex:
            print(f"[调用失败] {ex}")

    print("会话结束。")

asyncio.run(main())
