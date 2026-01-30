# 从当前仓库迁移到 Full-Stack-FastAPI-Template

## 结论：可以迁移

可以从当前 **wisdomprompt1** 仓库迁移到 **full-stack-fastapi-template** 结构。推荐做法是：**以 template 为基底，把当前业务（workflow + 产品页）迁进去**，这样既保留登录、用户、DB、Docker 等能力，又保留你的 RAG/工作流功能。

---

## 两种迁移思路

| 思路 | 做法 | 适用 |
|------|------|------|
| **A. 以 template 为基底** | 复制/生成一份 template，把 wisdomprompt1 的 backend 业务 + 前端 AppPage 迁进去 | 想要完整认证、DB、Docker、CI，推荐 |
| **B. 在现有仓库里引入 template 能力** | 在当前 wisdomprompt1 里加入 JWT、PostgreSQL、OpenAPI 客户端等 | 想保持现有目录为主、只补能力时用 |

下面按 **思路 A** 写具体步骤（思路 B 可逆着看：在 wisdomprompt1 里加 template 的模块）。

---

## 思路 A：以 Template 为基底 — 分步迁移

### 1. 准备 template 基底

- 用 Copier 从 template 生成新项目，或直接复制 `full-stack-fastapi-template` 到新目录（如 `wisdomprompt-app`）。
- 配置 `.env`（`SECRET_KEY`、`POSTGRES_PASSWORD`、`FIRST_SUPERUSER_PASSWORD` 等），能跑通 `docker compose up` 和前后端。

### 2. 迁移后端业务

**2.1 目录与包名**

- Template 后端包名为 `app`（如 `from app.core.config import settings`）。
- 当前是 `backend`（如 `from backend.services import workflow`）。
- 迁移时：在 template 的 `backend/app/` 下新增/合并内容，**所有原 `backend.xxx` 改为 `app.xxx`**。

**2.2 要迁入的内容**

| 当前 wisdomprompt1 | 迁入到 template 的位置 |
|--------------------|-------------------------|
| `backend/services/`（agent, workflow, search, embedding, vector_store, content_fetch） | `backend/app/services/`（新建目录，或与现有 `app/` 下逻辑合并） |
| `backend/prompts/`（query_decompose.txt 等） | `backend/app/prompts/`（template 已有 `prompts/` 可复用或新建） |
| `backend/api/endpoints/workflow.py` | `backend/app/api/routes/workflow.py`（或 `backend/app/api/routes/workflow/` 多文件） |
| `backend/models/schemas.py` 中与 workflow 相关的 Pydantic 模型 | `backend/app/models.py` 末尾或单独 `app/schemas/workflow.py` |
| `backend/core/config.py` 中的 LLM/Embedding/Search 等配置 | 合并进 `backend/app/core/config.py`（Settings 里加字段） |

**2.3 配置合并**

在 template 的 `app/core/config.py` 中增加当前项目用到的环境变量，例如：

- `LLM_PROVIDER`, `OPENAI_API_KEY`, `LLM_MODEL_ID`
- `GEMINI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`
- `TOP_K`, `MIN_SIMILARITY_SCORE`
- `SEARCH_SOURCE`, `BRAVE_API_KEY`, `EXA_API_KEY`, `SERPER_API_KEY`
- `JINA_READER_ENABLED`, `JINA_DAILY_LIMIT_*`
- （若暂时不用 PostgreSQL 做 RAG）可保留 `DATABASE_URL` 或 SQLite 等

**2.4 依赖**

把当前 `backend/requirements.txt` 里用到的包合并进 template 的 `backend/pyproject.toml`（或 requirements），例如：

- `openai`, `exa-py`, `httpx`, `duckdb`（若 vector_store 用 DuckDB）等。

**2.5 路由注册**

在 template 的 `backend/app/api/main.py` 里：

```python
from app.api.routes import items, login, private, users, utils, workflow

api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
```

**2.6 SSE 与导入**

- Workflow 的 `/workflow/stream` 继续返回 `StreamingResponse`，无需为 SSE 单独生成 OpenAPI client。
- 所有原 `from backend.xxx` 改为 `from app.xxx`；原 `get_settings()` 若在 template 里是 `settings = Settings()`，可统一用 `from app.core.config import settings`。

### 3. 迁移前端“产品页”

**3.1 页面与路由**

- Template 使用 **TanStack Router**，路由在 `frontend/src/routes/`。
- 把当前 `frontend/src/pages/AppPage.tsx` 迁到 template 的某一路由下，例如：
  - `frontend/src/routes/_layout/app.tsx`（需登录的 layout 下），或
  - `frontend/src/routes/app.tsx`（若希望不强制登录）。

**3.2 API 调用**

- 当前 AppPage 用 `fetch(WORKFLOW_DECOMPOSE)` 和 `fetch(WORKFLOW_STREAM)`。
- 迁移后：
  - **方式 1（最快）**：继续用 `fetch`，仅把 `API_BASE` 改为 template 的前端环境变量（如 `import.meta.env.VITE_API_URL` 或你定义的 `VITE_API_BASE_URL`），并加上鉴权：在 header 里带 `Authorization: Bearer <token>`（token 从 localStorage 或 useAuth 取）。
  - **方式 2（可选）**：在 OpenAPI 里描述 `/workflow/decompose` 与 `/workflow/stream`（stream 可标为非标准或仅文档），用 `@hey-api/openapi-ts` 生成 client，再用生成的 service 替代 fetch（SSE 仍可能需手写 EventSource/fetch + stream）。

**3.3 鉴权**

- 若 workflow 接口需要登录：在 template 后端给 `workflow` 路由加 `Depends(get_current_user)`（或你定义的依赖）；前端在请求头带 token。
- 若暂时不做鉴权：可先不挂 `CurrentUser`，和当前行为一致。

**3.4 UI**

- 当前 AppPage 是朴素 HTML + Tailwind 风格；template 使用 shadcn/ui。
- 迁移时可以先保留现有样式，仅把页面放进 template 的 layout（如 sidebar + 主内容区），再逐步把按钮、输入框等换成 shadcn 组件。

### 4. 可选：Docker 与 OpenAPI

- **Docker**：template 已有 `compose.yml`；若你的服务需要额外环境变量（如 `OPENAI_API_KEY`、`BRAVE_API_KEY`），在 `backend` 的 `environment` 或 `.env` 里加上即可。
- **OpenAPI**：若希望前端用生成 client 调用 decompose（非 stream），可在 FastAPI 中保证 `/api/v1/workflow/decompose` 被 OpenAPI 描述；stream 接口可保留为“仅文档”或不在 client 中调用，继续用 fetch + ReadableStream。

---

## 迁移检查清单

- [ ] 以 template 为基底能本地/ Docker 跑通登录与现有 API。
- [ ] 后端：`app/services/`、`app/prompts/`、`app/api/routes/workflow.py` 就位，且所有 import 为 `app.xxx`。
- [ ] 后端：`app/core/config.py` 含 LLM/Embedding/Search 等配置。
- [ ] 后端：`api_router` 已挂载 `/workflow`。
- [ ] 前端：AppPage 迁入 `routes/_layout/app.tsx`（或你选的路由），请求指向新 API 并带 token（若需登录）。
- [ ] 环境变量：`.env` 与 Docker 中已配置所有 API Key 与可选 DB。

---

## 小结

- **可以从当前仓库迁移过去**：推荐以 full-stack-fastapi-template 为基底，把 wisdomprompt1 的 workflow 后端与产品页前端迁进去。
- 主要工作：**包名从 `backend` 改为 `app`**、**配置与依赖合并**、**前端路由与请求基地址/鉴权**；SSE 流式接口可继续用 fetch，不必强行用 OpenAPI client。
- 按上述步骤做完后，你既保留 template 的认证、用户、DB、Docker、CI，又保留现有的 RAG 工作流与产品页逻辑。

如果你希望，我可以按「思路 A」在仓库里给出具体改动的文件列表和每步的 diff 式修改说明（不直接改 template 仓库，只在你当前 wisdomprompt1 里生成一份“迁移后的目标结构”说明或脚本）。
