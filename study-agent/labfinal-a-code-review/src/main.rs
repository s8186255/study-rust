//! Final Project A：代码审查助手（D2 15:30-17:30）
//!
//! 要求（见课程设计「Final Project」节）：
//! - preamble 设计（有明确的审查标准与人格）
//! - 工具 >= 2 个：读文件、搜索符号、运行 cargo check（任选实现两个以上）
//! - >= 1 处结构化输出（CodeReview）
//! - 加分项：流式 / 子 Agent（agent.into_tool()）/ 工具错误自纠正
//!
//! 以下为起点骨架，按需求自行补全。

use rig::agent::AgentBuilder;
use rig::prelude::*;
use rig::providers::openai::{self, OpenAI};
use schemars::JsonSchema;
use serde::Deserialize;

#[derive(Debug, Deserialize, JsonSchema)]
struct CodeReview {
    severity: String,
    issues: Vec<String>,
    summary: String,
}

// TODO 1: 实现工具 read_file(path) —— 返回文件内容（注意错误信息要可自纠正）
// TODO 2: 实现工具 cargo_check() —— 用 std::process::Command 跑 cargo check，返回 stderr
// TODO 3: 组装 agent：preamble 写清「仅报告事实，必须先读代码再下结论」
// TODO 4: prompt_typed::<CodeReview> 输出报告，打印为 JSON
// TODO 5(加分): 用 agent.prompt(..).stream() 展示审查过程

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let model = OpenAI::from_env()?.completion(openai::GPT_5_2);

    let _agent = AgentBuilder::new(model)
        .name("code-reviewer")
        .preamble("TODO: 在此写你的审查标准与行为边界")
        .build();

    anyhow::bail!("Final Project 骨架：请按 README 完成后替换本行")
}
