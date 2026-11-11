// Lab 8：分支与并发 —— 条件路由（Switch/条件边）+ 扇出
using Microsoft.Agents.AI.Workflows;

var even = new FunctionExecutor<int, int>(
    "Even", (input, ctx, ct) => ValueTask.FromResult(input * 10));
var odd = new FunctionExecutor<int, int>(
    "Odd", (input, ctx, ct) => ValueTask.FromResult(input + 1));

// 条件边（AddEdge<T> + Func<T,bool>）：根据消息内容走不同分支
var workflow = new WorkflowBuilder(even)
    .AddEdge(even, even, (int n) => n % 2 == 0)
    .AddEdge(even, odd, (int n) => n % 2 != 0)
    .WithOutputFrom(even, odd)
    .Build();

foreach (var input in new[] { 4, 7 })
{
    Console.WriteLine($"\n=== 输入 {input} ===");
    await using Run run = await InProcessExecution.RunAsync(workflow, input);
    foreach (var evt in run.OutgoingEvents)
        if (evt is WorkflowOutputEvent output)
            Console.WriteLine($"分支输出: {output.As<int>()}");
}

// ---- 课堂练习 ----
// 1. 扇出+扇入：AddFanOutEdge / AddFanInBarrierEdge，一个输入同时给两个"评审"节点再汇聚
// 2. 对比 LangGraph 的 conditional edges（见笔记对比表）
