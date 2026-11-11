// Lab 11：多智能体协作 —— Group Chat（群聊）
// RoundRobinGroupChatManager 编排多个 Agent 轮流发言（程序员 + 评审员），按完成条件终止
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Microsoft.Agents.AI.Workflows;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

var writer = new ChatClientAgent(client, new ChatClientAgentOptions
{
    Name = "Writer",
    ChatOptions = new ChatOptions { Instructions = "你是程序员，负责写出简短的代码思路（不超过 5 行）。" },
});
var reviewer = new ChatClientAgent(client, new ChatClientAgentOptions
{
    Name = "Reviewer",
    ChatOptions = new ChatOptions { Instructions = "你是评审员。若思路合格，回复以 APPROVED 开头并说明理由；否则给出修改意见。" },
});

// 群聊工作流：参与者注入到 manager 工厂，轮转发言；终止条件 = 最后一条助手消息以 APPROVED 开头
var workflow = AgentWorkflowBuilder.CreateGroupChatBuilderWith(agents =>
        new RoundRobinGroupChatManager(agents, (_, history, _) => ValueTask.FromResult(
            history.LastOrDefault(m => m.Role == ChatRole.Assistant)?.Text?.StartsWith("APPROVED") == true)))
    .AddParticipants([writer, reviewer])
    .Build();

await using Run run = await InProcessExecution.RunAsync(
    workflow, new ChatMessage(ChatRole.User, "写一个判断字符串是否回文的函数思路"));
foreach (var evt in run.OutgoingEvents)
    if (evt is WorkflowOutputEvent output)
        Console.WriteLine($"[群聊输出] {output}");

// ---- 课堂练习 ----
// 1. 在终止条件里加最大轮数限制（manager.MaximumIterationCount），防止死循环
// 2. 自定义 GroupChatManager 子类，实现按内容选择的调度策略
