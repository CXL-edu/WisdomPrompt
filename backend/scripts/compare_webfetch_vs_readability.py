#!/usr/bin/env python3
"""
同一份 HTML 下对比：旧 webfetch（_html_to_text）vs 新 Readability（_readability_to_markdown）。
GitHub blob 链接会先显示 raw 内容（fetch_content 实际使用的方式），再显示页面 HTML 的两种提取。
从项目根运行: PYTHONPATH=. .venv/bin/python backend/scripts/compare_webfetch_vs_readability.py [URL]
"""
import asyncio
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(_root)


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(f"URL: {url}\n")

    from backend.services import content_fetch

    is_github_blob = content_fetch._is_github_blob_url(url)
    raw_content = None
    if is_github_blob:
        raw_content, _ = await content_fetch._github_raw_fetch(url)

    # 0. GitHub raw（仅 blob 链接有；fetch_content 实际会用此）
    if raw_content:
        print("=" * 60)
        print("0. GitHub raw（fetch_content 对 blob 链接实际使用）")
        print("   做法: blob 转 raw.githubusercontent.com 拉取文件原文")
        print(f"   结果长度: {len(raw_content)} 字符")
        print("   预览（前 400 字）:")
        print("-" * 40)
        print(raw_content[:])
        print("-" * 40)
        print()

    print("同一份页面 HTML，两种提取方式对比：\n")

    # 拉取页面 HTML（GitHub 易 429，失败则重试一次）
    raw_html, err = await content_fetch._webfetch_raw(url)
    if not raw_html and is_github_blob:
        await asyncio.sleep(3)
        raw_html, err = await content_fetch._webfetch_raw(url)
    if not raw_html:
        print(f"页面 HTML 拉取失败: {err}")
        if is_github_blob and raw_content:
            print("（上方的 GitHub raw 为实际使用结果；两种方法需页面 HTML 才能对比，可稍后重试）")
        else:
            sys.exit(1)
        return
    print(f"原始页面 HTML 长度: {len(raw_html)} 字符\n")

    # 1. 旧 webfetch：_html_to_text（去 script/style、去标签、压空白）
    old_text = content_fetch._html_to_text(raw_html)
    print("=" * 60)
    print("1. 旧 webfetch（_html_to_text）")
    print("   做法: 去掉 script/style/noscript → 去掉所有标签 → 合并空白")
    print(f"   结果长度: {len(old_text)} 字符")
    print("   预览（前 400 字）:")
    print("-" * 40)
    print(old_text[:])
    print("-" * 40)
    print()

    # 2. 新 Readability：正文抽取 + html2text → Markdown
    new_md = content_fetch._readability_to_markdown(raw_html)
    if new_md is None:
        new_md = "(Readability 未提取到正文)"
    print("=" * 60)
    print("2. 新 Readability（_readability_to_markdown）")
    print("   做法: Mozilla Readability 抽正文 → html2text 转 Markdown")
    print(f"   结果长度: {len(new_md)} 字符")
    print("   预览（前 400 字）:")
    print("-" * 40)
    print(new_md[:])
    print("-" * 40)
    print()

    # 对比小结
    print("=" * 60)
    print("对比小结")
    if raw_content is not None:
        print(f"  GitHub raw 长度: {len(raw_content)}（实际使用）")
    print(f"  旧 webfetch 长度: {len(old_text)}  新 Readability 长度: {len(new_md)}")
    if is_github_blob:
        print("  GitHub blob：raw 为文件正文；旧 webfetch 多为导航；新 Readability 易抽到错误文案。")
    else:
        print("  旧: 整页文本，含导航/侧栏/页脚，无结构")
        print("  新: 仅正文，标题/列表/链接保留为 Markdown，更适合 RAG/总结")


if __name__ == "__main__":
    asyncio.run(main())
