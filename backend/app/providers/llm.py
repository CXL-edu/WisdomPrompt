from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast, override

from openai import AsyncOpenAI

from app.config import settings


@dataclass(frozen=True)
class SubtaskSuggestion:
    name: str


class LLM:
    async def split_query(self, query: str, prompt: str) -> list[SubtaskSuggestion]:
        _ = (query, prompt)
        raise NotImplementedError

    async def summarize_document(
        self,
        *,
        subtask: str,
        doc_title: str | None,
        doc_content: str,
        url: str | None,
        prompt: str,
    ) -> str:
        _ = (subtask, doc_title, doc_content, url, prompt)
        raise NotImplementedError

    async def final_answer(
        self,
        *,
        query: str,
        subtasks: list[str],
        summaries: list[str],
        prompt: str,
    ) -> str:
        _ = (query, subtasks, summaries, prompt)
        raise NotImplementedError


class OpenAICompatibleLLM(LLM):
    _client: AsyncOpenAI
    _model: str

    def __init__(self, *, api_key: str, base_url: str, model: str):
        # NVIDIA NIM is OpenAI-compatible; use OpenAI SDK with base_url override.
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    @override
    async def split_query(self, query: str, prompt: str) -> list[SubtaskSuggestion]:
        text = prompt.replace("{{QUERY}}", query)
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You only return valid JSON with keys: rewritten_query, tasks."},
                {"role": "user", "content": text},
            ],
        )
        content = resp.choices[0].message.content or ""
        obj = parse_json_object(content)
        tasks_obj = obj.get("tasks")
        if not isinstance(tasks_obj, list) or not tasks_obj:
            return [SubtaskSuggestion(name=query.strip())]

        tasks = cast(list[object], tasks_obj)
        out: list[SubtaskSuggestion] = []
        for t in tasks:
            if isinstance(t, str) and t.strip():
                out.append(SubtaskSuggestion(name=t.strip()))
        return out or [SubtaskSuggestion(name=query.strip())]

    @override
    async def summarize_document(
        self,
        *,
        subtask: str,
        doc_title: str | None,
        doc_content: str,
        url: str | None,
        prompt: str,
    ) -> str:
        text = (
            prompt.replace("{{SUBTASK}}", subtask)
            .replace("{{TITLE}}", doc_title or "")
            .replace("{{CONTENT}}", doc_content)
            .replace("{{URL}}", url or "")
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    @override
    async def final_answer(
        self,
        *,
        query: str,
        subtasks: list[str],
        summaries: list[str],
        prompt: str,
    ) -> str:
        text = (
            prompt.replace("{{QUERY}}", query)
            .replace("{{SUBTASKS}}", "\n".join(f"- {s}" for s in subtasks))
            .replace("{{SUMMARIES}}", "\n".join(f"- {s}" for s in summaries))
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": text},
            ],
        )
        return (resp.choices[0].message.content or "").strip()


def get_llm() -> LLM:
    if not settings.nvidia_api_key:
        raise RuntimeError("NVIDIA_API_KEY is not set")
    return OpenAICompatibleLLM(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        model=settings.nvidia_model,
    )


def parse_json_object(text: str) -> dict[str, object]:
    """Parse an LLM response into a JSON object.

    Handles markdown code fences and validates the result is a JSON object.
    """

    s = text.strip()
    if s.startswith("```"):
        # Drop the first fence line (may include language name).
        s = s.split("\n", 1)[1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]

    obj = cast(object, json.loads(s))
    if not isinstance(obj, dict):
        raise ValueError("Expected a JSON object")

    out: dict[str, object] = {}

    obj_dict = cast(dict[object, object], obj)
    for k, v in obj_dict.items():
        # Keep only string keys to avoid surprising types downstream.
        if isinstance(k, str):
            out[k] = v
    return out
