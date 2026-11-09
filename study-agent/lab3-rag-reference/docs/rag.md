# RAG 的原理

embedding 把文本映射成向量，语义相近的文本距离更近。
检索时把用户问题也变成向量，找最近的文档块注入上下文。

dynamic_context(n, index) 会在每轮 prompt 前自动检索 top-n 文档，
模型本身不知道检索的存在，它只是收到了一段上下文。
