"""Tiny evaluation helpers. See docs/EVALUATION.md for what these do NOT measure."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from .normalizer import Normalizer


def wer(reference: str, hypothesis: str) -> float:
    r, h = reference.lower().split(), hypothesis.lower().split()
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, start=1):
        cur = [i]
        for j, hw in enumerate(h, start=1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw)))
        prev = cur
    return prev[-1] / len(r)


def evaluate_tsv(path: Path, normalizer: Normalizer) -> Dict[str, float]:
    """TSV: asr_hypothesis <TAB> reference_indonesian. Lines starting with # are skipped."""
    base: List[float] = []
    ours: List[float] = []
    with open(path, encoding="utf-8", newline="") as fh:
        rows = (r for r in fh if r.strip() and not r.startswith("#"))
        for row in csv.reader(rows, delimiter="\t"):
            if len(row) < 2:
                continue
            hyp, ref = row[0], row[1]
            base.append(wer(ref, hyp))
            ours.append(wer(ref, normalizer.normalize(hyp)))
    n = len(base)
    return {
        "n": n,
        "baseline_wer": sum(base) / n if n else 0.0,
        "wanda_wer": sum(ours) / n if n else 0.0,
    }
