from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.providers.openai_http import OpenAIHttpClient, parse_json_object


@dataclass(frozen=True)
class SubtaskSuggestion:
    name: str


class LLM:
    def split_query(self, query: str) -> list[SubtaskSuggestion]:
        raise NotImplementedError

    def summarize_document(self, *, subtask: str, doc_title: str | None, doc_content: str) -> str:
        raise NotImplementedError

    def final_answer(self, *, query: str, subtasks: list[str], summaries: list[str]) -> str:
        raise NotImplementedError


class MockLLM(LLM):
    def split_query(self, query: str) -> list[SubtaskSuggestion]:
        # Minimal heuristic split: keep it as one task unless obvious separators exist.
        raw = query.strip()
        parts = [p.strip() for p in raw.replace("\n", ";").split(";") if p.strip()]
        if len(parts) == 0:
            return [SubtaskSuggestion(name=raw)]
        if len(parts) == 1:
            return [SubtaskSuggestion(name=parts[0])]
        return [SubtaskSuggestion(name=p) for p in parts]

    def summarize_document(self, *, subtask: str, doc_title: str | None, doc_content: str) -> str:
        title = (doc_title or "").strip()
        snippet = doc_content.strip().replace("\n", " ")
        snippet = snippet[:280] + ("..." if len(snippet) > 280 else "")
        if title:
            return f"[{subtask}] {title}: {snippet}"
        return f"[{subtask}] {snippet}"

    def final_answer(self, *, query: str, subtasks: list[str], summaries: list[str]) -> str:
        lines = [f"Query: {query}", "", "Subtasks:"]
        for s in subtasks:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("Synthesized notes:")
        for sm in summaries:
            lines.append(f"- {sm}")
        lines.append("")
        lines.append("Answer: (mock) Review the notes above and refine with real LLM providers.")
        return "\n".join(lines)


class OpenAILLM(LLM):
    def __init__(self, *, api_key: str, base_url: str, model: str):
        self._client = OpenAIHttpClient(api_key=api_key, base_url=base_url)
        self._model = model

    def split_query(self, query: str) -> list[SubtaskSuggestion]:
        # Split is used synchronously in HTTP handler; keep a sync wrapper.
        raise RuntimeError("OpenAILLM.split_query must be called via async adapter")

    async def split_query_async(self, query: str, prompt: str) -> list[SubtaskSuggestion]:
        text = prompt.replace("{{QUERY}}", query)
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "rewritten_query": {"type": "string"},
                "tasks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["rewritten_query", "tasks"],
        }
        resp = await self._client.responses_text(model=self._model, input_text=text, json_schema=schema, schema_name="step1")
        obj = parse_json_object(resp.text)
        tasks = obj.get("tasks") or []
        if not isinstance(tasks, list) or not tasks:
            return [SubtaskSuggestion(name=query.strip())]
        out: list[SubtaskSuggestion] = []
        for t in tasks:
            if isinstance(t, str) and t.strip():
                out.append(SubtaskSuggestion(name=t.strip()))
        return out or [SubtaskSuggestion(name=query.strip())]

    async def summarize_document_async(self, *, subtask: str, doc_title: str | None, doc_content: str, url: str | None, prompt: str) -> str:
        text = (
            prompt.replace("{{SUBTASK}}", subtask)
            .replace("{{TITLE}}", doc_title or "")
            .replace("{{CONTENT}}", doc_content)
            .replace("{{URL}}", url or "")
        )
        resp = await self._client.responses_text(model=self._model, input_text=text)
        return resp.text.strip()

    async def final_answer_async(self, *, query: str, subtasks: list[str], summaries: list[str], prompt: str) -> str:
        text = (
            prompt.replace("{{QUERY}}", query)
            .replace("{{SUBTASKS}}", "\n".join(f"- {s}" for s in subtasks))
            .replace("{{SUMMARIES}}", "\n".join(f"- {s}" for s in summaries))
        )
        resp = await self._client.responses_text(model=self._model, input_text=text)
        return resp.text.strip()


def get_llm() -> LLM:
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAILLM(api_key=settings.openai_api_key, base_url=settings.openai_base_url, model=settings.openai_model)
    return MockLLM()
