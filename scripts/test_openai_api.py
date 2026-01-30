#!/usr/bin/env python3
"""测试当前环境能否正常调用 OpenAI API。从项目根目录运行: python scripts/test_openai_api.py"""
from pathlib import Path
import os
import sys

# 确保项目根在 path 里并加载 .env
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # 无 dotenv 则依赖环境变量

api_key = os.environ.get("OPENAI_API_KEY")
model = os.environ.get("LLM_MODEL_ID", "gpt-4o-mini")
# 测试脚本默认 30 秒超时，便于快速看到结果；可通过 OPENAI_TIMEOUT 覆盖
timeout = float(os.environ.get("OPENAI_TIMEOUT", "30"))
base_url = os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI_BASE_URL")


def main():
    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY（.env 或环境变量）")
        sys.exit(1)

    print("=== OpenAI API 连通性测试 ===")
    print(f"模型: {model}")
    print(f"超时: {timeout}s")
    if base_url:
        print(f"Base URL: {base_url}")
    else:
        print("Base URL: (默认 api.openai.com)")
    print("正在调用 chat completions...")

    try:
        from openai import OpenAI
        kwargs = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )
        text = (resp.choices[0].message.content or "").strip()
        print(f"成功. 回复: {repr(text)}")
        return 0
    except Exception as e:
        print(f"失败: {type(e).__name__}: {e}")
        if "timed out" in str(e).lower() or "timeout" in str(type(e).__name__).lower():
            print("提示: 若在国内或需代理，可在 .env 中设置 OPENAI_API_BASE 指向可用端点。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
