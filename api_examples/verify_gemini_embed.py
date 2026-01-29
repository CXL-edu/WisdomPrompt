#!/usr/bin/env python3
"""验证 Gemini API 能否将文本转为 embedding 向量。使用方式：
   GEMINI_API_KEY=你的key python scripts/verify_gemini_embed.py
   或在 .env 中设置 GEMINI_API_KEY（勿提交 .env）
"""
from __future__ import annotations

import os
import sys
import time

import httpx

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("请设置环境变量 GEMINI_API_KEY", file=sys.stderr)
        sys.exit(1)

    test_text = "什么是生命的意义？"
    payload = {
        "content": {
            "parts": [{"text": test_text}]
        }
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    t0 = time.perf_counter()
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(GEMINI_EMBED_URL, json=payload, headers=headers)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if resp.status_code != 200:
        print(f"请求失败: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    embedding = data.get("embedding") or {}
    values = embedding.get("values") or []

    print("Gemini 文本 Embedding 验证成功")
    print(f"  测试文本: {test_text}")
    print(f"  请求耗时: {elapsed_ms:.2f} ms")
    print(f"  向量维度: {len(values)}")
    print(f"  前 8 维: {values[:8]}")
    print("  ...")

    # 批量测试：多段文本一次请求，总耗时接近单段，可摊薄单段延迟
    batch_texts = [
        "什么是生命的意义？",
        "存在的目的是什么？",
        "如何烤蛋糕？",
    ]
    batch_payload = {
        "content": {
            "parts": [{"text": t} for t in batch_texts]
        }
    }
    t1 = time.perf_counter()
    with httpx.Client(timeout=30.0) as client:
        r2 = client.post(GEMINI_EMBED_URL, json=batch_payload, headers=headers)
    batch_ms = (time.perf_counter() - t1) * 1000
    if r2.status_code == 200:
        print()
        print(f"批量 embedding（{len(batch_texts)} 段）: 总耗时 {batch_ms:.2f} ms，约 {batch_ms / len(batch_texts):.0f} ms/段")

    print()
    print("说明: 单次 2–3 秒主要来自网络往返（国内访问 Google API 延迟高）。")
    print("优化: ① 尽量批量请求多段文本 ② 建索引时用 Batch API（约半价且高吞吐）③ 对延迟敏感可改用本地模型（如 sentence-transformers，约 10–50 ms/段）")
    return


if __name__ == "__main__":
    main()
