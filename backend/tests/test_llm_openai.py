import os

import pytest

from app.providers.llm import get_llm


@pytest.mark.asyncio
async def test_openai_split_query_live():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    llm = get_llm()
    prompt = (
        "Return JSON with keys rewritten_query and tasks. "
        "User query: list key Milvus features."
    )
    tasks = await llm.split_query("Milvus features", prompt)
    assert tasks
    assert all(t.name for t in tasks)
