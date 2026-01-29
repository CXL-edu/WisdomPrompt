"""Request/response schemas for workflow API."""
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class WorkflowDecomposeRequest(BaseModel):
    """Request body for decompose-only (step 1)."""

    query: str = Field(..., min_length=1, description="User query")


class WorkflowDecomposeResponse(BaseModel):
    sub_tasks: List[str]


class WorkflowRunRequest(BaseModel):
    """Request body for workflow run (SSE)."""

    query: str = Field(..., min_length=1, description="User query")
    from_step: int = Field(1, ge=1, le=4, description="Start from step 1–4 (re-run from here)")
    cached: Optional[dict[str, Any]] = Field(
        None,
        description="Cached results for steps before from_step: sub_tasks, retrieval, summaries",
    )


class SubTaskItem(BaseModel):
    name: str


class RetrievalHit(BaseModel):
    content: str
    url: Optional[str] = None
    source: Optional[str] = None
    similarity: Optional[float] = None


class RetrievalResult(BaseModel):
    sub_task: str
    hits: List[RetrievalHit] = []
    error: Optional[str] = None


class SummaryResult(BaseModel):
    sub_task: str
    summary: str
    error: Optional[str] = None
