# maf-python-agent

Microsoft Agent Framework (MAF) **Python** 学习实验集 —— 与课程笔记《72 MAF-agent框架》的 Lab 0 ~ Lab 20 一一对应，与姊妹仓库 `maf-csharp-agent`（C# 1.28.0）**实验内容逐一对齐**。

## 环境要求

- Python 3.12（本仓库已带 `.venv`）
- 模型服务：OpenAI 兼容服务（默认 `http://10.126.126.2:8089/v1`，模型 `gemma-4-26B-A4B`）
- lab6 需要 Node.js/npx（MCP filesystem server）

## 安装与运行

```powershell
# venv 已创建；从零开始时：
uv venv .venv --python 3.12
uv pip install -r requirements.txt

# 运行单个 lab（在仓库根目录）
.venv\Scripts\python.exe lab1_hello_agent\main.py
```

## 配置

每个 lab 目录下有独立 `config.json`（机制与 study-agent / maf-csharp-agent 对齐，**改配置切换模型服务，代码不动**）：

```json
{
  "base_url": "http://10.126.126.2:8089/v1",
  "api_key": "",
  "model": "gemma-4-26B-A4B",
  "temperature": 0.7
}
```

## 目录结构（与 maf-csharp-agent 对齐）

| 目录 | 实验内容 | 关键 API |
| --- | --- | --- |
| `common/maf_common.py` | 公共库：config.json 加载 + ChatCompletions 客户端工厂 | OpenAIChatCompletionClient |
| `lab0_env` | 环境准备：连通性验证 | client.as_agent |
| `lab1_hello_agent` | 第一个 Agent：统一抽象 / 流式 / 多模态 | run / run(stream=True) / Content.from_uri |
| `lab2_function_tools` | 函数工具（Function Calling） | @tool |
| `lab3_agent_session` | 会话：多轮对话记忆 | create_session / session= |
| `lab4_structured_output` | 结构化输出 | options={"response_format": Model} |
| `lab5_react` | ReAct 循环（显式 Thought→Action→Observation） | 手工循环 |
| `lab6_mcp` | MCP 工具接入（filesystem server） | MCPStdioTool |
| `lab7_workflow_sequential` | Workflow 串行流水线 | @executor + WorkflowBuilder |
| `lab8_workflow_branch_parallel` | 条件路由（Switch） | add_switch_case_edge_group |
| `lab9_agent_as_tool` | Agent-as-Tool 分层委托 | agent.as_tool |
| `lab10_handoff` | 多智能体 Handoff 交接 | HandoffBuilder |
| `lab11_groupchat` | 多智能体 Group Chat 群聊 | GroupChatBuilder |
| `lab12_magentic` | Magentic 磁控调度（MAF 招牌） | MagenticBuilder + StandardMagenticManager |
| `lab13_hitl` | 人机协同（方案审批） | 控制台审批 + 会话修订 |
| `lab14_checkpoint` | Checkpoint 持久化与恢复 | FileCheckpointStorage |
| `lab15_memory` | 会话序列化持久化（跨进程记忆） | session.to_dict / AgentSession.from_dict |
| `lab16_context_provider` | Context Provider / RAG 注入 | ContextProvider.before_run |
| `lab17_middleware_otel` | 中间件 + 可观测性 | AgentMiddleware.process |
| `lab18_harness_agent` | Harness：待办管理/上下文压缩/工具审批 | create_harness_agent |
| `lab19_foundry` | Foundry/Azure OpenAI 生产迁移（Entra ID） | FoundryChatClient |
| `lab20_final` | 毕业项目：智能客服工作台 | 综合以上 |

## 版本说明

- `agent-framework-core / openai / orchestrations` **1.25.0**（MAF Python GA，与 C# 1.28 同代）
- MAF Python 关键 API 对照（已按 1.25 实测校准）：
  - 客户端：`OpenAIChatCompletionClient(model=..., base_url=...)` —— 本地 OpenAI 兼容端点不支持 Responses API，必须用 ChatCompletions 客户端
  - Agent：`client.as_agent(name=..., instructions=..., tools=[...])`；调用 `agent.run(msg, session=..., stream=True)`
  - 会话：`agent.create_session()` → AgentSession；序列化 `session.to_dict()` / `AgentSession.from_dict(...)`
  - 工具：`@tool` 装饰器（docstring 即描述）；Agent-as-Tool：`agent.as_tool(...)`
  - 编排：`HandoffBuilder / GroupChatBuilder / MagenticBuilder / SequentialBuilder`（agent_framework.orchestrations）
  - 工作流：`@executor` 节点 + `WorkflowBuilder(start_executor=...)`；事件 `result` 列表（type=='output'）
  - 结构化输出：`agent.run(q, options={"response_format": PydanticModel})` → `response.value`
  - Harness：`create_harness_agent(client=..., agent_instructions=..., ...)`（todo/压缩/审批开箱即用）
