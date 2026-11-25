"""Re-rank ASR hypotheses using lexicon coverage and (optionally) an n-gram language model."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .normalizer import Normalizer


def coverage(text: str, normalizer: Normalizer) -> float:
    toks = normalizer.analyze(text)
    if not toks:
        return 0.0
    total = 0.0
    for t in toks:
        if t.kind in ("exact", "protected", "phrase"):
            total += 1.0
        elif t.kind == "fuzzy":
            total += 0.5 * t.score
    return total / len(toks)


def rescore_nbest(
    hypotheses: Sequence[Tuple[str, float]],
    normalizer: Normalizer,
    weight: float = 0.5,
    lm=None,
    lm_weight: float = 0.1,
) -> List[Tuple[str, float]]:
    """hypotheses: (text, asr_score in 0..1, higher is better). Best first.

    final = asr_score + weight * lexicon_coverage + lm_weight * average_log_probability
    The language-model term is skipped when `lm` is None.
    """
    scored = []
    for text, asr in hypotheses:
        s = asr + weight * coverage(text, normalizer)
        if lm is not None:
            s += lm_weight * lm.avg_logprob(text)
        scored.append((text, s))
    return sorted(scored, key=lambda x: x[1], reverse=True)
