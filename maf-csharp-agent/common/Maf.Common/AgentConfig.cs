using System.Text.Json;

namespace Maf.Common;

/// <summary>
/// 对齐 study-agent 的 config.json 机制：
///   base_url  : OpenAI 兼容服务地址（须带 /v1）
///   api_key   : 可空（留空 = 服务端未启用鉴权，用占位值）
///   model     : 模型 Id
///   temperature: 可选，默认 0.7
/// 改配置文件即可切换模型服务，代码不动。
/// </summary>
public sealed class AgentConfig
{
    public string BaseUrl { get; set; } = "";
    public string? ApiKey { get; set; }
    public string Model { get; set; } = "";
    public float Temperature { get; set; } = 0.7f;

    public string EffectiveKey => string.IsNullOrWhiteSpace(ApiKey) ? "not-needed" : ApiKey!;

    /// <summary>从运行目录（lab 目录）读取 config.json。</summary>
    public static AgentConfig Load()
    {
        string[] candidates =
        [
            Path.Combine(Directory.GetCurrentDirectory(), "config.json"),
            Path.Combine(AppContext.BaseDirectory, "config.json"),
        ];

        foreach (var path in candidates)
        {
            if (!File.Exists(path)) continue;
            var cfg = JsonSerializer.Deserialize<AgentConfig>(
                File.ReadAllText(path),
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true, ReadCommentHandling = JsonCommentHandling.Skip });
            return cfg ?? throw new InvalidDataException($"config.json 解析失败: {path}");
        }

        throw new FileNotFoundException("未找到 config.json（请在 lab 目录下运行 dotnet run）");
    }
}
