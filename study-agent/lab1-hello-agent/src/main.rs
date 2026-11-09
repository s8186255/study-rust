//! Lab1：跑通第一个 Agent（课程模块 D1-M2）
//!
//! 目标：
//! 1. 理解 Agent 三要素：模型 + preamble（系统提示词）+ prompt（本次任务）
//! 2. 理解「换 provider 只换 client」
//!
//! 对接配置：本 lab 目录下的 `config.json`
//!   - base_url：OpenAI 兼容服务地址（如 InferenceRouter2，须带 /v1）
//!   - api_key：可填可不填（留空或省略 = 服务端未启用鉴权，用占位值）
//!   - model：模型 Id（如 gemma-4-26B-A4B）
//!   - temperature：可选，默认 0.7
//! 改配置文件即可切换模型服务，代码不动。
//!
//! system（系统提示词）与 prompt（本次任务）必填，从命令行获取：
//!   cargo run -- --system "You are a helpful assistant." --prompt "求详细介绍python语言"
//!   也可写 --system=xxx / --prompt=xxx；cargo run -- --help 查看用法
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use rig::agent::AgentBuilder;
use rig::providers::openai::{self, OpenAI};
use serde::Deserialize;
use std::path::Path;

/// 对应 config.json；除 base_url / model 外其余字段均可省略
#[derive(Debug, Deserialize)]
struct AgentConfig {
    base_url: String,
    model: String,
    #[serde(default)]
    api_key: Option<String>,
    #[serde(default = "d_temperature")]
    temperature: f64,
}

fn d_temperature() -> f64 {
    0.7
}

impl AgentConfig {
    /// 从本 lab 目录读取 config.json（用 CARGO_MANIFEST_DIR 定位，
    /// 无论 cargo run 在 workspace 根还是本目录执行都能找到）
    fn load() -> anyhow::Result<Self> {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("config.json");
        let text = std::fs::read_to_string(&path)
            .map_err(|e| anyhow::anyhow!("读取配置失败 {}: {e}", path.display()))?;
        Ok(serde_json::from_str(&text)?)
    }

    /// key 可用可不用：留空/省略时返回占位值（Router 未配置 Server.ApiKey 即可）
    fn effective_key(&self) -> &str {
        match self.api_key.as_deref() {
            Some(k) if !k.trim().is_empty() => k,
            _ => "not-needed",
        }
    }
}

/// 命令行必填参数：--system 与 --prompt
#[derive(Debug, Default)]
struct CliArgs {
    system: Option<String>,
    prompt: Option<String>,
}

const USAGE: &str = "用法: lab1-hello-agent --system <系统提示词> --prompt <本次任务>\n\
                     也可写 --system=xxx / --prompt=xxx；两个参数均必填";

fn next_val(args: &mut impl Iterator<Item = String>, flag: &str) -> anyhow::Result<String> {
    args.next().ok_or_else(|| anyhow::anyhow!("{flag} 缺少参数值"))
}

fn parse_args() -> anyhow::Result<CliArgs> {
    let mut out = CliArgs::default();
    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        let Some(rest) = arg.strip_prefix("--") else {
            anyhow::bail!("未知参数 {arg}；{USAGE}");
        };
        // --flag=value 形式
        if let Some((k, v)) = rest.split_once('=') {
            match k {
                "system" => out.system = Some(v.to_string()),
                "prompt" => out.prompt = Some(v.to_string()),
                _ => anyhow::bail!("未知参数 --{k}；{USAGE}"),
            }
            continue;
        }
        // --flag value 形式
        match rest {
            "help" | "h" => {
                println!("{USAGE}");
                std::process::exit(0);
            }
            "system" | "s" => out.system = Some(next_val(&mut args, "--system")?),
            "prompt" | "p" => out.prompt = Some(next_val(&mut args, "--prompt")?),
            _ => anyhow::bail!("未知参数 --{rest}；{USAGE}"),
        }
    }
    // 必填校验
    Ok(CliArgs {
        system: Some(out.system.ok_or_else(|| anyhow::anyhow!("缺少必填参数 --system；{USAGE}"))?),
        prompt: Some(out.prompt.ok_or_else(|| anyhow::anyhow!("缺少必填参数 --prompt；{USAGE}"))?),
    })
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cfg = AgentConfig::load()?;
    let cli = parse_args()?;

    // system / prompt 只从命令行获取（parse_args 已做必填校验）
    let system = cli.system.unwrap_or_default();
    let prompt = cli.prompt.unwrap_or_default();

    println!("配置: base_url={} model={}", cfg.base_url, cfg.model);
    println!("system: {system}");
    println!("prompt: {prompt}");

    // OpenAI 兼容 client：等价于 api.http 里
    // POST {{baseUrl}}/v1/chat/completions，Authorization: Bearer <key>
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let client: OpenAI = config.client();

    // .chat() 走 Chat Completions 路线（POST /v1/chat/completions）
    let model = client.chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .preamble(system)
        .temperature(cfg.temperature)
        .build();

    let response = agent.prompt(prompt).await?;
    println!("{}", response.output());

    // ---- 课堂练习 ----
    // 1. cargo run -- --system "你是一名相声演员" 观察 system 对回答风格的影响
    // 2. 改 config.json 的 temperature 0.0 / 1.0，各跑三次对比
    // 3. 进阶：改 base_url/model 直连 DashScope 等其它 OpenAI 兼容服务，业务代码不动
    Ok(())
}
