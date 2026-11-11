using System.ClientModel;
using Microsoft.Extensions.AI;
using OpenAI;

namespace Maf.Common;

/// <summary>
/// 统一的模型接入工厂：OpenAI 兼容服务 → IChatClient。
/// MAF 的 ChatClientAgent 只依赖 IChatClient，换 provider 只换这一处。
/// </summary>
public static class AgentFactory
{
    public static IChatClient CreateChatClient(AgentConfig cfg)
    {
        var openai = new OpenAIClient(
            new ApiKeyCredential(cfg.EffectiveKey),
            new OpenAIClientOptions { Endpoint = new Uri(cfg.BaseUrl) });

        // GET/POST {base_url}/chat/completions（base_url 已含 /v1）
        return openai.GetChatClient(cfg.Model).AsIChatClient();
    }

    public static (IChatClient Client, AgentConfig Config) CreateDefault()
    {
        var cfg = AgentConfig.Load();
        return (CreateChatClient(cfg), cfg);
    }
}
