from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import settings


@dataclass(frozen=True)
class SubtaskSuggestion:
    name: str


class LLM:
    async def split_query(self, query: str, prompt: str) -> list[SubtaskSuggestion]:
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
        raise NotImplementedError

    async def final_answer(
        self,
        *,
        query: str,
        subtasks: list[str],
        summaries: list[str],
        prompt: str,
    ) -> str:
        raise NotImplementedError


class OpenAILLM(LLM):
    def __init__(self, *, api_key: str, base_url: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

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
        tasks = obj.get("tasks") or []
        if not isinstance(tasks, list) or not tasks:
            return [SubtaskSuggestion(name=query.strip())]
        out: list[SubtaskSuggestion] = []
        for t in tasks:
            if isinstance(t, str) and t.strip():
                out.append(SubtaskSuggestion(name=t.strip()))
        return out or [SubtaskSuggestion(name=query.strip())]

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
    if settings.llm_provider != "openai":
        raise RuntimeError("LLM_PROVIDER must be 'openai'")
    if not settings.openai_api_key:
        raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
    return OpenAILLM(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.openai_model)


def parse_json_object(text: str) -> dict:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1]
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    return json.loads(s)
