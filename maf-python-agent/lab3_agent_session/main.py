# Lab 3：会话（AgentSession）—— 实现多轮对话
# 对应 maf-csharp-agent/lab3-agent-session
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client


async def main():
    client, _ = get_client()
    agent = client.as_agent(name="MemoryAgent", instructions="你是有记性的助手，回答简洁。")

    # 带 AgentSession：同一会话内跨调用记忆（agent.create_session() 创建会话）
    session = agent.create_session()
    await agent.run("我叫 Alice，最喜欢的数字是 42。", session=session)
    print(f"[带会话] {(await agent.run('我叫什么名字？最喜欢的数字是多少？', session=session)).text}")

    # 无状态对比：不传 session，两次调用互不相关
    print(f"[无会话] {(await agent.run('我叫什么名字？')).text}")

    # ---- 课堂讨论 ----
    # 服务端历史（Session 由 provider 托管）与本地历史（自管 Message 列表）的差异：
    # 存储位置、续接方式、成本与隐私；结合课程笔记 Lab 3 小节

asyncio.run(main())
