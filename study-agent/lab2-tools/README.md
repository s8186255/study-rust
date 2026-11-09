# Lab2：工具调用（D1-M4）· 交互式流式版

参考 [lab1-hello-agent-daemon-typer](../lab1-hello-agent-daemon-typer) 改造：

- 连接信息在 `config.json`（`base_url` / `api_key` / `model` / `temperature` / `system`）
- **daemon 方式**：REPL 循环，输入任务 → 回答
- **真·流式**：token 到达即打印；**工具调用/结果事件也实时打印**，工具循环全程可见
- 退出：输入 `exit` / `quit` / `q` / `退出`，或 Ctrl+Z（回车）/ Ctrl+D（EOF）
- 启动时自动 chdir 到本 lab 目录，工具里的相对路径 `data` 处处可用

## 步骤

```bash
cargo run -p lab2-tools
```

试试输入：

```text
统计 data 目录下每个 .md 文件的字数，并给出总字数。
```

观察终端：模型先 `[tool] → list_md_files(...)`，再逐个 `[tool] → word_count(...)`，
每次执行完打印 `[tool] ← ...`，最后流式汇总回答。

## 检查点

1. 模型给了不存在的路径，你的工具该返回什么？（带原因的错误，让模型能重试；看 `[tool] ←` 的输出）
2. `ToolContext` 会出现在给模型的参数 schema 里吗？（不会）
3. 为什么 `description` 里要写「Use it rather than …」这类选用提示？

## 扩展练习

- 新增工具 `char_count(path)`，对比模型在两个相似工具间的选择
- 故意把 `word_count` 的 description 写含糊，观察误调用率变化
- 用 `CompletionCall` 事件统计每次任务的 token 用量
