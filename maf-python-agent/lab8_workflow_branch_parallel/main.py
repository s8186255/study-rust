# Lab 8：分支与并发 —— 条件路由（Switch）
# 对应 maf-csharp-agent/lab8-workflow-branch-parallel
# Source 节点收消息 → Switch 条件边按内容路由 → 叶节点产出工作流输出
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.maf_common  # noqa: F401  引入 UTF-8 控制台修复
from agent_framework import (
    Case,
    Default,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)


@executor(id="Source")
async def source(n: int, ctx: WorkflowContext[int]):
    await ctx.send_message(n)


@executor(id="EvenBranch", workflow_output=int)
async def even_branch(n: int, ctx: WorkflowContext[int]):
    await ctx.yield_output(n * 10)


@executor(id="OddBranch", workflow_output=int)
async def odd_branch(n: int, ctx: WorkflowContext[int]):
    await ctx.yield_output(n + 1)


async def main():
    # Switch 条件边组：根据消息内容路由到不同分支（类比 LangGraph conditional edges）
    workflow = (
        WorkflowBuilder(start_executor=source, output_from=[even_branch, odd_branch])
        .add_switch_case_edge_group(
            source,
            [
                Case(condition=lambda n: n % 2 == 0, target=even_branch),
                Case(condition=lambda n: n % 2 != 0, target=odd_branch),
                Default(target=odd_branch),
            ],
        )
        .build()
    )

    for value in (4, 7):
        print(f"\n=== 输入 {value} ===")
        result = await workflow.run(value)
        for event in result:
            if event.type == "output":
                print(f"分支输出: {event.data}")

    # ---- 课堂练习 ----
    # 1. 扇出+扇入：add_fan_out_edges / add_fan_in_edges，一个输入同时给两个"评审"节点再汇聚
    # 2. 对比 LangGraph 的 conditional edges（见笔记对比表）

asyncio.run(main())
