//! Final Project B：团队知识库问答（D2 15:30-17:30）
//!
//! 要求（见课程设计「Final Project」节）：
//! - 一批 markdown 文档 embedding 入库（RAG）
//! - 工具 >= 2：列出文档、按文件名取全文
//! - 结构化输出：回答必须含「引用来源」字段
//! - 加分项：多轮会话（chat + history 或 memory）/ 流式 / 检索不到时明确说不知道
//!
//! 起点骨架，按需求自行补全。入库签名可参考 lab4-rag。

use rig::agent::AgentBuilder;
use rig::prelude::*;
use rig::providers::openai::{self, OpenAI};
use schemars::JsonSchema;
use serde::Deserialize;

#[derive(Debug, Deserialize, JsonSchema)]
struct KbAnswer {
    answer: String,
    /// 被引用的文档文件名列表
    sources: Vec<String>,
}

// TODO 1: 读 ./kb 下所有 md 文档，embedding 入库（参考 lab4-rag）
// TODO 2: 工具 list_docs() / read_doc(name)
// TODO 3: agent = preamble(仅依据上下文回答) + dynamic_context(n, store) + tools
// TODO 4: prompt_typed::<KbAnswer> 输出，打印答案与来源
// TODO 5(加分): chat + Vec<Message> 多轮追问；检索不到时回答「不知道」

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let model = OpenAI::from_env()?.completion(openai::GPT_5_2);

    let _agent = AgentBuilder::new(model)
        .name("kb-qa")
        .preamble("TODO: 在此写知识库问答的行为边界")
        .build();

    anyhow::bail!("Final Project 骨架：请按 README 完成后替换本行")
}
