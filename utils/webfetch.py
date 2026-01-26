import re
from typing import Dict, Literal, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import html2text


class WebFetchError(Exception):
    pass


GITHUB_REPO_RE = re.compile(r"https?://github\.com/([^/]+)/([^/]+)/?$")
MAX_SIZE_BYTES = 5 * 1024 * 1024


def fetch(
    url: str,
    format: Literal["markdown", "text", "html"] = "markdown",
    timeout: int = 30,
    smart: bool = True,
    return_meta: bool = False,
) -> str | Dict[str, str]:
    """Fetch a URL and return content (optionally with metadata)."""
    if not url.startswith("http://") and not url.startswith("https://"):
        raise WebFetchError("URL must start with http:// or https://")
    parsed = urlparse(url)
    if not parsed.netloc:
        raise WebFetchError("Invalid URL")

    final_url = _maybe_github_readme(url, format) if smart else url
    response = requests.get(final_url, timeout=timeout)
    response.raise_for_status()

    if len(response.content) > MAX_SIZE_BYTES:
        raise WebFetchError("Response too large")

    content_type = response.headers.get("content-type", "text/plain")
    content = _format_content(response.text, content_type, format)

    if return_meta:
        return {
            "content": content,
            "url": final_url,
            "original_url": url,
            "content_type": content_type,
            "format": format,
            "size": str(len(response.text)),
        }

    return content


def fetch_many(urls: list[str], **kwargs: object) -> list[Dict[str, str]]:
    results: list[Dict[str, str]] = []
    for url in urls:
        try:
            content = fetch(url, **kwargs)
            results.append({"url": url, "content": str(content), "success": "true"})
        except Exception as exc:
            results.append({"url": url, "error": str(exc), "success": "false"})
    return results


def _maybe_github_readme(url: str, format: str) -> str:
    if format not in {"markdown", "text"}:
        return url
    match = GITHUB_REPO_RE.match(url)
    if not match:
        return url
    user, repo = match.groups()
    for branch in ("main", "master"):
        raw_url = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/README.md"
        try:
            head = requests.head(raw_url, timeout=5)
            if head.status_code == 200:
                return raw_url
        except requests.RequestException:
            continue
    return url


def _format_content(content: str, content_type: str, format: str) -> str:
    is_html = "text/html" in content_type.lower()
    if format == "html" or not is_html:
        return content

    soup = BeautifulSoup(content, "lxml")
    for tag in soup(["script", "style", "noscript", "iframe", "object", "embed"]):
        tag.decompose()

    if format == "text":
        return " ".join(soup.get_text(separator=" ").split())

    converter = html2text.HTML2Text()
    converter.ignore_images = False
    converter.ignore_links = False
    converter.body_width = 0
    return converter.handle(str(soup))
