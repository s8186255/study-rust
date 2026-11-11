// Lab 5：ReAct 循环（Reasoning + Acting）—— 手动实现 Thought → Action → Observation → Final Answer
// 对比 Lab 2：原生 Function Calling 是模型内部"隐式 ReAct"；这里显式控制循环，便于注入自定义策略
using System.Data;
using System.Text.RegularExpressions;
using Microsoft.Extensions.AI;
using Maf.Common;

var (client, _) = AgentFactory.CreateDefault();

const string Instructions = """
你使用 ReAct 模式回答问题。每轮严格输出以下格式之一（不要输出多余内容）：

Thought: <思考>
Action: <工具名，只能是 Calculator 或 Knowledge>
Action Input: <工具入参>

或（问题已解决时）：

Thought: <思考>
Final Answer: <最终答案>

可用工具：
- Calculator: 计算四则运算，入参为表达式，如 "12800*0.8"
- Knowledge: 查询公司知识库，入参为关键词
""";

// 极简工具集（真实场景换成数据库/HTTP 等）
static string Calculator(string expr)
{
    var dt = new DataTable();
    return Convert.ToDouble(dt.Compute(expr, null)).ToString();
}
static string Knowledge(string keyword) => keyword switch
{
    var k when k.Contains("报销") => "《差旅制度》：月度差旅报销上限 5000 元",
    var k when k.Contains("打印机") => "3 楼茶水间有 2 台共享打印机",
    _ => "知识库中没有相关内容",
};

var tools = new Dictionary<string, Func<string, string>>
{
    ["Calculator"] = Calculator,
    ["Knowledge"] = Knowledge,
};

string question = "月度差旅报销上限是多少？如果已报销 3 次、每次 1200 元，还剩多少额度？";
List<ChatMessage> history =
[
    new ChatMessage(ChatRole.System, Instructions),
    new ChatMessage(ChatRole.User, question),
];

const int MaxSteps = 8;
for (int step = 1; step <= MaxSteps; step++)
{
    var resp = await client.GetResponseAsync(history);
    history.Add(new ChatMessage(ChatRole.Assistant, resp.Text));
    Console.WriteLine($"--- 第 {step} 步 ---\n{resp.Text}\n");

    if (resp.Text.Contains("Final Answer:")) break;

    // 解析 Action / Action Input，执行工具，把 Observation 拼回上下文
    var action = ParseField(resp.Text, "Action");
    var input = ParseField(resp.Text, "Action Input");
    var observation = tools.TryGetValue(action ?? "", out var fn)
        ? fn(input ?? "")
        : $"未知工具 {action}";
    Console.WriteLine($"[Observation] {observation}\n");
    history.Add(new ChatMessage(ChatRole.User, $"Observation: {observation}"));
}

// 进阶练习：
// 1. 死循环检测：同一 Action+Input 连续出现 N 次则强制终止并要求给出 Final Answer
// 2. 在 Observation 中注入错误信息，观察 Agent 的自我纠错
// 3. 把整个循环封装成自定义 Executor 接入 Workflow（结合 Lab 7）

static string? ParseField(string text, string field)
{
    var match = Regex.Match(text, $@"{field}:\s*(.+)");
    return match.Success ? match.Groups[1].Value.Trim() : null;
}
