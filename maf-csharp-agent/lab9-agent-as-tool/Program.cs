// Lab 9：Agent-as-Tool —— 多 Agent 协作的基础模式
// 把一个 Agent 包装成另一个 Agent 的工具（AsAIFunction），形成分层委托架构，实现职责隔离
using Microsoft.Agents.AI;
using System.ComponentModel;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

[Description("查询指定客户的投资组合持仓")]
static string GetPortfolio([Description("客户名")] string clientName) =>
    $"{clientName} 当前持仓：股票 60%、债券 30%、现金 10%";

// 子 Agent：数据分析（内部再用投资组合工具）
ChatClientAgent analyst = new(client, new ChatClientAgentOptions
{
    Name = "DataAnalyst",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是数据分析专家。先调用工具查询持仓，再给出 2 句以内的分析。",
        Tools = [AIFunctionFactory.Create(GetPortfolio)],
    },
});

// 把子 Agent 包装成工具 —— 编排方无需知道子 Agent 的实现细节
var analystTool = analyst.AsAIFunction();

// 编排 Agent：投资顾问
ChatClientAgent advisor = new(client, new ChatClientAgentOptions
{
    Name = "InvestmentAdvisor",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是投资顾问。需要数据分析时调用 DataAnalyst 工具，基于其结果给出简短建议。",
        Tools = [analystTool],
    },
});

Console.WriteLine((await advisor.RunAsync("帮我分析 Alice 的资产配置是否合理")).Text);

// ---- 课堂讨论 ----
// Agent-as-Tool（嵌套委托、结果回传）vs Handoff（平级、控制权转移）：见课程笔记 Lab 9 / Lab 10
