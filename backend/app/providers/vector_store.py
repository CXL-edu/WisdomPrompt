from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class VectorDoc:
    id: str
    vector: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorStore(Protocol):
    def upsert(self, docs: list[VectorDoc]) -> None:
        ...

    def search(self, query_vector: list[float], *, top_k: int) -> list[VectorHit]:
        ...


class MockVectorStore(VectorStore):
    def __init__(self):
        self._docs: dict[str, VectorDoc] = {}

    def upsert(self, docs: list[VectorDoc]) -> None:
        for d in docs:
            self._docs[d.id] = d

    def search(self, query_vector: list[float], *, top_k: int) -> list[VectorHit]:
        # Cosine similarity (vectors are normalized by embedder).
        hits: list[VectorHit] = []
        for d in self._docs.values():
            score = _dot(query_vector, d.vector)
            hits.append(VectorHit(id=d.id, score=score, metadata=d.metadata))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]


def _dot(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


class MilvusVectorStore(VectorStore):
    def __init__(self, *, uri: str, token: str | None, collection: str, dim: int):
        # Dynamic import keeps this optional in dev/tests and avoids hard dependency.
        pymilvus = __import__("pymilvus")
        Collection = getattr(pymilvus, "Collection")
        CollectionSchema = getattr(pymilvus, "CollectionSchema")
        DataType = getattr(pymilvus, "DataType")
        FieldSchema = getattr(pymilvus, "FieldSchema")
        connections = getattr(pymilvus, "connections")
        utility = getattr(pymilvus, "utility")

        connections.connect(uri=uri, token=(token or ""))

        self._collection_name = collection
        if not utility.has_collection(collection):
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields=fields, description="wisdomprompt docs")
            Collection(name=collection, schema=schema)

        self._collection = Collection(collection)
        if not self._collection.has_index():
            # Some type stubs mark this as async; treat as best-effort.
            _ = self._collection.create_index(
                field_name="vector",
                index_params={"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}},
            )
        self._collection.load()

    def upsert(self, docs: list[VectorDoc]) -> None:
        if not docs:
            return
        ids = [d.id for d in docs]
        vectors = [d.vector for d in docs]
        meta = [d.metadata for d in docs]
        # Best-effort upsert: delete existing ids then insert.
        self._collection.delete(expr=f'id in ["' + '\",\"'.join(ids) + '"]')
        self._collection.insert([ids, vectors, meta])
        self._collection.flush()

    def search(self, query_vector: list[float], *, top_k: int) -> list[VectorHit]:
        res = self._collection.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            output_fields=["id", "metadata"],
        )
        res_any = cast(Any, res)
        out: list[VectorHit] = []
        for hit in res_any[0]:
            out.append(
                VectorHit(
                    id=str(hit.entity.get("id")),
                    score=float(hit.score),
                    metadata=cast(dict[str, Any], hit.entity.get("metadata") or {}),
                )
            )
        return out
