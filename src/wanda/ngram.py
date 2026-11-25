"""Small interpolated n-gram language model, trainable on any plain-text corpus.

Use it to re-rank speech-recognition hypotheses. Check the licence of any corpus you train on
(for example Wikipedia text is CC BY-SA) and note that formal written text may under-represent
spoken dialects. Training data and models are never bundled with Wanda.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_TOK = re.compile(r"[^\W\d_]+", re.UNICODE)
BOS, EOS = "<s>", "</s>"
_DEFAULT_LAMBDAS = {1: (1.0,), 2: (0.7, 0.3), 3: (0.6, 0.3, 0.1)}


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOK.findall(text)]


class NGramLM:
    def __init__(self, order: int = 3, k: float = 0.1, lambdas: Optional[Tuple[float, ...]] = None):
        if order not in _DEFAULT_LAMBDAS:
            raise ValueError("order must be 1, 2 or 3")
        self.order, self.k = order, k
        self.lambdas = tuple(lambdas) if lambdas else _DEFAULT_LAMBDAS[order]
        self.counts: List[Counter] = [Counter() for _ in range(order + 1)]
        self.hist: List[Counter] = [Counter() for _ in range(order + 1)]
        self.vocab: set = set()

    def train(self, sentences: Iterable[str]) -> "NGramLM":
        for s in sentences:
            words = tokenize(s)
            if not words:
                continue
            toks = [BOS] * (self.order - 1) + words + [EOS]
            for i in range(self.order - 1, len(toks)):
                self.vocab.add(toks[i])
                for n in range(1, self.order + 1):
                    gram = tuple(toks[i - n + 1 : i + 1])
                    self.counts[n][gram] += 1
                    self.hist[n][gram[:-1]] += 1
        return self

    def _p(self, word: str, history: Tuple[str, ...]) -> float:
        v = len(self.vocab) + 1
        total = 0.0
        for n, lam in zip(range(self.order, 0, -1), self.lambdas):
            h = history[len(history) - (n - 1):] if n > 1 else ()
            num = self.counts[n].get(h + (word,), 0)
            den = self.hist[n].get(h, 0)
            if n == 1:
                p = (num + self.k) / (den + self.k * v)
            else:
                p = num / den if den > 0 else 0.0
            total += lam * p
        return total

    def logprob(self, sentence: str) -> float:
        words = tokenize(sentence)
        toks = [BOS] * (self.order - 1) + words + [EOS]
        lp = 0.0
        for i in range(self.order - 1, len(toks)):
            lp += math.log(max(self._p(toks[i], tuple(toks[i - self.order + 1 : i])), 1e-12))
        return lp

    def avg_logprob(self, sentence: str) -> float:
        return self.logprob(sentence) / (len(tokenize(sentence)) + 1)

    def perplexity(self, sentence: str) -> float:
        return math.exp(-self.avg_logprob(sentence))

    def evaluate(self, sentences: Iterable[str]) -> Dict[str, float]:
        """Average per-token log probability and perplexity on held-out sentences."""
        lps = [self.avg_logprob(x) for x in sentences if tokenize(x)]
        if not lps:
            return {"sentences": 0, "mean_avg_logprob": 0.0, "perplexity": float("inf")}
        m = sum(lps) / len(lps)
        return {"sentences": len(lps), "mean_avg_logprob": m, "perplexity": math.exp(-m)}

    def save(self, path: Path) -> None:
        data = {"order": self.order, "k": self.k, "lambdas": list(self.lambdas), "vocab": sorted(self.vocab),
                "counts": [{" ".join(g): c for g, c in cn.items()} for cn in self.counts],
                "hist": [{" ".join(g): c for g, c in hs.items()} for hs in self.hist]}
        Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "NGramLM":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        lm = cls(d["order"], d["k"], tuple(d["lambdas"]))
        lm.vocab = set(d["vocab"])
        lm.counts = [Counter({tuple(g.split(" ")) if g else (): c for g, c in cn.items()}) for cn in d["counts"]]
        lm.hist = [Counter({tuple(g.split(" ")) if g else (): c for g, c in hs.items()}) for hs in d["hist"]]
        return lm
