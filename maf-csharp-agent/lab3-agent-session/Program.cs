// Lab 3：会话（AgentSession）—— 实现多轮对话
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();
AIAgent agent = new ChatClientAgent(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是有记性的助手，回答简洁。" },
});

// 带 AgentSession：同一会话内跨调用记忆（MAF 1.28 用 CreateSessionAsync 创建会话）
AgentSession session = await agent.CreateSessionAsync();
await agent.RunAsync("我叫 Alice，最喜欢的数字是 42。", session);
Console.WriteLine($"[带会话] {(await agent.RunAsync("我叫什么名字？最喜欢的数字是多少？", session)).Text}");

// 无状态对比：不传 session，两次调用互不相关
Console.WriteLine($"[无会话] {(await agent.RunAsync("我叫什么名字？")).Text}");

// ---- 课堂讨论 ----
// 服务端历史（Session 由 provider 托管）与本地历史（自管 ChatMessage 列表）的差异：
// 存储位置、续接方式、成本与隐私；结合课程笔记 Lab 3 小节
