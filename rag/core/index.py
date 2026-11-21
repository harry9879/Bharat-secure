"""Embedding index: multilingual-e5-small vectors, searched by cosine similarity.

A plain NumPy matrix is enough for ~12k passages (one matrix-vector product
per search, a few milliseconds); no vector database needed.
"""

import json

import numpy as np

from . import config

_model = None


def embedder():
    global _model
    if _model is None:
        import torch
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBED_MODEL, device="cuda" if torch.cuda.is_available() else "cpu")
    return _model


def embed(texts, kind: str):
    """kind is "passage" (knowledge base) or "query" (live call): e5 expects the prefix."""
    return embedder().encode([f"{kind}: {t}" for t in texts], batch_size=64, normalize_embeddings=True,
                             show_progress_bar=len(texts) > 500, convert_to_numpy=True).astype(np.float32)


class Index:
    def __init__(self, vectors: np.ndarray, passages: list[dict]):
        self.vectors = vectors
        self.passages = passages
        self.groups = np.array([p["group"] for p in passages])
        self.sources = np.array([p["source"] for p in passages])

    @classmethod
    def load(cls, folder=config.INDEX_DIR):
        vectors = np.load(folder / "vectors.npy").astype(np.float32)
        passages = [json.loads(l) for l in open(folder / "passages.jsonl", encoding="utf-8")]
        return cls(vectors, passages)

    def save(self, folder=config.INDEX_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "vectors.npy", self.vectors.astype(np.float16))
        with open(folder / "passages.jsonl", "w", encoding="utf-8") as fh:
            for p in self.passages:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")

    def search(self, query_vector: np.ndarray, k: int = config.TOP_K, exclude_group: str | None = None,
               exclude_sources: tuple[str, ...] = ()):
        """Top-k passages as [(similarity, passage)].

        exclude_group / exclude_sources leave passages out of the search, so an
        evaluation never finds the item it is testing (or hand-written cards
        that were written after seeing the test items).
        """
        sims = self.vectors @ query_vector
        if exclude_group is not None:
            sims = np.where(self.groups == exclude_group, -1.0, sims)
        for source in exclude_sources:
            sims = np.where(self.sources == source, -1.0, sims)
        top = np.argpartition(-sims, k)[:k]
        top = top[np.argsort(-sims[top])]
        return [(float(sims[i]), self.passages[i]) for i in top]
