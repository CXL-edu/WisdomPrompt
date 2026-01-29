"""Agent: LLM calls for query decompose, sub-task summarize, and final answer. Uses OpenAI and prompts from backend/prompts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncIterator, List

from openai import AsyncOpenAI
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


async def _chat(system: str, user: str) -> str:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL_ID
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=False,
    )
    if not resp.choices or not resp.choices[0].message.content:
        return ""
    return resp.choices[0].message.content


async def _chat_stream(system: str, user: str) -> AsyncIterator[str]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.LLM_MODEL_ID
    stream_resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=True,
    )
    async for chunk in stream_resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def decompose_query(query: str) -> List[str]:
    """Rewrite/split user query into 1–4 sub-tasks. Returns list of strings."""
    system = _load_prompt("query_decompose.txt")
    out = await _chat(system, query)
    out = out.strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        arr = json.loads(out)
        if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
            return arr[:4]
        return [query]
    except json.JSONDecodeError:
        logger.warning("decompose_non_json", raw=out[:200])
        return [query]


async def summarize_sub_task(sub_task: str, retrieved_content: str) -> str:
    """Summarize/organize retrieved content for one sub-task. Returns plain text or short markdown."""
    system = _load_prompt("sub_task_summarize.txt")
    user = f"Sub-task: {sub_task}\n\nRetrieved content:\n{retrieved_content}"
    return await _chat(system, user)


async def generate_final_answer(original_query: str, sub_task_summaries: List[tuple[str, str]]) -> str:
    """Generate final Markdown answer from original query and (sub_task_name, summary) pairs."""
    system = _load_prompt("final_answer.txt")
    parts = [f"Original user query: {original_query}\n"]
    for name, summary in sub_task_summaries:
        parts.append(f"Sub-task: {name}\nSummary: {summary}\n")
    user = "\n".join(parts)
    return await _chat(system, user)


async def stream_final_answer(original_query: str, sub_task_summaries: List[tuple[str, str]]) -> AsyncIterator[str]:
    """Stream final Markdown answer chunk by chunk."""
    system = _load_prompt("final_answer.txt")
    parts = [f"Original user query: {original_query}\n"]
    for name, summary in sub_task_summaries:
        parts.append(f"Sub-task: {name}\nSummary: {summary}\n")
    user = "\n".join(parts)
    async for chunk in _chat_stream(system, user):
        yield chunk
