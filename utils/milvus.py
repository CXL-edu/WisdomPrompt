from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence

from pymilvus import MilvusClient


@dataclass(frozen=True)
class MilvusConfig:
    uri: str
    token: Optional[str] = None
    db_name: str = "default"
    timeout: Optional[float] = None


def get_client(cfg: MilvusConfig) -> MilvusClient:
    """Create a MilvusClient using the minimal config."""
    options: dict[str, Any] = {"uri": cfg.uri, "db_name": cfg.db_name}
    if cfg.token:
        options["token"] = cfg.token
    if cfg.timeout is not None:
        options["timeout"] = cfg.timeout
    return MilvusClient(**options)


def ensure_collection(
    client: MilvusClient,
    name: str,
    dimension: int,
    metric: str = "COSINE",
) -> None:
    """Create collection if it does not exist."""
    if not client.has_collection(name):
        client.create_collection(
            collection_name=name,
            dimension=dimension,
            metric_type=metric,
        )


def insert_vectors(
    client: MilvusClient,
    name: str,
    records: Iterable[dict[str, Any]],
) -> Any:
    """Insert a batch of records into a collection."""
    return client.insert(collection_name=name, data=list(records))


def search(
    client: MilvusClient,
    name: str,
    vector: Sequence[float],
    limit: int = 5,
    output_fields: Optional[list[str]] = None,
    filter_expr: str = "",
) -> Any:
    """Run a vector search and return raw results."""
    return client.search(
        collection_name=name,
        data=[list(vector)],
        limit=limit,
        output_fields=output_fields or [],
        filter=filter_expr,
    )
