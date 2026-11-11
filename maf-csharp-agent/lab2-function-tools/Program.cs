// Lab 2：函数工具（Function Tools）—— 让 Agent "动手做事"
// AIFunctionFactory 把普通 C# 方法注册为 LLM 可调用的工具（Function Calling）
using System.ComponentModel;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, cfg) = AgentFactory.CreateDefault();

[Description("查询指定城市的当前天气")]
static string GetWeather([Description("城市名，例如：北京")] string city) =>
    city.Contains("北京") ? "晴，18℃，东风 2 级" : "多云，22℃，湿度 60%";

[Description("按人民币金额计算 8 折后的价格")]
static double Discount([Description("商品原价")] double price) => Math.Round(price * 0.8, 2);

AIAgent agent = new ChatClientAgent(client, new ChatClientAgentOptions
{
    Name = "LifeAgent",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是生活助手。涉及天气或折扣问题时必须先调用工具，不要编造结果。",
        Temperature = cfg.Temperature,
        Tools = [AIFunctionFactory.Create(GetWeather), AIFunctionFactory.Create(Discount)],
    },
});

Console.WriteLine((await agent.RunAsync("北京今天天气怎么样？适合穿什么？")).Text);
Console.WriteLine((await agent.RunAsync("一件 299 元的外套打 8 折多少钱？")).Text);

// ---- 课堂练习 ----
// 1. 多工具场景：观察 Agent 自主选择调用哪个工具
// 2. 故意把工具描述写含糊，观察调用错乱 —— 理解 [Description] 的作用
