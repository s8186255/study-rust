# Lab 14：Checkpoint 持久化 —— 工作流在中断后从存档恢复运行
# 对应 maf-csharp-agent/lab14-checkpoint
# 结合 Lab 13 的审批场景：人工审批"隔夜"再恢复，工作流进度不丢
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.maf_common  # noqa: F401  引入 UTF-8 控制台修复
from agent_framework import (
    FileCheckpointStorage,
    WorkflowBuilder,
    WorkflowContext,
    executor,
)

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"


@executor(id="Extract")
async def extract(data: str, ctx: WorkflowContext[str]):
    await ctx.send_message(f"提取信息: {data}")


@executor(id="Validate")
async def validate(data: str, ctx: WorkflowContext[str]):
    await ctx.send_message(f"校验: {data}")


@executor(id="Summarize", workflow_output=str)
async def summarize(data: str, ctx: WorkflowContext[str]):
    await ctx.yield_output(f"总结: {data}")


async def main():
    # 每个超级步的检查点写入检查点存储（演示用文件版，可直接落盘/恢复）
    storage = FileCheckpointStorage(str(CHECKPOINT_DIR))

    workflow = (
        WorkflowBuilder(start_executor=extract, checkpoint_storage=storage, output_from=[summarize])
        .add_edge(extract, validate)
        .add_edge(validate, summarize)
        .build()
    )

    print("=== 第一次运行（写入检查点）===")
    result = await workflow.run("原始数据")
    for event in result:
        if event.type == "output":
            print(f"工作流输出: {event.data}")

    # 从最近一次检查点恢复（不能同时提供 message 与 checkpoint_id：只传 checkpoint_id）
    checkpoint_id = workflow.get_last_checkpoint_id()
    if checkpoint_id:
        print(f"\n[Checkpoint] 找到最近检查点 {checkpoint_id}，从存档恢复运行……")
        result = await workflow.run(
            checkpoint_id=checkpoint_id,
            checkpoint_storage=storage,
        )
        for event in result:
            if event.type == "output":
                print(f"恢复后输出: {event.data}")

    print("\n练习：在 validate 抛出异常中断 → 从最近检查点恢复，验证 extract 不再重跑")

asyncio.run(main())
