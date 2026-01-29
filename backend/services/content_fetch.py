"""Content fetch: webfetch first with retry, then Jina Reader fallback with daily limit."""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

# Simple HTML text extraction (no bs4 dependency)
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_SCRIPT_STYLE = re.compile(r"<(?:script|style|noscript)[^>]*>.*?</(?:script|style|noscript)>", re.DOTALL | re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")
_MAX_BODY = 500_000  # ~500k chars


def _html_to_text(html: str) -> str:
    s = _SCRIPT_STYLE.sub(" ", html)
    s = _TAGS.sub(" ", s)
    s = _WHITESPACE.sub(" ", s).strip()
    return s[: _MAX_BODY] if len(s) > _MAX_BODY else s


def _jina_usage_path() -> Path:
    base = os.environ.get("WISDOMPROMPT_DATA_DIR")
    if base:
        return Path(base) / "jina_usage.json"
    return Path(__file__).resolve().parents[2] / "data" / "jina_usage.json"


def _read_jina_usage() -> tuple[str, int, int]:
    p = _jina_usage_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    today = date.isoformat(date.today())
    if not p.exists():
        return today, 0, 0
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        d = data.get("date", "")
        if d != today:
            return today, 0, 0
        return today, data.get("count", 0), data.get("tokens", 0)
    except Exception:
        return today, 0, 0


def _write_jina_usage(day: str, count: int, tokens: int) -> None:
    p = _jina_usage_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"date": day, "count": count, "tokens": tokens}, f, indent=0)


def _estimate_tokens(text: str) -> int:
    return max(0, (len(text) + 3) // 4)


async def _webfetch_once(url: str) -> tuple[Optional[str], Optional[str]]:
    """Fetch URL and return (content_text, error_message)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "text/html" in ct:
                return _html_to_text(resp.text), None
            return resp.text[:_MAX_BODY], None
    except Exception as e:
        return None, str(e)


async def _jina_read(url: str) -> tuple[Optional[str], Optional[str]]:
    """Jina Reader GET; returns (content, error)."""
    # r.jina.ai/{url}
    reader_url = f"https://r.jina.ai/{url}"
    headers = {"Accept": "application/json", "X-With-Generated-Alt": "true"}
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(reader_url, headers=headers)
            resp.raise_for_status()
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        content = data.get("content", "") if isinstance(data, dict) else resp.text
        return (content or resp.text), None
    except Exception as e:
        return None, str(e)


async def fetch_content(url: str) -> dict:
    """
    Fetch page content: webfetch with one retry (delay 2s), then Jina if enabled and under limit.
    Returns {"content": str, "url": str, "source": "webfetch"|"jina"} or raises.
    """
    settings = get_settings()
    content, err = await _webfetch_once(url)
    if content is not None:
        return {"content": content, "url": url, "source": "webfetch"}
    logger.info("webfetch_failed_first", url=url, error=err)
    await asyncio.sleep(2)
    content, err = await _webfetch_once(url)
    if content is not None:
        return {"content": content, "url": url, "source": "webfetch"}
    logger.info("webfetch_failed_retry", url=url, error=err)
    if not settings.JINA_READER_ENABLED:
        raise RuntimeError(f"Content fetch failed (webfetch): {err}")
    day, count, tokens = _read_jina_usage()
    if count >= settings.JINA_DAILY_LIMIT_COUNT:
        raise RuntimeError("Jina daily request limit reached")
    content, jina_err = await _jina_read(url)
    if content is None:
        raise RuntimeError(f"Jina fetch failed: {jina_err}")
    new_tokens = tokens + _estimate_tokens(content)
    if new_tokens > settings.JINA_DAILY_LIMIT_TOKENS:
        raise RuntimeError("Jina daily token limit reached")
    _write_jina_usage(day, count + 1, new_tokens)
    return {"content": content, "url": url, "source": "jina"}
