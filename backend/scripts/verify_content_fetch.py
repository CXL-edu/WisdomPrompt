#!/usr/bin/env python3
"""
验证 content_fetch 链路：Readability / webfetch / Jina。
从项目根运行: PYTHONPATH=. .venv/bin/python backend/scripts/verify_content_fetch.py [URL]
"""
import asyncio
import os
import sys

# 确保从项目根加载 .env
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(_root)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://zhuanlan.zhihu.com/p/639453312"
    print(f"URL: {url}\n")

    from backend.services import content_fetch

    try:
        out = await content_fetch.fetch_content(url)
        source = out.get("source", "")
        content = out.get("content", "")
        print(f"source={source} content_len={len(content)}")
        print(f"content 前 200 字: {content[:200].replace(chr(10), ' ')}...")
        assert source in ("readability", "webfetch", "jina"), f"unexpected source: {source}"
        assert content, "content 为空"
        print("\n验证通过：content_fetch 可跑通（Readability / webfetch / Jina）。")
    except Exception as e:
        print(f"失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
