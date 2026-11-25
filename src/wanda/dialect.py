"""Dialect and speech-level (register) detection from lexicon cues.

This is deliberately simple and transparent: it counts words that the lexicon tags with a
dialect or register. With a small seed lexicon it is weak, and it improves only as reviewed
entries from more dialect areas are added. It reports its evidence so a person can judge it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .lexicon import Lexicon
from .phonetics import normalize_orthography

_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*", re.UNICODE)
ALIASES = {"rembang": "pantura-rembang", "pantura": "pantura-rembang"}
STANDARD_WEIGHT = 0.3  # a 'standard' word is weak evidence for any particular regional dialect


@dataclass
class DialectResult:
    top: str
    confidence: float
    scores: Dict[str, float]
    register: str
    registers: Dict[str, int]
    cues: List[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"dialect": self.top, "confidence": round(self.confidence, 3),
                "scores": {k: round(v, 3) for k, v in self.scores.items()},
                "register": self.register, "registers": self.registers, "cues": self.cues}


class DialectDetector:
    def __init__(self, lexicon: Optional[Lexicon] = None):
        self.lexicon = lexicon or Lexicon.default()

    def detect(self, text: str) -> DialectResult:
        scores: Dict[str, float] = {}
        registers: Dict[str, int] = {}
        cues: List[dict] = []
        for m in _WORD.finditer(text):
            for e in self.lexicon.exact(normalize_orthography(m.group(0))):
                dia = ALIASES.get(e.dialect, e.dialect)
                w = STANDARD_WEIGHT if dia == "standard" else 1.0
                scores[dia] = scores.get(dia, 0.0) + w
                registers[e.register] = registers.get(e.register, 0) + 1
                cues.append({"word": m.group(0), "dialect": dia, "register": e.register})
        total = sum(scores.values())
        if total == 0:
            return DialectResult("unknown", 0.0, {}, "unknown", {}, [])
        top = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        reg = sorted(registers.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return DialectResult(top, scores[top] / total, scores, reg, registers, cues)
