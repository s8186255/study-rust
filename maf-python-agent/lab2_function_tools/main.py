# Lab 2：函数工具（Function Tools）—— 让 Agent "动手做事"
# 对应 maf-csharp-agent/lab2-function-tools
# @tool 装饰器把普通 Python 函数注册为 LLM 可调用的工具（Function Calling）
import asyncio
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import tool


@tool
def get_weather(city: str) -> str:
    """查询指定城市的当前天气"""
    if "北京" in city:
        return "晴，18℃，东风 2 级"
    return "多云，22℃，湿度 60%"


@tool
def discount(price: float) -> float:
    """按人民币金额计算 8 折后的价格"""
    return round(price * 0.8, 2)


async def main():
    client, _ = get_client()
    agent = client.as_agent(
        name="LifeAgent",
        instructions="你是生活助手。涉及天气或折扣问题时必须先调用工具，不要编造结果。",
        tools=[get_weather, discount],
    )

    print((await agent.run("北京今天天气怎么样？适合穿什么？")).text)
    print((await agent.run("一件 299 元的外套打 8 折多少钱？")).text)

    # ---- 课堂练习 ----
    # 1. 多工具场景：观察 Agent 自主选择调用哪个工具
    # 2. 故意把 docstring 写含糊，观察调用错乱 —— 理解 docstring 即工具描述

asyncio.run(main())
