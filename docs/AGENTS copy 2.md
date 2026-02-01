# 主 Agent 指引（必读）

**文档摘要**：本文件为最高优先级指引。每次任务开始必须完整阅读。说明：文档与工具目录、任务图、契约推演、子 Agent 管理、默认技术栈以及文档冲突优先级与阅读顺序。

**目录索引**
- [阅读顺序与优先级](#阅读顺序与优先级)
- [核心文档位置与要求](#核心文档位置与要求)
- [任务图与待办维护](#任务图与待办维护)
- [契约优先与契约推演](#契约优先与契约推演)
- [子 Agent 管理](#子-agent-管理)
- [默认技术栈](#默认技术栈)

## 阅读顺序与优先级
- 每次任务开始：先读本文件，再读 `.project_info_for_ai/project_process.md`。
- 如涉及 API/联调/前后端改动：再读 `.project_info_for_ai/api_development.md`。
- `changelog.md` 按需阅读（行为/兼容性关注时）。
- 文档冲突时的优先级（高→低）：
  1) AGENTS.md
  2) `.project_info_for_ai/project_process.md`
  3) `.project_info_for_ai/api_development.md`
  4) `.project_info_for_ai/changelog.md`
  5) `docs/api-collaboration.md`

## 核心文档位置与要求
- 主目录：`.project_info_for_ai/`
  - `project_process.md`（灵魂文档，摘要+目录，含任务图入口快照）。
  - `api_development.md`（API 契约，摘要+目录）。
  - `changelog.md`（日志，摘要+目录）。
  - `integration/` 仅用于契约推演草案；定稿后移入 `integration/archive/` 并在 API 文档改为指向 archive。
  - `task_graph.json`：唯一权威任务图（结构化依赖）。
- `docs/api-collaboration.md`：联调细则（错误体、版本、Mock 等）；在主文档中引用，不再重复。

## 任务图与待办维护
- 权威源：`.project_info_for_ai/task_graph.json`。结构：`id, name, description, status(pending/completed), assigned_agent?, dependencies[], downstream[], hints?, definition_of_done?`。
- 依赖：仅任务 ID，默认“完成后才能开始”；无依赖即可并行。
- 下游：`downstream` 可为空，用于完成时提醒触发。
- 每次完成任务：必须更新 `task_graph.json`；若关键状态变更，可在 `project_process.md` 快照同步一句话。
- `project_process.md` 仅保留关键任务快照和模板指引，若有冲突以 JSON 为准。

## 契约优先与契约推演
- 强烈建议先定契约（类型/接口/文档）再写逻辑；确需例外须在说明中标注原因。
- 当接口/逻辑复杂或输出形态不确定时，建议触发契约推演：在 `integration/` 草案撰写（单一负责人、另一方仅提结构化反馈）；收敛后同步到 `api_development.md`；草案归档至 `integration/archive/`。
- API 或对外行为变更：必须同步更新 `api_development.md` 与 `changelog.md`。

## 子 Agent 管理
- 主源：`.project_info_for_ai/agents/`（定义、何时调用、边界、技术栈）。更新后**手动**同步到 `.cursor/agents/`、`.claude/agents/`、`.opencode/agents/`；如有不一致，以主源为准。
- 调用子 Agent 时：
  - 创建：若无合适子 Agent，可直接创建并写入主源。
  - 记忆：复杂或跨多轮任务时，先读该子 Agent 的记忆（`.project_info_for_ai/agent_memories/<name>_memory.md`）。每个子 Agent 只写自己的记忆，主 Agent 不代写。
  - 提示：调用时明确目录/命令/目标。

## 默认技术栈
- 后端：FastAPI、Pydantic、DuckDB + VSS（生产可换 PostgreSQL/Milvus）、LLM/Embedding、结构化日志、异步、模块化。
- 前端：React、Vite、Tailwind CSS、shadcn UI；强调配色与一致风格，Markdown 文档页能力，产品页交互效果。
- 若项目/子 Agent 定义有更新，以更新内容覆盖此默认。
