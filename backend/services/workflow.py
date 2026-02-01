"""Product page workflow: decompose -> retrieve -> summarize -> final answer. Yields SSE-style events."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, List, Optional

from backend.core.config import get_settings
from backend.core.logging_config import get_logger
from backend.services import agent
from backend.services import content_fetch
from backend.services import embedding
from backend.services import search as search_service
from backend.services import vector_store

logger = get_logger(__name__)


async def run_workflow(
    query: str,
    from_step: int = 1,
    cached: Optional[dict[str, Any]] = None,
) -> AsyncIterator[dict[str, Any]]:
    """
    Run the four-step workflow; yields events for SSE.
    Events: step1_sub_tasks, step2_retrieval_start, step2_retrieval_progress, step2_retrieval_done,
    step3_summary_done, step4_chunk, step4_done, error.
    """
    settings = get_settings()
    cache = cached or {}
    sub_tasks: List[str] = []
    retrieval_results: List[dict] = []
    summaries: List[tuple[str, str]] = []

    try:
        # Step 1: Decompose
        if from_step <= 1:
            sub_tasks = cache.get("sub_tasks") or []
            if not sub_tasks:
                sub_tasks = await agent.decompose_query(query)
            yield {"event": "step1_sub_tasks", "data": {"sub_tasks": sub_tasks}}
        else:
            sub_tasks = cache.get("sub_tasks") or []
            if not sub_tasks:
                yield {
                    "event": "error",
                    "data": {"message": "cached sub_tasks required when from_step > 1"},
                }
                return

        # Step 2: Retrieve (vector + web search + content fetch). Always run web search and merge so we have fresh, relevant content.
        if from_step <= 2:
            store = vector_store.get_vector_store()
            seen_urls: set[str] = set()
            for i, st in enumerate(sub_tasks):
                yield {
                    "event": "step2_retrieval_start",
                    "data": {"index": i, "sub_task": st},
                }
                st_embed = await embedding.embed_text(st)
                vector_hits = await store.search(
                    st_embed,
                    top_k=settings.TOP_K,
                    min_similarity=settings.MIN_SIMILARITY_SCORE,
                )
                hits: List[dict] = []
                progress_count = 0
                total_expected = len(vector_hits)
                for h in vector_hits:
                    url = h.get("url") or ""
                    if url:
                        seen_urls.add(url)
                    hit = {
                        "content": h.get("content", ""),
                        "url": url,
                        "source": h.get("source"),
                        "similarity": h.get("similarity"),
                    }
                    hits.append(hit)
                    progress_count += 1
                    yield {
                        "event": "step2_retrieval_progress",
                        "data": {
                            "index": i,
                            "sub_task": st,
                            "hit": hit,
                            "progress": progress_count,
                            "total": total_expected,
                        },
                    }
                logger.info(
                    "retrieval_vector_hits", sub_task=st[:60], n=len(vector_hits)
                )
                web_results = await search_service.search_web(st, count=8)
                logger.info(
                    "retrieval_web_results", sub_task=st[:60], n=len(web_results)
                )
                total_expected = len(vector_hits) + min(5, len(web_results))
                n_fetched = 0
                for w in web_results[:5]:
                    url = (w.get("url") or "").strip()
                    if not url or url in seen_urls:
                        continue
                    try:
                        fetched = await content_fetch.fetch_content(url)
                        content = fetched.get("content", "")
                        if content:
                            emb = await embedding.embed_text(content[:8000])
                            await store.add(
                                content[:12000], url, fetched.get("source", "web"), emb
                            )
                            hit = {
                                "content": content[:4000],
                                "url": url,
                                "source": fetched.get("source"),
                                "similarity": 0.0,
                            }
                            hits.append(hit)
                            seen_urls.add(url)
                            n_fetched += 1
                            progress_count += 1
                            yield {
                                "event": "step2_retrieval_progress",
                                "data": {
                                    "index": i,
                                    "sub_task": st,
                                    "hit": hit,
                                    "progress": progress_count,
                                    "total": total_expected,
                                },
                            }
                    except Exception as e:
                        logger.warning(
                            "content_fetch_failed", url=url[:80], error=str(e)
                        )
                        snippet = (
                            (w.get("title") or "") + "\n" + (w.get("description") or "")
                        )
                        if snippet.strip():
                            hit = {
                                "content": snippet[:2000],
                                "url": url,
                                "source": "search_snippet",
                                "similarity": 0.0,
                            }
                            hits.append(hit)
                            seen_urls.add(url)
                            progress_count += 1
                            yield {
                                "event": "step2_retrieval_progress",
                                "data": {
                                    "index": i,
                                    "sub_task": st,
                                    "hit": hit,
                                    "progress": progress_count,
                                    "total": total_expected,
                                },
                            }
                logger.info(
                    "retrieval_merged",
                    sub_task=st[:60],
                    n_vector=len(vector_hits),
                    n_web_fetched=n_fetched,
                    n_total=len(hits),
                )
                retrieval_results.append({"sub_task": st, "hits": hits})
                yield {
                    "event": "step2_retrieval_done",
                    "data": {"index": i, "sub_task": st, "hits": hits},
                }
        else:
            retrieval_results = list(cache.get("retrieval") or [])

        # Step 3: Summarize each sub-task
        if from_step <= 3:
            for i, res in enumerate(retrieval_results):
                st = res.get("sub_task", "")
                hits = res.get("hits", [])
                combined = "\n\n".join(
                    h.get("content", "") for h in hits if h.get("content")
                )
                summary = await agent.summarize_sub_task(st, combined or "No content.")
                summaries.append((st, summary))
                yield {
                    "event": "step3_summary_done",
                    "data": {"index": i, "sub_task": st, "summary": summary},
                }
        else:
            summaries = [
                (r.get("sub_task", ""), r.get("summary", ""))
                for r in (cache.get("summaries") or [])
            ]
            if not summaries and cache.get("summaries"):
                for s in cache["summaries"]:
                    if isinstance(s, (list, tuple)) and len(s) >= 2:
                        summaries.append((str(s[0]), str(s[1])))
                    elif isinstance(s, dict):
                        summaries.append((s.get("sub_task", ""), s.get("summary", "")))

        # Step 4: Final answer (stream)
        async for chunk in agent.stream_final_answer(query, summaries):
            yield {"event": "step4_chunk", "data": {"text": chunk}}
        yield {"event": "step4_done", "data": {}}

    except Exception as e:
        logger.exception("workflow_error", error=str(e))
        yield {"event": "error", "data": {"message": str(e)}}
