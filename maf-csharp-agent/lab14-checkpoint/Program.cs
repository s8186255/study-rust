// Lab 14：Checkpoint 持久化 —— 工作流在中断后从存档恢复运行
// 结合 Lab 13 的审批场景：人工审批"隔夜"再恢复，工作流进度不丢
using Microsoft.Agents.AI.Workflows;

FunctionExecutor<string, string> Step(string name) =>
    new(name, (input, ctx, ct) => ValueTask.FromResult($"{name}: {input}"));

var step1 = Step("提取信息");
var step2 = Step("校验");
var step3 = Step("总结");

var workflow = new WorkflowBuilder(step1)
    .AddEdge(step1, step2)
    .AddEdge(step2, step3)
    .WithOutputFrom(step3)
    .Build();

// 每个超级步的检查点写入检查点管理器（演示用内存版；持久化可换 JSON 文件存储）
var checkpoints = CheckpointManager.CreateInMemory();
string sessionId = "";

await using (Run run = await InProcessExecution.RunAsync(workflow, "原始数据", checkpoints))
{
    sessionId = run.SessionId;
    foreach (var evt in run.OutgoingEvents)
        if (evt is WorkflowOutputEvent output)
            Console.WriteLine($"工作流输出: {output.As<string>()}");
}

// 从最近一次检查点恢复（演示：重新驱动一次，进度从存档续起）
var latest = await checkpoints.GetLatestCheckpointAsync(sessionId);
if (latest is not null)
{
    Console.WriteLine("\n[Checkpoint] 找到最近检查点，恢复运行……");
    await using Run resumed = await InProcessExecution.ResumeAsync(workflow, latest, checkpoints);
    foreach (var evt in resumed.OutgoingEvents)
        if (evt is WorkflowOutputEvent output)
            Console.WriteLine($"恢复后输出: {output.As<string>()}");
}

Console.WriteLine("\n练习：在 step2 抛出异常中断 → 从最近检查点 Resume，验证 step1 不再重跑");
