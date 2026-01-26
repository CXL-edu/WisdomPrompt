from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.events import emit_event
from app.models import (
    Document,
    DocumentKind,
    FinalAnswer,
    Run,
    RunStatus,
    Source,
    SourceProvider,
    Step,
    StepStatus,
    Subtask,
    Summary,
)
from pathlib import Path

from app.providers.llm import LLM, get_llm
from app.providers.search.arxiv import ArxivProvider
from app.providers.search.base import SearchProvider
from app.providers.search.exa import ExaProvider
from app.providers.search.github import GitHubCodeSearchProvider
from app.providers.search.serper import SerperProvider
from app.providers.vector_store import MilvusVectorStore, MockVectorStore, VectorDoc


def _hash_obj(obj: object) -> str:
    return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()


def _ensure_steps(db: Session, run: Run) -> None:
    existing = {s.index for s in run.steps}
    for i in range(1, 5):
        if i not in existing:
            db.add(Step(run_id=run.id, index=i, status=StepStatus.pending))
    db.commit()


def _llm():
    return get_llm()


def _read_prompt(name: str) -> str:
    p = Path(__file__).parent / "prompts" / name
    if not p.exists():
        # Prompts live under app/prompts.
        p = Path(__file__).parent / "prompts" / name
    if not p.exists():
        p = Path(__file__).parent.parent / "prompts" / name
    return p.read_text(encoding="utf-8")


def _vector_store():
    if settings.vector_store == "milvus":
        if not settings.milvus_uri:
            raise RuntimeError("VECTOR_STORE=milvus but MILVUS_URI is not set")
        return MilvusVectorStore(
            uri=settings.milvus_uri,
            token=settings.milvus_token,
            collection=settings.milvus_collection,
            id_field=settings.milvus_id_field,
            text_field=settings.milvus_text_field,
            vector_field=settings.milvus_vector_field,
            metadata_field=settings.milvus_metadata_field,
        )
    if settings.vector_store == "mock":
        return MockVectorStore()
    raise RuntimeError("VECTOR_STORE must be 'mock' or 'milvus'")


def _search_providers() -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    if settings.exa_api_key:
        providers.append(ExaProvider(settings.exa_api_key))
    if settings.serper_api_key:
        providers.append(SerperProvider(settings.serper_api_key))
    if settings.github_token:
        providers.append(GitHubCodeSearchProvider(settings.github_token))
    # arXiv is public.
    providers.append(ArxivProvider())
    return providers


async def run_from_step(db_factory: Callable[[], Session], run_id: str, from_step: int) -> None:
    # Orchestrates step 2-4 (and optionally step1 rerun).
    db: Session = db_factory()
    try:
        run = db.get(Run, run_id)
        if not run:
            return
        _ensure_steps(db, run)
        vs = _vector_store()
        llm = _llm()
        providers = _search_providers()

        # Invalidate downstream artifacts.
        _invalidate_downstream(db, run, from_step)

        if from_step <= 1:
            await _step1(db, run, llm)
            return

        if from_step <= 2:
            await _step2(db, run, vs, providers)
        if from_step <= 3:
            await _step3(db, run, llm)
        if from_step <= 4:
            await _step4(db, run, llm)
    except Exception as e:  # noqa: BLE001
        run = db.get(Run, run_id)
        if run:
            run.status = RunStatus.failed
            run.error = str(e)
            run.updated_at = dt.datetime.now(dt.UTC)
            db.commit()
            emit_event(db, run_id, "run.failed", {"error": str(e)})
    finally:
        db.close()


def _invalidate_downstream(db: Session, run: Run, from_step: int) -> None:
    # Mark steps > from_step as invalidated, and delete derived artifacts.
    for s in run.steps:
        if s.index > from_step:
            s.status = StepStatus.invalidated
            s.output_json = None
            s.error = None
    if from_step <= 2:
        # Clear docs, sources, summaries, final answer.
        db.query(Summary).filter(Summary.run_id == run.id).delete()
        db.query(Source).join(Document).filter(Document.run_id == run.id).delete(synchronize_session=False)
        db.query(Document).filter(Document.run_id == run.id).delete()
        db.query(FinalAnswer).filter(FinalAnswer.run_id == run.id).delete()
    elif from_step == 3:
        db.query(Summary).filter(Summary.run_id == run.id).delete()
        db.query(FinalAnswer).filter(FinalAnswer.run_id == run.id).delete()
    elif from_step == 4:
        db.query(FinalAnswer).filter(FinalAnswer.run_id == run.id).delete()
    run.current_step = from_step
    run.updated_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "step.invalidated", {"from_step": from_step})


async def _step1(db: Session, run: Run, llm: LLM) -> None:
    step = db.query(Step).filter(Step.run_id == run.id, Step.index == 1).one()
    step.status = StepStatus.running
    step.started_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "step.started", {"step": 1})

    prompt = _read_prompt("step1_query_split.md")
    suggestions = await llm.split_query(run.query, prompt)
    # Replace existing subtasks.
    db.query(Subtask).filter(Subtask.run_id == run.id).delete()
    for i, s in enumerate(suggestions):
        db.add(Subtask(run_id=run.id, name=s.name, order=i, confirmed=False))
    run.status = RunStatus.waiting_confirm
    run.current_step = 1
    run.updated_at = dt.datetime.now(dt.UTC)
    step.status = StepStatus.done
    step.finished_at = dt.datetime.now(dt.UTC)
    out_json: dict[str, Any] = {"subtasks": [s.name for s in suggestions]}
    step.output_json = out_json
    db.commit()
    emit_event(db, run.id, "subtasks.suggested", {"subtasks": out_json["subtasks"]})
    emit_event(db, run.id, "step.completed", {"step": 1})


async def _step2(db: Session, run: Run, vs, providers: list[SearchProvider]) -> None:
    run.status = RunStatus.running
    run.current_step = 2
    run.updated_at = dt.datetime.now(dt.UTC)
    step = db.query(Step).filter(Step.run_id == run.id, Step.index == 2).one()
    step.status = StepStatus.running
    step.started_at = dt.datetime.now(dt.UTC)
    step.input_hash = _hash_obj([(s.order, s.name) for s in run.subtasks])
    db.commit()
    emit_event(db, run.id, "step.started", {"step": 2})

    # Ensure subtasks are confirmed.
    subtasks = db.query(Subtask).filter(Subtask.run_id == run.id).order_by(Subtask.order.asc()).all()
    if not subtasks or not all(s.confirmed for s in subtasks):
        raise RuntimeError("subtasks not confirmed")

    for st in subtasks:
        emit_event(db, run.id, "retrieval.started", {"subtask_id": st.id, "subtask": st.name})

        hits = vs.search(st.name, top_k=settings.top_k)
        high_hits = [h for h in hits if h.score >= settings.high_score_threshold]

        used_web = False
        if len(high_hits) < settings.min_high_score_hits:
            used_web = True
            # Web search fallback.
            for p in providers:
                emit_event(db, run.id, "retrieval.web_search", {"subtask_id": st.id, "provider": p.__class__.__name__, "query": st.name})
                try:
                    results = await p.search(st.name, limit=3)
                except Exception as e:  # noqa: BLE001
                    emit_event(db, run.id, "retrieval.web_search_failed", {"subtask_id": st.id, "provider": p.__class__.__name__, "error": str(e)})
                    continue
                for r in results:
                    doc = Document(run_id=run.id, subtask_id=st.id, title=r.title, content=r.content, kind=DocumentKind.web)
                    db.add(doc)
                    db.commit()
                    db.refresh(doc)
                    src = Source(
                        document_id=doc.id,
                        provider=SourceProvider(r.provider),
                        url=r.url,
                        meta_json=r.meta,
                    )
                    db.add(src)
                    db.commit()

                    # Insert into vector store for future retrieval.
                    vs.upsert(
                        [
                            VectorDoc(
                                id=doc.id,
                                content=f"{r.title or ''}\n{r.content}",
                                metadata={
                                    "run_id": run.id,
                                    "subtask_id": st.id,
                                    "provider": r.provider,
                                    "url": r.url,
                                    "title": r.title,
                                },
                            )
                        ]
                    )

                    emit_event(
                        db,
                        run.id,
                        "retrieval.card",
                        {
                            "subtask_id": st.id,
                            "document": {
                                "id": doc.id,
                                "title": doc.title,
                                "content": doc.content,
                                "source": {"provider": r.provider, "url": r.url},
                            },
                        },
                    )
        else:
            # Serve existing (vector) hits from DB. Some hits may be missing in SQL.
            for h in high_hits:
                doc = db.get(Document, h.id)
                if not doc:
                    continue
                doc.score = h.score
                db.commit()
                src = doc.sources[0] if doc.sources else None
                emit_event(
                    db,
                    run.id,
                    "retrieval.card",
                    {
                        "subtask_id": st.id,
                        "document": {
                            "id": doc.id,
                            "title": doc.title,
                            "content": doc.content,
                            "score": h.score,
                            "source": {"provider": (src.provider.value if src else "milvus"), "url": (src.url if src else None)},
                        },
                    },
                )

        emit_event(db, run.id, "retrieval.completed", {"subtask_id": st.id, "used_web": used_web})

    step.status = StepStatus.done
    step.finished_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "step.completed", {"step": 2})


async def _step3(db: Session, run: Run, llm: LLM) -> None:
    run.current_step = 3
    run.updated_at = dt.datetime.now(dt.UTC)
    step = db.query(Step).filter(Step.run_id == run.id, Step.index == 3).one()
    step.status = StepStatus.running
    step.started_at = dt.datetime.now(dt.UTC)
    step.input_hash = _hash_obj([d.id for d in db.query(Document).filter(Document.run_id == run.id).all()])
    db.commit()
    emit_event(db, run.id, "step.started", {"step": 3})

    subtasks = db.query(Subtask).filter(Subtask.run_id == run.id).order_by(Subtask.order.asc()).all()
    for st in subtasks:
        docs = db.query(Document).filter(Document.run_id == run.id, Document.subtask_id == st.id).all()
        for d in docs:
            url = d.sources[0].url if d.sources else None
            prompt = _read_prompt("step3_summarize.md")
            summary_text = await llm.summarize_document(
                subtask=st.name,
                doc_title=d.title,
                doc_content=d.content,
                url=url,
                prompt=prompt,
            )
            sm = Summary(run_id=run.id, subtask_id=st.id, document_id=d.id, summary_text=summary_text)
            db.add(sm)
            db.commit()
            emit_event(db, run.id, "summary.generated", {"subtask_id": st.id, "document_id": d.id, "summary": summary_text})

    step.status = StepStatus.done
    step.finished_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "step.completed", {"step": 3})


async def _step4(db: Session, run: Run, llm: LLM) -> None:
    run.current_step = 4
    run.updated_at = dt.datetime.now(dt.UTC)
    step = db.query(Step).filter(Step.run_id == run.id, Step.index == 4).one()
    step.status = StepStatus.running
    step.started_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "step.started", {"step": 4})

    subtasks = db.query(Subtask).filter(Subtask.run_id == run.id).order_by(Subtask.order.asc()).all()
    summaries = db.query(Summary).filter(Summary.run_id == run.id).all()
    prompt = _read_prompt("step4_final_answer.md")
    answer = await llm.final_answer(
        query=run.query,
        subtasks=[s.name for s in subtasks],
        summaries=[s.summary_text for s in summaries],
        prompt=prompt,
    )
    db.add(FinalAnswer(run_id=run.id, content=answer))
    run.status = RunStatus.completed
    run.updated_at = dt.datetime.now(dt.UTC)
    step.status = StepStatus.done
    step.finished_at = dt.datetime.now(dt.UTC)
    db.commit()
    emit_event(db, run.id, "final.answer", {"content": answer})
    emit_event(db, run.id, "run.completed", {})
