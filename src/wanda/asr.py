"""ASR integration layer: plug any speech-to-text engine into Wanda.

Core code needs no ML libraries. `FasterWhisperAdapter` and `TransformersWhisperAdapter` import
their libraries lazily and are OPTIONAL. They have not been run against real audio in this
repository's automated tests; the tests use a fake adapter. Whisper's language code for
Javanese is 'jw'. Check the result on your own audio before relying on it.
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

from pathlib import Path

from .evaluate import wer
from .normalizer import Normalizer
from .rescore import rescore_nbest

Hypotheses = List[Tuple[str, float]]


class STTAdapter:
    """Interface: return (text, score in 0..1) hypotheses, best first if the engine ranks them."""

    def transcribe_nbest(self, audio_path: str) -> Hypotheses:  # pragma: no cover - interface
        raise NotImplementedError


class FunctionAdapter(STTAdapter):
    """Wrap any callable (for example one that calls your own STT service)."""

    def __init__(self, fn: Callable[[str], Sequence[Tuple[str, float]]]):
        self.fn = fn

    def transcribe_nbest(self, audio_path: str) -> Hypotheses:
        return list(self.fn(audio_path))


class FasterWhisperAdapter(STTAdapter):
    def __init__(self, model_size: str = "small", language: str = "jw", beam_size: int = 5,
                 device: str = "auto", compute_type: str = "int8"):
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install faster-whisper to use this adapter") from e
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language, self.beam_size = language, beam_size

    def transcribe_nbest(self, audio_path: str) -> Hypotheses:  # pragma: no cover
        segments, _ = self.model.transcribe(audio_path, language=self.language, beam_size=self.beam_size)
        segs = list(segments)
        text = " ".join(s.text.strip() for s in segs).strip()
        score = sum(math.exp(s.avg_logprob) for s in segs) / len(segs) if segs else 0.0
        return [(text, score)]


class TransformersWhisperAdapter(STTAdapter):
    def __init__(self, model_id: str = "openai/whisper-small", language: str = "javanese"):
        try:
            from transformers import pipeline
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install transformers torch to use this adapter") from e
        self.pipe = pipeline("automatic-speech-recognition", model=model_id)
        self.language = language

    def transcribe_nbest(self, audio_path: str) -> Hypotheses:  # pragma: no cover
        out = self.pipe(audio_path, generate_kwargs={"language": self.language, "task": "transcribe"})
        return [(out["text"].strip(), 0.5)]


def process_audio(audio_path: str, adapter: STTAdapter, normalizer: Optional[Normalizer] = None,
                  lm=None, lm_weight: float = 0.1) -> dict:
    """audio -> STT hypotheses -> re-rank -> Wanda annotation of the best one."""
    norm = normalizer or Normalizer()
    hyps = adapter.transcribe_nbest(audio_path)
    if not hyps:
        raise ValueError("the STT adapter returned no hypotheses")
    ranked = rescore_nbest(hyps, norm, lm=lm, lm_weight=lm_weight)
    best = ranked[0][0]
    return {"best": best, "ranked": [{"text": t, "score": round(s, 4)} for t, s in ranked], **norm.annotate(best)}


def evaluate_adapter(adapter: STTAdapter, manifest: Path, normalizer: Optional[Normalizer] = None,
                     lm=None, lm_weight: float = 0.1) -> dict:
    """Run an STT adapter over recordings and compare the engine's own top transcript with Wanda's output.

    Manifest TSV: audio_path <TAB> reference_indonesian [<TAB> dialect]. Relative audio paths are resolved
    against the manifest's folder. References are the Indonesian MEANING of what was said, as in the
    other evaluation files. Only use recordings made with the speakers' consent (governance/).
    """
    norm = normalizer or Normalizer()
    base = Path(manifest).parent
    status, items = "unspecified", []
    for line in Path(manifest).read_text(encoding="utf-8").splitlines():
        if line.startswith("# status:"):
            status = line.split(":", 1)[1].strip()
            continue
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) < 2:
            continue
        path = Path(c[0]) if Path(c[0]).is_absolute() else base / c[0]
        dialect = c[2].strip() if len(c) > 2 and c[2].strip() else "unspecified"
        hyps = adapter.transcribe_nbest(str(path))
        if not hyps:
            continue
        ranked = rescore_nbest(hyps, norm, lm=lm, lm_weight=lm_weight)
        raw_best, wanda_text = hyps[0][0], norm.normalize(ranked[0][0])
        items.append({"audio": c[0], "dialect": dialect, "raw": raw_best, "wanda": wanda_text,
                      "reference": c[1], "raw_wer": wer(c[1], raw_best), "wanda_wer": wer(c[1], wanda_text)})
    def mean(xs): return sum(xs) / len(xs) if xs else 0.0
    per = {}
    for it in items:
        per.setdefault(it["dialect"], []).append(it)
    return {"status": status, "n": len(items), "raw_wer": mean([i["raw_wer"] for i in items]),
            "wanda_wer": mean([i["wanda_wer"] for i in items]),
            "per_dialect": {d: {"n": len(v), "raw_wer": mean([i["raw_wer"] for i in v]), "wanda_wer": mean([i["wanda_wer"] for i in v])} for d, v in sorted(per.items())},
            "items": items}
