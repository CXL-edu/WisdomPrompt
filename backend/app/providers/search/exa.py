from __future__ import annotations

import httpx

from app.providers.search.base import SearchProvider, SearchResult


class ExaProvider(SearchProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        # API docs vary by plan; keep wrapper minimal and provenance-rich.
        url = "https://api.exa.ai/search"
        headers = {"x-api-key": self._api_key, "content-type": "application/json"}
        payload = {
            "query": query,
            "numResults": limit,
            "contents": {"text": True},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        out: list[SearchResult] = []
        for item in data.get("results", [])[:limit]:
            out.append(
                SearchResult(
                    title=item.get("title"),
                    content=(item.get("text") or item.get("snippet") or "").strip(),
                    url=item.get("url"),
                    provider="exa",
                    meta={"exa_id": item.get("id")},
                )
            )
        return [r for r in out if r.content]
