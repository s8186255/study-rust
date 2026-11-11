// Lab 19：Foundry Agent Service 集成（生产部署）
//
// 服务端能力：聊天历史由服务端托管、内置安全护栏、Azure 身份认证（Entra ID）。
// 需要环境变量（未配置时打印迁移指引并退出）：
//   FOUNDRY_ENDPOINT   = https://<resource>.openai.azure.com/  （Azure OpenAI 终结点）
//   FOUNDRY_DEPLOYMENT = 部署名
using Azure.AI.OpenAI;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;

var endpoint = Environment.GetEnvironmentVariable("FOUNDRY_ENDPOINT");
var deployment = Environment.GetEnvironmentVariable("FOUNDRY_DEPLOYMENT");

if (string.IsNullOrWhiteSpace(endpoint) || string.IsNullOrWhiteSpace(deployment))
{
    Console.WriteLine("未配置 FOUNDRY_ENDPOINT / FOUNDRY_DEPLOYMENT，跳过云端调用。\n");
    Console.WriteLine("迁移指引（从前序 lab 迁到 Foundry）：");
    Console.WriteLine("  1) IChatClient 换为 Azure OpenAI + Entra ID：");
    Console.WriteLine("     var aoai = new AzureOpenAIClient(new Uri(endpoint), new DefaultAzureCredential());");
    Console.WriteLine("     IChatClient chat = aoai.GetChatClient(deployment).AsIChatClient();");
    Console.WriteLine("  2) ChatClientAgent 及业务代码不变 —— 统一抽象的价值");
    Console.WriteLine("  3) 会话历史由服务端托管延续（对比 Lab 3 / Lab 15 的自管历史）");
    return;
}

// 生产接入：Azure 身份认证（DefaultAzureCredential 支持 az login / Managed Identity / env）
AzureOpenAIClient aoaiClient = new(new Uri(endpoint), new DefaultAzureCredential());
IChatClient chat = aoaiClient.GetChatClient(deployment).AsIChatClient();

var agent = new ChatClientAgent(chat, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是生产环境 Agent，回答简短。" },
});

Console.WriteLine((await agent.RunAsync("用一句话验证连通性")).Text);

// ---- 课堂练习 ----
// 1. az login 后配置两个环境变量运行本 lab，验证服务端历史自动延续（多轮）
// 2. 对比本地 OpenAI 兼容 client 与 Foundry 的认证、计费、护栏差异
