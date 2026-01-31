#!/usr/bin/env python3
"""
分别用 3 种方式请求指定 URL，打印是否成功及耗时。
从项目根运行: PYTHONPATH=. .venv/bin/python backend/scripts/bench_content_fetch.py [URL]
"""
import asyncio
import os
import sys
import time

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(_root)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://zhuanlan.zhihu.com/p/639453312"
    print(f"URL: {url}\n")

    from backend.services import content_fetch

    # 1. webfetch（_webfetch_once）
    print("1. webfetch (_webfetch_once)")
    t0 = time.perf_counter()
    content, err = await content_fetch._webfetch_once(url)
    elapsed = time.perf_counter() - t0
    ok = content is not None
    print(f"   成功: {ok}  耗时: {elapsed:.2f}s")
    if err:
        print(f"   错误: {err[:120]}")
    if ok and content:
        print(f"   内容长度: {len(content)}  前80字: {content[:80].replace(chr(10), ' ')}...")
    print()

    # 2. readability（_webfetch_raw + _readability_to_markdown）
    print("2. readability (_webfetch_raw + _readability_to_markdown)")
    t0 = time.perf_counter()
    raw_html, raw_err = await content_fetch._webfetch_raw(url)
    fetch_elapsed = time.perf_counter() - t0
    if raw_html:
        md = content_fetch._readability_to_markdown(raw_html)
        total_elapsed = time.perf_counter() - t0
        ok = bool(md)
        print(f"   成功: {ok}  拉取耗时: {fetch_elapsed:.2f}s  总耗时: {total_elapsed:.2f}s")
        if ok:
            print(f"   内容长度: {len(md)}  前80字: {md[:80].replace(chr(10), ' ')}...")
    else:
        total_elapsed = time.perf_counter() - t0
        print(f"   成功: False  耗时: {total_elapsed:.2f}s")
        print(f"   错误: {raw_err[:120] if raw_err else '无 HTML'}")
    print()

    # 3. Jina Reader（_jina_read）
    print("3. Jina Reader (_jina_read)")
    t0 = time.perf_counter()
    content, jina_err = await content_fetch._jina_read(url)
    elapsed = time.perf_counter() - t0
    ok = content is not None
    print(f"   成功: {ok}  耗时: {elapsed:.2f}s")
    if jina_err:
        print(f"   错误: {jina_err[:120]}")
    if ok and content:
        print(f"   内容长度: {len(content)}  前80字: {content[:80].replace(chr(10), ' ')}...")
    print()

    print("--- 说明 ---")
    print("卡很久原因：知乎等站对直连/Jina 返回 403 或超时，Jina 单次 timeout 约 20s，webfetch 约 15s。")
    print("fetch_content 顺序：_webfetch_raw -> _webfetch_once -> sleep(2s) -> _webfetch_once -> _jina_read，")
    print("全失败时最坏约 15+15+2+15+20 ≈ 67s。已缩短 timeout 以减少等待。")


if __name__ == "__main__":
    asyncio.run(main())
