"""Web search: brave / exa / serper via SEARCH_SOURCE. Returns title, url, description per hit."""
from __future__ import annotations

import asyncio
from typing import Any, List

import httpx
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)


def _normalize_hit(title: str, url: str, description: str) -> dict[str, str]:
    return {"title": title or "", "url": url or "", "description": description or ""}


async def _search_brave(query: str, count: int, api_key: str) -> List[dict[str, str]]:
    if not api_key:
        logger.warning("brave_search_no_api_key")
        return []
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": count}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=headers, params=params)
        resp.raise_for_status()
    data = resp.json()
    results = data.get("web", {}).get("results", [])
    return [_normalize_hit(r.get("title", ""), r.get("url", ""), r.get("description", "")) for r in results]


async def _search_serper(query: str, num: int, api_key: str) -> List[dict[str, str]]:
    if not api_key:
        logger.warning("serper_search_no_api_key")
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": num}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
    data = resp.json()
    results = data.get("organic", [])
    return [
        _normalize_hit(r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
        for r in results
    ]


def _search_exa_sync(query: str, num_results: int, api_key: str) -> List[dict[str, str]]:
    try:
        from exa_py import Exa
    except ImportError:
        logger.warning("exa_py_not_installed")
        return []
    if not api_key:
        logger.warning("exa_search_no_api_key")
        return []
    exa = Exa(api_key)
    resp = exa.search(query, num_results=num_results)
    results = getattr(resp, "results", []) or []
    return [
        _normalize_hit(getattr(r, "title", "") or "", getattr(r, "url", "") or "", getattr(r, "text", "") or getattr(r, "description", "") or "")
        for r in results
    ]


async def _search_exa(query: str, count: int, api_key: str) -> List[dict[str, str]]:
    return await asyncio.to_thread(_search_exa_sync, query, count, api_key)


async def search_web(query: str, count: int = 10) -> List[dict[str, str]]:
    """Run web search using SEARCH_SOURCE (brave / exa / serper). Returns list of {title, url, description}. Fallback to serper/exa when brave key missing."""
    settings = get_settings()
    source = settings.SEARCH_SOURCE
    if source == "brave" and settings.BRAVE_API_KEY:
        out = await _search_brave(query, count, settings.BRAVE_API_KEY)
        if out:
            return out
        logger.warning("brave_returned_empty", query=query[:80])
    if source == "serper" or (source == "brave" and not settings.BRAVE_API_KEY):
        return await _search_serper(query, count, settings.SERPER_API_KEY)
    if source == "exa":
        return await _search_exa(query, count, settings.EXA_API_KEY)
    if settings.SERPER_API_KEY:
        return await _search_serper(query, count, settings.SERPER_API_KEY)
    if settings.EXA_API_KEY:
        return await _search_exa(query, count, settings.EXA_API_KEY)
    logger.warning("no_search_api_key")
    return []
