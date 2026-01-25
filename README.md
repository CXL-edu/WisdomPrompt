# wisdomprompt

交互式提示/技能语义检索 + RAG 工作流。

本仓库实现了 `wisdomprompt/docs/origin_idea.md` 中的 PRD：
- 前端：Vite + React + TailwindCSS（shadcn 风格的 UI 组件）
- 后端：FastAPI + Python
- 向量存储：Milvus（或用于开发/测试的本地模拟）

## 本地开发

后端：

**方式一：使用 venv（推荐，独立虚拟环境）**

Linux/Mac:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .  # 安装当前项目为可编辑模式
uvicorn app.main:app --reload --port 8000
```

> **命令说明：**
> - `.venv\Scripts\Activate.ps1`：激活虚拟环境后，所有 `pip install` 命令都会在该虚拟环境中安装包，而不是系统 Python 或 conda 环境
> - `pip install -e .`：`-e` 表示 "editable"（可编辑模式），`.` 表示当前目录
>   - **读取 `pyproject.toml`**：pip 会读取当前目录的 `pyproject.toml` 文件
>   - **安装项目本身**：将当前项目（`wisdomprompt-backend`）安装到虚拟环境中
>   - **自动安装依赖**：同时安装 `pyproject.toml` 中 `dependencies` 列表的所有包（包括 `uvicorn[standard]`、`fastapi` 等）
>   - **可编辑模式**：代码修改会立即生效，无需重新安装
> - **安装其他包**：安装第三方包时**不需要** `-e` 参数，直接使用 `pip install 包名` 即可。`-e` 只用于安装本地开发项目

> **故障排查：如果出现 `'uvicorn' is not recognized` 错误**
> 1. **检查虚拟环境是否激活**：提示符前应该有 `(.venv)`
> 2. **重新激活虚拟环境**：
>    ```powershell
>    .venv\Scripts\Activate.ps1
>    ```
> 3. **检查依赖是否安装**：
>    ```powershell
>    pip list | findstr uvicorn
>    ```
> 4. **如果未安装，重新执行安装**：
>    ```powershell
>    pip install -e .
>    ```
> 5. **验证安装**：
>    ```powershell
>    python -m uvicorn app.main:app --reload --port 8000
>    ```
>    或者使用完整路径：
>    ```powershell
>    .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
>    ```

**方式二：使用 Conda（使用 conda 管理的 Python 环境）**

```bash
cd backend
conda create -n wisdomprompt-backend python=3.12
conda activate wisdomprompt-backend
pip install -U pip
pip install -e .
uvicorn app.main:app --reload --port 8000
```

> **环境安装位置说明：**
> - **venv 方式**：虚拟环境安装在 `projects/backend/.venv`（完整路径：`F:\project\OpenSource\WisdomPrompt\projects\backend\.venv`）
> - **conda 方式**：环境安装在 conda 的 envs 目录（通常为 `%CONDA_PREFIX%\envs\wisdomprompt-backend`）
> - **项目依赖包**：通过 `pip install -e .` 以可编辑模式安装，实际代码仍在 `backend` 目录，在虚拟环境中创建链接
> - **注意**：`python -m venv` 会创建独立的虚拟环境，即使当前在 conda 环境中运行，也会创建新的隔离环境。如果想直接使用 conda 环境，请使用方式二。

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。

## 配置

后端读取环境变量：

- `VECTOR_STORE=mock|milvus`（默认：`mock`）
- `MILVUS_URI` / `MILVUS_TOKEN`（用于 Milvus Cloud）
- `EXA_API_KEY`（可选）
- `SERPER_API_KEY`（可选）
- `GITHUB_TOKEN`（可选）
- `LLM_PROVIDER=mock|openai`（默认：`mock`）
- `OPENAI_API_KEY`（如果 `LLM_PROVIDER=openai`）

## 说明

- 模拟提供者支持在没有外部密钥的情况下运行测试/构建。
- 所有检索的内容都存储了明确的来源信息（提供者 + URL）。

## Milvus MCP

PRD 中提到了 "Milvus MCP"。如果您想要一个用于代理工具的 MCP 兼容 Milvus 边车，
请查看 `zilliztech/mcp-server-milvus`：https://github.com/zilliztech/mcp-server-milvus

当 `VECTOR_STORE=milvus` 时，此后端也可以通过 `pymilvus` 直接连接到 Milvus。
