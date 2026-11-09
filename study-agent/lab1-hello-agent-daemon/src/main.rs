//! Lab1-daemon：交互式 Agent（课程模块 D1-M2）
//!
//! 在 lab1-hello-agent 基础上演进：
//! 1. system（系统提示词）放进 config.json，改配置即改人设，不用重编译
//! 2. 运行后进入交互循环：用户输入 → LLM 回答 → 继续输入（终端 TUI / REPL）
//! 3. 退出方式：输入 exit / quit / q / 退出，或 Ctrl+Z（回车）/ Ctrl+D（EOF）
//!
//! 对接配置：本 lab 目录下的 `config.json`
//!   - base_url：OpenAI 兼容服务地址（如 InferenceRouter2，须带 /v1）
//!   - api_key：可填可不填（留空或省略 = 服务端未启用鉴权，用占位值）
//!   - model：模型 Id（如 gemma-4-26B-A4B）
//!   - temperature：可选，默认 0.7
//!   - system：系统提示词，可选，默认 "You are a helpful assistant."
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use rig::agent::AgentBuilder;
use rig::providers::openai::{self, OpenAI};
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
    println!("========================================");
    println!(" Lab1-daemon 交互式 Agent");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" system   = {}", cfg.system);
    println!(" 输入内容与模型对话；exit / quit / q / 退出 结束");
    println!("========================================");

    // OpenAI 兼容 client：等价于 api.http 里
    // POST {{baseUrl}}/v1/chat/completions，Authorization: Bearer <key>
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let client: OpenAI = config.client();

    // .chat() 走 Chat Completions 路线（POST /v1/chat/completions）
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

        // 调 LLM 并回显；等待期间用 spinner 动画显示「正在获取信息」
        print!("assistant> ");
        io::stdout().flush()?;

        // tokio::select! 同时竞争两个 future：
        //   - agent.prompt(input)：真正的 LLM 请求
        //   - spinner：每 120ms 刷新一次动画帧，永远不会自己完成
        // 请求先完成 → 返回响应，spinner 被自动丢弃（取消）。
        // ASCII 帧 + \r 回到行首，兼容各类 Windows 终端。
        const FRAMES: [char; 4] = ['|', '/', '-', '\\'];
        let spinner = async {
            let mut i = 0usize;
            loop {
                print!("\rassistant {} 正在获取信息...", FRAMES[i % FRAMES.len()]);
                let _ = io::stdout().flush();
                i += 1;
                tokio::time::sleep(std::time::Duration::from_millis(120)).await;
            }
        };
        let result = tokio::select! {
            r = agent.prompt(input) => r,
            _ = spinner => unreachable!("spinner 永不完成"),
        };

        // \r 回到行首，\x1b[K 清除整行（Windows Terminal / VS Code 终端均支持）
        print!("\r\x1b[K");
        io::stdout().flush()?;
        match result {
            Ok(resp) => {
                println!("{}\n", resp.output());
                turns += 1;
            }
            Err(e) => println!("[错误] {e}\n（服务是否在线？检查 config.json 的 base_url/model）\n"),
        }
    }

    println!("共完成 {turns} 轮对话，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 改 config.json 的 system 为中文人设（如相声演员），观察回答风格变化
// 2. 改 temperature 0.0 / 1.0，同一问题各问三次对比
// 3. 进阶：多轮对话——目前每轮独立（无记忆）；用 rig 的 chat history
//    把上一轮回答存入 Vec，再传给下一轮，实现上下文记忆
