// Lab 10：多智能体协作 —— Handoff（交接）
// 分流 Agent 根据用户问题把控制权"交接"给专业 Agent，上下文随交接转移
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Microsoft.Agents.AI.Workflows;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

static ChatClientAgent NewAgent(IChatClient c, string name, string instructions) =>
    new(c, new ChatClientAgentOptions
    {
        Name = name,
        ChatOptions = new ChatOptions { Instructions = instructions },
    });

var triage = NewAgent(client, "Triage",
    "你是客服分流员。判断问题属于'订单'还是'技术支持'，把控制权交给对应专员。");
var order = NewAgent(client, "OrderSupport", "你是订单专员，负责查订单、退换货，回答不超过 3 句。");
var tech = NewAgent(client, "TechSupport", "你是技术支持，负责排查登录、报错问题，回答不超过 3 句。");

// Handoff 工作流：triage 是入口，可把控制权交给 order / tech
var workflow = new HandoffWorkflowBuilder(triage)
    .WithHandoff(triage, order)
    .WithHandoff(triage, tech)
    .AddParticipants([order, tech])
    .Build();

foreach (var question in new[]
{
    "我的订单三天了还没发货",
    "登录 APP 一直报 500 错误",
})
{
    Console.WriteLine($"\n=== 用户: {question} ===");
    await using Run run = await InProcessExecution.RunAsync(workflow, new ChatMessage(ChatRole.User, question));
    foreach (var evt in run.OutgoingEvents)
        if (evt is WorkflowOutputEvent output)
            Console.WriteLine($"[响应] {output}");
}

// ---- 课堂练习 ----
// 1. 加一个"投诉专员"，观察分流与交接
// 2. 打印全部事件（去掉 if 过滤），观察交接消息如何流转
