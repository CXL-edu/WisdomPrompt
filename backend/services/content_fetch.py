"""Content fetch: webfetch first with retry, then Readability (Mozilla), then Jina Reader fallback with daily limit."""
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

# Readability + html2text (optional: used when webfetch succeeds but we want article-only, or as fallback before Jina)
def _readability_available() -> bool:
    try:
        from readability import Document  # noqa: F401
        import html2text  # noqa: F401
        return True
    except ImportError:
        return False

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


# 拉取超时：过大会在 403/5xx 时卡很久
_WEBFETCH_TIMEOUT = 15.0
_JINA_TIMEOUT = 20.0

# Readability 结果过短或含常见错误文案时，回退到旧 webfetch
_READABILITY_MIN_LEN = 150
_READABILITY_BAD_PHRASES = ("can't perform that action", "you can't perform", "this page could not be found")


def _is_github_blob_url(url: str) -> bool:
    return "github.com" in url and "/blob/" in url


def _github_blob_to_raw_url(url: str) -> Optional[str]:
    """github.com/owner/repo/blob/branch/path -> raw.githubusercontent.com/owner/repo/branch/path"""
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        if p.netloc not in ("github.com", "www.github.com"):
            return None
        parts = p.path.strip("/").split("/")
        if len(parts) >= 5 and parts[2] == "blob":
            owner, repo, _, branch, *path = parts
            raw_path = "/".join([owner, repo, branch] + path)
            return f"https://raw.githubusercontent.com/{raw_path}"
    except Exception:
        pass
    return None


async def _github_raw_fetch(url: str) -> tuple[Optional[str], Optional[str]]:
    """GitHub blob URL 时直接拉 raw 文件内容。返回 (content, error)。"""
    raw_url = _github_blob_to_raw_url(url)
    if not raw_url:
        return None, None
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_WEBFETCH_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = await client.get(raw_url)
            resp.raise_for_status()
            text = resp.text
            return (text[: _MAX_BODY] if len(text) > _MAX_BODY else text), None
    except Exception as e:
        return None, str(e)


def _readability_result_ok(content: str) -> bool:
    """Readability 抽到的内容是否可信：过短或含错误文案则用旧 webfetch。"""
    if not content or len(content.strip()) < _READABILITY_MIN_LEN:
        return False
    lower = content.lower()
    for phrase in _READABILITY_BAD_PHRASES:
        if phrase in lower:
            return False
    return True


async def _webfetch_once(url: str) -> tuple[Optional[str], Optional[str]]:
    """Fetch URL and return (content_text, error_message)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_WEBFETCH_TIMEOUT,
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


async def _webfetch_raw(url: str) -> tuple[Optional[str], Optional[str]]:
    """Fetch URL and return (raw_html, error_message). Only returns HTML for text/html; else (None, err)."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_WEBFETCH_TIMEOUT,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            ct = resp.headers.get("content-type", "")
            if "text/html" not in ct:
                return None, "content-type is not text/html"
            return resp.text, None
    except Exception as e:
        return None, str(e)


def _readability_to_markdown(html: str) -> Optional[str]:
    """Extract main article with Mozilla Readability and convert to Markdown. Returns None on failure."""
    try:
        from readability import Document
        import html2text
    except ImportError:
        return None
    try:
        doc = Document(html if isinstance(html, str) else html.decode("utf-8", errors="replace"))
        summary_html = doc.summary()
        if not summary_html or not summary_html.strip():
            return None
        h2t = html2text.HTML2Text()
        h2t.ignore_links = False
        h2t.body_width = 0
        text = h2t.handle(summary_html)
        text = _WHITESPACE.sub(" ", text).strip()
        return text[:_MAX_BODY] if len(text) > _MAX_BODY else text
    except Exception:
        return None


async def _jina_read(url: str) -> tuple[Optional[str], Optional[str]]:
    """Jina Reader GET; returns (content, error).
    不使用 API Key，走无 Key 模式：0 token 消耗，限 20 RPM。
    """
    reader_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "application/json",
        # 不传 Authorization，不扣 Jina token
        "X-Token-Budget": "16000",  # 限制单次返回长度，避免超长页
    }
    try:
        async with httpx.AsyncClient(timeout=_JINA_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(reader_url, headers=headers)
            resp.raise_for_status()
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        content = data.get("content", "") if isinstance(data, dict) else resp.text
        return (content or resp.text), None
    except Exception as e:
        return None, str(e)


async def fetch_content(url: str) -> dict:
    """
    Fetch page content: GitHub raw（blob 链接）> raw HTML + Readability/webfetch > webfetch 重试 > Jina。
    Returns {"content": str, "url": str, "source": "webfetch"|"readability"|"jina"} or raises.
    """
    settings = get_settings()

    # GitHub blob 链接直接拉 raw 文件，避免 Readability 抽到错误区域
    if _is_github_blob_url(url):
        content, err = await _github_raw_fetch(url)
        if content:
            return {"content": content, "url": url, "source": "webfetch"}

    # 一次 raw 拉取：优先 Readability，结果不可信时回退到旧 webfetch
    if _readability_available():
        raw_html, _ = await _webfetch_raw(url)
        if raw_html:
            content = _readability_to_markdown(raw_html)
            if content and _readability_result_ok(content):
                return {"content": content, "url": url, "source": "readability"}
            content = _html_to_text(raw_html)
            if content:
                return {"content": content, "url": url, "source": "webfetch"}

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
