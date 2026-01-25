from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.providers.search.base import SearchProvider, SearchResult


class ArxivProvider(SearchProvider):
    async def search(self, query: str, *, limit: int) -> list[SearchResult]:
        # arXiv export API returns Atom XML.
        url = "https://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": min(20, max(1, limit)),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            xml_text = r.text

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
        }
        root = ET.fromstring(xml_text)
        out: list[SearchResult] = []
        for entry in root.findall("atom:entry", ns)[:limit]:
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            entry_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
            out.append(
                SearchResult(
                    title=title,
                    content=summary,
                    url=pdf_url or entry_id,
                    provider="arxiv",
                    meta={"entry_id": entry_id, "pdf_url": pdf_url},
                )
            )
        return [r for r in out if r.content]
