# 内部 API 规范

- 所有 REST 接口前缀 /api/v1
- 错误返回统一结构：{ code, message, details }
- 分页参数：page（从 1 开始）、page_size（默认 20，最大 100）
