from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class OpenAIResponse:
    text: str


class OpenAIHttpClient:
    def __init__(self, *, api_key: str, base_url: str):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def responses_text(
        self,
        *,
        model: str,
        input_text: str,
        json_schema: dict | None = None,
        schema_name: str = "output",
        strict: bool = True,
    ) -> OpenAIResponse:
        url = f"{self._base_url}/responses"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {"model": model, "input": input_text}
        if json_schema is not None:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": json_schema,
                    "strict": strict,
                }
            }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()

        # The Responses API returns output[] with content parts.
        # We join all text parts.
        out_parts: list[str] = []
        for item in data.get("output", []) or []:
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    out_parts.append(c.get("text") or "")
        return OpenAIResponse(text="".join(out_parts).strip())

    async def embeddings(self, *, model: str, input_texts: list[str]) -> list[list[float]]:
        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "input": input_texts}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        vectors: list[list[float]] = []
        for item in data.get("data", []) or []:
            vectors.append(item.get("embedding") or [])
        return vectors


def parse_json_object(text: str) -> dict:
    # Be tolerant of code fences.
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return json.loads(s)
