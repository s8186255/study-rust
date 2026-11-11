// Lab 15：记忆（Memory / 长期记忆）—— AgentSession 序列化持久化，跨"进程"记住对话
// 这是"本地历史"路线；Provider 托管记忆（如 Mem0）见课程笔记 Lab 15 小节
using System.Text.Json;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();
ChatClientAgent agent = new(client, new ChatClientAgentOptions
{
    ChatOptions = new ChatOptions { Instructions = "你是长期助理。" },
});

var sessionFile = "session.json";
AgentSession session;

if (File.Exists(sessionFile))
{
    // 第二次运行：从磁盘恢复会话状态（MAF 提供会话级序列化 API）
    var element = JsonDocument.Parse(File.ReadAllText(sessionFile)).RootElement;
    session = await agent.DeserializeSessionAsync(element, new JsonSerializerOptions());
    Console.WriteLine("[已从 session.json 恢复历史会话]");
}
else
{
    session = await agent.CreateSessionAsync();
}

// 第一次运行时写下偏好；第二次运行应"记得"偏好
await agent.RunAsync("我的偏好：回答尽量简洁，不用表情符号。", session);
Console.WriteLine((await agent.RunAsync("我的偏好是什么？", session)).Text);

var snapshot = await agent.SerializeSessionAsync(session, new JsonSerializerOptions());
File.WriteAllText(sessionFile, JsonSerializer.Serialize(snapshot));
Console.WriteLine($"\n[会话已保存到 {sessionFile}] —— 重新运行 dotnet run 验证跨会话记忆");

// 删除 session.json 即可重置
