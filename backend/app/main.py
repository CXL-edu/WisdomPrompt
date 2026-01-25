from __future__ import annotations

import asyncio

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal, get_db, init_db
from app.events import emit_event, sse_event_stream
from app.models import Document, FinalAnswer, Run, RunStatus, Step, StepStatus, Subtask, Summary
from app.orchestrator import run_from_step
from app.providers.llm import MockLLM
from app.schemas import ConfirmSubtasksIn, RerunIn, RunCreateIn, RunCreatedOut, RunSnapshotOut, SubtaskIn


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _snapshot(db: Session, run: Run) -> RunSnapshotOut:
    subtasks = db.query(Subtask).filter(Subtask.run_id == run.id).order_by(Subtask.order.asc()).all()
    docs = db.query(Document).filter(Document.run_id == run.id).all()
    sums = db.query(Summary).filter(Summary.run_id == run.id).all()
    fa = db.query(FinalAnswer).filter(FinalAnswer.run_id == run.id).one_or_none()

    retrieval: dict[str, list[dict[str, object]]] = {}
    for d in docs:
        src = d.sources[0] if d.sources else None
        if d.subtask_id not in retrieval:
            retrieval[d.subtask_id] = []
        row: dict[str, object] = {
            "id": d.id,
            "title": d.title,
            "content": d.content,
            "score": d.score,
            "source": {
                "provider": (src.provider.value if src else None),
                "url": (src.url if src else None),
            },
        }
        retrieval[d.subtask_id].append(row)

    summaries: dict[str, str] = {s.document_id: s.summary_text for s in sums}
    return RunSnapshotOut(
        run_id=run.id,
        query=run.query,
        status=run.status.value,
        current_step=run.current_step,
        subtasks=[SubtaskIn(id=s.id, name=s.name, order=s.order) for s in subtasks],
        retrieval=retrieval,
        summaries=summaries,
        final_answer=(fa.content if fa else None),
    )


@app.post("/api/runs", response_model=RunCreatedOut)
def create_run(payload: RunCreateIn, db: Session = Depends(get_db)) -> RunCreatedOut:
    run = Run(query=payload.query, status=RunStatus.created, current_step=1)
    db.add(run)
    db.commit()
    db.refresh(run)

    # Ensure steps.
    for i in range(1, 5):
        db.add(Step(run_id=run.id, index=i, status=StepStatus.pending))
    db.commit()

    emit_event(db, run.id, "run.created", {"query": payload.query})

    # Step 1: split query into subtasks (sync) and wait for confirmation.
    llm = MockLLM()
    suggestions = llm.split_query(payload.query)
    for i, s in enumerate(suggestions):
        db.add(Subtask(run_id=run.id, name=s.name, order=i, confirmed=False))
    run.status = RunStatus.waiting_confirm
    db.commit()
    emit_event(db, run.id, "subtasks.suggested", {"subtasks": [s.name for s in suggestions]})

    subtasks = db.query(Subtask).filter(Subtask.run_id == run.id).order_by(Subtask.order.asc()).all()
    return RunCreatedOut(
        run_id=run.id,
        status=run.status.value,
        subtasks=[SubtaskIn(id=s.id, name=s.name, order=s.order) for s in subtasks],
    )


@app.get("/api/runs/{run_id}", response_model=RunSnapshotOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunSnapshotOut:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return _snapshot(db, run)


@app.get("/api/runs/{run_id}/events")
def events(run_id: str, request: Request):
    # SSE endpoint; Last-Event-ID enables resume.
    last_id = 0
    try:
        hdr = request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")
        if hdr:
            last_id = int(hdr)
    except ValueError:
        last_id = 0

    return StreamingResponse(
        sse_event_stream(
            db_factory=SessionLocal,
            run_id=run_id,
            request=request,
            last_event_id=last_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/runs/{run_id}/subtasks/confirm")
async def confirm_subtasks(run_id: str, payload: ConfirmSubtasksIn, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    # Replace subtasks with the user-confirmed list.
    db.query(Subtask).filter(Subtask.run_id == run_id).delete()
    for st in payload.subtasks:
        db.add(Subtask(run_id=run_id, name=st.name, order=st.order, confirmed=True))
    run.status = RunStatus.running
    run.current_step = 2
    db.commit()
    emit_event(db, run_id, "subtasks.confirmed", {"subtasks": [s.name for s in payload.subtasks]})

    # Kick off async pipeline from step2.
    asyncio.create_task(run_from_step(SessionLocal, run_id, 2))
    return {"ok": True}


@app.post("/api/runs/{run_id}/step/{step_index}/rerun")
async def rerun(run_id: str, step_index: int, payload: RerunIn, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if step_index < 1 or step_index > 4:
        raise HTTPException(status_code=400, detail="invalid step")

    emit_event(db, run_id, "rerun.requested", {"from_step": step_index, "reason": payload.reason})
    asyncio.create_task(run_from_step(SessionLocal, run_id, step_index))
    return {"ok": True}
