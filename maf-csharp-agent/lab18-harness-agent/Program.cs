// Lab 18：Harness Agent（长任务型 Agent）—— 待办管理 + 上下文压缩 + 工具审批
//
// 官方 Harness Agent 内置上述三项能力；本 lab 用手工循环演示其工作原理，
// 便于在真实 Harness API 到位前理解机制（参照课程笔记 Lab 18）。
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

// 工具集：标记"危险"的工具执行前需人工审批
static string MoveFile(string from, string to) => $"已把 {from} 移动到 {to}";
static string ListDir(string path) => "file1.txt, notes.md, archive/, docs/";

var tools = new Dictionary<string, (Func<string, string, string> Fn, bool NeedsApproval)>
{
    ["ListDir"]  = ((a, _) => ListDir(a), false),
    ["MoveFile"] = (MoveFile, true),
};

var agent = new ChatClientAgent(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions
    {
        Instructions = """
        你是文件整理助手。收到任务后：
        1. 先输出待办清单（TodoList），每行一个任务；
        2. 逐个任务执行：先说明要调用什么工具与参数；
        3. 每完成一步，输出更新后的清单（完成项打 [x]）。
        任务：把 file1.txt 归档到 archive/，把 notes.md 移到 docs/。
        """,
    },
});

// 长任务循环：模拟 Harness 的 todo 推进 + 上下文压缩 + 审批
var thread = await agent.CreateSessionAsync();
var todoText = (await agent.RunAsync("开始整理", thread)).Text;
Console.WriteLine($"--- 待办清单 ---\n{todoText}\n");

for (int turn = 1; turn <= 4; turn++)
{
    Console.Write($"[工具审批] 允许执行本轮文件操作? (y/n): ");
    if (Console.ReadLine()?.Trim().Equals("y", StringComparison.OrdinalIgnoreCase) != true)
    {
        Console.WriteLine("[已拒绝] 本轮操作取消\n");
        continue;
    }

    var result = (await agent.RunAsync($"继续执行第 {turn} 步，并更新清单", thread)).Text;
    Console.WriteLine(result);

    // 上下文压缩：对话过长时让模型自己总结历史（Harness 内置行为）
    if (turn == 2)
        Console.WriteLine("\n[上下文压缩] 对话超过阈值 → 用摘要替换早期消息，保留最新轮\n");
}

// ---- 课堂练习 ----
// 1. 实现真正的上下文压缩：保留 System + 摘要 + 最近 N 轮
// 2. 待办清单落盘（todo.json），进程重启后继续推进
