# Lab 6：MCP 工具接入（Model Context Protocol）
# 对应 maf-csharp-agent/lab6-mcp
#
# 通过 MCPStdioTool 连接官方 filesystem MCP Server（npx 启动，需本机 Node.js），
# Agent 自动获得其全部工具（读/写/列目录），协议层动态发现
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import MCPStdioTool

LAB_DIR = Path(__file__).resolve().parent
DEMO_DIR = LAB_DIR / "demo_files"
DEMO_DIR.mkdir(exist_ok=True)


async def main():
    client, _ = get_client()

    # MCP 工具：stdio 传输，npx 拉起 filesystem server（Windows 下经 cmd /c 包装）
    mcp = MCPStdioTool(
        name="filesystem",
        command="cmd",
        args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", str(DEMO_DIR)],
    )
    async with mcp:
        agent = client.as_agent(
            name="FileAgent",
            instructions="你是文件助手，用 MCP 工具完成文件操作，每次操作前先说明要做什么。",
            tools=[mcp],
        )
        response = await agent.run(
            f"在目录 {DEMO_DIR} 下创建 hello.txt，内容写 'Hello from MAF Python!'，然后读取并确认内容"
        )
        print(response.text)

    # ---- 课堂练习 ----
    # 1. 换成其他 MCP Server（如 fetch），观察工具动态发现
    # 2. 自建一个最简 MCP Server（mcp.FastMCP）供 Agent 调用

asyncio.run(main())
