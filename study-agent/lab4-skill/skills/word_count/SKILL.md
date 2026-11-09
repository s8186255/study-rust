---
name: word_count
description: 统计文本文件的行数、词数、字符数，可选输出词频 Top-N。当用户需要"字数统计 / 文本统计"类结果时选择本 skill。
---

# word_count

统计一个文本文件的行数 / 词数 / 字符数，输出 JSON。

## 用法

```
python scripts/main.py <file> [--top N]
```

- `file`：文本文件路径（相对工作目录，如 `README.md`）
- `--top N`：额外输出出现次数最多的 N 个词（可选）

## 示例

```
python scripts/main.py README.md --top 5
```

## 输出格式

```json
{"file": "README.md", "lines": 12, "words": 87, "chars": 620}
```

出错时输出 `{"error": "..."}` 并以非零码退出。
