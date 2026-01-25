from __future__ import annotations

import httpx

from app.providers.search.base import SearchProvider, SearchResult


class GitHubCodeSearchProvider(SearchProvider):
    def __init__(self, token: str):
        self._token = token

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        # GitHub code search: store provenance-rich snippets.
        url = "https://api.github.com/search/code"
        headers = {
            "Accept": "application/vnd.github.text-match+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        params = {"q": query, "per_page": min(50, max(1, limit))}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()

        out: list[SearchResult] = []
        for item in (data.get("items") or [])[:limit]:
            repo = (item.get("repository") or {}).get("full_name")
            path = item.get("path")
            html_url = item.get("html_url")
            matches = item.get("text_matches") or []
            snippet = "\n".join((m.get("fragment") or "") for m in matches).strip()
            if not snippet:
                snippet = f"{repo}:{path}"
            out.append(
                SearchResult(
                    title=f"{repo}:{path}",
                    content=snippet,
                    url=html_url,
                    provider="github",
                    meta={"sha": item.get("sha"), "path": path, "repo": repo},
                )
            )
        return [r for r in out if r.content]
