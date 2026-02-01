# 项目进展（灵魂文档）

**文档摘要**：记录项目待办、模块状态与依赖触发；任务图权威源在 `.project_info_for_ai/task_graph.json`。本文件作为入口快照：阅读后若需详情，请打开 task_graph.json。

**目录索引**
- [任务图入口](#任务图入口)
- [待办事项模板](#待办事项模板)
- [更新约定](#更新约定)

## 任务图入口
- 权威任务图：`.project_info_for_ai/task_graph.json`（若与本文件快照冲突，以 JSON 为准）。
- 阅读顺序：先看本节，再打开 JSON。
- 快照：
  - Create subagent prompt tooling — completed — 依赖：无 — 触发：无
  - Refine subagent generation workflow — completed — 依赖：无 — 触发：无
  - Switch subagent format to Markdown — completed — 依赖：无 — 触发：无

## 待办事项模板
使用下列核心模板（可扩展行数/段落）：
- 任务名：
- 状态：pending/completed
- 依赖：任务 ID 列表（全部为完成后才能开始）
- 完成后触发：任务 ID 列表（可为空）
- 描述：要做什么、注意事项
- 负责 Agent：可选（backend-build / frontend-interaction / main 等）
- 提示（hints）：可选（相关或待创建的路径）
- 完成判定（definition_of_done）：可选（可验证的检查）

## 更新约定
- 完成任务后：必须更新 `.project_info_for_ai/task_graph.json`；如有重要状态变化，可在本文件快照同步简述。
- 新任务规划：在 JSON 中添加；必要时在本文件“快照”列出关键任务，保持可读性。
- 依赖一律视为完成后才能开始；无依赖即默认可并行。
