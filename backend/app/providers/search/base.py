from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    title: str | None
    content: str
    url: str | None
    provider: str
    meta: dict | None = None


class SearchProvider:
    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        raise NotImplementedError
