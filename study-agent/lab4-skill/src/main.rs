//! Lab4-skill：技能系统 · 交互式流式版（课程模块 D2-M8）
//!
//! 核心思想：**skill = 一个文件夹（SKILL.md 描述 + scripts/ 下的可执行脚本）**。
//! 与 lab2「Rust 工具」对照：
//!   - lab2：能力长在 Rust 二进制里，改能力要重编译
//!   - lab4：能力是外部文件，**新增 skill 只需加文件夹**，主程序零改动
//!   - 模型选型的依据从 doc 注释变成了 SKILL.md 的 description
//!
//! 两个工具构成一个"技能发现 + 调用"闭环：
//!   1. list_skills：扫描 skills/ 下含 SKILL.md 的目录，返回名称与描述
//!   2. run_skill：以子进程方式执行 `python skills/<name>/scripts/main.py <args>`
//!
//! 参考 lab2-tools 改造：config.json 连接配置 + daemon REPL + 真流式输出，
//! 工具调用/结果事件实时打印。
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
    Msg(String),
}

impl std::fmt::Display for ToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ToolError::Io(e) => write!(f, "io error: {e}"),
            ToolError::Msg(m) => write!(f, "{m}"),
        }
    }
}

impl std::error::Error for ToolError {}

impl From<std::io::Error> for ToolError {
    fn from(e: std::io::Error) -> Self {
        ToolError::Io(e)
    }
}

/// 列出所有可用 skill（名称 + 一句话描述）。
/// 需要完成某类任务时，先调用本工具查看有哪些 skill 可选。
#[rig_tool]
async fn list_skills() -> Result<Vec<String>, ToolError> {
    let mut out = Vec::new();
    for entry in std::fs::read_dir("skills")? {
        let path = entry?.path();
        let skill_md = path.join("SKILL.md");
        if !skill_md.is_file() {
            continue;
        }
        let name = path
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default();
        // 从 frontmatter 抽取 description 一行，作为模型选型依据
        let desc = std::fs::read_to_string(&skill_md)?
            .lines()
            .find(|l| l.trim_start().starts_with("description:"))
            .map(|l| {
                l.trim()
                    .trim_start_matches("description:")
                    .trim()
                    .to_string()
            })
            .unwrap_or_default();
        out.push(format!("{name}: {desc}"));
    }
    Ok(out)
}

async fn run_python(
    prog: &str,
    script: &str,
    args: &[String],
) -> std::io::Result<std::process::Output> {
    tokio::process::Command::new(prog)
        .arg(script)
        .args(args)
        .output()
        .await
}

/// 执行指定 skill 的 Python 脚本并返回 stdout。
/// skill 名必须来自 list_skills 的返回；args 是传给脚本的命令行参数
/// （具体用法见该 skill 目录下的 SKILL.md）。
#[rig_tool]
async fn run_skill(skill: String, args: Vec<String>) -> Result<String, ToolError> {
    // 防路径穿越：skill 只能是 skills/ 下的直接子目录名
    if skill.is_empty()
        || skill.contains("..")
        || skill.contains('/')
        || skill.contains('\\')
        || skill.contains(':')
    {
        return Err(ToolError::Msg(format!("非法 skill 名称: {skill}")));
    }
    let script = format!("skills/{skill}/scripts/main.py");
    if !Path::new(&script).is_file() {
        return Err(ToolError::Msg(format!(
            "skill 不存在: {skill}（可先用 list_skills 查看可用技能）"
        )));
    }

    // Windows 上优先 python，未安装再试 py 启动器
    let output = match run_python("python", &script, &args).await {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            run_python("py", &script, &args).await?
        }
        other => other?,
    };

    if !output.status.success() {
        return Err(ToolError::Msg(format!(
            "脚本执行失败({}): {}",
            output.status,
            String::from_utf8_lossy(&output.stderr).trim()
        )));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
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
    "你是技能助手。完成任务前先用 list_skills 查看可用技能，选择合适的 skill 并用 run_skill 执行，依据脚本的真实输出回答；不要臆造结果。".to_string()
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

    // `skills/` 是相对路径，统一切到本 lab 目录
    std::env::set_current_dir(env!("CARGO_MANIFEST_DIR"))?;

    println!("====================================================");
    println!(" Lab4 技能系统 · 交互式流式 Agent");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" system   = {}", cfg.system);
    println!(" 工作目录 = {}", env!("CARGO_MANIFEST_DIR"));
    println!(" 试试输入：统计 README.md 的字数，并给出词频前 5 的词。");
    println!(" 输入 exit / quit / q / 退出 结束");
    println!("====================================================");

    // OpenAI 兼容 client（等价于 POST {{baseUrl}}/v1/chat/completions）
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let model = config.client().chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .name("skill-runner")
        .preamble(cfg.system.clone())
        // #[rig_tool] 生成类型 ListSkills / RunSkill
        .tool(ListSkills)
        .tool(RunSkill)
        .temperature(cfg.temperature)
        .default_max_turns(8)
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
        let mut at_newline = false;

        let mut stream = agent.prompt(input).stream();
        while let Some(item) = stream.next().await {
            match item? {
                MultiTurnStreamItem::StreamAssistantItem(event) => {
                    if let Item::Event(StreamEvent::Text { text, .. }) = event {
                        print!("{text}");
                        let _ = io::stdout().flush();
                        at_newline = !text.ends_with('\n');
                    }
                }
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
                MultiTurnStreamItem::ToolResult { tool_result } => {
                    let dbg = format!("{tool_result:?}");
                    let head: String = dbg.chars().take(160).collect();
                    println!(
                        "[tool] ← {head}{}",
                        if dbg.chars().count() > 160 { " …" } else { "" }
                    );
                    at_newline = true;
                }
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
// 1. 新增一个 skill：复制 word_count 文件夹结构，写一个 char_replace（字符替换）脚本，
//    不改任何 Rust 代码，观察模型自动学会用新技能
// 2. 把 word_count 的 description 写含糊，观察模型是否还选得对
// 3. 给 run_skill 传 `../` 之类的参数，验证路径穿越防护
// 4. 进阶：把 run_skill 改为白名单校验参数，防止脚本被滥用
