// Lab 7：Workflow 入门 —— 两个 Executor 的顺序流水线
// 理解三要素：Executor（收消息→处理→发消息）、Edge（类型化路由）、Run/事件流
// 注意：Workflow 是纯 C# 编排，节点不一定是 Agent；与 Lab 9+ 的 Agent 编排形成对照
//
// FunctionExecutor<TIn, TOut>：MAF 提供的"函数式节点"，用委托定义处理逻辑；
// 自定义节点也可以继承 Executor<TInput> 并重写 public override ValueTask HandleAsync(...)，
// 中间结果用 context.SendMessageAsync / context.YieldOutputAsync 传递。
using Microsoft.Agents.AI.Workflows;

var upper = new FunctionExecutor<string, string>(
    "UpperCase", (input, ctx, ct) => ValueTask.FromResult(input.ToUpperInvariant()));
var count = new FunctionExecutor<string, string>(
    "CountLength", (input, ctx, ct) => ValueTask.FromResult($"长度 = {input.Length}"));

// 声明式建图：源节点 → 目标节点，指定输出节点
var workflow = new WorkflowBuilder(upper)
    .AddEdge(upper, count)
    .WithOutputFrom(count)
    .Build();

await using Run run = await InProcessExecution.RunAsync(workflow, "hello maf workflow");
foreach (var evt in run.OutgoingEvents)
{
    if (evt is WorkflowOutputEvent output)
        Console.WriteLine($"工作流输出: {output.As<string>()}");
}

// ---- 课堂练习 ----
// 1. 加第三个节点（如 TrimExecutor），串成三步流水线
// 2. 结合 Agent：让某个 Executor 内部调用 ChatClientAgent（翻译→审校→润色）
// 3. 改用继承 Executor<TInput> 的自定义节点，理解 HandleAsync / SendMessageAsync / YieldOutputAsync
