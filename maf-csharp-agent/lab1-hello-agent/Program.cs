// Lab 1：第一个 Agent —— AIAgent 统一抽象 + 流式输出 + 多模态输入
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, cfg) = AgentFactory.CreateDefault();
Console.WriteLine($"provider: {cfg.BaseUrl}  model: {cfg.Model}\n");

// 统一抽象：无论底层是 OpenAI 兼容服务 / Azure OpenAI / Foundry，对外都是同一个 ChatClientAgent
// 指令放在 ChatOptions.Instructions；Name/Description 放在 ChatClientAgentOptions
AIAgent agent = new ChatClientAgent(client, new ChatClientAgentOptions
{
    Name = "Joker",
    ChatOptions = new ChatOptions
    {
        Instructions = "你是一名冷笑话演员，回答简短且有梗。",
        Temperature = cfg.Temperature,
    },
});

// 1. 一次性调用：一行 RunAsync 拿到回复
var response = await agent.RunAsync("讲一个关于程序员的笑话");
Console.WriteLine($"[RunAsync] {response.Text}\n");

// 2. 流式输出（打字机效果）
Console.Write("[流式] ");
await foreach (var update in agent.RunStreamingAsync("再讲一个更短的"))
    Console.Write(update.Text);
Console.WriteLine("\n");

// 3. 多模态输入：文本 + 图片 URI 的富内容 ChatMessage
//    （需要服务端模型支持 vision；不支持时会走 catch，可跳过）
try
{
    ChatMessage message = new(ChatRole.User, new AIContent[]
    {
        new TextContent("用一句话描述这张图片，并讲一个相关笑话"),
        new UriContent(new Uri("https://upload.wikimedia.org/wikipedia/commons/3/3f/Cat03.jpg"), "image/jpeg"),
    });
    Console.WriteLine($"[多模态] {(await agent.RunAsync(message)).Text}");
}
catch (Exception ex)
{
    Console.WriteLine($"[多模态] 服务端不支持或调用失败：{ex.Message}");
}

// ---- 课堂练习 ----
// 1. 修改 Instructions 观察风格变化
// 2. 换 config.json 的 model，业务代码不变（统一抽象的意义）
