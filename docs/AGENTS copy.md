# 主 Agent 指引

本文件描述主 Agent 需要的信息与知识，并引导在合适时机调用子 Agent。

## 子 Agent 列表

子 Agent 定义放在各工具对应的 **`.<工具名>/agents/`** 下（Cursor：`.cursor/agents/`，Claude Code：`.claude/agents/`，OpenCode：`.opencode/agents/`），方式相同。主 Agent 在规划或派发任务时可根据「当前任务所属模块」决定调用哪个子 Agent。

| 子 Agent | 职责 | 何时调用 |
|----------|------|----------|
| **backend-build** | 后端构建与运行（FastAPI、`backend/`） | 启动/构建/测试后端、安装后端依赖、排查后端启动失败、执行 backend 脚本时 |
| **frontend-interaction** | 前端交互与构建（React/Vite、`frontend/`） | 做前端页面/组件、改交互、启动前端、安装前端依赖、排查前端报错、与后端联调前端时 |

## 建议流程

- **涉及前后端联调**：先确认 API 契约（如 `.project_process_for_ai/api_development.md` 或项目内约定），再分别派给 backend-build 或 frontend-interaction；完成一方后可在 prompt 中写明需触发的联调或后续步骤。
- **主 Agent 指导子 Agent 执行命令**：在调用子 Agent 的 **prompt** 中明确写出要执行的命令或功能（例如「请在 `frontend/` 下执行 `npm run dev`」或「请根据 api_development.md 实现登录页并调用 /api/login」）。

## 可选：Superpowers（全局已安装）

若任务涉及 TDD、脑暴、写计划、执行计划、系统性调试、代码评审、Git worktree 等流程，主 Agent 应参考 **`docs/cursor-superpowers-bootstrap.md`**，并按其中约定读取全局 Superpowers 技能：`~/.codex/superpowers/skills/<技能名>/SKILL.md`。

## 可选：项目进程与记忆

若项目维护了 `.project_process_for_ai/`（含 `api_development.md`、`project_process.md`、`changelog.md`、`integration/`、`agent_memories/`），主 Agent 在派发任务前可先读取相关文件。**子 Agent 的「定义」与「何时调用」** 已统一放在本工具的 `.<工具名>/agents/` 下，主 Agent 直接阅读该目录下的 .md 即可决定调用哪个子 Agent 以及传入的上下文；`agent_memories/` 可用于其它项目/会话记忆。


## Superpowers System

<EXTREMELY_IMPORTANT>
You have superpowers. Superpowers teach you new skills and capabilities. RIGHT NOW run: `~/.codex/superpowers/.codex/superpowers-codex bootstrap` and follow the instructions it returns.
</EXTREMELY_IMPORTANT>
