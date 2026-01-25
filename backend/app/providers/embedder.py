from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]


class Embedder:
    def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError


class HashEmbedder(Embedder):
    """Deterministic local embedder.

    Not truly semantic, but makes the system runnable without external models/keys.
    """

    def __init__(self, dim: int):
        if dim <= 0:
            raise ValueError("embedding dim must be positive")
        self._dim = dim

    def embed(self, text: str) -> EmbeddingResult:
        # Expand SHA256 into dim floats in [-1, 1], then L2-normalize.
        h = hashlib.sha256(text.encode("utf-8")).digest()
        out: list[float] = []
        counter = 0
        while len(out) < self._dim:
            b = hashlib.sha256(h + counter.to_bytes(4, "little")).digest()
            for i in range(0, len(b), 4):
                if len(out) >= self._dim:
                    break
                v = int.from_bytes(b[i : i + 4], "little", signed=False)
                out.append(((v / 2**32) * 2.0) - 1.0)
            counter += 1
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        out = [x / norm for x in out]
        return EmbeddingResult(vector=out)
