//! Lab5-websearch：联网搜索与网页获取 · 交互式流式版（课程模块 D2-M10）
//!
//! 三个工具构成"搜索 → 打开 → 追踪"闭环：
//!   1. web_search(query)：Bing 搜索（国内可达，无需 API Key），返回标题+链接+摘要
//!   2. fetch_url(url)：抓取网页，剥掉 script/style/标签，返回正文文本（上限 4000 字）
//!   3. extract_links(url)：列出页面上的链接（标题 + URL），供模型继续追踪
//!
//! 教学要点：
//!   - 模型"会上网"的本质：抓 HTML → 正则清洗 → 喂文本；它自己看不了网页
//!   - SSRF 防护：拒绝 localhost / 内网地址（工具是你能执行任意 HTTP 的手臂）
//!   - 抓取结果必须截断：网页正文动辄几十 KB，直接灌给模型会爆上下文
//!
//! 注意：需要能访问外网；搜索用 Bing（https://www.bing.com）。
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use futures::StreamExt;
use regex::Regex;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::providers::openai;
use rig::rig_tool;
use rig::streaming::{Item, StreamEvent};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use std::path::Path;
use std::time::Duration;

/// 工具错误：必须是模型能读懂、能自我纠正的信息，不要 panic。
#[derive(Debug)]
enum ToolError {
    Net(String),
    Msg(String),
}

impl std::fmt::Display for ToolError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ToolError::Net(e) => write!(f, "网络错误: {e}"),
            ToolError::Msg(m) => write!(f, "{m}"),
        }
    }
}

impl std::error::Error for ToolError {}

impl From<reqwest::Error> for ToolError {
    fn from(e: reqwest::Error) -> Self {
        ToolError::Net(e.to_string())
    }
}

/// 抓取结果上限：防止长文撑爆模型上下文
const MAX_CHARS: usize = 4000;

/// 构建共享 HTTP 客户端：超时 + 浏览器 UA（不少站点会拒绝无 UA 的请求）
fn http() -> Result<reqwest::Client, ToolError> {
    Ok(reqwest::Client::builder()
        .timeout(Duration::from_secs(15))
        .user_agent("Mozilla/5.0 (lab5-websearch-agent/0.1)")
        .build()?)
}

/// SSRF 防护：只允许公网 http(s) 地址
fn check_url(url: &str) -> Result<(), ToolError> {
    let u = url.to_lowercase();
    let ok = u.starts_with("http://") || u.starts_with("https://");
    if !ok {
        return Err(ToolError::Msg(format!(
            "拒绝访问：只支持 http/https（收到 {url}）"
        )));
    }
    let blocked = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "169.254."];
    if blocked.iter().any(|b| u.contains(b)) {
        return Err(ToolError::Msg(
            "拒绝访问：不允许访问本机或内网地址（SSRF 防护）".into(),
        ));
    }
    Ok(())
}

/// 剥掉 HTML，得到可读正文文本
fn html_to_text(html: &str) -> String {
    let strip = |re: &Regex, s: &str| re.replace_all(s, "").into_owned();
    let html = strip(&Regex::new(r"(?is)<script[^>]*>.*?</script>").unwrap(), html);
    let html = strip(&Regex::new(r"(?is)<style[^>]*>.*?</style>").unwrap(), &html);
    let html = strip(&Regex::new(r"(?s)<!--.*?-->").unwrap(), &html);
    let text = strip(&Regex::new(r"<[^>]+>").unwrap(), &html);
    // 常见 HTML 实体还原
    let text = text.replace("&nbsp;", " ").replace("&amp;", "&");
    let text = text.replace("&lt;", "<").replace("&gt;", ">");
    let text = text.replace("&quot;", "\"").replace("&#39;", "'");
    // 连续空白压成单个空格，空行去重
    let ws = Regex::new(r"[ \t\r\f]+").unwrap();
    let mut out = String::new();
    for line in ws.replace_all(&text, " ").trim().lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        out.push_str(line);
        out.push('\n');
    }
    out
}

fn decode(s: &str) -> String {
    s.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
}

/// 联网搜索。输入搜索关键词，返回 Bing 结果列表（标题 + URL + 摘要）。
/// 回答时效性/事实性问题前，先用本工具搜索。
#[rig_tool]
async fn web_search(query: String) -> Result<String, ToolError> {
    let html = http()?
        .get("https://www.bing.com/search")
        .query(&[("q", query.as_str()), ("mkt", "zh-CN")])
        .send()
        .await?
        .text()
        .await?;

    // 解析 Bing 结果块：<li class="b_algo"><h2><a href=...>标题</a></h2> ... <p>摘要</p>
    let item = Regex::new(r#"(?is)<li class="b_algo".*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>"#).unwrap();
    let tag = Regex::new(r"<[^>]+>").unwrap();

    let mut out = String::new();
    for (i, cap) in item.captures_iter(&html).take(8).enumerate() {
        let url = decode(&cap[1]);
        let title = decode(&tag.replace_all(&cap[2], "").to_string());
        let snippet = decode(&tag.replace_all(&cap[3], "").to_string());
        out.push_str(&format!(
            "{}. {}\n   {}\n   {}\n",
            i + 1,
            title.trim(),
            url.trim(),
            snippet.trim()
        ));
    }
    if out.is_empty() {
        out = "未解析到搜索结果（页面结构可能变化，可改用 fetch_url 抓取搜索引擎页面）".into();
    }
    Ok(out)
}

/// 抓取网页正文。输入 http/https 开头的公网 URL，返回清洗后的文本
/// （最多 4000 字符，超出部分截断并注明）。
#[rig_tool]
async fn fetch_url(url: String) -> Result<String, ToolError> {
    check_url(&url)?;
    let resp = http()?.get(&url).send().await?;
    let status = resp.status();
    if !status.is_success() {
        return Err(ToolError::Msg(format!(
            "抓取失败：HTTP {status}（URL 是否有效？可换 fetch_url 试试别的地址）"
        )));
    }
    let ctype = resp
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_lowercase();
    let body = resp.text().await?;
    if ctype.contains("json") {
        return Ok(format!("JSON 响应（{} 字节）:\n{}", body.len(), &body[..body.len().min(MAX_CHARS)]));
    }
    if !ctype.contains("html") && !ctype.contains("text") {
        return Err(ToolError::Msg(format!(
            "不支持的内容类型: {ctype}（只支持网页/文本）"
        )));
    }

    let mut text = html_to_text(&body);
    if text.chars().count() > MAX_CHARS {
        text = text.chars().take(MAX_CHARS).collect();
        text.push_str("\n…（正文过长已截断，可用 extract_links 找子页面继续追）");
    }
    Ok(format!("来源: {url}\n\n{text}"))
}

/// 列出网页上的所有链接（标题 + URL），用于追踪子页面。
#[rig_tool]
async fn extract_links(url: String) -> Result<String, ToolError> {
    check_url(&url)?;
    let html = http()?.get(&url).send().await?.text().await?;
    let link = Regex::new(r#"(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>"#).unwrap();
    let tag = Regex::new(r"<[^>]+>").unwrap();

    let mut out = Vec::new();
    for cap in link.captures_iter(&html).take(50) {
        let href = decode(&cap[1]);
        let text = decode(&tag.replace_all(&cap[2], "").to_string());
        let text = text.trim().to_string();
        if href.starts_with("javascript:") || href.starts_with('#') {
            continue;
        }
        out.push(format!("- [{}] {}", if text.is_empty() { "(无标题)" } else { &text }, href));
    }
    if out.is_empty() {
        return Ok("页面上没有解析到链接".into());
    }
    Ok(out.join("\n"))
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
    "你是联网助手。回答时效性问题前，先用 web_search 搜索，再用 fetch_url 打开最相关的页面核实；只依据抓到的内容回答，并注明信息来源 URL。".to_string()
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

    println!("====================================================");
    println!(" Lab5 联网搜索与网页获取 · 交互式流式 Agent");
    println!(" base_url = {}", cfg.base_url);
    println!(" model    = {}", cfg.model);
    println!(" 工具     = web_search / fetch_url / extract_links");
    println!(" 试试输入：搜一下 rig 是什么，并打开它的官方仓库看看。");
    println!(" 输入 exit / quit / q / 退出 结束");
    println!("====================================================");

    // OpenAI 兼容 client（等价于 POST {{baseUrl}}/v1/chat/completions）
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let model = config.client().chat(&cfg.model);

    let agent = AgentBuilder::new(model)
        .name("web-agent")
        .preamble(cfg.system.clone())
        // #[rig_tool] 生成类型 WebSearch / FetchUrl / ExtractLinks
        .tool(WebSearch)
        .tool(FetchUrl)
        .tool(ExtractLinks)
        .temperature(cfg.temperature)
        .default_max_turns(10) // 联网任务步数可能更多，放宽一点
        .build();

    let stdin = io::stdin();
    let mut turns = 0usize;

    loop {
        // 提示符 → 读一个问题/任务
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

        // 真·流式：token 到达即打印；搜索/抓取过程实时可见
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
// 1. 给 fetch_url 传 http://localhost:8089 ，观察 SSRF 防护如何拦截
// 2. 问一个时效性问题（如"rig 最新版本是多少"），观察 搜索→打开→回答 的链路
// 3. 把 MAX_CHARS 改成 500，观察模型信息不足时的行为（会不会继续 fetch 别的页面？）
// 4. 进阶：把 web_search 的结果加上缓存（HashMap），体会工具层的工程优化
