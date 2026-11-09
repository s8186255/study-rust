//! Lab1-daemon-typer：真·流式输出的交互式 Agent（课程模块 D1-M2）
//!
//! 在 lab1-hello-agent-daemon 基础上演进：
//! 1. 用 `agent.prompt(..).stream()` 发起流式请求（POST /v1/chat/completions，
//!    "stream": true，SSE），LLM 每生成一段 token 就立刻打印一个——
//!    输出速度完全由模型决定，无需任何人为延时
//! 2. 退出方式：输入 exit / quit / q / 退出，或 Ctrl+Z（回车）/ Ctrl+D（EOF）
//!
//! 与「假打字机」的区别：假打字机等完整回答到手后用 sleep 逐字回放；
//! 真流式是 token 到达即显示，首字延迟 = 服务端首个 token 的生成时间。
//!
//! 对接配置：本 lab 目录下的 `config.json`
//!   - base_url：OpenAI 兼容服务地址（如 InferenceRouter2，须带 /v1）
//!   - api_key：可填可不填（留空或省略 = 服务端未启用鉴权，用占位值）
//!   - model：模型 Id（如 gemma-4-26B-A4B）
//!   - temperature：可选，默认 0.7
//!   - system：系统提示词，可选，默认 "You are a helpful assistant."
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use futures::StreamExt;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::providers::openai::{self, OpenAI};
use rig::streaming::{Item, StreamEvent};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
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
    #[serde(default = "d_system")]
    system: String,
}

fn d_temperature() -> f64 {
    0.7
}
fn d_system() -> String {
    "You are a helpful assistant.".to_string()
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

const EXIT_WORDS: [&str; 4] = ["exit", "quit", "q", "退出"];

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cfg = AgentConfig::load()?;
    println!("====================================================");
    println!(" Lab1-daemon-typer 交互式 Agent（真·流式输出）");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" system   = {}", cfg.system);
    println!(" 输入内容与模型对话；exit / quit / q / 退出 结束");
    println!("====================================================");

    // OpenAI 兼容 client：等价于 api.http 里
    // POST {{baseUrl}}/v1/chat/completions，Authorization: Bearer <key>
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let client: OpenAI = config.client();

    // .chat() 走 Chat Completions 路线
    let model = client.chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .preamble(cfg.system.clone())
        .temperature(cfg.temperature)
        .build();

    let stdin = io::stdin();
    let mut turns = 0usize;

    loop {
        // 提示符 → 读一行用户输入
        print!("you> ");
        io::stdout().flush()?;

        let mut line = String::new();
        if stdin.lock().read_line(&mut line)? == 0 {
            println!(); // EOF（Ctrl+Z 回车 / Ctrl+D）
            break;
        }
        let input = line.trim();
        if input.is_empty() {
            continue;
        }
        if EXIT_WORDS.contains(&input.to_lowercase().as_str()) {
            break;
        }

        // 真·流式：prompt() 返回 AgentRunner，.stream() 得到事件流。
        // 流的 item 依次为：文本/推理增量（StreamAssistantItem）、
        // 工具事件（本例无工具）、最后的 FinalResponse。
        print!("assistant> ");
        io::stdout().flush()?;

        let mut stream = agent.prompt(input).stream();
        while let Some(item) = stream.next().await {
            match item? {
                // 模型吐出的增量内容：只关心文本 delta，到达即打印
                MultiTurnStreamItem::StreamAssistantItem(event) => {
                    if let Item::Event(StreamEvent::Text { text, .. }) = event {
                        print!("{text}");
                        let _ = io::stdout().flush();
                    }
                    // 其余事件（推理片段、部分开始/结束等）本例忽略
                }
                // 本 agent 无工具，也不会出现结构化输出，其余变体一律跳过
                // （enum 标了 #[non_exhaustive]，必须留通配臂）
                MultiTurnStreamItem::FinalResponse(_) => {}
                _ => {}
            }
        }
        println!("\n");
        turns += 1;
    }

    println!("共完成 {turns} 轮对话，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 改 config.json 的 system 为中文人设，观察回答风格变化
// 2. 对比 daemon（等完整回答）与本版：问一个长问题，感受「首字延迟」差异
// 3. 进阶：统计本次回答的 token 数——CompletionCall 事件带 usage
// 4. 进阶：多轮对话——把 FinalResponse 里的消息存入 history 传给下一轮
