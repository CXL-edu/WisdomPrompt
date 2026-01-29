"""DuckDB + VSS vector store: async writes, dedup by URL, top_k search with min similarity."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import List, Optional

import duckdb
from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger(__name__)

# Default DB path under project root when run from project root
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vectors.duckdb")


def _get_db_path() -> str:
    base = os.environ.get("WISDOMPROMPT_DATA_DIR")
    if base:
        return str(Path(base) / "vectors.duckdb")
    return DEFAULT_DB_PATH


def _ensure_db_and_table(conn: duckdb.DuckDBPyConnection, dimension: int) -> None:
    conn.execute("INSTALL vss; LOAD vss;")
    conn.execute("CREATE SEQUENCE IF NOT EXISTS knowledge_id_seq;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge (
            id BIGINT PRIMARY KEY,
            content TEXT NOT NULL,
            url TEXT,
            source TEXT,
            embedding FLOAT[%d],
            created_at TIMESTAMP DEFAULT current_timestamp
        )
        """
        % dimension
    )
    # Dedup by url is done in _sync_add (SELECT before INSERT)


def _sync_add(content: str, url: Optional[str], source: str, embedding: List[float], db_path: str, dimension: int) -> None:
    conn = duckdb.connect(db_path)
    try:
        _ensure_db_and_table(conn, dimension)
        if url:
            existing = conn.execute("SELECT 1 FROM knowledge WHERE url = ?", [url]).fetchone()
            if existing:
                logger.debug("vector_store_skip_duplicate_url", url=url)
                return
        embed_lit = _embedding_literal(embedding, dimension)
        new_id = conn.execute("SELECT nextval('knowledge_id_seq')").fetchone()[0]
        conn.execute(
            "INSERT INTO knowledge (id, content, url, source, embedding) VALUES (?, ?, ?, ?, " + embed_lit + ")",
            [new_id, content, url, source],
        )
        conn.commit()
    finally:
        conn.close()


def _embedding_literal(vec: List[float], dimension: int) -> str:
    """Safe literal for SQL: [v1,v2,...]::FLOAT[dim]. vec is our own data, not user input."""
    part = ",".join(str(float(x)) for x in vec[:dimension])
    return f"[{part}]::FLOAT[{dimension}]"


def _sync_search(
    query_embedding: List[float], top_k: int, min_similarity: float, db_path: str, dimension: int
) -> List[dict]:
    conn = duckdb.connect(db_path)
    try:
        _ensure_db_and_table(conn, dimension)
        qlit = _embedding_literal(query_embedding, dimension)
        # array_cosine_similarity: 1 = same, -1 = opposite; we want >= min_similarity
        sql = f"""
            SELECT content, url, source, array_cosine_similarity(embedding, {qlit}) AS sim
            FROM knowledge
            WHERE array_cosine_similarity(embedding, {qlit}) >= ?
            ORDER BY sim DESC
            LIMIT ?
            """
        rows = conn.execute(sql, [min_similarity, top_k]).fetchall()
        return [
            {"content": r[0], "url": r[1], "source": r[2], "similarity": float(r[3])}
            for r in rows
        ]
    finally:
        conn.close()


class VectorStore:
    """DuckDB + VSS vector store with async write and URL dedup."""

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or _get_db_path()
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._settings = get_settings()
        self._dim = self._settings.EMBEDDING_DIMENSION

    async def add(self, content: str, url: Optional[str], source: str, embedding: List[float]) -> None:
        """Add one document; skip if url already exists (dedup by URL)."""
        await asyncio.to_thread(
            _sync_add,
            content,
            url,
            source,
            embedding,
            self._db_path,
            self._dim,
        )

    async def add_many(
        self,
        items: List[tuple[str, Optional[str], str, List[float]]],
    ) -> None:
        """Add multiple (content, url, source, embedding); dedup by URL per item."""
        for content, url, source, embedding in items:
            await self.add(content, url, source, embedding)

    async def search(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> List[dict]:
        """Return top_k hits with similarity >= min_similarity."""
        k = top_k if top_k is not None else self._settings.TOP_K
        min_s = min_similarity if min_similarity is not None else self._settings.MIN_SIMILARITY_SCORE
        return await asyncio.to_thread(
            _sync_search,
            query_embedding,
            k,
            min_s,
            self._db_path,
            self._dim,
        )


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
