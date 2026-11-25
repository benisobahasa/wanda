"""Confidence calibration tools: reliability table, expected calibration error, Platt scaling.

Wanda's confidence scores are hand-set similarity values, not probabilities. These tools measure
how far they are from observed accuracy on labelled data and can fit a simple correction. They
are only as good as the labelled data you give them (see docs/EVALUATION.md).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .normalizer import Normalizer


def reliability_table(conf: Sequence[float], correct: Sequence[bool], bins: int = 5) -> List[dict]:
    rows = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(conf) if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if not idx:
            rows.append({"lo": lo, "hi": hi, "n": 0, "mean_conf": None, "accuracy": None})
            continue
        rows.append({"lo": lo, "hi": hi, "n": len(idx),
                     "mean_conf": sum(conf[i] for i in idx) / len(idx),
                     "accuracy": sum(1 for i in idx if correct[i]) / len(idx)})
    return rows


def ece(conf: Sequence[float], correct: Sequence[bool], bins: int = 5) -> float:
    n = len(conf)
    if n == 0:
        return 0.0
    return sum(r["n"] / n * abs(r["mean_conf"] - r["accuracy"]) for r in reliability_table(conf, correct, bins) if r["n"])


class PlattScaler:
    """p = sigmoid(a * confidence + b), fitted by gradient descent on log-loss."""

    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a, self.b = a, b

    def fit(self, conf: Sequence[float], correct: Sequence[bool], iters: int = 4000, lr: float = 0.5) -> "PlattScaler":
        y = [1.0 if c else 0.0 for c in correct]
        if not y:
            return self
        if all(v == y[0] for v in y):  # one class only: cannot learn a slope
            self.a, self.b = 0.0, (3.0 if y[0] else -3.0)
            return self
        a, b, n = 0.0, 0.0, float(len(y))
        for _ in range(iters):
            ga = gb = 0.0
            for x, t in zip(conf, y):
                p = 1 / (1 + math.exp(-(a * x + b)))
                ga += (p - t) * x
                gb += (p - t)
            a -= lr * ga / n
            b -= lr * gb / n
        self.a, self.b = a, b
        return self

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b}

    @classmethod
    def from_dict(cls, d: dict) -> "PlattScaler":
        return cls(float(d["a"]), float(d["b"]))

    def predict(self, conf: float) -> float:
        return 1 / (1 + math.exp(-(self.a * conf + self.b)))


def collect_decisions(words_tsv: Path, normalizer: Normalizer) -> Dict[str, object]:
    """TSV: word <TAB> gold. gold is the expected Indonesian output, or '=' if the word must stay unchanged.

    Only decisions where Wanda actually rewrote the word are scored; abstentions are counted.
    """
    pairs: List[Tuple[float, bool]] = []
    abstained = total = 0
    with open(words_tsv, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 2:
                continue
            word, gold = cols[0], cols[1]
            gold = word if gold == "=" else gold
            r = normalizer.analyze_word(word)
            total += 1
            if r.applied:
                pairs.append((r.score, r.output.lower() == gold.lower()))
            else:
                abstained += 1
    return {"pairs": pairs, "abstained": abstained, "total": total}


def calibration_report(words_tsv: Path, normalizer: Normalizer, bins: int = 5) -> dict:
    d = collect_decisions(words_tsv, normalizer)
    conf = [p[0] for p in d["pairs"]]
    ok = [p[1] for p in d["pairs"]]
    scaler = PlattScaler().fit(conf, ok)
    return {"total": d["total"], "rewritten": len(conf), "abstained": d["abstained"],
            "accuracy_when_rewritten": (sum(ok) / len(ok)) if ok else None,
            "ece": ece(conf, ok, bins), "table": reliability_table(conf, ok, bins),
            "platt": {"a": scaler.a, "b": scaler.b}}
