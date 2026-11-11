// Lab 13：人机协同（Human-in-the-Loop）—— Agent 提出方案 → 人工审批 → 继续 / 回退
//
// 这里演示 Agent 级 HITL；工作流级请用 RequestInfoExecutor + InProcessExecution.ResumeAsync
// （可结合 Lab 7 的顺序工作流，在校验节点暂停等待人工输入）
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();
var planner = new ChatClientAgent(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是方案规划师，输出不超过 5 行的简短方案。" },
});

// 1. Agent 产出方案
var thread = await planner.CreateSessionAsync();
var plan = (await planner.RunAsync("为公司年会出一个简短的创意方案", thread)).Text;
Console.WriteLine($"--- Agent 方案 ---\n{plan}\n");

// 2. 人工审批（控制台模拟）
Console.Write("审批结果（y = 通过 / n = 回退重写）: ");
var approved = Console.ReadLine()?.Trim().Equals("y", StringComparison.OrdinalIgnoreCase) == true;

// 3. 根据审批结果继续执行或回退
if (approved)
{
    Console.WriteLine("\n[已批准] 按方案执行……（此处接入真实执行逻辑）");
}
else
{
    var revised = (await planner.RunAsync("方案被否决了，请重写一版更简单、成本更低的", thread)).Text;
    Console.WriteLine($"--- 修订方案 ---\n{revised}");
}

// ---- 课堂练习 ----
// 1. 循环审批：连续 n 次否决后升级给"人工接管"角色
// 2. 把审批做成工具：只有调用 approve_plan 工具（需人工确认）才能继续
