#!/bin/bash
# 将 Git hooks 指向仓库内的 .githooks，便于 clone 后统一启用提交/推送前检查
set -e
cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath .githooks
echo "已设置 core.hooksPath = .githooks，commit/push 将使用仓库内钩子。"
if command -v pre-commit &>/dev/null; then
  echo "建议再执行: pre-commit install-hooks  # 拉取 pre-commit 所需环境"
fi
