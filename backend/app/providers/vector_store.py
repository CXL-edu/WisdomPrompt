from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class VectorDoc:
    id: str
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorStore(Protocol):
    def upsert(self, docs: list[VectorDoc]) -> None:
        ...

    def search(self, query_text: str, *, top_k: int) -> list[VectorHit]:
        ...


class MockVectorStore(VectorStore):
    def __init__(self):
        self._docs: dict[str, VectorDoc] = {}

    def upsert(self, docs: list[VectorDoc]) -> None:
        for d in docs:
            self._docs[d.id] = d

    def search(self, query_text: str, *, top_k: int) -> list[VectorHit]:
        # Simple token-overlap score to support offline dev/tests.
        q = _tokenize(query_text)
        hits: list[VectorHit] = []
        for d in self._docs.values():
            score = _overlap_score(q, _tokenize(d.content))
            hits.append(VectorHit(id=d.id, score=score, metadata=d.metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _overlap_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a))


class MilvusVectorStore(VectorStore):
    def __init__(
        self,
        *,
        uri: str,
        token: str | None,
        collection: str,
        id_field: str,
        text_field: str,
        vector_field: str,
        metadata_field: str,
    ):
        # Dynamic import keeps this optional in dev/tests and avoids hard dependency.
        pymilvus = __import__("pymilvus")
        self._client = getattr(pymilvus, "MilvusClient")(uri=uri, token=(token or ""))
        self._collection = collection
        self._id_field = id_field
        self._text_field = text_field
        self._vector_field = vector_field
        self._metadata_field = metadata_field

        if not self._client.has_collection(collection_name=collection):
            raise RuntimeError(
                "Milvus collection not found. Create it with an embedding function enabled, "
                "then configure MILVUS_COLLECTION to match."
            )

    def upsert(self, docs: list[VectorDoc]) -> None:
        if not docs:
            return
        ids = [d.id for d in docs]
        payload = [
            {
                self._id_field: d.id,
                self._text_field: d.content,
                self._metadata_field: d.metadata,
            }
            for d in docs
        ]
        # Best-effort upsert: delete existing ids then insert.
        id_list = "\",\"".join(ids)
        self._client.delete(
            collection_name=self._collection,
            filter=f'{self._id_field} in ["{id_list}"]',
        )
        self._client.insert(collection_name=self._collection, data=payload)

    def search(self, query_text: str, *, top_k: int) -> list[VectorHit]:
        res = self._client.search(
            collection_name=self._collection,
            data=[query_text],
            anns_field=self._vector_field,
            limit=top_k,
            output_fields=[self._id_field, self._metadata_field],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 16}},
        )
        res_any = cast(Any, res)
        out: list[VectorHit] = []
        for hit in res_any[0]:
            hit_id = getattr(hit, "id", None)
            score = getattr(hit, "score", None)
            entity = getattr(hit, "entity", None)
            if hasattr(hit, "get"):
                hit_id = hit.get("id", hit_id)
                score = hit.get("score", hit.get("distance", score))
                entity = hit.get("entity", entity)
            if entity is None and hasattr(hit, "get"):
                entity = hit
            meta = {}
            if entity and hasattr(entity, "get"):
                meta = cast(dict[str, Any], entity.get(self._metadata_field) or {})
            out.append(VectorHit(id=str(hit_id), score=float(score or 0.0), metadata=meta))
        return out
