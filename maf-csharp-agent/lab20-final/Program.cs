// Lab 20：综合实战（毕业项目）—— 智能客服工作台
//
// 流程：意图识别 → 路由到专业 Agent（带工具）→ 危险操作人工审批 → 结果汇总
// 覆盖：Lab 1 统一抽象 / Lab 2 工具 / Lab 3 会话 / Lab 13 HITL / Lab 17 中间件
using Microsoft.Agents.AI;
using System.ComponentModel;
using System.Diagnostics;
using Microsoft.Extensions.AI;
using Maf.Common;

// 遥测中间件（Lab 17 成果复用）
ActivitySource.AddActivityListener(new ActivityListener
{
    ShouldListenTo = s => s.Name == "MAF.Final",
    Sample = (ref ActivityCreationOptions<ActivityContext> _) => ActivitySamplingResult.AllData,
    ActivityStopped = a => Console.WriteLine($"[OTel] {a.DisplayName} {a.Duration.TotalMilliseconds:F0}ms"),
});

var (client, _) = AgentFactory.CreateDefault();
IChatClient pipeline = new TracingClient(client);

// ---- 角色定义 ----
[Description("查询订单状态")]
static string GetOrder([Description("订单号")] string orderId) => $"订单 {orderId}：已发货（圆通），预计明天送达";

[Description("执行退款（危险操作）")]
static string Refund([Description("订单号")] string orderId) => $"订单 {orderId} 已退款";

var intent = new ChatClientAgent(pipeline, new ChatClientAgentOptions
{
    Name = "Intent",
    ChatOptions = new ChatOptions { Instructions = "识别用户意图，只输出 Order / Refund / Tech / Other 之一，不要多余文字。" },
});
var orderAgent = new ChatClientAgent(pipeline, new ChatClientAgentOptions
{
    Name = "OrderSupport",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是订单专员，先调用工具查订单，再回复。",
        Tools = [AIFunctionFactory.Create(GetOrder)],
    },
});
var refundAgent = new ChatClientAgent(pipeline, new ChatClientAgentOptions
{
    Name = "RefundSupport",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是退款专员。先说明将执行的退款操作及订单号，等待确认后再调用工具。",
        Tools = [AIFunctionFactory.Create(Refund)],
    },
});
var fallback = new ChatClientAgent(pipeline, new ChatClientAgentOptions
{
    Name = "General",
    ChatOptions = new ChatOptions { Instructions = "你是通用客服，简短回答。" },
});

// ---- 主循环：多轮客服对话 ----
Console.WriteLine("智能客服工作台（输入 q 退出）");
var intentSession = await intent.CreateSessionAsync();
while (true)
{
    Console.Write("\n用户输入: ");
    var question = Console.ReadLine();
    if (string.IsNullOrWhiteSpace(question) || question.Trim() is "q" or "quit") break;

    // 1. 意图识别（同一会话内多轮）
    var intentText = (await intent.RunAsync(question, intentSession)).Text.Trim();
    Console.WriteLine($"[意图识别] {intentText}");

    // 2. 路由（Handoff 思路）
    AIAgent target = intentText switch
    {
        "Order"  => orderAgent,
        "Refund" => refundAgent,
        _        => fallback,
    };

    // 3. 危险操作人工审批（HITL）
    if (target == refundAgent)
    {
        Console.Write("[人工审批] 允许执行退款? (y/n): ");
        if (Console.ReadLine()?.Trim().Equals("y", StringComparison.OrdinalIgnoreCase) != true)
        {
            Console.WriteLine("[已拦截] 退款操作已取消，转人工处理。");
            continue;
        }
    }

    // 4. 专业 Agent 处理
    var reply = (await target.RunAsync(question, await target.CreateSessionAsync())).Text;
    Console.WriteLine($"[客服] {reply}");
}

Console.WriteLine("会话结束。");

/// <summary>追踪中间件（Lab 17 复用）</summary>
sealed class TracingClient(IChatClient inner, string sourceName = "MAF.Final") : DelegatingChatClient(inner)
{
    private readonly ActivitySource Source = new(sourceName);
    public override async Task<ChatResponse> GetResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null, CancellationToken ct = default)
    {
        using var activity = Source.StartActivity("chat.completions");
        activity?.SetTag("model", options?.ModelId);
        return await base.GetResponseAsync(messages, options, ct);
    }
}
