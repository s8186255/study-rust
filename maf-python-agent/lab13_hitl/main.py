# Lab 13：人机协同（Human-in-the-Loop）—— 关键决策点暂停等待人工输入
# 对应 maf-csharp-agent/lab13-hitl
#
# 两种典型方式：
# ① Agent 层：工具审批（approval_mode），见 Lab 18 Harness 的工具审批
# ② 编排层：工作流暂停在关键节点，人工确认后继续（本 lab 演示控制台审批）
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client


async def main():
    client, _ = get_client()
    planner = client.as_agent(name="Planner", instructions="你是方案规划师，输出不超过 5 行的简短方案。")

    # 1. Agent 产出方案
    session = planner.create_session()
    plan = (await planner.run("给公司设计一个内部文档审批流程的简短方案", session=session)).text
    print(f"[Agent 方案]\n{plan}\n")

    # 2. 人工审批（这里是控制台；生产里对应审批 UI / 工单系统，隔夜审批即"进程暂停"）
    decision = input("[人工审批] 批准该方案? (y/n): ").strip().lower()
    if decision == "y":
        print("\n[执行] 方案已批准，进入实施……")
    else:
        # 3. 拒绝 → 把人工意见反馈回 Agent，让其在同一会话内修订（上下文保留）
        feedback = input("[反馈] 请输入修改意见: ")
        revised = (await planner.run(f"根据人工意见修订方案：{feedback}", session=session)).text
        print(f"\n[修订方案]\n{revised}")

    # ---- 课堂练习 ----
    # 1. 模拟"隔夜审批"：把 session 序列化存盘，重开进程后再恢复继续（结合 Lab 15）
    # 2. 在 Workflow 中用 request_info 事件实现节点级暂停（见 agent_framework 文档 Human-in-the-Loop）

asyncio.run(main())
