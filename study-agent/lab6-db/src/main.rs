//! Lab-db：SQLite 数据分析 · 交互式流式版（课程模块 D2-M9）
//!
//! 核心思想：**模型不直接连数据库**——它只生成 SQL，执行永远在你的工具里。
//! 两个只读工具构成"看结构 → 查数据 → 分析"闭环：
//!   1. db_schema：列出所有表的建表语句（模型写 SQL 的依据）
//!   2. query_sql：执行一条 SELECT，结果以 JSON 行数组返回（上限 50 行）
//!
//! 安全设计（教学重点）：
//!   - 以 SQLITE_OPEN_READ_ONLY 打开，即使 SQL 被注入也无法写库
//!   - 拒绝多语句（含分号）与非 SELECT/WITH 开头的语句
//!   - rusqlite 是阻塞 IO，放在 spawn_blocking 里，不卡 async 运行时
//!
//! 参考 lab2/lab4 改造：config.json + daemon REPL + 真流式输出 + 工具事件实时打印。
//! 示例库 data/sample.db 由 python 脚本生成（sales 40 行 / employees 7 行）。
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use futures::StreamExt;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::providers::openai;
use rig::rig_tool;
use rig::streaming::{Item, StreamEvent};
use rusqlite::types::ValueRef;
use rusqlite::{Connection, OpenFlags};
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

impl From<rusqlite::Error> for ToolError {
    fn from(e: rusqlite::Error) -> Self {
        // SQL 错误原样透传：SQLite 的报错信息模型能看懂并自行修正
        ToolError::Msg(e.to_string())
    }
}

/// 以只读模式打开示例库
fn open_ro() -> Result<Connection, ToolError> {
    Ok(Connection::open_with_flags(
        "data/sample.db",
        OpenFlags::SQLITE_OPEN_READ_ONLY,
    )?)
}

/// 列出数据库中所有用户表的建表语句。
/// 写 SQL 前先调用本工具，了解有哪些表和字段。
#[rig_tool]
async fn db_schema() -> Result<String, ToolError> {
    tokio::task::spawn_blocking(|| -> Result<String, ToolError> {
        let conn = open_ro()?;
        let mut stmt = conn.prepare(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        )?;
        let mut out = Vec::new();
        let mut rows = stmt.query([])?;
        while let Some(row) = rows.next()? {
            let name: String = row.get(0)?;
            let sql: String = row.get(1)?;
            out.push(format!("{name}: {sql}"));
        }
        Ok(out.join("\n\n"))
    })
    .await
    .map_err(|e| ToolError::Msg(e.to_string()))?
}

/// 校验并执行一条只读 SELECT，返回 JSON 行数组（最多 50 行）。
/// 一次只允许一条语句，不要写分号；表结构未知时先调用 db_schema。
#[rig_tool]
async fn query_sql(sql: String) -> Result<Vec<serde_json::Value>, ToolError> {
    tokio::task::spawn_blocking(move || -> Result<Vec<serde_json::Value>, ToolError> {
        let s = sql.trim();
        let lower = s.to_lowercase();
        if s.contains(';') {
            return Err(ToolError::Msg(
                "拒绝执行：一次只能一条语句，SQL 里不要包含分号".into(),
            ));
        }
        if !(lower.starts_with("select") || lower.starts_with("with")) {
            return Err(ToolError::Msg(
                "拒绝执行：只允许 SELECT / WITH 查询，本工具不能修改数据".into(),
            ));
        }

        let conn = open_ro()?;
        let mut stmt = conn.prepare(s)?;
        let cols: Vec<String> =
            stmt.column_names().iter().map(|c| c.to_string()).collect();
        let mut rows = stmt.query([])?;

        let mut out = Vec::new();
        while let Some(row) = rows.next()? {
            if out.len() >= 50 {
                out.push(serde_json::json!({"note": "结果超过 50 行，已截断；请缩小查询范围"}));
                break;
            }
            let mut obj = serde_json::Map::new();
            for (i, col) in cols.iter().enumerate() {
                let v = match row.get_ref(i)? {
                    ValueRef::Null => serde_json::Value::Null,
                    ValueRef::Integer(n) => serde_json::json!(n),
                    ValueRef::Real(f) => serde_json::json!(f),
                    ValueRef::Text(t) => serde_json::json!(String::from_utf8_lossy(t)),
                    ValueRef::Blob(b) => serde_json::json!(format!("<blob {} bytes>", b.len())),
                };
                obj.insert(col.clone(), v);
            }
            out.push(serde_json::Value::Object(obj));
        }
        Ok(out)
    })
    .await
    .map_err(|e| ToolError::Msg(e.to_string()))?
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
    "你是数据分析助手。先用 db_schema 查看表结构，再用 query_sql 执行 SELECT 查询做分析；只依据查询结果回答，不要编造数字。SQL 里不要用分号。".to_string()
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

    // `data/sample.db` 是相对路径，统一切到本 lab 目录
    std::env::set_current_dir(env!("CARGO_MANIFEST_DIR"))?;

    println!("====================================================");
    println!(" Lab-db SQLite 数据分析 · 交互式流式 Agent");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" 数据库   = data/sample.db（只读）");
    println!(" system   = {}", cfg.system);
    println!(" 试试输入：每个地区的总销售额是多少？哪个产品卖得最好？");
    println!(" 输入 exit / quit / q / 退出 结束");
    println!("====================================================");

    // OpenAI 兼容 client（等价于 POST {{baseUrl}}/v1/chat/completions）
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let model = config.client().chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .name("db-analyst")
        .preamble(cfg.system.clone())
        // #[rig_tool] 生成类型 DbSchema / QuerySql
        .tool(DbSchema)
        .tool(QuerySql)
        .temperature(cfg.temperature)
        .default_max_turns(8)
        .build();

    let stdin = io::stdin();
    let mut turns = 0usize;

    loop {
        // 提示符 → 读一个分析问题
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

        // 真·流式：token 到达即打印；SQL 执行过程实时可见
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

    println!("共完成 {turns} 轮分析，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 故意让模型写错误 SQL（如拼错列名），观察 [tool] ← 里的 SQLite 报错与自我修正
// 2. 把 query_sql 的 SELECT 校验去掉，讨论：只靠只读连接够不够安全？
// 3. 进阶：新增工具 top_n(table, column, n)，动态生成参数化查询（防注入的正确姿势）
// 4. 进阶：换 postgres（rusqlite → tokio-postgres），体会"模型不连库，工具连库"的解耦
