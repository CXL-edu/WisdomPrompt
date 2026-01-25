from __future__ import annotations

from pydantic import BaseModel, Field


class SubtaskIn(BaseModel):
    id: str | None = None
    name: str = Field(min_length=1)
    order: int


class RunCreateIn(BaseModel):
    query: str = Field(min_length=1)


class RunCreatedOut(BaseModel):
    run_id: str
    status: str
    subtasks: list[SubtaskIn]


class RunSnapshotOut(BaseModel):
    run_id: str
    query: str
    status: str
    current_step: int
    subtasks: list[SubtaskIn]
    retrieval: dict
    summaries: dict
    final_answer: str | None


class ConfirmSubtasksIn(BaseModel):
    subtasks: list[SubtaskIn]


class RerunIn(BaseModel):
    reason: str | None = None
