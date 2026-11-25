"""Semantic similarity and embedding backends (optional plug-ins).

Wanda does not train embedding models. `LexicalSimilarity` is a dependency-free baseline
(character trigram cosine); it measures spelling overlap, not true meaning. For real semantic
similarity or contextual embeddings plug in a multilingual sentence-embedding model through
`SentenceEmbeddingSimilarity` (optional, lazy import, not run in this repo's automated tests).
Evaluate any such model on dialect data before trusting it.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import List, Sequence, Tuple


def _trigrams(text: str) -> Counter:
    t = f"  {text.lower().strip()} "
    return Counter(t[i : i + 3] for i in range(len(t) - 2))


class LexicalSimilarity:
    def similarity(self, a: str, b: str) -> float:
        x, y = _trigrams(a), _trigrams(b)
        dot = sum(x[g] * y[g] for g in x)
        na = math.sqrt(sum(v * v for v in x.values()))
        nb = math.sqrt(sum(v * v for v in y.values()))
        return dot / (na * nb) if na and nb else 0.0


class SentenceEmbeddingSimilarity:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer, util
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install sentence-transformers to use this backend") from e
        self._model, self._util = SentenceTransformer(model_name), util

    def embed(self, texts: Sequence[str]):  # pragma: no cover
        return self._model.encode(list(texts))

    def similarity(self, a: str, b: str) -> float:  # pragma: no cover
        va, vb = self.embed([a, b])
        return float(self._util.cos_sim(va, vb))


def rank_candidates(candidates: Sequence[str], context: str, backend=None) -> List[Tuple[str, float]]:
    """Rank candidate glosses by similarity to the sentence context, best first."""
    be = backend or LexicalSimilarity()
    return sorted(((c, be.similarity(c, context)) for c in candidates), key=lambda x: x[1], reverse=True)
