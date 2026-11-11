// Lab 6：MCP 工具接入 —— 通过 Model Context Protocol 动态发现外部工具
//
// 前置：本机有 Node.js/npx。此处接入官方 filesystem MCP server，只暴露当前目录。
// 服务端未装时 npx 会自动拉取；离线环境可改用本机已有 MCP server。
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

var transport = new StdioClientTransport(new StdioClientTransportOptions
{
    Command = "npx",
    Arguments = ["-y", "@modelcontextprotocol/server-filesystem", "."],
});

await using var mcp = await McpClient.CreateAsync(transport);
var tools = await mcp.ListToolsAsync();
Console.WriteLine($"发现 MCP 工具 {tools.Count} 个: {string.Join(", ", tools.Select(t => t.Name))}\n");

// MCP 工具（McpClientTool）实现了 AITool，可直接挂到 Agent 上
AIAgent agent = new ChatClientAgent(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions
    {
        Instructions = "你是文件助手，用 MCP 工具完成文件操作，每次操作前先说明要做什么。",
        Tools = [.. tools],
    },
});

Console.WriteLine((await agent.RunAsync("列出当前目录有哪些文件，并新建 hello.txt 写入一行：你好 MAF")).Text);

// 进阶练习：自建一个最简 MCP server（stdio），供本 Agent 调用
