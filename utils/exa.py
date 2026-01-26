import os
from typing import Any, Dict, List, Optional

from exa_py import Exa


def get_client(api_key: Optional[str] = None) -> Exa:
    token = api_key or os.getenv("EXA_API_KEY")
    if not token:
        raise ValueError("EXA_API_KEY is required")
    return Exa(token)


def search(
    query: str,
    num_results: int = 10,
    category: Optional[str] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = get_client(api_key)
    results = client.search(
        query,
        num_results=num_results,
        category=category,
        start_published_date=start_published_date,
        end_published_date=end_published_date,
    )
    payload: List[Dict[str, Any]] = []
    for item in results.results:
        payload.append(
            {
                "title": item.title,
                "url": item.url,
                "author": item.author,
                "published_date": str(item.published_date) if item.published_date else None,
                "text": item.text,
            }
        )
    return payload


def search_with_contents(
    query: str,
    num_results: int = 5,
    max_characters: int = 500,
    highlights: bool = True,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = get_client(api_key)
    results = client.search_and_contents(
        query,
        num_results=num_results,
        text={"max_characters": max_characters},
        highlights=highlights,
    )
    payload: List[Dict[str, Any]] = []
    for item in results.results:
        payload.append(
            {
                "title": item.title,
                "url": item.url,
                "text": item.text,
                "highlights": item.highlights,
            }
        )
    return payload
