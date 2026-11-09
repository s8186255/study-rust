# Lab-db：SQLite 数据分析（D2-M9）· 交互式流式版

**模型不直接连数据库**——它只生成 SQL，执行永远在你的工具里。两个只读工具构成"看结构 → 查数据 → 分析"闭环：

1. `db_schema`：列出所有表的建表语句（模型写 SQL 的依据）
2. `query_sql`：执行一条 SELECT，结果以 JSON 行数组返回（上限 50 行）

## 安全设计（教学重点）

- **只读连接**：`SQLITE_OPEN_READ_ONLY`，即使 SQL 被注入也写不了库
- **单语句校验**：拒绝含分号的多语句；只放行 `SELECT` / `WITH` 开头
- **阻塞隔离**：rusqlite 是阻塞 IO，放进 `spawn_blocking`，不卡 async 运行时
- **错误透传**：SQLite 报错原样返回给模型，它能看懂并自我修正重试

## 步骤

```bash
cargo run -p lab-db
```

试试输入：

```text
每个地区的总销售额是多少？哪个产品卖得最好？
```

观察终端：`[tool] → DbSchema {}` → `[tool] → QuerySql {"sql": "SELECT ..."}`
（可能多轮修正/细分查询）→ 流式分析回答。

## 示例数据

`data/sample.db` 由 python 内置 sqlite3 生成：

- `sales`（40 行）：region / product / amount / qty / sale_date
- `employees`（7 行）：name / dept / salary

想换数据：直接用任意 SQLite 工具改 `data/sample.db`，或重跑生成脚本。

## 检查点

1. 为什么模型拿不到数据库连接？拿得到会有什么风险？
2. 只靠只读连接就安全了吗？还得防什么？（SELECT 也能拖全表：需要行数上限/超时/白名单）
3. 模型写错 SQL 后是怎么恢复的？（看 `[tool] ←` 的报错信息与下一轮调用）

## 扩展练习

- 故意让模型拼错列名，观察报错→修正循环
- 新增工具 `top_n(table, column, n)`：动态生成**参数化查询**（防注入的正确姿势）
- 进阶：换 postgres（rusqlite → tokio-postgres），体会"模型不连库，工具连库"的解耦
- 进阶：把查询结果画成文本柱状图（另一个工具），让分析更直观
