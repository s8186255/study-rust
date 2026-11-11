# Lab 19：Foundry Agent Service 集成（生产部署）
# 对应 maf-csharp-agent/lab19-foundry
#
# 将本地 ChatClientAgent 迁移到 Microsoft Foundry Agent Service：
# 获得服务端聊天历史、内置安全护栏与 Azure 身份认证（Entra ID）
# 依赖：pip install agent-framework-azure-ai（含 FoundryChatClient）
# 环境变量：FOUNDRY_PROJECT_ENDPOINT、FOUNDRY_MODEL_DEPLOYMENT_NAME、FOUNDRY_PROJECT_NAME
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common.maf_common  # noqa: F401  引入 UTF-8 控制台修复


async def main():
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        print("未配置 Foundry 环境。迁移步骤：\n")
        print("1. pip install agent-framework-azure-ai")
        print("2. 设置环境变量：FOUNDRY_PROJECT_ENDPOINT / FOUNDRY_MODEL_DEPLOYMENT_NAME / FOUNDRY_PROJECT_NAME")
        print("3. az login 完成 Entra ID 认证")
        print("4. 把本 lab 的 get_client() 替换为 FoundryChatClient：\n")
        print(
            "   from agent_framework.foundry import FoundryChatClient\n"
            "   client = FoundryChatClient(project_endpoint=os.environ['FOUNDRY_PROJECT_ENDPOINT'],\n"
            "                              model=os.environ['FOUNDRY_MODEL_DEPLOYMENT_NAME'])\n"
            "   agent = client.as_agent(name='ProdAgent', instructions='你是生产环境 Agent，回答简短。')\n"
        )
        print("5. 验证服务端历史自动延续：会话由 Agent Session Store 托管（与 Lab 3/15 的自管历史对比）")
        return

    from agent_framework.foundry import FoundryChatClient

    client = FoundryChatClient(
        project_endpoint=endpoint,
        model=os.environ.get("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"),
    )
    agent = client.as_agent(name="ProdAgent", instructions="你是生产环境 Agent，回答简短。")

    session = agent.create_session()
    print((await agent.run("一句话介绍 MAF", session=session)).text)
    print((await agent.run("你刚才说了什么？", session=session)).text)  # 服务端历史延续

asyncio.run(main())
