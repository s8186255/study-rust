// Lab 17：中间件 + OpenTelemetry 链路追踪
// 1) 遥测中间件：记录每次 LLM 调用的延迟与 token 消耗
// 2) 合规中间件：返回前敏感内容过滤
// 3) 追踪中间件：产出 Activity（OpenTelemetry Span），可接 Aspire Dashboard / 后端
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

// 注册 Activity 监听器（演示用；生产环境用 OpenTelemetry SDK 导出）
ActivitySource.AddActivityListener(new ActivityListener
{
    ShouldListenTo = s => s.Name == "MAF.Lab17",
    Sample = (ref ActivityCreationOptions<ActivityContext> _) => ActivitySamplingResult.AllData,
    ActivityStopped = a => Console.WriteLine($"[OTel] span={a.DisplayName}  {a.Duration.TotalMilliseconds:F0}ms\n"),
});

var (client, _) = AgentFactory.CreateDefault();

// 中间件链：Tracing(最外) → Telemetry → Compliance → 真实模型
IChatClient pipeline = new TracingClient(
    new TelemetryClient(
        new ComplianceClient(client)));

var agent = new ChatClientAgent(pipeline, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是普通助手，正常回答。" },
});

Console.WriteLine((await agent.RunAsync("用一句话介绍 Microsoft Agent Framework")).Text);
Console.WriteLine((await agent.RunAsync("请介绍暴力行为的心理学成因")).Text);

// ---- 课堂练习 ----
// 1. 增加"函数调用中间件"：拦截敏感工具（如删除文件），未授权时直接拒绝
// 2. 用 OpenTelemetry SDK + Console Exporter 把 span 真正导出
// 3. 把 TelemetryClient 的统计汇总到请求结束后输出（累计延迟/token）

/// <summary>追踪中间件：为每次模型调用产出 Activity（OTel Span）</summary>
sealed class TracingClient(IChatClient inner, string sourceName = "MAF.Lab17") : DelegatingChatClient(inner)
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

/// <summary>遥测中间件：延迟 + token 用量日志</summary>
sealed class TelemetryClient(IChatClient inner) : DelegatingChatClient(inner)
{
    public override async Task<ChatResponse> GetResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null, CancellationToken ct = default)
    {
        var sw = Stopwatch.StartNew();
        var resp = await base.GetResponseAsync(messages, options, ct);
        sw.Stop();
        Console.WriteLine($"[遥测] 延迟={sw.ElapsedMilliseconds}ms  tokens: in={resp.Usage?.InputTokenCount} out={resp.Usage?.OutputTokenCount}");
        return resp;
    }
}

/// <summary>合规中间件：命中敏感词则拦截替换</summary>
sealed class ComplianceClient(IChatClient inner) : DelegatingChatClient(inner)
{
    private static readonly string[] Banned = ["暴力"];

    public override async Task<ChatResponse> GetResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null, CancellationToken ct = default)
    {
        var resp = await base.GetResponseAsync(messages, options, ct);
        if (Banned.Any(resp.Text.Contains))
            return new ChatResponse(new ChatMessage(ChatRole.Assistant, "【合规拦截】回复包含受限内容，已屏蔽。"));
        return resp;
    }
}
