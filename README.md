# WisdomPrompt

联网搜索、知识库检索与提示词生成，一站式智能问答。

## 技术栈

- **前端**：Vite、React、Tailwind CSS、React Router、react-markdown；路由 `/`、`/about`、`/app`、`/docs`
- **后端**：FastAPI、DuckDB + VSS、OpenAI LLM、Gemini Embedding；产品页流式 SSE
- **搜索**：Brave / Exa / Serper（由 `.env` 的 `SEARCH_SOURCE` 选择；无 `BRAVE_API_KEY` 时自动用 Serper）；正文拉取：webfetch + Jina Reader 备用

## 快速开始

### 1. 环境

- Python 3.10+
- Node 18+

### 2. 后端

```bash
# 项目根目录
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

# 补全 .env：OPENAI_API_KEY、GEMINI_API_KEY、可选 BRAVE_API_KEY 等（见 .env 内注释）

# 启动（从项目根目录运行，以便加载 .env）
PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- 健康检查：`GET http://localhost:8000/api/v1/health`
- 产品页流式：`POST http://localhost:8000/api/v1/workflow/stream`，body: `{"query": "你的问题", "from_step": 1}`

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

- 默认：`http://localhost:5173`
- 产品页：`/app`，输入问题后提交，将流式展示子任务、检索、整理与最终答案；支持 Markdown 渲染与一键复制

### 4. 联调

- 后端 CORS 已允许 `http://localhost:5173`
- 前端默认请求 `http://localhost:8000`，可通过 `frontend/.env` 设置 `VITE_API_BASE_URL`

### 5. 子路径部署

挂到主站子路径 `/wisdom-prompt` 时见主站 **DEPLOY_NGINX_WISDOMPROMPT.md**；前端在 `frontend/.env` 设 `VITE_API_BASE_URL=https://你的域名/wisdom-prompt`。

### 6. PM2 管理（生产）

前置：`npm i -g pm2`，后端 venv + 依赖 + `.env`，前端 `cd frontend && npm run build`。

```bash
pm2 start ecosystem.config.cjs   # 启动
pm2 stop ecosystem.config.cjs    # 停止
pm2 restart ecosystem.config.cjs
pm2 logs
```

## 本地安全检查（commit / push 前）

本项目通过 **仓库内 Git 钩子**（`.githooks`）统一做提交与推送前检查：

- **pre-commit**：pre-commit 框架（YAML、尾随空格、合并冲突等）
- **pre-push**：gitleaks 全仓库扫描，避免密钥、Token、密码等敏感信息被推送

**克隆或拉取本仓库后，只需在本机执行一次：**

```bash
./scripts/setup-git-hooks.sh
```

（或手动执行：`git config core.hooksPath .githooks`）

建议再安装 pre-commit 与 gitleaks，以便检查生效：

```bash
pip install pre-commit
pre-commit install-hooks
# gitleaks 请按官方文档安装：https://github.com/gitleaks/gitleaks
```

之后每次 `git commit` / `git push` 都会自动跑上述检查；未安装时对应钩子会跳过并提示。

## 配置说明

- **.env**（项目根）：`SEARCH_SOURCE`（brave/exa/serper，建议 serper 或配置好 `BRAVE_API_KEY`）、`SERPER_API_KEY`、`JINA_READER_ENABLED`、`LLM_MODEL_ID`、`OPENAI_API_KEY`、`GEMINI_API_KEY` 等
- 向量库与 Jina 用量文件：默认在 `data/` 下（`vectors.duckdb`、`jina_usage.json`）。若出现 DuckDB 文件被占用（如 IDE 锁文件），可设置环境变量 `WISDOMPROMPT_DATA_DIR=/tmp/wisdomprompt_data` 让后端使用独立目录，或关闭占用该文件的其他进程。

## 项目结构

- `backend/`：FastAPI 应用、config、prompts、services（agent、embedding、vector_store、search、content_fetch、workflow）、api
- `frontend/`：Vite + React、四路由页面、产品页 SSE 消费与 Markdown 展示
- `origin_idea_copy.md`：产品与研发说明
- `backend/scripts/verify_retrieval.py`：验证检索链路（分解→向量→联网→拉取→合并），`PYTHONPATH=. python backend/scripts/verify_retrieval.py "你的问题"`
