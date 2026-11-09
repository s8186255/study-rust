# Final Project A：代码审查助手

## 需求

输入一段 Rust 代码/项目目录，输出结构化的审查报告。

## 必做

- [ ] preamble：明确的审查标准（如「只报事实、必须先读代码、按严重度分级」）
- [ ] 工具 >= 2：`read_file`、`cargo_check`（或自选），description 写清何时选它
- [ ] `prompt_typed::<CodeReview>` 结构化输出（severity / issues / summary）
- [ ] `max_turns` 设置合理，工具错误能让模型自我纠正（如改路径重试）

## 加分

- [ ] 流式展示审查过程
- [ ] 子 Agent：把「安全审查」拆成子 Agent，用 `into_tool()` 挂给主 Agent
- [ ] RAG：把团队编码规范 md 入库，`dynamic_context` 注入审查标准

## 验收（对照课程标准）

| 等级 | 标准 |
|---|---|
| 及格 | 编译运行，单轮问答正确，工具被正确调用 |
| 良好 | 多轮任务中模型能根据工具错误自我纠正 |
| 优秀 | 加分项 + 能讲出 max_turns / 错误设计 / description 的考量 |
