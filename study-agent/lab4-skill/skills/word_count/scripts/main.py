#!/usr/bin/env python3
"""统计文本文件的行数、词数、字符数（可选输出词频 Top-N）。

用法:
    python main.py <file> [--top N]
示例:
    python main.py README.md --top 5
"""
import argparse
import json
import sys
from collections import Counter


def main() -> None:
    ap = argparse.ArgumentParser(description="统计文本文件的行数/词数/字符数")
    ap.add_argument("file", help="要统计的文本文件路径")
    ap.add_argument("--top", type=int, default=0, help="同时输出词频 Top-N（默认不输出）")
    a = ap.parse_args()

    try:
        with open(a.file, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(json.dumps({"error": f"无法读取文件 {a.file}: {e}"}, ensure_ascii=False))
        sys.exit(1)

    words = text.split()
    result = {
        "file": a.file,
        "lines": len(text.splitlines()),
        "words": len(words),
        "chars": len(text),
    }
    if a.top > 0:
        result["top"] = Counter(
            w.lower() for w in words if any(c.isalnum() for c in w)
        ).most_common(a.top)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
