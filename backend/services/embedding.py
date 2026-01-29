"""Gemini embedding service: single and batch embed with configurable model/dimension."""
from __future__ import annotations

import asyncio
from typing import List

import httpx
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

GEMINI_EMBED_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"


async def embed_text(text: str) -> List[float]:
    """Embed a single text; returns vector of length EMBEDDING_DIMENSION."""
    settings = get_settings()
    url = GEMINI_EMBED_URL_TEMPLATE.format(model=settings.EMBEDDING_MODEL)
    payload = {"content": {"parts": [{"text": text}]}}
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    data = resp.json()
    values = (data.get("embedding") or {}).get("values") or []
    if len(values) != settings.EMBEDDING_DIMENSION:
        logger.warning(
            "embedding_dimension_mismatch",
            expected=settings.EMBEDDING_DIMENSION,
            got=len(values),
        )
    return [float(x) for x in values]


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed multiple texts in one batch request when API supports it; else concurrent single requests."""
    if not texts:
        return []
    settings = get_settings()
    url = GEMINI_EMBED_URL_TEMPLATE.format(model=settings.EMBEDDING_MODEL)
    headers = {"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY}

    # Batch embed: single request with multiple contents (if supported)
    # Gemini embedContent accepts one content; for multiple we do concurrent requests
    async def one(t: str) -> List[float]:
        payload = {"content": {"parts": [{"text": t}]}}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        data = resp.json()
        values = (data.get("embedding") or {}).get("values") or []
        return [float(x) for x in values]

    results = await asyncio.gather(*[one(t) for t in texts])
    return list(results)
