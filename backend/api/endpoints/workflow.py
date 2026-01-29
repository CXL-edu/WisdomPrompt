"""SSE endpoint for product page workflow; decompose-only for confirm-before-run."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.models.schemas import (
    WorkflowDecomposeRequest,
    WorkflowDecomposeResponse,
    WorkflowRunRequest,
)
from backend.services import agent
from backend.services import workflow as workflow_service

router = APIRouter()


@router.post("/decompose", response_model=WorkflowDecomposeResponse)
async def workflow_decompose(body: WorkflowDecomposeRequest):
    """Only run step 1 (query decompose). Returns sub_tasks for user to edit/confirm before running retrieval."""
    sub_tasks = await agent.decompose_query(body.query)
    return WorkflowDecomposeResponse(sub_tasks=sub_tasks)


@router.post("/stream")
async def workflow_stream(body: WorkflowRunRequest):
    """Stream workflow events as SSE. POST body: query, from_step (1–4), optional cached."""

    async def event_generator():
        async for ev in workflow_service.run_workflow(
            query=body.query,
            from_step=body.from_step,
            cached=body.cached,
        ):
            event = ev.get("event", "message")
            data = ev.get("data", {})
            payload = json.dumps(data, ensure_ascii=False)
            yield f"event: {event}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
