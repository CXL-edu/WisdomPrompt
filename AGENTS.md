# 主 Agent 指引（必读）

**文档摘要**：最高优先级指引。每次任务开始必须完整阅读。内容涵盖：阅读顺序与优先级、核心文档位置、任务图创建与字段说明（含示例）、契约优先与契约推演、子 Agent 管理、默认技术栈。

**目录索引**
- [阅读顺序与文档优先级](#阅读顺序与文档优先级)
- [核心文档位置与要求](#核心文档位置与要求)
- [任务与任务图规范](#任务与任务图规范)
- [契约优先与契约推演](#契约优先与契约推演)
- [子 Agent 管理](#子-agent-管理)
- [默认技术栈](#默认技术栈)

## 阅读顺序与文档优先级
- 每次任务开始：先读本文件，再读 `.project_info_for_ai/project_process.md`。
- 如涉及 API/联调/前后端改动：再读 `.project_info_for_ai/api_development.md` 和 `.project_info_for_ai/api-collaboration.md`（联调细则）。
- `changelog.md` 按需阅读（行为/兼容性关注时）。
- 文档冲突优先级（高→低）：
  1) AGENTS.md
  2) `.project_info_for_ai/project_process.md`
  3) `.project_info_for_ai/api_development.md`
  4) `.project_info_for_ai/changelog.md`
  5) `.project_info_for_ai/api-collaboration.md`

## 核心文档位置与要求
- 主目录：`.project_info_for_ai/`
  - `project_process.md`：灵魂文档，摘要+目录，含任务图入口快照。
  - `api_development.md`：API 契约，摘要+目录。
  - `changelog.md`：开发日志，摘要+目录。
  - `integration/`：仅用于契约推演草案；定稿后移入 `integration/archive/` 并在 API 文档改为指向 archive。
  - `task_graph.json`：唯一权威任务图（结构化依赖）。
  - `api-collaboration.md`：API 设计/联调细则（路径 `.project_info_for_ai/api-collaboration.md`）。
  - `.create_agent/`：子 Agent 生成工具入口（脚本）；读取 `backend/prompts/cc_subagent_sys_prompt.md`（系统提示词）与 `backend/prompts/cc_subagent_user_prompt.md`（用户提示词模板，需传入 user_input），输出提示词或生成 Markdown 到 `.project_info_for_ai/agents/`，并可同步到各工具的 agents 目录。

## 任务与任务图规范
- 权威源：`.project_info_for_ai/task_graph.json`。
- 何时创建任务：新需求/功能、API 变更、阻塞/问题、需要联调或跨模块配合时。
- 字段定义（schema）：
  - `id`：唯一任务 ID。
  - `name`：简短任务名。
  - `description`：要做什么，包含关键细节。
  - `status`：`pending` | `completed`。无中间态，未完成即保持 pending。
  - `assigned_agent`（可选）：执行者或首选子 Agent（如 backend-build / frontend-interaction / main）；为空时由主 Agent 决定。
  - `dependencies`：任务 ID 列表；全部为“完成后才能开始”。为空表示可并行。
  - `downstream`（可选）：完成后应触发/提醒的任务 ID；完成后请提醒或排队下游，不要自动修改下游任务。
  - `hints`（可选）：相关或待创建的路径、注意事项；仅作提示，除非任务说明要求，不必立刻创建文件。
  - `definition_of_done`（可选）：可验证的完成判定；非平凡任务尽量填写，默认可理解为“代码/文档更新并通过必要校验”。
- 示例（可复制修改）：
```json
{
  "id": "task_api_contract_seed",
  "name": "Seed initial API contract",
  "description": "Draft minimal api_development.md sections for core endpoints to unblock parallel work.",
  "status": "pending",
  "assigned_agent": "backend-build",
  "dependencies": [],
  "downstream": ["task_frontend_mock"],
  "hints": [".project_info_for_ai/api_development.md (to be created)", "integration/ (for contract drafts)"],
  "definition_of_done": "api_development.md contains paths, params, responses for core endpoints"
}
```
- 操作准则：
  - 创建/修改/更新状态都在 `task_graph.json` 进行；若 `project_process.md` 中存在快照，完成真实更新后同步快照或删除示例行，避免混淆。
  - 依赖一律默认“完成后才能开始”；无依赖即可并行。
  - 完成任务后：更新 `status` 为 completed；若触发下游任务，在调用/提示时写明。

## 契约优先与契约推演
- 强烈建议先定契约（类型/接口/文档）再写逻辑；确需例外须在说明中标注原因。
  - 例外记录：在任务 description 中写明原因；若影响对外行为，在 `changelog.md` 记一行。
- 契约推演（建议触发条件）：接口/算法复杂、输出形态不确定、跨多模块协作时。
- 推演流程：在 `integration/` 草案撰写（单一负责人，另一方仅提结构化反馈）；收敛后同步到 `api_development.md`；草案移至 `integration/archive/`，并在 API 文档改为指向 archive。
  - 同步提示：归档后务必把 `api_development.md` 中的「设计过程见 integration/xxx」改为指向 archive 路径。
- API 或对外行为变更：必须同步更新 `api_development.md` 与 `changelog.md`。

## 子 Agent 管理
- 主源：`.project_info_for_ai/agents/`（定义、何时调用、边界、技术栈）。更新后**手动**同步到 `.cursor/agents/`、`.claude/agents/`、`.opencode/agents/`；不一致时以主源为准。
- 创建：若无合适子 Agent，可直接创建并写入主源。
- 记忆：复杂或跨多轮任务时，先读该子 Agent 的记忆（`.project_info_for_ai/agent_memories/<name>_memory.md`）。每个子 Agent 只写自己的记忆，主 Agent 不代写。
- 调用时：在 prompt 中明确目录/命令/目标。
- 若首次创建子 Agent，缺少记忆文件则新建对应 `<name>_memory.md`。
- 为防遗忘，同步子 Agent 定义时可在提交信息或 TODO 中注明“synced tool agent definitions”。
- 生成流程：主 Agent 应开启**新对话**确保上下文干净；只调用 `./.project_info_for_ai/.create_agent/create_agent.sh "<user_input>"`，**不要**自行选择 `--prompt-only` 或生成模式，由脚本基于 `OPENAI_API_KEY` 与 `OPENAI_API_BASE/OPENAI_BASE_URL` 自动选择“生成 Markdown”或“输出完整提示词”。大多数情况下会输出完整提示词，主 Agent 需在新对话中据此生成子 Agent Markdown，并保存到 `.project_info_for_ai/agents/`。
- 同步流程：生成/保存后运行 `./.project_info_for_ai/.create_agent/sync_agents.sh` 将子 Agent Markdown 复制到 `.cursor/agents/`、`.claude/agents/`、`.opencode/agents/`。

## 默认技术栈
- 后端：FastAPI、Pydantic、DuckDB + VSS（生产可换 PostgreSQL/Milvus）、LLM/Embedding、结构化日志、异步、模块化。
- 前端：React、Vite、Tailwind CSS、shadcn UI；强调配色与一致风格，Markdown 文档页能力，产品页交互效果。
- 若项目或子 Agent 定义有更新，以更新内容覆盖此默认。
