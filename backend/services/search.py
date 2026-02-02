"""Web search: brave / exa / serper via SEARCH_SOURCE. Returns title, url, description per hit."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import TYPE_CHECKING

import httpx
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

if TYPE_CHECKING:
    from backend.core.config import Settings

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 300
_CACHE: dict[tuple[str, int], tuple[float, list[dict[str, str]]]] = {}

_COOLDOWN_SECONDS = 900


@dataclass
class _ProviderStats:
    success: int = 0
    failure: int = 0
    avg_latency: float = 0.0
    cooldown_until: float = 0.0


_PROVIDER_STATS: dict[str, _ProviderStats] = {
    "brave": _ProviderStats(),
    "serper": _ProviderStats(),
    "exa": _ProviderStats(),
}


def _now() -> float:
    return time.time()


def _cache_get(key: tuple[str, int]) -> list[dict[str, str]] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    ts, data = entry
    if _now() - ts > _CACHE_TTL_SECONDS:
        _ = _CACHE.pop(key, None)
        return None
    return data


def _cache_set(key: tuple[str, int], data: list[dict[str, str]]) -> None:
    _CACHE[key] = (_now(), data)


def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            return True
    return "429" in str(exc)


def _mark_success(provider: str, latency: float) -> None:
    stats = _PROVIDER_STATS[provider]
    stats.success += 1
    if stats.avg_latency == 0.0:
        stats.avg_latency = latency
    else:
        stats.avg_latency = stats.avg_latency * 0.7 + latency * 0.3


def _mark_failure(provider: str, rate_limited: bool) -> None:
    stats = _PROVIDER_STATS[provider]
    stats.failure += 1
    if rate_limited:
        stats.cooldown_until = max(stats.cooldown_until, _now() + _COOLDOWN_SECONDS)


def _provider_score(provider: str) -> float:
    stats = _PROVIDER_STATS[provider]
    total = stats.success + stats.failure
    success_rate = stats.success / total if total else 0.5
    latency_penalty = min(stats.avg_latency / 5.0, 1.0) if stats.avg_latency else 0.0
    return success_rate - latency_penalty


def _provider_available(provider: str, settings: "Settings") -> bool:
    stats = _PROVIDER_STATS[provider]
    if stats.cooldown_until and stats.cooldown_until > _now():
        return False
    if provider == "brave":
        return bool(settings.BRAVE_API_KEY)
    if provider == "serper":
        return bool(settings.SERPER_API_KEY)
    if provider == "exa":
        return bool(settings.EXA_API_KEY)
    return False


def _normalize_hit(title: str, url: str, description: str) -> dict[str, str]:
    return {"title": title or "", "url": url or "", "description": description or ""}


async def _search_brave(query: str, count: int, api_key: str) -> list[dict[str, str]]:
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
    return [
        _normalize_hit(r.get("title", ""), r.get("url", ""), r.get("description", ""))
        for r in results
    ]


async def _search_serper(query: str, num: int, api_key: str) -> list[dict[str, str]]:
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


def _search_exa_sync(
    query: str, num_results: int, api_key: str
) -> list[dict[str, str]]:
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
        _normalize_hit(
            getattr(r, "title", "") or "",
            getattr(r, "url", "") or "",
            getattr(r, "text", "") or getattr(r, "description", "") or "",
        )
        for r in results
    ]


async def _search_exa(query: str, count: int, api_key: str) -> list[dict[str, str]]:
    return await asyncio.to_thread(_search_exa_sync, query, count, api_key)


async def search_web(query: str, count: int = 10) -> list[dict[str, str]]:
    """Run web search using SEARCH_SOURCE (brave / exa / serper). Returns list of {title, url, description}. Fallback to serper/exa when brave key missing."""
    settings = get_settings()
    cache_key = (query, count)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    source = settings.SEARCH_SOURCE
    order = ["brave", "serper", "exa"]
    if source in order:
        order.remove(source)
        order.insert(0, source)

    candidates = [p for p in order if _provider_available(p, settings)]
    if not candidates:
        logger.warning("no_search_api_key")
        return []

    candidates.sort(key=lambda p: (-_provider_score(p), order.index(p)))

    for candidate in candidates:
        start = time.perf_counter()
        try:
            if candidate == "brave":
                out = await _search_brave(query, count, settings.BRAVE_API_KEY)
            elif candidate == "serper":
                out = await _search_serper(query, count, settings.SERPER_API_KEY)
            else:
                out = await _search_exa(query, count, settings.EXA_API_KEY)
            elapsed = time.perf_counter() - start
            if out:
                _mark_success(candidate, elapsed)
                _cache_set(cache_key, out)
                return out
            _mark_failure(candidate, False)
            logger.warning(
                "search_returned_empty", provider=candidate, query=query[:80]
            )
        except Exception as exc:
            _mark_failure(candidate, _is_rate_limit_error(exc))
            logger.warning(
                "search_failed",
                provider=candidate,
                error=str(exc)[:200],
                query=query[:80],
            )

    return []
