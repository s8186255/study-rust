# Lab 15：记忆（Memory / 长期记忆）—— AgentSession 序列化持久化，跨"进程"记住对话
# 对应 maf-csharp-agent/lab15-memory
# 这是"本地历史"路线；Provider 托管记忆（如 Mem0，见 agent_framework.mem0）见课程笔记 Lab 15 小节
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import AgentSession

SESSION_FILE = Path(__file__).resolve().parent / "session.json"


async def main():
    client, _ = get_client()
    agent = client.as_agent(name="LongTermAssistant", instructions="你是长期助理。")

    if SESSION_FILE.exists():
        # 第二次运行：从磁盘恢复会话状态（MAF 会话可序列化）
        session = AgentSession.from_dict(json.loads(SESSION_FILE.read_text(encoding="utf-8")))
        print("[已从 session.json 恢复历史会话]")
    else:
        session = agent.create_session()

    # 第一次运行时写下偏好；第二次运行应"记得"偏好
    await agent.run("我的偏好：回答尽量简洁，不用表情符号。", session=session)
    print((await agent.run("我的偏好是什么？", session=session)).text)

    SESSION_FILE.write_text(json.dumps(session.to_dict(), ensure_ascii=False), encoding="utf-8")
    print(f"\n[会话已保存到 {SESSION_FILE.name}] —— 重新运行 python main.py 验证跨会话记忆")

    # 删除 session.json 即可重置

asyncio.run(main())
