import os

import pytest

from app.providers.vector_store import MilvusVectorStore, VectorDoc


def _env(name: str) -> str | None:
    return os.getenv(name)


def test_milvus_vector_store_live():
    if not _env("MILVUS_URI") or not _env("MILVUS_COLLECTION"):
        pytest.skip("MILVUS_URI or MILVUS_COLLECTION not set")

    store: MilvusVectorStore | None = None
    try:
        store = MilvusVectorStore(
            uri=_env("MILVUS_URI") or "",
            token=_env("MILVUS_TOKEN"),
            collection=_env("MILVUS_COLLECTION") or "",
            id_field=os.getenv("MILVUS_ID_FIELD", "id"),
            text_field=os.getenv("MILVUS_TEXT_FIELD", "content"),
            vector_field=os.getenv("MILVUS_VECTOR_FIELD", "vector"),
            metadata_field=os.getenv("MILVUS_METADATA_FIELD", "metadata"),
        )
    except RuntimeError as exc:
        pytest.skip(str(exc))

    assert store is not None

    store.upsert(
        [
            VectorDoc(
                id="test-doc",
                content="Milvus is a vector database for similarity search.",
                metadata={"source": "test"},
            )
        ]
    )
    hits = store.search("Milvus vector database", top_k=3)
    assert hits
