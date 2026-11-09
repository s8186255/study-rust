# Lab3：RAG 文档问答（D2-M7）· 交互式流式版

参考 [lab1-hello-agent-daemon-typer](../lab1-hello-agent-daemon-typer) 改造：

- 连接与模型在 `config.json`；RAG 需要**两个模型**：`model`（chat）+ `embedding_model`
- 启动时加载 `./docs` 下的 .md → embedding 入库（内存向量库）→ REPL 问答
- **真·流式**：token 到达即打印
- 退出：输入 `exit` / `quit` / `q` / `退出`，或 Ctrl+Z（回车）/ Ctrl+D（EOF）
- 启动时自动 chdir 到本 lab 目录，`./docs` 相对路径处处可用

## 步骤

```bash
cargo run -p lab3-rag
```

## config.json

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "embedding_model": "jina-embeddings-v5-omni",
  "temperature": 0.7,
  "system": "仅依据提供的上下文回答；上下文里没有的信息，明确说不知道。"
}
```

`embedding_model` 留空/省略时回退 OpenAI 官方 `TEXT_EMBEDDING_3_SMALL`；
走 InferenceRouter2 时填 catalog 里的 embed 模型（如 `jina-embeddings-v5-omni`）。

## 检查点

1. RAG 和「把全部文档塞进 preamble」的区别？（成本、上下文上限、噪声）
2. 检索发生在哪一侧？（应用侧，`dynamic_context` 自动完成；对模型只是普通上下文）
3. `dynamic_context(3, ..)` 的 3 调大有什么代价？

## 扩展练习

- 让回答带上引用来源（提示：Doc 的 `path` 元数据会随上下文一起给到模型）
- 问一个 docs 里没有的问题，验证它是否回答「不知道」
- 换用 Qdrant / LanceDB（开对应 feature），对比代码改动量
- 大库优化：`InMemoryVectorStore::builder()` 切 `IndexStrategy::LSH`

## 已知注意（rig 0.46.0 的 API 变化，已在本版适配）

- `Embed` derive 宏：`use rig::Embed;`（原 `rig::embeddings::Embed` 只剩 trait）
- 入库流程：`EmbeddingsBuilder::new(embedder).documents(..)?.build().await?`
  → `InMemoryVectorStore::from_documents(..)` → `store.index(embedder)` → `dynamic_context(.., index)`
- 文档类型需 `Serialize`（向量库存的是可序列化文档）
