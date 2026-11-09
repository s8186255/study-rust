# Final Project B：团队知识库问答

## 需求

对 `./kb` 下的 markdown 文档做问答，回答必须可溯源。

## 必做

- [ ] 文档 embedding 入库（参考 lab4-rag 的骨架）
- [ ] `dynamic_context(n, store)` 检索增强
- [ ] 工具 >= 2：`list_docs`、`read_doc`
- [ ] `prompt_typed::<KbAnswer>`：answer + sources（引用来源）
- [ ] 上下文没有的信息，明确回答「不知道」

## 加分

- [ ] 多轮追问（`agent.chat(prompt, &mut history)`）
- [ ] 流式输出
- [ ] 把回答与来源一起渲染（如 `#[derive(Embed)]` 的 path 元数据）

## 验收（对照课程标准）

| 等级 | 标准 |
|---|---|
| 及格 | 编译运行，检索命中时回答正确且带来源 |
| 良好 | 上下文外的问题明确说不知道；多轮追问不丢上下文 |
| 优秀 | 加分项 + 能讲出 RAG / 检索数量 / 结构化输出的权衡 |
