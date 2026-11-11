# Lab 5：ReAct 循环（Reasoning + Acting）—— 显式控制推理-行动循环
# 对应 maf-csharp-agent/lab5-react
#
# Lab 2 的原生 Function Calling 是"隐式 ReAct"；本 lab 自己实现显式循环：
# Thought → Action → Observation → ... → Final Answer，完全掌控轨迹与迭代上限
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client

# ---- 本地工具注册表（模拟环境反馈）----
def get_weather(city: str) -> str:
    return "晴，18℃，东风 2 级" if "北京" in city else "多云，22℃"

def get_flight_price(route: str) -> str:
    return "北京-上海 经济舱 850 元" if "北京" in route else "约 1200 元"

TOOLS = {"get_weather": get_weather, "get_flight_price": get_flight_price}

MAX_ITERATIONS = 5

async def main():
    client, _ = get_client()
    agent = client.as_agent(
        name="ReActAgent",
        instructions=(
            "你是 ReAct 代理。每一步只输出一个 Thought/Action 块：\n"
            "Thought: 你的推理\n"
            "Action: 工具名（只能是 get_weather 或 get_flight_price）\n"
            "Action Input: 工具参数（一段文字或 JSON）\n"
            "得到 Observation 后继续下一步；当信息足够时，最后一行输出 "
            "Final Answer: <答案>。不要编造 Observation。"
        ),
    )

    question = "我下周想从北京去上海出差，告诉我那边天气如何，机票大概多少钱？"
    print(f"[问题] {question}\n")

    history = [f"Question: {question}"]
    for i in range(1, MAX_ITERATIONS + 1):
        thought_block = (await agent.run("\n".join(history))).text
        print(f"--- 第 {i} 轮 ---\n{thought_block}\n")
        history.append(f"Assistant: {thought_block}")

        action_match = re.search(r"Action:\s*(\w+)", thought_block)
        input_match = re.search(r"Action Input:\s*(.+)", thought_block)
        if not action_match or thought_block.rstrip().endswith(("Final Answer",)) is False and "Final Answer:" in thought_block:
            pass
        if "Final Answer:" in thought_block:
            print("[ReAct 循环结束]")
            return
        if not action_match:
            print("[终止] 未解析到 Action，模型可能已给出答案或偏离协议")
            return

        name, arg = action_match.group(1), (input_match.group(1).strip() if input_match else "")
        try:
            observation = TOOLS[name](arg)
        except Exception as ex:
            observation = f"工具执行失败：{ex}"
        print(f"Observation: {observation}\n")
        history.append(f"Observation: {observation}")
    else:
        print("[终止] 达到最大迭代次数（死循环保护）")

    # ---- 课堂练习 ----
    # 1. 注入错误 Observation（如 get_weather 返回异常），验证自我纠错
    # 2. 打印完整轨迹（history），对比 Lab 2 隐式 Function Calling 的过程不可见性

asyncio.run(main())
