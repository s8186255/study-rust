# lab14 综合实验（多智能体 + 记忆 + HITL 的端到端项目）

场景：「个人 AI 分身」——能算账、查知识库，对外发邮件前必须人工审批，跨会话记得用户是谁。
一个图串起 lab2-lab13 的全部核心能力。模型配置与 lab4 相同（本目录 `config.json`）。

## 运行方式

```powershell
cd langgraph-agent\lab14
uv sync
uv run langgraph-agent
```

## demo 脚本（四轮验证 + 一次审批）

1. 自我介绍 → 名字写入长期记忆（Store）
2. `3+5 再乘以 12` → ReAct 两跳调用 calculate，打字机流式输出
3. 查知识库并发邮件 → lookup_kb 后调 send_report，**在 sensitive_tools 前暂停** →
   人工批准 → invoke(None) 恢复 → 发送成功
4. 「刚才那道题结果多少？」→ 同 thread 短期记忆（checkpointer）生效
5. 换全新 thread 问「我叫什么」→ 长期记忆（Store）生效

## 关键点

- **compile 三件套**：`checkpointer=`（短期记忆）+ `interrupt_before=`（HITL）+ `store=`（长期记忆），
  一行配置决定整个应用的行为骨架
- **工具分级**：`route_tools` 把 tool_calls 分流到 safe/sensitive 两个 ToolNode，审批粒度只落在敏感节点
- **双记忆分工**：checkpointer 存对话历史（thread 内），Store 存用户事实（跨 thread）；
  agent 节点开场先查 Store 拼进 system prompt
- **流式 + HITL 协同**：stream 走 token 流；中断检测靠 `get_state()` 读 pending tool_calls
- **可扩展方向**：敏感节点换成真实邮件 API；Store 换 PostgresStore；图直接复用 lab13 的
  FastAPI 骨架对外服务
