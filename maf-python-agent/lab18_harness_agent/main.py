# Lab 18：Harness Agent（长任务型 Agent）—— 内置待办/上下文压缩/工具审批
# 对应 maf-csharp-agent/lab18-harness-agent
# create_harness_agent 开箱即用：todo 管理、上下文压缩、工具审批、文件记忆等企业特性
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import create_harness_agent

LAB_DIR = Path(__file__).resolve().parent


async def main():
    client, _ = get_client()

    # Harness Agent：默认启用 todo 待办管理与上下文压缩；关闭联网搜索等可选能力
    agent = create_harness_agent(
        client=client,
        name="FileOrganizer",
        agent_instructions=(
            "你是文件整理助手。收到任务后：\n"
            "1. 先列出待办清单（todo），每行一个任务；\n"
            "2. 逐个任务执行：先说明要做什么；\n"
            "3. 每完成一步，输出更新后的清单（完成项打 [x]）。\n"
            "当前工作目录里有两个文件 file1.txt 与 notes.md，把它们分别整理为 archived_file1.txt 与 docs_notes.md（复制后改名）。"
        ),
        disable_web_search=True,          # 关闭联网搜索（本地演示）
        loop_max_iterations=10,           # 循环上限，防失控
    )

    # 准备演示文件
    (LAB_DIR / "file1.txt").write_text("重要文件内容 A", encoding="utf-8")
    (LAB_DIR / "notes.md").write_text("# 笔记\n- 条目 1", encoding="utf-8")

    # Harness 的工具审批中间件要求运行在会话上
    session = agent.create_session()
    response = await agent.run("请开始整理文件，完成后总结每一步做了什么。", session=session)
    print(response.text)

    # ---- 课堂练习 ----
    # 1. 观察自动生成的 todo 列表如何随任务推进更新
    # 2. 把任务加大（10 个文件），观察上下文压缩策略（默认 SummarizationStrategy）介入
    # 3. 与 Lab 13 的"编排层人工审批"对比：Harness 是 Agent 层的工具审批

asyncio.run(main())
