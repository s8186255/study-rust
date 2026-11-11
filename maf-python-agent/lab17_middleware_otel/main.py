# Lab 17：中间件 + 可观测性 —— 拦截与观测 Agent 行为
# 对应 maf-csharp-agent/lab17-middleware-otel
#
# AgentMiddleware：在 Agent 调用前后插入逻辑（日志、脱敏、重试、合规检查）
# 生产环境建议配合 agent_framework.observability（OpenTelemetry）导出完整调用链
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client
from agent_framework import AgentContext, AgentMiddleware


class TelemetryMiddleware(AgentMiddleware):
    """日志中间件：记录每次 LLM 调用的耗时"""

    async def process(self, context: AgentContext, call_next):
        start = time.perf_counter()
        response = await call_next()
        print(f"[遥测] 本次调用耗时 {time.perf_counter() - start:.2f}s")
        return response


class SensitiveWordMiddleware(AgentMiddleware):
    """合规中间件：返回前做敏感词过滤"""

    BLOCKED = ("机密", "绝密")

    async def process(self, context: AgentContext, call_next):
        response = await call_next()
        text = getattr(response, "text", None)
        if text:
            for word in self.BLOCKED:
                if word in text:
                    print(f"[合规拦截] 检出敏感词：{word}")
                    return type(response).from_updates([])  # 返回空响应
        return response


async def main():
    client, _ = get_client()
    agent = client.as_agent(
        name="GuardedAssistant",
        instructions="你是普通助手，正常回答。",
        middleware=[TelemetryMiddleware(), SensitiveWordMiddleware()],
    )

    print((await agent.run("用一句话介绍 Python")).text)
    print((await agent.run("请把'这是绝密文件'这句话复述一遍")).text)

    # ---- 课堂练习 ----
    # 1. 重试中间件：捕获网络异常，指数退避重试 2 次
    # 2. 接入 OpenTelemetry：安装 opentelemetry-sdk 后调用
    #    agent_framework.observability.setup_observability()，观察 span 层级与 token 用量

asyncio.run(main())
