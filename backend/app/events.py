from __future__ import annotations

import json
import time
from collections.abc import Generator
from collections.abc import Callable

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import RunEvent


def emit_event(db: Session, run_id: str, type_: str, data: dict[str, object] | None = None) -> RunEvent:
    # Monotonic per-run sequence number.
    next_seq = (db.query(func.max(RunEvent.seq)).filter(RunEvent.run_id == run_id).scalar() or 0) + 1
    ev = RunEvent(run_id=run_id, seq=next_seq, type=type_, data_json=data)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _format_sse(ev_type: str, data: dict[str, object] | None, event_id: int) -> str:
    payload = json.dumps(data or {}, ensure_ascii=True)
    # SSE format: id/event/data lines separated by \n, and a blank line terminator.
    return f"id: {event_id}\nevent: {ev_type}\ndata: {payload}\n\n"


def sse_event_stream(
    *,
    db_factory: Callable[[], Session],
    run_id: str,
    request: Request,
    last_event_id: int = 0,
    poll_interval_s: float = 0.5,
    keepalive_s: float = 10.0,
) -> Generator[str, None, None]:
    last_keepalive = time.monotonic()

    while True:
        if request.client is None:
            break
        if request.is_disconnected():
            break

        now = time.monotonic()
        if now - last_keepalive >= keepalive_s:
            last_keepalive = now
            yield ": keepalive\n\n"

        db: Session = db_factory()
        try:
            rows = (
                db.query(RunEvent)
                .filter(RunEvent.run_id == run_id, RunEvent.seq > last_event_id)
                .order_by(RunEvent.seq.asc())
                .all()
            )
            for r in rows:
                last_event_id = r.seq
                yield _format_sse(r.type, r.data_json, r.seq)
        finally:
            db.close()

        time.sleep(poll_interval_s)
