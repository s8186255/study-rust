# Lab 0：环境准备 —— 连通性验证
# 对应 maf-csharp-agent/lab0-env；验证 venv、agent-framework 安装与模型服务连通
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client


async def main():
    client, cfg = get_client()
    print(f"provider: {cfg.base_url}  model: {cfg.model}\n")

    agent = client.as_agent(name="ping", instructions="只回答 PONG")
    response = await agent.run("PING")
    print(f"连通性验证: {response.text}")
    print("\n环境就绪 ✔（agent-framework-core 1.25.0 + OpenAI 兼容端点）")

asyncio.run(main())
