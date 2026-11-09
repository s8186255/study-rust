//! Lab2：自定义工具 + 交互式流式输出（课程模块 D1-M4）
//!
//! 目标：
//! 1. 用 `#[rig_tool]` 宏把普通 async fn 变成模型可调用的工具
//! 2. 观察多轮工具调用循环：模型声明调用 -> 你的代码执行 -> 结果回灌 -> 循环
//! 3. 体会 description 与错误信息对模型行为的影响
//!
//! 参考 lab1-hello-agent-daemon-typer 改造：
//!   - 连接信息在 config.json（base_url / api_key / model / temperature / system）
//!   - daemon 方式：REPL 循环，输入任务 → 流式输出回答
//!   - 真·流式：token 到达即打印；工具调用/结果事件也实时打印，全程可见
//!
//! 工作目录说明：启动时自动 chdir 到本 lab 目录，工具里的相对路径 `data`
//! 无论从 workspace 根还是本目录执行都能找到。
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use futures::StreamExt;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::providers::openai;
use rig::rig_tool;
use rig::streaming::{Item, StreamEvent};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use std::path::Path;

/// 工具错误：必须是模型能读懂、能自我纠正的信息，不要 panic。
#[derive(Debug)]
enum ToolError {
    Io(std::io::Error),
}

impl std::fmt::Display for ToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ToolError::Io(e) => write!(f, "io error: {e}"),
        }
    }
}

impl std::error::Error for ToolError {}

impl From<std::io::Error> for ToolError {
    fn from(e: std::io::Error) -> Self {
        ToolError::Io(e)
    }
}

/// 统计一个文本文件的单词数。
/// 注意：doc 注释/描述要写「做什么 + 什么时候选它」，这是模型选工具的唯一依据。
#[rig_tool]
async fn word_count(path: String) -> Result<usize, ToolError> {
    let text = std::fs::read_to_string(&path)?;
    Ok(text.split_whitespace().count())
}

/// 列出目录下所有 .md 文件的相对路径。
#[rig_tool]
async fn list_md_files(dir: String) -> Result<Vec<String>, ToolError> {
    let mut out = Vec::new();
    for entry in std::fs::read_dir(&dir)? {
        let entry = entry?;
        let path = entry.path();
        if path.extension().is_some_and(|e| e == "md") {
            out.push(path.to_string_lossy().into_owned());
        }
    }
    Ok(out)
}

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
    "你是文件统计助手。只依据工具返回的事实回答，不要臆造数字。".to_string()
}

impl AgentConfig {
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

    // 工具用相对路径 `data`，统一切到本 lab 目录再干活
    std::env::set_current_dir(env!("CARGO_MANIFEST_DIR"))?;

    println!("====================================================");
    println!(" Lab2 工具调用 · 交互式流式 Agent");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" system   = {}", cfg.system);
    println!(" 工作目录 = {}", env!("CARGO_MANIFEST_DIR"));
    println!(" 试试输入：统计 data 目录下每个 .md 文件的字数，并给出总字数。");
    println!(" 输入 exit / quit / q / 退出 结束");
    println!("====================================================");

    // OpenAI 兼容 client（等价于 POST {{baseUrl}}/v1/chat/completions）
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let model = config.client().chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .name("file-stats")
        .preamble(cfg.system.clone())
        // #[rig_tool] 会生成类型 WordCount / ListMdFiles 与大写静态量；
        // 静态量不能 move，直接用类型构造（或 .tool(WordCount::default())）
        .tool(WordCount)
        .tool(ListMdFiles)
        .temperature(cfg.temperature)
        .default_max_turns(8) // 防失控循环；注意不是 max_turns()
        .build();

    let stdin = io::stdin();
    let mut turns = 0usize;

    loop {
        // 提示符 → 读一行任务
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

        // 真·流式：token 到达即打印；工具调用/结果事件实时可见
        print!("assistant> ");
        io::stdout().flush()?;
        let mut at_newline = false; // 当前行是否已有输出内容

        let mut stream = agent.prompt(input).stream();
        while let Some(item) = stream.next().await {
            match item? {
                // 文本增量：到达即打印（打字机效果来自 LLM 本身的生成节奏）
                MultiTurnStreamItem::StreamAssistantItem(event) => {
                    if let Item::Event(StreamEvent::Text { text, .. }) = event {
                        print!("{text}");
                        let _ = io::stdout().flush();
                        at_newline = !text.ends_with('\n');
                    }
                }
                // 模型发起工具调用：换行打印调用详情
                MultiTurnStreamItem::ToolCall { tool_call } => {
                    if !at_newline {
                        println!();
                    }
                    println!(
                        "[tool] → {}({:?})",
                        tool_call.function.name, tool_call.function.arguments
                    );
                    at_newline = true;
                }
                // 工具执行完毕、结果已回灌模型：打印摘要（Debug 可能较长，截断）
                MultiTurnStreamItem::ToolResult { tool_result } => {
                    let dbg = format!("{tool_result:?}");
                    let head: String = dbg.chars().take(160).collect();
                    println!("[tool] ← {head}{}", if dbg.chars().count() > 160 { " …" } else { "" });
                    at_newline = true;
                }
                // enum 标了 #[non_exhaustive]，必须留通配臂
                MultiTurnStreamItem::FinalResponse(_) => {}
                _ => {}
            }
        }
        println!("\n");
        turns += 1;
    }

    println!("共完成 {turns} 轮任务，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 传一个不存在的路径给 word_count，观察 [tool] ← 里的错误信息与模型重试
// 2. 把 word_count 的实现包进 blocking(..)，思考为什么阻塞 IO 不能直接放 async fn
// 3. 进阶：手写 impl Tool 版本的 word_count（参考讲义 5.3 第二种写法）
