#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 优先使用项目 venv，其次 python3，再次 python（须为 3.x）
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null && python3 -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' 2>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null && python -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' 2>/dev/null; then
  PYTHON=python
else
  echo "ERROR: Python 3 required (python3 or python)." >&2
  exit 1
fi

SYS_PROMPT_PATH="$ROOT_DIR/backend/prompts/cc_subagent_sys_prompt.md"
USER_PROMPT_PATH="$ROOT_DIR/backend/prompts/cc_subagent_user_prompt.md"
AGENTS_DIR="$ROOT_DIR/.project_info_for_ai/agents"

usage() {
  cat <<'USAGE'
Usage:
  ./.project_info_for_ai/.create_agent/create_agent.sh "<user_input>"
  ./.project_info_for_ai/.create_agent/create_agent.sh --prompt-only "<user_input>"

Notes:
- Auto-selects mode: if OPENAI_API_KEY and OPENAI_API_BASE/OPENAI_BASE_URL are set, it generates Markdown.
- Otherwise it prints the full prompt for a clean, new-chat generation step.
- Optional envs: LLM_MODEL_ID, OPENAI_TIMEOUT.
USAGE
}

build_prompt() {
  local user_input="$1"
  "$PYTHON" - "$SYS_PROMPT_PATH" "$USER_PROMPT_PATH" "$user_input" <<'PY'
from pathlib import Path
import sys

sys_prompt = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
user_template = Path(sys.argv[2]).read_text(encoding="utf-8").strip()
user_input = sys.argv[3]
user_prompt = user_template.replace("{user_input}", user_input)

print(sys_prompt)
print()
print(user_prompt)
PY
}

prompt_only=0
if [[ "${1:-}" == "--prompt-only" ]]; then
  prompt_only=1
  shift
fi

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

user_input="$*"

if [[ ! -f "$SYS_PROMPT_PATH" ]]; then
  echo "ERROR: missing system prompt at $SYS_PROMPT_PATH" >&2
  exit 1
fi
if [[ ! -f "$USER_PROMPT_PATH" ]]; then
  echo "ERROR: missing user prompt at $USER_PROMPT_PATH" >&2
  exit 1
fi

mkdir -p "$AGENTS_DIR"

if [[ "$prompt_only" -eq 1 ]]; then
  build_prompt "$user_input"
  exit 0
fi

# 未设置时尝试从项目根目录 .env 加载（不覆盖已有环境变量）
if [[ -z "${OPENAI_API_KEY:-}" ]] && [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT_DIR/.env" 2>/dev/null || true
  set +a
fi

api_key="${OPENAI_API_KEY:-}"
base_url="${OPENAI_API_BASE:-${OPENAI_BASE_URL:-https://api.openai.com/v1}}"

if [[ -z "$api_key" || -z "$base_url" ]]; then
  build_prompt "$user_input"
  exit 0
fi

"$PYTHON" - <<'PY'
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("openai") else 1)
PY

if [[ $? -ne 0 ]]; then
  echo "Installing openai package..." >&2
  if ! "$PYTHON" -m pip install --quiet openai 2>/dev/null; then
    echo "WARNING: pip install openai failed, printing prompt only." >&2
    build_prompt "$user_input"
    exit 0
  fi
fi

"$PYTHON" - "$SYS_PROMPT_PATH" "$USER_PROMPT_PATH" "$user_input" "$AGENTS_DIR" <<'PY'
from pathlib import Path
import os
import re
import sys

sys_prompt = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
user_template = Path(sys.argv[2]).read_text(encoding="utf-8").strip()
user_input = sys.argv[3]
agents_dir = Path(sys.argv[4])

user_prompt = user_template.replace("{user_input}", user_input)

api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
if not api_key:
  print("ERROR: OPENAI_API_KEY must be set.", file=sys.stderr)
  sys.exit(1)

model = os.environ.get("LLM_MODEL_ID", "gpt-5.2")
try:
  timeout = float(os.environ.get("OPENAI_TIMEOUT", "60"))
except ValueError:
  timeout = 60.0

try:
  from openai import OpenAI
except Exception as exc:
  print(f"ERROR: openai package not available: {exc}", file=sys.stderr)
  sys.exit(1)

kwargs = {"api_key": api_key, "timeout": timeout}
kwargs["base_url"] = base_url.rstrip("/")

client = OpenAI(**kwargs)
resp = client.chat.completions.create(
  model=model,
  messages=[
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": user_prompt},
  ],
  max_completion_tokens=1800,
)

text = (resp.choices[0].message.content or "").strip()
if not text.startswith("---"):
  print("ERROR: response did not start with YAML frontmatter.", file=sys.stderr)
  sys.exit(1)

parts = text.split("---", 2)
if len(parts) < 3:
  print("ERROR: response missing closing frontmatter delimiter.", file=sys.stderr)
  sys.exit(1)

frontmatter = parts[1].strip().splitlines()
meta = {}
for line in frontmatter:
  if not line.strip() or ":" not in line:
    continue
  key, value = line.split(":", 1)
  meta[key.strip()] = value.strip()

identifier = meta.get("name", "")
if not identifier:
  print("ERROR: 'name' missing in frontmatter.", file=sys.stderr)
  sys.exit(1)
if not re.match(r"^[a-z0-9-]+$", identifier):
  print(f"ERROR: invalid name: {identifier!r}", file=sys.stderr)
  sys.exit(1)

out_path = agents_dir / f"{identifier}.md"
out_path.write_text(text + "\n", encoding="utf-8")
print(str(out_path))
PY
