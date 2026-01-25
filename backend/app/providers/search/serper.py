from __future__ import annotations

import httpx

from app.providers.search.base import SearchProvider, SearchResult


class SerperProvider(SearchProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": self._api_key, "content-type": "application/json"}
        payload = {"q": query, "num": limit}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        out: list[SearchResult] = []
        for item in (data.get("organic") or [])[:limit]:
            out.append(
                SearchResult(
                    title=item.get("title"),
                    content=(item.get("snippet") or "").strip(),
                    url=item.get("link"),
                    provider="serper",
                    meta={"position": item.get("position")},
                )
            )
        return [r for r in out if r.content]
