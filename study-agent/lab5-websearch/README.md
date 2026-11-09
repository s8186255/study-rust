# Lab5：联网搜索与网页获取（D2-M10）· 交互式流式版

三个工具构成"**搜索 → 打开 → 追踪**"闭环：

1. `web_search(query)`：Bing 搜索（国内可达，无需 API Key），返回标题 + URL + 摘要（最多 8 条）
2. `fetch_url(url)`：抓取网页 → 剥掉 script/style/标签 → 正文文本（上限 4000 字符）
3. `extract_links(url)`：列出页面链接（最多 50 条），供模型追踪子页面

## 步骤

```bash
cargo run -p lab5-websearch
```

试试输入：

```text
搜一下 rig 是什么，并打开它的官方仓库看看。
```

观察终端：`[tool] → WebSearch {"query": ...}` → `[tool] → FetchUrl {"url": ...}` → 流式回答（要求注明来源 URL）。

## 教学要点（课堂讲解）

1. **模型"会上网"的本质**：抓 HTML → 正则清洗 → 喂文本；模型自己看不了网页，
   它看到的是清洗后的纯文本
2. **SSRF 防护**：工具是执行任意 HTTP 的手臂，必须拒绝
   `localhost` / `127.0.0.1` / `192.168.` / `10.` 等内网地址
3. **上下文保护**：网页正文动辄几十 KB，`MAX_CHARS = 4000` 截断，
   剩下的让模型用 `extract_links` 继续追
4. **超时与 UA**：15 秒超时；浏览器 UA，避免被站点直接拒绝

## config.json

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "temperature": 0.7,
  "system": "你是联网助手。回答时效性问题前，先用 web_search 搜索，再用 fetch_url 打开最相关的页面核实；只依据抓到的内容回答，并注明信息来源 URL。"
}
```

## 检查点

1. 给 `fetch_url` 传 `http://localhost:8089` 会发生什么？（SSRF 拦截，看报错信息）
2. 为什么 `fetch_url` 要限制内容类型与长度？（防二进制文件/超长页撑爆上下文）
3. `web_search` 依赖页面结构（`b_algo`）解析，这有什么脆弱性？

## 扩展练习

- 问一个时效性问题（如"rig 最新版本是多少"），观察完整链路
- 把 `MAX_CHARS` 改成 500，观察模型信息不足时的行为
- 进阶：搜索结果加缓存（HashMap），体会工具层工程优化
- 进阶：给 `fetch_url` 加 robots.txt 检查，讨论爬虫礼仪
