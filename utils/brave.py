import os
from typing import Any, Dict, Optional

import requests

BASE_URL = "https://api.search.brave.com/res/v1"


def search(
    query: str,
    api_key: Optional[str] = None,
    count: int = 10,
    search_lang: str = "zh-hans",
    country: str = "US",
    safesearch: str = "moderate",
    freshness: str = "py",
    timeout: int = 30,
) -> Dict[str, Any]:
    token = api_key or os.getenv("BRAVE_API_KEY")
    if not token:
        raise ValueError("BRAVE_API_KEY is required")

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": token,
    }
    params = {
        "q": query,
        "count": count,
        "search_lang": search_lang,
        "country": country,
        "safesearch": safesearch,
        "freshness": freshness,
    }
    response = requests.get(
        f"{BASE_URL}/web/search",
        headers=headers,
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()
