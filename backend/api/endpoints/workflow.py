"""SSE endpoint for product page workflow."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.models.schemas import WorkflowRunRequest
from backend.services import workflow as workflow_service

router = APIRouter()


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
