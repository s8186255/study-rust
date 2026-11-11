// Lab 12：MagenticWorkflow 磁控调度（MAF 招牌，源自 Magentic-One）
// Orchestrator 负责任务规划 + 进度账本（Ledger），动态决定"下一步谁来做、是否重规划、何时完成"
// 与 Group Chat 的差异：Group Chat 靠轮转规则，Magentic 靠目标驱动的动态编排
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

var orchestrator = NewAgent(client, "Orchestrator", "你是任务编排者，负责规划与调度。");
var researcher = NewAgent(client, "Researcher", "你是研究员，负责检索与整理事实要点，回答不超过 4 句。");
var coder = NewAgent(client, "Coder", "你是程序员，负责编写或修正代码片段，只输出代码与一句说明。");
var reviewer = NewAgent(client, "Reviewer", "你是评审员，检查产出是否满足任务目标，回答不超过 3 句。");

var workflow = new MagenticWorkflowBuilder(orchestrator)
    .AddParticipants([researcher, coder, reviewer])
    .WithMaxRounds(10)          // 防失控：编排轮数上限
    .Build();

await using Run run = await InProcessExecution.RunAsync(
    workflow,
    new ChatMessage(ChatRole.User, "写一个把 CSV 的前 3 行转成 Markdown 表格的 C# 方法，并做自检"));
foreach (var evt in run.OutgoingEvents)
    if (evt is WorkflowOutputEvent output)
        Console.WriteLine($"[Magentic 输出]\n{output}");

// ---- 课堂练习 ----
// 1. 打印全部事件观察 Ledger（任务清单/事实/进度）如何推进
// 2. 人为让 Coder 指令改成"总是输出错误代码"，观察 Orchestrator 的重规划能力
