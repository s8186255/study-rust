# maf-csharp-agent

Microsoft Agent Framework (MAF) C# 学习实验集 —— 与课程笔记《72 MAF-agent框架》的 Lab 0 ~ Lab 20 一一对应，**一个实验一个目录/项目**。

## 环境要求

- .NET 10 SDK（`dotnet --list-sdks` ≥ 10.0）
- 模型服务：OpenAI 兼容服务（默认 `http://10.126.126.2:8089/v1`，模型 `gemma-4-26B-A4B`）
- lab6 需要 Node.js/npx（MCP filesystem server）

## 配置

每个 lab 目录下有独立 `config.json`（机制与 study-agent 对齐，**改配置切换模型服务，代码不动**）：

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "temperature": 0.7
}
```

## 运行

```powershell
dotnet build maf-csharp-agent.slnx      # 构建全部
cd lab1-hello-agent; dotnet run        # 运行单个 lab
```

## 目录结构

| 目录 | 实验内容 | 依赖特性 |
| --- | --- | --- |
| `common/Maf.Common` | 公共库：config.json 加载 + OpenAI 兼容 IChatClient 工厂 | 全部 lab 复用 |
| `lab0-env` | 环境准备：连通性验证 | IChatClient |
| `lab1-hello-agent` | 第一个 Agent：统一抽象 / 流式 / 多模态 | ChatClientAgent |
| `lab2-function-tools` | 函数工具（Function Calling） | AIFunctionFactory |
| `lab3-agent-session` | 会话：多轮对话记忆 | AgentSession |
| `lab4-structured-output` | 结构化输出 | RunAsync<T> |
| `lab5-react` | ReAct 循环（Thought→Action→Observation） | 手工循环 |
| `lab6-mcp` | MCP 工具接入（filesystem server） | ModelContextProtocol |
| `lab7-workflow-sequential` | Workflow 串行流水线 | WorkflowBuilder |
| `lab8-workflow-branch-parallel` | 条件路由 + 扇出 | AddEdge\<T\> condition |
| `lab9-agent-as-tool` | Agent-as-Tool 分层委托 | AsAIFunction |
| `lab10-handoff` | 多智能体 Handoff 交接 | HandoffWorkflowBuilder |
| `lab11-groupchat` | 多智能体 Group Chat 群聊 | AgentWorkflowBuilder |
| `lab12-magnetic` | Magentic 磁控调度（MAF 招牌） | MagenticWorkflowBuilder |
| `lab13-hitl` | 人机协同（方案审批） | HITL |
| `lab14-checkpoint` | Checkpoint 持久化与恢复 | CheckpointManager |
| `lab15-memory` | 会话序列化持久化（跨进程记忆） | SerializeSessionAsync |
| `lab16-context-provider` | Context Provider / RAG 注入 | IChatClient 装饰器 |
| `lab17-middleware-otel` | 中间件 + OpenTelemetry 链路追踪 | DelegatingChatClient |
| `lab18-harness-agent` | Harness：待办管理/上下文压缩/工具审批 | 长任务循环 |
| `lab19-foundry` | Foundry/Azure OpenAI 生产迁移（Entra ID） | Azure.Identity |
| `lab20-final` | 毕业项目：智能客服工作台 | 综合以上 |

## 版本说明

- `Microsoft.Agents.AI` / `Microsoft.Agents.AI.Workflows` **1.28.0**（统一版本由 `Directory.Packages.props` 管理，改一处全升）
- `Microsoft.Extensions.AI.OpenAI` 11.0.0、`ModelContextProtocol` 2.4.0、`Azure.AI.OpenAI` 2.1.0
- MAF 1.28 关键 API 对照：
  - 会话：`agent.CreateSessionAsync()` → `AgentSession`（旧版 GetNewThread/AgentThread 已更名）
  - 指令：`ChatClientAgentOptions.ChatOptions.Instructions`
  - Agent-as-Tool：`agent.AsAIFunction()`
  - Executor：`public override ValueTask HandleAsync(...)`（返回 ValueTask，结果用 SendMessageAsync/YieldOutputAsync 传递）或直接用 `FunctionExecutor<TIn,TOut>` 委托节点
  - 工作流事件：`run.OutgoingEvents`（同步 IEnumerable）
