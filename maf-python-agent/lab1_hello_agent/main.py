# Lab 1：第一个 Agent —— AIAgent 统一抽象 + 流式输出 + 多模态输入
# 对应 maf-csharp-agent/lab1-hello-agent
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client

# 统一抽象：无论底层是 OpenAI 兼容服务 / Azure OpenAI / Foundry，对外都是同一个 Agent
# 指令与采样参数在创建时传入（也可在 run 时覆盖）


async def main():
    client, cfg = get_client()
    agent = client.as_agent(name="Joker", instructions="你是一名冷笑话演员，回答简短且有梗。")

    # 1. 一次性调用：一行 run 拿到回复
    response = await agent.run("讲一个关于程序员的笑话")
    print(f"[run] {response.text}\n")

    # 2. 流式输出（打字机效果）：run(stream=True) 逐段产出 AgentResponseUpdate
    print("[流式] ", end="")
    async for update in agent.run("再讲一个更短的", stream=True):
        print(update.text or "", end="")
    print("\n")

    # 3. 多模态输入：文本 + 图片 URI 的富内容 Message
    #    （需要服务端模型支持 vision；不支持时会走 except，可跳过）
    try:
        from agent_framework import Content, Message
        message = Message(
            role="user",
            contents=[
                Content.from_text("用一句话描述这张图片，并讲一个相关笑话"),
                Content.from_uri("https://upload.wikimedia.org/wikipedia/commons/3/3f/Cat03.jpg", media_type="image/jpeg"),
            ],
        )
        print(f"[多模态] {(await agent.run(message)).text}")
    except Exception as ex:
        print(f"[多模态] 服务端不支持或调用失败：{ex}")

    # ---- 课堂练习 ----
    # 1. 修改 instructions 观察风格变化
    # 2. 换 config.json 的 model，业务代码不变（统一抽象的意义）

asyncio.run(main())
