// Lab 4：结构化输出（Structured Output）—— 让 Agent 直接输出强类型 C# 对象
using System.Text.Json;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();
ChatClientAgent agent = new(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是发票信息抽取助手，只依据文本内容抽取，不要编造。" },
});

// RunAsync<T>：模型按 T 的 JSON Schema 返回，框架负责解析为强类型
var response = await agent.RunAsync<Invoice>(
    "从下面的文本抽取发票信息：\n发票号码 2024-0981；购买方：上海科技有限公司；合计金额 12800.50 元");

var invoice = response.Result;
Console.WriteLine($"号码={invoice.InvoiceNo}  购买方={invoice.Buyer}  金额={invoice.TotalAmount}");

// ---- 课堂练习 ----
// 1. 换一段不完整文本，观察缺失字段的处理（可空字段设计）
// 2. 把 record 换成更复杂的嵌套类型（如明细行列表）

public sealed record Invoice(string InvoiceNo, string Buyer, double TotalAmount);
