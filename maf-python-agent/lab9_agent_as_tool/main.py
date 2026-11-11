# Lab 9：Agent-as-Tool —— 多 Agent 协作的基础模式
# 对应 maf-csharp-agent/lab9-agent-as-tool
# 把一个 Agent 包装成另一个 Agent 的工具（agent.as_tool()），形成分层委托架构，实现职责隔离
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import tool


@tool
def get_portfolio(client_name: str) -> str:
    """查询指定客户的投资组合持仓"""
    return f"{client_name} 当前持仓：股票 60%、债券 30%、现金 10%"


async def main():
    client, _ = get_client()

    # 子 Agent：数据分析（内部再用投资组合工具）
    analyst = client.as_agent(
        name="DataAnalyst",
        instructions="你是数据分析专家。先调用工具查询持仓，再给出 2 句以内的分析。",
        tools=[get_portfolio],
    )

    # 把子 Agent 包装成工具 —— 编排方无需知道子 Agent 的实现细节
    analyst_tool = analyst.as_tool(
        name="DataAnalyst",
        description="查询指定客户的投资组合并给出数据分析",
        arg_name="client_name",
        arg_description="客户名",
    )

    # 编排 Agent：投资顾问
    advisor = client.as_agent(
        name="InvestmentAdvisor",
        instructions="你是投资顾问。需要数据分析时调用 DataAnalyst 工具，基于其结果给出简短建议。",
        tools=[analyst_tool],
    )

    print((await advisor.run("帮我分析 Alice 的资产配置是否合理")).text)

    # ---- 课堂讨论 ----
    # Agent-as-Tool（嵌套委托、结果回传）vs Handoff（平级、控制权转移）：见课程笔记 Lab 9 / Lab 10

asyncio.run(main())
