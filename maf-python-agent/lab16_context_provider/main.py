# Lab 16：上下文提供者（Context Providers）—— 每次调用前自动注入知识库检索结果（RAG）
# 对应 maf-csharp-agent/lab16-context-provider
# ContextProvider 在模型调用前被回调，可向 SessionContext 注入消息/指令/工具
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import ContextProvider

# 极简"知识库"（生产中替换为向量检索）
KB = [
    ("报销", "《差旅制度》：月度差旅报销上限 5000 元，审核需 3 个工作日。"),
    ("请假", "《考勤制度》：年假 10 天，需提前 2 天在 OA 申请。"),
    ("打印机", "《办公指南》：3 楼茶水间有 2 台共享打印机，工号登录使用。"),
]


class RagContextProvider(ContextProvider):
    """RAG 上下文提供者：请求前自动检索并注入"""

    def __init__(self):
        super().__init__(source_id="rag")

    async def before_run(self, *, agent, session, context, state) -> None:
        question = "".join(m.text or "" for m in context.input_messages)[:200]
        hits = [doc for kw, doc in KB if kw in question]
        if hits:
            context.extend_instructions(
                "rag",
                "【知识库检索结果】\n" + "\n".join(hits),
            )


async def main():
    client, _ = get_client()
    agent = client.as_agent(
        name="EnterpriseAssistant",
        instructions="你是企业助手。回答时引用知识来源（【知识库检索结果】中的制度名）。",
        context_providers=[RagContextProvider()],
    )

    print((await agent.run("公司差旅报销上限是多少？多久到账？")).text)
    print()
    print((await agent.run("年假有几天？怎么申请？")).text)

    # ---- 课堂练习 ----
    # 1. 把"关键词匹配"换成向量检索（嵌入模型 + 余弦相似度，参考 agent_framework._vectors）
    # 2. 对比：手动拼接上下文（Lab 5 的 Observation）与 Provider 自动注入的差异

asyncio.run(main())
