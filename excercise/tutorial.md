- [RUST语法基础](#rust语法基础)
  - [第一个 console 程序：hello world](#第一个-console-程序hello-world)
    - [代码示例](#代码示例)
    - [关键点解释](#关键点解释)
  - [变量定义](#变量定义)
    - [代码示例](#代码示例-1)
    - [关键点解释](#关键点解释-1)
  - [操作符](#操作符)
    - [代码示例](#代码示例-2)
    - [关键点解释](#关键点解释-2)
  - [判断语句](#判断语句)
    - [代码示例](#代码示例-3)
    - [关键点解释](#关键点解释-3)
  - [循环语句](#循环语句)
    - [代码示例](#代码示例-4)
    - [关键点解释](#关键点解释-4)
  - [数据类型](#数据类型)
    - [代码示例](#代码示例-5)
    - [关键点解释](#关键点解释-5)
  - [字符和字符串](#字符和字符串)
    - [代码示例](#代码示例-6)
    - [关键点解释](#关键点解释-6)
  - [特殊字符](#特殊字符)
    - [代码示例](#代码示例-7)
    - [关键点解释](#关键点解释-7)

# RUST语法基础

## 第一个 console 程序：hello world

### 代码示例

```bash
cargo new hello_world
cd hello_world
```

```rust
// src/main.rs
fn main() {
    println!("Hello, world!");
}
```

```bash
cargo run      # 编译并运行 -> Hello, world!
cargo build    # 只编译 -> target/debug/hello_world(.exe)
cargo check    # 只做检查，最快，日常首选
```

### 关键点解释

- `fn main()` 是程序入口，无参数、无返回值。
- `println!` 带 `!`，是**宏**不是函数；宏在编译期展开，能接受可变参数并做格式检查。
- 语句以 `;` 结尾；块 `{ }` 里最后一个不带 `;` 的表达式会作为返回值。
- `cargo new` 会生成 `Cargo.toml` + `src/main.rs` + `.gitignore`（已忽略 `/target`）。
- debug 与 release 分开：`--release` 产物在 `target/release/`。

---

## 变量定义

### 代码示例

```rust
let x = 5;                  // 不可变
// x = 6;                   // 编译错误

let mut y = 5;              // mut 才能改
y = 6;

let z: i32 = 10;            // 显式类型标注
const MAX: u32 = 100;       // 常量：必须标类型，命名全大写

// 遮蔽 shadowing：重新绑定，可换类型、换可变性
let a = 1;
let a = a + 1;
let a = "abc";              // 合法，a 变成 &str

let (p, q) = (1, "x");      // 元组解构
let _unused = 1;            // _ 前缀消除未使用警告

// 必须先初始化
// let n: i32;
// println!("{}", n);       // 编译错误
```

### 关键点解释

- **默认不可变**，写 `mut` 才可变 —— 这是 Rust 的核心设计，不是限制而是约束。
- `const` 是编译期常量：必须标注类型、值必须是常量表达式、可全局声明。
- **遮蔽（shadowing）与 `mut` 的区别**：遮蔽用 `let` 重新绑定，可以改变类型；`mut` 改变值但类型固定。
- 变量使用前必须初始化，编译器会做**未初始化检查**（这点比 C/C++ 安全）。
- 未使用变量只是警告不是错误，加 `_` 前缀可消除。

---

## 操作符

### 代码示例

```rust
let (a, b) = (7, 3);

// 算术
println!("{} {} {} {} {}", a + b, a - b, a * b, a / b, a % b);  // 10 4 21 2 1

// 比较
println!("{} {}", a > b, a == b);                               // true false

// 逻辑
println!("{} {} {}", true && false, true || false, !true);      // false true false

// 位运算
println!("{} {} {} {}", a & b, a | b, a ^ b, a << 1);           // 3 7 4 14

// 复合赋值（不存在 ++ / --）
let mut c = 1;
c += 2;

// 范围
for i in 0..3 {}      // 0,1,2
for i in 0..=3 {}     // 0,1,2,3

// 没有隐式数值转换，必须 as
let f = a as f64;     // 7.0
// let g = a + 1.0;   // 编译错误：i32 + f64

// 引用与解引用
let r = &c;
let v = *r;
```

### 关键点解释

- **没有 `++` / `--`**，用 `+= 1`。
- 整数除法向零截断（`7 / 3 == 2`），取余符号跟被除数。
- **不做隐式数值转换**：`i32 + f64` 是编译错误，必须 `as` 显式转换。
- `&&` `||` 是短路求值。
- 整数溢出：debug 模式 **panic**，release 模式**环绕**（wrap）。需要显式环绕用 `wrapping_*`。
- `..` 不含上界，`..=` 含上界。

---

## 判断语句

### 代码示例

```rust
let n = 5;

if n > 0 {
    println!("positive");
} else if n < 0 {
    println!("negative");
} else {
    println!("zero");
}

// if 是表达式，可以返回值
let label = if n % 2 == 0 { "even" } else { "odd" };

// 条件必须是 bool
// if n { }              // 编译错误：expected bool, found integer

// match：多分支匹配，必须穷尽
match n {
    0 => println!("zero"),
    1 | 2 => println!("one or two"),     // | 表示或
    3..=9 => println!("3 to 9"),         // 范围
    _ => println!("other"),              // 兜底
}

// match 也是表达式
let s = match n { 0 => "zero", _ => "nonzero" };

// 带条件的 match 分支
match n {
    x if x < 0 => println!("neg"),
    _ => println!("non-neg"),
}

// if let：只关心一种模式
let opt: Option<i32> = Some(3);
if let Some(v) = opt { println!("{}", v); }

// let-else：不匹配就提前返回
let Some(v) = opt else { return; };
```

### 关键点解释

- **if 的条件必须是 `bool`**，没有 truthy/falsy，不能写 `if n`。
- `if` / `match` 都是**表达式**，可以直接赋值给变量，但**所有分支返回值类型必须一致**。
- `match` 比 `if-else` 链更受推荐，因为编译器强制**穷尽性检查**。
- `_` 是通配模式，放最后兜底。
- `if let` 用于只关心一种模式、其余忽略的场景，比 `match` 简洁。

---

## 循环语句

### 代码示例

```rust
// loop：无限循环，可用 break 返回值
let mut i = 0;
let r = loop {
    i += 1;
    if i == 3 { break i * 2; }   // r == 6
};

// while
while i < 5 {
    i += 1;
}

// for：最常用，遍历迭代器
for x in 0..5 { println!("{}", x); }
for x in [1, 2, 3] { }                    // 数组（按值）
for x in &[1, 2, 3] { }                   // 数组（按引用）
for (idx, val) in [10, 20].iter().enumerate() { }
for i in (0..10).rev() { }                // 倒序

// 控制
for x in 0..10 {
    if x == 1 { continue; }
    if x == 5 { break; }
}

// 标签：跳出外层循环
'outer: for x in 0..3 {
    for y in 0..3 {
        if x + y == 3 { break 'outer; }
    }
}

// while let
let mut st = Some(1);
while let Some(v) = st { st = None; }
```

### 关键点解释

- 三种循环：`loop`（无限）、`while`（条件）、`for`（迭代）。
- `loop` 可用 `break value;` 返回值，**只有 `loop` 能带值 break**，`while` / `for` 不行。
- `for` 遍历的是实现了 `IntoIterator` 的东西；`0..5` 是 `Range`。
- 遍历数组：`iter()` 借用不移动、`into_iter()` 消耗、`iter_mut()` 可变借用。
- 标签语法 `'name:`，配合 `break 'name` / `continue 'name` 跳多层。
- 无限循环用 `loop` 而非 `while true`（编译器更清楚意图）。

---

## 数据类型

### 代码示例

```rust
// 整数（默认 i32）
let a: i8 = -1;          // i8 i16 i32 i64 i128 isize
let b: u8 = 1;           // u8 u16 u32 u64 u128 usize
let c = 1_000_000;       // 下划线分隔，可读性好
let d = 0xff;            // 十六进制 = 255
let e: u8 = b'A';        // 字节字面量

// 浮点（默认 f64）
let f: f32 = 1.0;
let g = 2.0;

// 布尔、字符
let h = true;
let i = 'A';             // char，4 字节

// 元组：可放不同类型，长度固定
let t: (i32, f64, char) = (1, 2.0, 'x');
let (x, y, z) = t;       // 解构
println!("{}", t.0);     // 索引访问
let unit = ();           // 单元类型，类似 void

// 数组：固定长度，栈上
let arr: [i32; 3] = [1, 2, 3];
let zeros = [0; 5];      // [0,0,0,0,0]
println!("{}", arr[0]);

// 切片：数组的视图
let sl = &arr[0..2];

// Vec：堆上，可变长
let mut v: Vec<i32> = Vec::new();
v.push(1);
let v2 = vec![1, 2, 3];

// 字符串
let s1 = String::from("hello");   // 堆上，可增长
let s2: &str = "hello";           // 切片，不可变

// 可选值（Rust 没有 null）
let n: Option<i32> = None;
```

### 关键点解释

- 整数默认 `i32`，浮点默认 `f64`；`usize` / `isize` 随平台字长，用作集合索引。
- 数组 `[T; N]` 长度编译期固定；`Vec<T>` 堆分配可变长。**数组越界会 panic**（Rust 做边界检查）。
- 元组各元素类型可不同，用 `.0` `.1` 访问；空元组 `()` 是单元类型，无返回值的函数默认返回它。
- **Rust 没有 null**，用 `Option<T>`（`Some(v)` / `None`），强制你处理空值。
- 数字字面量可用 `_` 分隔提高可读性（`1_000_000`）。

---

## 字符和字符串

### 代码示例

```rust
// char：单引号，4 字节，一个 Unicode 标量值
let c1 = 'A';
let c2 = '中';
let c3 = '😀';
println!("{}", '😀'.len_utf8());    // 4

// &str：字符串切片，不可变
let s1: &str = "hello";

// String：堆上可变
let mut s2 = String::from("hello");
s2.push_str(", world");
s2.push('!');

// 转换
let s3: String = s1.to_string();
let s4: &str = &s2;                  // 借用，Deref 强转

// 拼接
let s5 = String::from("a") + &s2;    // + 右侧须 &str，且会移动左侧
let s6 = format!("{}-{}", s1, s2);   // 推荐：不转移所有权

// 遍历（不能用下标取字符！）
for ch in " hi中".chars() { }        // 按字符
for b in "hi".bytes() { }            // 按字节

// 长度
println!("{}", "中".len());           // 3（UTF-8 字节数）
println!("{}", "中".chars().count()); // 1（字符数）
```

### 关键点解释

- `char` 用**单引号**且固定 4 字节，能放任意 Unicode；字符串用**双引号**。
- `&str` 是不可变借用（字面量是 `&'static str`，存在二进制里）；`String` 拥有堆上数据、可增长。
- **不能用索引访问字符**：`"中"[0]` 编译错误。因为 UTF-8 变长，下标取到的是字节边界不确定的位置。
- `len()` 返回**字节数**，字符数要 `chars().count()`。
- 拼接优先 `format!`：`+` 会 move 左侧变量，之后就不能再用了。
- 函数参数优先用 `&str`（`String` 会自动解引用强转，两种都能传）。

---

## 特殊字符

### 代码示例

```rust
// 常用转义
let nl = "\n";        // 换行
let tb = "\t";        // 制表符
let cr = "\r";        // 回车
let bs = "\\";        // 反斜杠
let q  = "\"";        // 双引号
let sq = '\'';        // 单引号（char 中必须转义）
let z  = "\0";        // 空字符

// Unicode 转义
let u1 = "\u{4E2D}";  // 中
let e1 = "\u{1F600}"; // 😀

// 原始字符串：不做任何转义
let raw  = r"C:\Users\name";       // 反斜杠原样保留
let raw2 = r#"He said "hi""#;     // 内容含 " 用 r#""#
let raw3 = r##"a "#" b"##;        // 含 "# 再加一层 #

// 字节串
let b: &[u8; 2] = b"hi";          // 字节串字面量
let braw = br"raw\nbytes";        // 原始字节串

// 续行：行尾 \ 会去掉换行和前导空白
let long = "abc\
    def";                          // -> "abcdef"
```

### 关键点解释

- 常用转义：`\n` `\t` `\\` `\"` `\'` `\0`。
- `r"..."` **原始字符串不做转义**，写 Windows 路径、正则时特别省事。
- 内容里有 `"` 就用 `r#""#`；万一含 `"#`，再加 `#`（`r##"..."##`），几层由内容决定。
- `\u{XXXX}` 写任意 Unicode 码点，也可直接写字符本身。
- `b"..."` 得到 `&[u8; N]` 字节串，char 里只能放 ASCII。
- 字符串里换行会保留；行尾加 `\` 可续行并吞掉缩进。

