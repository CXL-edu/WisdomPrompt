import os
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests


class JinaReader:
    """Minimal Jina reader/search wrapper."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        token = api_key or os.getenv("JINA_API_KEY")
        self.headers = {"Accept": "application/json", "X-With-Generated-Alt": "true"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.base_read = "https://r.jina.ai"
        self.base_search = "https://s.jina.ai"

    def read(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        response = requests.get(
            f"{self.base_read}/{url}",
            headers=self.headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return _parse_read_response(response, url)

    def read_post(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        response = requests.post(
            self.base_read,
            headers=self.headers,
            data={"url": url},
            timeout=timeout,
        )
        response.raise_for_status()
        return _parse_read_response(response, url)

    def search(self, query: str, timeout: int = 30) -> Dict[str, Any]:
        encoded = quote(query)
        response = requests.get(
            f"{self.base_search}/{encoded}",
            headers=self.headers,
            timeout=timeout,
        )
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            return {"query": query, "results": [{"content": response.text}]}
        return {"query": query, "results": data}


def _parse_read_response(response: requests.Response, url: str) -> Dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {"url": url, "title": None, "content": response.text}

    if isinstance(data, dict):
        return {
            "url": data.get("url", url),
            "title": data.get("title"),
            "content": data.get("content", "") or response.text,
        }

    return {"url": url, "title": None, "content": str(data)}
