#!/usr/bin/env python3
"""
验证后端检索链路：分解 -> 向量检索 -> 联网搜索 -> 正文拉取 -> 合并结果。
从项目根运行: PYTHONPATH=. python backend/scripts/verify_retrieval.py "你的问题"
"""
import asyncio
import json
import os
import sys

# 确保从项目根加载 .env
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "Python 如何读取环境变量"
    print(f"Query: {query}\n")

    from backend.core.config import get_settings
    from backend.services import agent, embedding, search as search_service, vector_store, content_fetch

    settings = get_settings()
    print("1. 配置检查")
    print(f"   SEARCH_SOURCE={settings.SEARCH_SOURCE}, BRAVE_API_KEY={'*' if settings.BRAVE_API_KEY else '(空)'}, SERPER_API_KEY={'*' if settings.SERPER_API_KEY else '(空)'}")
    print(f"   TOP_K={settings.TOP_K}, MIN_SIMILARITY_SCORE={settings.MIN_SIMILARITY_SCORE}\n")

    print("2. 分解子任务")
    sub_tasks = await agent.decompose_query(query)
    print(f"   子任务数: {len(sub_tasks)}")
    for i, st in enumerate(sub_tasks, 1):
        print(f"   - {i}: {st[:80]}")
    if not sub_tasks:
        print("   无子任务，退出")
        return
    st = sub_tasks[0]
    print()

    print("3. 向量检索（首个子任务）")
    vector_hits = []
    try:
        store = vector_store.get_vector_store()
        st_embed = await embedding.embed_text(st)
        vector_hits = await store.search(st_embed, top_k=settings.TOP_K, min_similarity=settings.MIN_SIMILARITY_SCORE)
    except Exception as e:
        print(f"   (向量检索跳过，如 DB 被占用可忽略): {e}")
    print(f"   命中数: {len(vector_hits)}")
    for i, h in enumerate(vector_hits[:3], 1):
        content_preview = (h.get("content") or "")[:150].replace("\n", " ")
        print(f"   - [{i}] sim={h.get('similarity')} url={h.get('url') or 'N/A'} content_preview={content_preview}...")
    print()

    print("4. 联网搜索（首个子任务）")
    web_results = await search_service.search_web(st, count=5)
    print(f"   搜索结果数: {len(web_results)}")
    for i, w in enumerate(web_results[:3], 1):
        print(f"   - [{i}] title={w.get('title', '')[:50]} url={w.get('url', '')[:60]}")
    if not web_results:
        print("   (无结果：请检查 SEARCH_SOURCE 及对应 API Key)")
    print()

    print("5. 正文拉取（第一个搜索结果的 URL）")
    if web_results:
        url = web_results[0].get("url") or ""
        if url:
            try:
                fetched = await content_fetch.fetch_content(url)
                content = fetched.get("content", "")
                source = fetched.get("source", "")
                print(f"   成功 source={source} content_len={len(content)}")
                print(f"   content 前 300 字: {content[:300].replace(chr(10), ' ')}...")
            except Exception as e:
                print(f"   失败: {e}")
        else:
            print("   URL 为空")
    else:
        print("   无搜索结果可拉取")
    print()

    print("6. 合并后用于整理的 content 长度（模拟 workflow）")
    seen = set()
    combined_parts = []
    for h in (vector_hits or []):
        u = h.get("url") or ""
        if u:
            seen.add(u)
        c = h.get("content") or ""
        if c:
            combined_parts.append(c[:4000])
    for w in web_results[:3]:
        u = (w.get("url") or "").strip()
        if not u or u in seen:
            continue
        try:
            fetched = await content_fetch.fetch_content(u)
            content = fetched.get("content", "")
            if content:
                combined_parts.append(content[:4000])
                seen.add(u)
        except Exception:
            snippet = (w.get("title") or "") + "\n" + (w.get("description") or "")
            if snippet.strip():
                combined_parts.append(snippet[:2000])
    combined = "\n\n".join(combined_parts)
    print(f"   合并后总字符数: {len(combined)} (应 >0 才能得到相关整理结果)")
    if combined:
        print("   验证通过：检索与拉取链路可跑通。")
    else:
        print("   警告：合并内容为空，整理步骤将收到 'No content.'。")


if __name__ == "__main__":
    asyncio.run(main())
