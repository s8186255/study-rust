# Lab 7：Workflow 入门 —— 两个 Executor 的顺序流水线
# 对应 maf-csharp-agent/lab7-workflow-sequential
#
# 理解三要素：Executor（收消息→处理→发消息）、Edge（类型化路由）、run() 事件流
# @executor 装饰器把异步函数变成节点；WorkflowContext[T] 声明 send_message 的类型
# 数据通过 ctx.send_message(发给下游) / ctx.yield_output(产出工作流输出) 传递
# 注意：Workflow 是纯 Python 编排，节点不一定是 Agent；与 Lab 9+ 的 Agent 编排形成对照
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.maf_common  # noqa: F401  引入 UTF-8 控制台修复
from agent_framework import WorkflowBuilder, WorkflowContext, executor


@executor(id="Upper")
async def upper(text: str, ctx: WorkflowContext[str]):
    await ctx.send_message(text.upper())


@executor(id="CountLength", workflow_output=str)
async def count_length(text: str, ctx: WorkflowContext[str]):
    await ctx.yield_output(f"长度 = {len(text)}")


async def main():
    # 声明式建图：起点 → 边 → 输出节点（output_from 指定哪些节点的 yield 是工作流输出）
    workflow = (
        WorkflowBuilder(start_executor=upper, output_from=[count_length])
        .add_edge(upper, count_length)
        .build()
    )

    # run 返回 WorkflowRunResult：事件列表，type=='output' 即工作流产出
    result = await workflow.run("hello maf workflow")
    for event in result:
        if event.type == "output":
            print(f"工作流输出: {event.data}")

    # 也可流式消费：workflow.run(..., stream=True) 逐个产出 WorkflowEvent

    # ---- 课堂练习 ----
    # 1. 加第三个节点（如 trim 节点），串成三步流水线
    # 2. 结合 Agent：让某个 Executor 内部调用 client.as_agent(...)（翻译→审校→润色）
    # 3. 改用继承 Executor 的自定义类节点，理解 WorkflowContext 的更多用法

asyncio.run(main())
