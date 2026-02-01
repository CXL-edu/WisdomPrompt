# 项目开发规范（AI 协作）

**总结**：本文档约定「AI 协作开发」时的记忆持久化、API 契约与目录结构。核心是在 `.project_process_for_ai/` 下维护 API 文档、项目进展、开发日志、联调草案与 Agent 记忆，并采用契约优先与契约推演流程；子 Agent 定义与主 Agent 指引分别放在 `.<工具名>/agents/` 与根目录 `AGENTS.md`。

**目录**
- [协作原则与目录约定](#协作原则与目录约定)
- [子 Agent 与主 Agent](#子-agent-与主-agent)
- [项目进展文档](#项目进展文档)
- [契约优先与契约推演](#契约优先与契约推演)
- [技术栈](#技术栈)
- [本文档变更记录](#本文档变更记录)

---

## 协作原则与目录约定

使用 AI 进行代码开发时有两方面很重要：
1. **历史上下文记忆**：让开发该模块的 AI 知道当前进度，记忆应持久化到文档中。
2. **API 契约解耦**：以 API 接口文档为契约，将开发解耦、独立推进，减少相互制约与等待。

在整体开发过程中，需在 **`.project_process_for_ai/`** 下维护：
- 三个文档：API 开发 `api_development.md`、项目进展 `project_process.md`、开发日志 `changelog.md`
- 两个文件夹：联调草案与记录 `integration/`、AI Agent 上下文记忆 `agent_memories/`

上述文档均以「总结描述」和「目录索引」为前两部分，方便 AI 快速理解与索引。

## 子 Agent 与主 Agent

**子 Agent 相关文档的保存位置（适配 Cursor、Claude Code、OpenCode）**  
- **子 Agent 定义文件**（如名称、描述、触发条件，主 Agent 用来决定「何时切换、读取、唤醒哪个子 agent、运行哪些功能」的上下文）：三者的子 Agent 方式相同，均放在 **`.<工具名>/agents/<sub_agent_name>.md`** 下，比如 Cursor 用 `.cursor/agents/`，Claude Code 用 `.claude/agents/`，OpenCode 用 `.opencode/agents/`。
- **子 Agent 记忆**（子 Agent 的历史记忆，在必要时读取以保持上下文，每次子 Agent 完成操作都要增加或更新记忆）：统一放在 `.project_process_for_ai/agent_memories/<sub_agent_name>_memory.md`，每个子 agent 只能修改自身的记忆，且由该子 agent 决定是否需要写入/更新记忆。当用户的静态信息（如技术栈、技术选型等）有明确变化且和子 agent 的定义冲突时，由该子 agent 决定是否更新子 agent 的定义。

在项目根目录下应有 `AGENTS.md` 文件（Claude Code 使用 `CLAUDE.md`），描述主 Agent 需要的信息与知识，需要完成明确的复杂工作时，会调用专门的子agent去执行，如果没有该专业方向的子agent则会调用`create_sub_agent`创建，在调用已有子agent执行任务时，由主agent决定是否给该子agent传递某些上下文信息，该子agent是否需要读取哪些子agent记忆。在创建或更新 sub_agent 时，主 agent 应先阅读 `.project_process_for_ai/` 下的内容，在 **`.<工具名>/agents/`** 下编写或更新对应的 agent .md（含定义与「何时调用」等描述），以便后续主 agent 知道应该切换、读取、唤醒哪些子 agent 以及运行哪些功能。






## 项目进展文档

项目进展 `project_process.md` 是 AI 进行开发的主要文档，应涵盖项目待办事项、功能模块等部分。
- 待办事项不只是传统的待办列表，还应包含依赖关系
- 功能模块中包含项目开发所需要的各个模块，如前端、交互、后端数据库、算法、后端校验等模块，如有需要按需增加
- 每个功能模块应该包含：模块定位、当前开发状况描述、该模块的待办开发事项（若涉及与其他模块的联调或依赖，应具体说明，便于 AI 完成当前或相关开发后触发对应开发或联调）。

## 契约优先与契约推演

**契约优先的开发**：接到需求后，先查阅资料、联网搜索，选定技术栈与方向，确定要构建的模块并设计 API；先不写逻辑，只写类型定义（Type/Interface）、数据结构或 API 文档。

当后端算法或业务逻辑较复杂、难以一次性确定 API 契约时，在 `.project_process_for_ai/integration/` 下进行契约推演，定稿后同步到 `api_development.md`。推演遵循「设计轮次 + 单一负责人」，避免多 agent 在同一文档内无序修改。

**契约推演流程**
- **场所**：使用 `integration` 下专用文档，如 `api_contract_draft.md`（或按能力拆分为 `integration/recommendation_api_draft.md` 等），不与其他联调记录混在同一文件。
- **负责人**：每轮契约由一方主导（通常为后端或「API 设计」agent），负责撰写和更新草案；另一方（前端/产品）只提交**结构化反馈**（缺哪些字段、分页方式、错误码建议等），不直接改草案正文。
- **草案模板**（便于 AI 与人类一致地读写）：
  - 目标与背景
  - 端点与行为（可含伪代码、关键逻辑）
  - 类型与数据结构
  - 错误与边界情况
  - 开放问题（待前后端/产品对齐）
  - 变更记录（每轮修订摘要）
- **收敛**：开放问题清空或达成共识后，将「端点 + 类型 + 错误」同步到正式 API 文档（如 `api_development.md`），并在该文档中注明「设计过程见 integration/xxx」。
- **定稿后对草案的处理**：不删除草案，保留设计过程与追溯。将文档移入 `integration/archive/`，并把 `api_development.md` 中的「设计过程见 integration/xxx」改为「见 integration/archive/xxx」。
- **小步定稿**：按能力分批推演与定稿（如先推荐 API，再反馈 API），避免一次性敲定整系统契约；复杂算法可先定**输出形状**与端点，后端用 stub 返回合法结构，前端按契约开发，再替换真实实现。


## 技术栈

- **后端**：FastAPI、pydantic、数据库（当前阶段 DuckDB + vss，生产级可用 PostgreSQL、Milvus）、LLM 与 Embedding 模型；架构模块化、异步；API 与交互支持文档（FastAPI）；结构化日志 (Structured Logging)。

- **前端**：React、Tailwind CSS、Vite、shadcn ui；基础能力包括页面配色、布局与美观（可参考 ui-ux-pro skills）；保持不同页面风格一致（落地页、产品页、介绍页）；文档页可渲染 markdown 文件夹/文件系统（如 fumadocs）；产品页交互效果为重点能力。

## 本文档变更记录

| 日期       | 变更说明 |
|------------|----------|
| 2025-02-01 | 初版优化：增加标题与总结、目录，统一目录名为 `.project_process_for_ai/`，补全章节标题，增加本文档变更记录；契约推演场所明确为 `.project_process_for_ai/integration/`；技术栈改为列表表述。 |




