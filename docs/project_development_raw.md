
使用AI进行代码开发时有二方面很重要
1. 让开发该模块的AI知道当前的进度，即具有历史上下文的记忆，这个记忆应该保存到文档中进行持久化
2. 以API接口文档为契约，将开发解耦、独立推进，减少相互制约与等待


在整体开发过程中需要在 `.project_info_for_ai` 文件夹中维护下面三个文档和二个文件夹：api 开发 `api_development.md` 文档、项目进展 `project_process.md` 文档、开发日志 `changelog.md` 文档，联调 `integration` 文档文件夹，AI Agent 上下文记忆 `agent_memories` 文件夹；且文档均以总结描述和目录索引为前两部分，方便 AI 进行快速理解和索引。




**子 Agent 相关文档的保存位置（适配 Cursor、Claude Code、OpenCode）**  
- **子 Agent 定义文件**（如名称、描述、触发条件，主 Agent 用来决定「何时切换、读取、唤醒哪个子 agent、运行哪些功能」的上下文）：三者的子 Agent 方式相同，均放在 **`.<工具名>/agents/<sub_agent_name>.md`** 下，比如 Cursor 用 `.cursor/agents/`，Claude Code 用 `.claude/agents/`，OpenCode 用 `.opencode/agents/`。
- **子 Agent 记忆**（子 Agent 的历史记忆，在必要时读取以保持上下文，每次子 Agent 完成操作都要增加或更新记忆）：统一放在 `.project_info_for_ai/agent_memories/<sub_agent_name>_memory.md`，每个子agent只能修改自身的记忆，且由该子agent决定是否需要写入/更新记忆。当用户的静态信息（如技术栈、技术选型等）有明确变化且和子agent的定义冲突时，由该子agent决定是否更新子agent的定义。

在项目根目录下应有 `AGENTS.md` 文件（Claude Code 使用 `CLAUDE.md`），描述主 Agent 需要的信息与知识，需要完成明确的复杂工作时，会调用专门的子agent去执行，如果没有该专业方向的子agent则会调用`create_sub_agent`创建，在调用已有子agent执行任务时，由主agent决定是否给该子agent传递某些上下文信息，该子agent是否需要读取哪些子agent记忆。在创建或更新 sub_agent 时，主 agent 应先阅读 `.project_info_for_ai` 下的内容，在 **`.<工具名>/agents/`** 下编写或更新对应的 agent .md（含定义与「何时调用」等描述），以便后续主 agent 知道应该切换、读取、唤醒哪些子 agent 以及运行哪些功能。






项目进展`project_process.md`文档是AI进行开发的最主要文档也是项目的灵魂文档，其应该涵盖项目待办事项、功能模块等部分。
- 待办事项不只是传统的待办列表，其还应该包含依赖关系
- 功能模块中包含项目开发所需要的各个模块，如前端、交互、后端数据库、算法、后端校验等模块，如有需要按需增加
- 每个功能模块应该包含模块定位，当前开发状况的描述，该模块的待办开发事项（在待办开发事项中如果涉及到和其他模块的联调、依赖等，应该具体说明，使得AI完成当前或其他相关开发后，能够提醒触发对应开发或联调）



契约优先的开发
在接到需求时，先查阅大量资料，联网搜索，选择合适的技术栈和技术方向，确定需要构建的模块，进行API的设计
先不写逻辑，只写类型定义（Type/Interface）、数据结构 或 API 文档

当后端算法或业务逻辑较复杂、难以一次性确定 API 契约时，在 `integration` 文件夹内进行契约推演，形成定稿后再同步到 `api_development.md`。推演遵循「设计轮次 + 单一负责人」，避免多 agent 在同一文档内无序修改。

契约推演流程
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


技术栈：

后端：
FastAPI、pydantic、数据库（当前阶段DuckDB + vss）（上生产级再用PostgreSQL、Milvus）、LLM和Embedding模型、
架构能力，模块化
异步，API 设计与交互支持文档。通过 FastAPI
结构化日志 (Structured Logging)

前端开发：
技术栈：React、Tailwind CSS、vite、shadcn ui
基础能力：页面配色、布局、美观程度。ui-ux-pro skills
保持不同页面风格一致。landing首页/落地页、产品页、介绍页
文档页。可直接渲染 markdown 文件的文件夹和文件系统，例如fumadocs等
重要能力。产品页的交互效果。




