# Lab3-rag-reference：RAG 问答 + 参考文献引用（D2-M7+）

在 [lab3-rag](../lab3-rag) 基础上演进：回答问题的同时，返回命中的参考文档信息。

## 两层引用机制（软 vs 硬）

| 层 | 机制 | 可靠性 |
|---|---|---|
| 提示层（软引用） | system 要求模型在正文句末用（见 文档名）注明来源 | 依赖模型自觉，可能漏标甚至编造 |
| 检索层（硬引用） | 每轮回答后用同一个索引跑 `top_n`，打印真实命中的 `path` 与相似度分数 | 来自代码，不可能造假 |

关键点：检索层与 `dynamic_context` 用**同一份向量、同样的 TOP_N**，所以 📎 列出的就是模型刚"看到"的上下文来源。

## 步骤

```bash
cargo run -p lab3-rag-reference
```

运行效果：

```text
you> rig 换模型厂商要改多少业务代码？
assistant> 只需要改 client 构造那一行（见 rig-overview.md）...
📎 参考文档：
   0.812  ./docs/rig-overview.md
   0.634  ./docs/faq.md
   0.598  ./docs/tools.md
```

## 检查点

1. 问一个 docs 里没有的问题：正文说「不知道」，📎 里分数是不是明显更低？
2. 模型的软引用（见 文档名）会标错吗？和硬引用对比
3. `top_n` 与 `dynamic_context` 为什么必须用同一个 TOP_N？

## 扩展练习

- 给 `top_n` 加 `.threshold(0.5)`，观察低相似度命中被过滤后的表现
- 把 📎 列表改成 Markdown 脚注格式，与正文编号一一对应
- 多轮引用：结合上一轮命中的文档，形成"追问"时的来源链

## rig 0.46 API 备注

- `top_n` 签名：`top_n::<T>(VectorSearchRequest) -> Vec<VectorSearchResult<T>>`，
  request 用 `VectorSearchRequest::builder().query(..).samples(..).build()` 构造
- `VectorSearchResult<T>` 字段：`score: f64` / `id: String` / `document: T`
- 因此 `Doc` 需要 `serde::Serialize + Deserialize`（入库读回都要）
- `index()` 消费 store：要两用（dynamic_context + top_n），用同一份嵌入建两个索引
