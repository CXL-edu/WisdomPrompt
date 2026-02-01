#!/usr/bin/env bash
# 用同一链接对比 Playwright 与 agent-browser 的打开结果
# 用法: ./scripts/compare-browser-open.sh [URL]
# 默认 URL: https://example.com

URL="${1:-https://example.com}"

echo "========== 测试链接: $URL =========="
echo ""

echo "--- 1) Playwright 打开（有头，会弹窗）---"
echo "执行: cd full-stack-fastapi-template/frontend && npx playwright open \"$URL\""
echo "（在项目 frontend 目录下运行，会启动 Chromium 并打开该链接）"
echo ""

echo "--- 2) agent-browser 打开（有头）---"
echo "执行: AGENT_BROWSER_HEADED=1 agent-browser open \"$URL\""
echo "（会启动 agent-browser 的浏览器并打开该链接）"
echo ""

echo "--- 3) 可选：无头模式下对比页面内容 ---"
echo "Playwright 获取标题: 见下方命令"
echo "agent-browser 获取标题: agent-browser open \"$URL\" && agent-browser get title"
echo ""
