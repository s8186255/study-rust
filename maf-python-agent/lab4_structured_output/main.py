# Lab 4：结构化输出（Structured Output）—— 让 Agent 直接输出强类型 Python 对象
# 对应 maf-csharp-agent/lab4-structured-output
# response_format 传 Pydantic 模型：模型按其 JSON Schema 返回，框架解析为强类型
import asyncio
import sys
from pathlib import Path

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.maf_common import get_client


class Invoice(BaseModel):
    """发票信息"""
    invoice_no: str = Field(description="发票号码")
    buyer: str = Field(description="购买方")
    total_amount: float = Field(description="合计金额")


async def main():
    client, _ = get_client()
    agent = client.as_agent(name="Extractor", instructions="你是发票信息抽取助手，只依据文本内容抽取，不要编造。")

    # run 时通过 options 传 response_format；AgentResponse.value 即解析后的对象
    response = await agent.run(
        "从下面的文本抽取发票信息：\n发票号码 2024-0981；购买方：上海科技有限公司；合计金额 12800.50 元",
        options={"response_format": Invoice},
    )
    invoice: Invoice = response.value
    print(f"号码={invoice.invoice_no}  购买方={invoice.buyer}  金额={invoice.total_amount}")

    # ---- 课堂练习 ----
    # 1. 换一段不完整文本，观察缺失字段的处理（Optional 字段设计）
    # 2. 把模型换成更复杂的嵌套类型（如明细行列表）

asyncio.run(main())
