//! Lab3-rag：RAG 文档问答 · 交互式流式版（课程模块 D2-M7）
//!
//! 流程：加载文档 -> embedding 入库 -> dynamic_context 检索增强 -> 流式回答
//!
//! 参考 lab1-hello-agent-daemon-typer 改造：
//!   - 连接与模型在 config.json（RAG 需要**两个模型**：chat + embedding）
//!   - daemon 方式：REPL 循环，输入问题 → 流式输出回答
//!   - 真·流式：token 到达即打印
//!
//! 工作目录说明：启动时自动 chdir 到本 lab 目录，`./docs` 相对路径处处可用。
//! embedding_model 留空/省略时回退到 OpenAI 官方 TEXT_EMBEDDING_3_SMALL；
//! 走 InferenceRouter2 时请填 catalog 里的 embed 模型（如 jina-embeddings-v5-omni）。
//!
//! 注意：embedding / 入库的具体签名在不同小版本间变动较频繁，
//! 编译不过时请对照 rustdoc（https://docs.rs/rig/latest/rig/vector_store/）微调。
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 rustdoc 为准。

use futures::StreamExt;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::Embed;
use rig::embeddings::EmbeddingsBuilder;
use rig::providers::openai::{self, OpenAI};
use rig::streaming::{Item, StreamEvent};
use rig::vector_store::in_memory_store::InMemoryVectorStore;
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use std::path::Path;

/// 文档类型：#[embed] 标记的字段参与向量化，其余字段作为元数据存储。
/// rig 0.46：Embed derive 宏在 `rig::derive::Embed`（不再与 trait 同路径）。
#[derive(Embed, Clone, serde::Serialize)]
struct Doc {
    #[embed]
    content: String,
    path: String,
}

fn load_docs(dir: &str) -> anyhow::Result<Vec<Doc>> {
    let mut docs = Vec::new();
    for entry in std::fs::read_dir(dir)? {
        let path = entry?.path();
        if path.extension().is_some_and(|e| e == "md") {
            let content = std::fs::read_to_string(&path)?;
            docs.push(Doc {
                content,
                path: path.to_string_lossy().into_owned(),
            });
        }
    }
    Ok(docs)
}

/// 对应 config.json；除 base_url / model 外其余字段均可省略
#[derive(Debug, Deserialize)]
struct AgentConfig {
    base_url: String,
    model: String,
    #[serde(default)]
    api_key: Option<String>,
    /// 留空/省略时回退到 OpenAI 官方 TEXT_EMBEDDING_3_SMALL
    #[serde(default)]
    embedding_model: Option<String>,
    #[serde(default = "d_temperature")]
    temperature: f64,
    #[serde(default = "d_system")]
    system: String,
}

fn d_temperature() -> f64 {
    0.7
}
fn d_system() -> String {
    "仅依据提供的上下文回答；上下文里没有的信息，明确说不知道。".to_string()
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

    /// embedding 模型：配置了用配置，否则回退 OpenAI 官方小模型
    fn effective_embedding_model(&self) -> String {
        match self.embedding_model.as_deref() {
            Some(m) if !m.trim().is_empty() => m.to_string(),
            _ => openai::TEXT_EMBEDDING_3_SMALL.to_string(),
        }
    }
}

const EXIT_WORDS: [&str; 4] = ["exit", "quit", "q", "退出"];

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cfg = AgentConfig::load()?;

    // `./docs` 是相对路径，统一切到本 lab 目录
    std::env::set_current_dir(env!("CARGO_MANIFEST_DIR"))?;

    // OpenAI 兼容 client（chat 与 embeddings 共用同一个 base_url）
    let config = openai::OpenAIConfig::new(cfg.effective_key()).with_base_url(&cfg.base_url);
    let client: OpenAI = config.client();

    // 1) embedding 模型：负责把文本变成向量
    let embed_model = cfg.effective_embedding_model();
    let embedder = client.embedding(&embed_model, None);

    // 2) 加载文档、批量 embedding、入库（内存向量库，余弦相似度）
    // rig 0.46 流程：EmbeddingsBuilder 批量嵌入 → from_documents 建库 → store.index() 建索引
    let documents = load_docs("./docs")?;
    println!(
        "已加载 {} 篇文档，embedding 入库中（模型：{embed_model}）...",
        documents.len()
    );
    let embedded = EmbeddingsBuilder::new(embedder.clone())
        .documents(documents)?
        .build()
        .await?;
    let store = InMemoryVectorStore::from_documents(embedded);
    let index = store.index(embedder);
    println!("入库完成。\n");

    println!("====================================================");
    println!(" Lab3-rag 知识库问答（真·流式输出）");
    println!(" base_url       = {}", cfg.base_url);
    println!(" chat 模型      = {}", cfg.model);
    println!(" embedding 模型 = {embed_model}");
    println!(" system         = {}", cfg.system);
    println!(" 输入问题与知识库对话；exit / quit / q / 退出 结束");
    println!("====================================================");

    // 3) 检索增强 Agent：每次 prompt 自动检索 top-3 注入上下文
    let model = client.chat(&cfg.model);
    let qa = AgentBuilder::new(model)
        .name("kb-qa")
        .preamble(cfg.system.clone())
        .temperature(cfg.temperature)
        .dynamic_context(3, index)
        .build();

    let stdin = io::stdin();
    let mut turns = 0usize;

    loop {
        // 提示符 → 读一个问题
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

        // 真·流式：token 到达即打印（检索由 dynamic_context 在 prompt 内自动完成）
        print!("assistant> ");
        io::stdout().flush()?;

        let mut stream = qa.prompt(input).stream();
        while let Some(item) = stream.next().await {
            match item? {
                MultiTurnStreamItem::StreamAssistantItem(event) => {
                    if let Item::Event(StreamEvent::Text { text, .. }) = event {
                        print!("{text}");
                        let _ = io::stdout().flush();
                    }
                }
                MultiTurnStreamItem::FinalResponse(_) => {}
                _ => {}
            }
        }
        println!("\n");
        turns += 1;
    }

    println!("共完成 {turns} 轮问答，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 问一个 docs 里没有的问题，验证它是否回答「不知道」
// 2. 把 dynamic_context(3, ..) 改成 (1, ..)，观察回答质量变化
// 3. 进阶：把 InMemoryVectorStore 换成 qdrant（features = ["qdrant"]），
//    体会「换库只换类型」
