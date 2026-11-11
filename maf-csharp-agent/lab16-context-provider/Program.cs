// Lab 16：上下文提供者（Context Providers）—— 每次调用前自动注入知识库检索结果（RAG）
//
// MAF 的官方能力是 AIContextProvider（在 Agent 调用模型前注入上下文）；
// 本 lab 用 IChatClient 装饰器实现同等效果，便于理解其原理。
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

// 极简"知识库"
var kb = new (string Keyword, string Doc)[]
{
    ("报销", "《差旅制度》：月度差旅报销上限 5000 元，审核需 3 个工作日。"),
    ("请假", "《考勤制度》：年假 10 天，需提前 2 天在 OA 申请。"),
    ("打印机", "《办公指南》：3 楼茶水间有 2 台共享打印机，工号登录使用。"),
};

var (client, _) = AgentFactory.CreateDefault();

// 装饰器包装：调用前检索知识库并注入系统上下文
IChatClient rag = new RagContextClient(client, kb);

AIAgent agent = new ChatClientAgent(rag, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是企业助手。回答时引用知识来源（【知识库检索结果】中的制度名）。" },
});

Console.WriteLine((await agent.RunAsync("公司差旅报销上限是多少？多久到账？")).Text);
Console.WriteLine();
Console.WriteLine((await agent.RunAsync("年假有几天？怎么申请？")).Text);

// ---- 课堂练习 ----
// 1. 把"关键词匹配"换成向量检索（嵌入模型 + 余弦相似度）
// 2. 对比：手动拼接上下文（Lab 5 的 Observation）与 Provider 自动注入的差异

/// <summary>上下文提供者装饰器：请求前自动注入 RAG 检索结果</summary>
sealed class RagContextClient(IChatClient inner, (string Keyword, string Doc)[] kb) : DelegatingChatClient(inner)
{
    public override Task<ChatResponse> GetResponseAsync(
        IEnumerable<ChatMessage> messages, ChatOptions? options = null, CancellationToken ct = default)
    {
        var last = messages.LastOrDefault(m => m.Role == ChatRole.User)?.Text ?? "";
        var hits = kb.Where(d => last.Contains(d.Keyword)).Select(d => d.Doc).ToList();

        if (hits.Count > 0)
        {
            var injected = "【知识库检索结果】\n" + string.Join("\n", hits);
            messages = messages.Append(new ChatMessage(ChatRole.System, injected));
        }
        return base.GetResponseAsync(messages, options, ct);
    }
}
