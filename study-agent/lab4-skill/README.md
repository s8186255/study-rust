# Lab4：技能系统（D2-M8）· 交互式流式版

**skill = 一个文件夹**（`SKILL.md` 描述 + `scripts/` 下可执行脚本）。与 lab2 的对照：

| | lab2 工具 | lab4 技能 |
|---|---|---|
| 能力位置 | Rust 二进制内（`#[rig_tool]`） | 外部文件（Python 脚本） |
| 新增能力 | 改 Rust 代码并重编译 | **加一个文件夹，主程序零改动** |
| 模型选型依据 | doc 注释生成的 description | `SKILL.md` frontmatter 的 description |

两个工具构成"发现 + 调用"闭环：

1. `list_skills`：扫描 `skills/` 下含 `SKILL.md` 的目录，返回名称 + 描述
2. `run_skill`：子进程执行 `python skills/<name>/scripts/main.py <args>`，回传 stdout

## 步骤

```bash
cargo run -p lab4-skill
```

试试输入：

```text
统计 README.md 的字数，并给出词频前 5 的词。
```

观察终端：模型先 `[tool] → ListSkills {}` 选技能，再 `[tool] → RunSkill {"skill": "word_count", ...}` 执行，最后依据脚本 JSON 输出回答。

## 目录结构

```
lab4-skill/
├── skills/
│   └── word_count/          ← 一个 skill 就是一个文件夹
│       ├── SKILL.md         ← 描述（模型选型依据）+ 用法说明
│       └── scripts/main.py  ← 可执行脚本
├── src/main.rs              ← 主程序（只有 list_skills / run_skill 两个工具）
└── config.json
```

## 检查点

1. 为什么 `run_skill` 要拒绝含 `..` / `\` / `/` 的 skill 名？（路径穿越防护）
2. 脚本报错时返回给模型的是什么？（带原因的错误信息，模型可自我纠正重试）
3. skill 的"接口文档"在哪？（SKILL.md；模型读不到它时调用参数就会瞎猜）

## 扩展练习

- 新增 skill：复制文件夹结构写一个 `char_replace` 脚本，**不改 Rust 代码**，观察模型自动学会新技能
- 把 word_count 的 description 写含糊，观察选型准确率变化
- 进阶：`run_skill` 增加参数白名单，防脚本滥用
- 进阶：SKILL.md 里加 `requires: python>=3.10`，`list_skills` 运行时校验
