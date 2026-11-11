// Lab 0：环境准备 —— 验证 .NET 10 SDK、NuGet 包与 OpenAI 兼容服务连通性
//
// 运行：在本目录执行 dotnet run（config.json 已随项目就位）
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, cfg) = AgentFactory.CreateDefault();
Console.WriteLine($"base_url = {cfg.BaseUrl}");
Console.WriteLine($"model    = {cfg.Model}");

// 最原始的 IChatClient 调用（不经过 Agent 抽象）
var response = await client.GetResponseAsync("你好，请用一句话自我介绍。");
Console.WriteLine($"回复: {response.Text}");

// ---- 课堂练习 ----
// 1. 改 config.json 的 model / base_url，验证"换服务不改代码"
// 2. 观察 temperature 0.0 与 1.0 的差异（改 AgentConfig 的 Temperature 传入 ChatOptions）
