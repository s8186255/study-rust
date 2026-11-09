//! Lab3-rag-reference：RAG 文档问答 + 参考文献引用 · 交互式流式版（课程模块 D2-M7+）
//!
//! 在 lab3-rag 基础上演进：回答问题的同时，返回命中的参考文档信息。
//!
//! 两层引用机制（课堂重点：一层是"软"的，一层是"硬"的）：
//!   1. 提示层（软引用）：system 要求模型在正文中用（见 文档名）注明来源——
//!      依赖模型自觉，可能漏标或编造
//!   2. 检索层（硬引用）：每轮回答后，用同一个向量索引跑 top_n，
//!      打印真实命中的文档路径与相似度分数——来自代码，不可能造假
//!      rig 0.46：top_n 接收 VectorSearchRequest（builder 构造），返回
//!      VectorSearchResult { score, id, document }
//!
//! 其余与 lab3-rag 相同：config.json 配置 chat + embedding 双模型、
//! daemon REPL、真·流式输出、启动时 chdir。
//!
//! 骨架基于 rig 0.46.0；若与 rustdoc 有出入，以 https://docs.rs/rig/latest/rig/ 为准。

use futures::StreamExt;
use rig::agent::{AgentBuilder, MultiTurnStreamItem};
use rig::Embed;
use rig::embeddings::EmbeddingsBuilder;
use rig::providers::openai::{self, OpenAI};
use rig::streaming::{Item, StreamEvent};
use rig::vector_store::in_memory_store::InMemoryVectorStore;
use rig::vector_store::request::VectorSearchRequest;
use rig::vector_store::VectorStoreIndex;
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use std::path::Path;

/// 文档类型：#[embed] 标记的字段参与向量化，其余字段作为元数据存储。
#[derive(Embed, Clone, serde::Serialize, serde::Deserialize)]
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
    "仅依据提供的上下文回答；上下文里没有的信息，明确说不知道。回答正文中涉及事实时，在句末用（见 文档名）注明来源文档。".to_string()
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
/// 每轮注入上下文 / 打印参考文档的命中数
const TOP_N: u64 = 3;

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
    let documents = load_docs("./docs")?;
    println!(
        "已加载 {} 篇文档，embedding 入库中（模型：{embed_model}）...",
        documents.len()
    );
    let embedded = EmbeddingsBuilder::new(embedder.clone())
        .documents(documents)?
        .build()
        .await?;

    // 建两个索引：一个给 dynamic_context（自动注入上下文），
    // 一个给每轮 top_n（打印参考文档）。rig 0.46 的 index() 消费 store，
    // 所以用同一份嵌入向量建两次（不再重复调用 embedding API）。
    let ctx_index = InMemoryVectorStore::from_documents(embedded.clone()).index(embedder.clone());
    let ref_index = InMemoryVectorStore::from_documents(embedded).index(embedder);
    println!("入库完成。\n");

    println!("====================================================");
    println!(" Lab3-rag 知识库问答（流式输出 + 参考文献引用）");
    println!(" base_url       = {}", cfg.base_url);
    println!(" chat 模型      = {}", cfg.model);
    println!(" embedding 模型 = {embed_model}");
    println!(" system         = {}", cfg.system);
    println!(" 输入问题与知识库对话；exit / quit / q / 退出 结束");
    println!("====================================================");

    // 3) 检索增强 Agent：每次 prompt 自动检索 top-N 注入上下文
    let model = client.chat(&cfg.model);
    let qa = AgentBuilder::new(model)
        .name("kb-qa")
        .preamble(cfg.system.clone())
        .temperature(cfg.temperature)
        .dynamic_context(TOP_N as usize, ctx_index)
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

        // ---- 硬引用：打印本轮真实命中的参考文档（来源 + 相似度）----
        // 与 dynamic_context 用同一份向量索引、同样的 TOP_N，
        // 所以这里列出的就是模型刚"看到"的上下文来源。
        let hits = ref_index
            .top_n::<Doc>(
                VectorSearchRequest::builder()
                    .query(input)
                    .samples(TOP_N)
                    .build(),
            )
            .await?;
        if hits.is_empty() {
            println!("📎 参考文档：（无命中）");
        } else {
            println!("📎 参考文档：");
            for h in &hits {
                println!("   {:.3}  {}", h.score, h.document.path);
            }
        }
        println!();
        turns += 1;
    }

    println!("共完成 {turns} 轮问答，再见。");
    Ok(())
}

// ---- 课堂练习 ----
// 1. 问一个 docs 里没有的问题，对比：正文说「不知道」，📎 里相似度明显更低
// 2. 给 top_n 加 .threshold(0.5)，观察低相似度命中被过滤后的表现
// 3. 对比软引用 vs 硬引用：故意问模糊问题，看模型的（见 文档名）会不会标错
// 4. 进阶：把 📎 列表改成 Markdown 脚注格式，与正文编号一一对应
