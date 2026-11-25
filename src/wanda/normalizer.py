"""Core: map Javanese/dialect tokens in an STT transcript to Indonesian meaning.

Design choices (see docs/ARCHITECTURE.md):
  * Conservative by default. A word is rewritten only when confidence is high.
  * Known Indonesian words are protected and never rewritten.
  * Every decision is reported so a downstream LLM (or a human) can see it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .lexicon import Entry, Lexicon
from .phonetics import normalize_orthography, similarity, to_units, weighted_distance

_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*", re.UNICODE)


@dataclass
class TokenResult:
    original: str
    kind: str  # exact | fuzzy | protected | unknown
    score: float = 0.0
    entry: Optional[Entry] = None
    alternatives: List[Entry] = field(default_factory=list)
    applied: bool = False
    output: str = ""
    start: int = -1
    end: int = -1

    def as_dict(self) -> dict:
        return {
            "original": self.original,
            "output": self.output,
            "kind": self.kind,
            "score": round(self.score, 3),
            "applied": self.applied,
            "gloss": self.entry.indonesian if self.entry else None,
            "register": self.entry.register if self.entry else None,
            "dialect": self.entry.dialect if self.entry else None,
            "matched_form": self.entry.form if self.entry else None,
            "ambiguous": bool(self.alternatives),
            "status": self.entry.status if self.entry else None,
            "span": [self.start, self.end],
        }


def _match_case(original: str, replacement: str) -> str:
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


class Normalizer:
    def __init__(
        self,
        lexicon: Optional[Lexicon] = None,
        min_confidence: float = 0.75,
        fuzzy: bool = True,
        max_cost_ratio: float = 0.34,
    ):
        self.lexicon = lexicon or Lexicon.default()
        self.min_confidence = min_confidence
        self.fuzzy = fuzzy
        self.max_cost_ratio = max_cost_ratio

    # -- single word ---------------------------------------------------
    def analyze_word(self, word: str) -> TokenResult:
        norm = normalize_orthography(word)
        hits = self.lexicon.exact(norm)
        if hits:
            return self._result(word, "exact", 1.0, hits)
        if norm in self.lexicon.protected:
            return TokenResult(word, "protected", 1.0, output=word)
        units = to_units(word)
        if self.fuzzy and len(units) >= 3:
            best, best_cost, tied = None, None, []
            for form in self.lexicon.forms():
                fu = to_units(form)
                cost = weighted_distance(units, fu)
                if cost > self.max_cost_ratio * max(len(units), len(fu)):
                    continue
                if best_cost is None or cost < best_cost - 1e-9:
                    best, best_cost, tied = form, cost, [form]
                elif abs(cost - best_cost) <= 1e-9:
                    tied.append(form)
            if best is not None:
                score = similarity(word, best)
                entries = self.lexicon.exact(best)
                glosses = {e.indonesian for t in tied for e in self.lexicon.exact(t)}
                res = self._result(word, "fuzzy", score, entries)
                if len(glosses) > 1:  # equally good but different meanings
                    res.alternatives = [e for t in tied for e in self.lexicon.exact(t)]
                    res.applied = False
                    res.output = word
                return res
        return TokenResult(word, "unknown", 0.0, output=word)

    def _result(self, word: str, kind: str, score: float, hits: List[Entry]) -> TokenResult:
        glosses = {h.indonesian for h in hits}
        res = TokenResult(word, kind, score, hits[0], list(hits[1:]) if len(glosses) > 1 else [])
        res.applied = score >= self.min_confidence and len(glosses) == 1
        res.output = _match_case(word, hits[0].indonesian) if res.applied else word
        return res

    # -- text ----------------------------------------------------------
    def analyze(self, text: str) -> List[TokenResult]:
        """Analyse text; multi-word expressions are matched first (longest match wins)."""
        ms = list(_WORD.finditer(text))
        out: List[TokenResult] = []
        i, maxlen = 0, self.lexicon.max_phrase_len
        while i < len(ms):
            done = False
            for length in range(min(maxlen, len(ms) - i), 1, -1):
                seg = ms[i : i + length]
                if any(text[seg[k].end() : seg[k + 1].start()].strip() for k in range(length - 1)):
                    continue  # punctuation between the words: not a phrase
                hits = self.lexicon.phrase(tuple(normalize_orthography(m.group(0)) for m in seg))
                if hits:
                    r = self._result(text[seg[0].start() : seg[-1].end()], "phrase", 1.0, hits)
                    r.start, r.end = seg[0].start(), seg[-1].end()
                    out.append(r)
                    i += length
                    done = True
                    break
            if not done:
                r = self.analyze_word(ms[i].group(0))
                r.start, r.end = ms[i].span()
                out.append(r)
                i += 1
        return out

    def normalize(self, text: str) -> str:
        out, last = [], 0
        for r in self.analyze(text):
            out.append(text[last : r.start])
            out.append(r.output)
            last = r.end
        out.append(text[last:])
        return "".join(out)

    def annotate(self, text: str) -> dict:
        """Return everything a downstream LLM or reviewer needs."""
        tokens = self.analyze(text)
        normalized = self.normalize(text)
        notes = [
            f"{t.original} -> {t.output} ({t.entry.register}, {t.entry.dialect}, {t.kind} {t.score:.2f})"
            for t in tokens
            if t.applied
        ]
        flagged = [
            f"{t.original}: ambiguous between "
            + ", ".join(sorted({e.indonesian for e in [t.entry, *t.alternatives]}))
            for t in tokens
            if t.alternatives
        ]
        context = (
            f"[STT transcript, may contain Javanese or dialect words]: {text}\n"
            f"[Probable Indonesian meaning]: {normalized}\n"
        )
        if notes:
            context += "[Rewrites]: " + "; ".join(notes) + "\n"
        if flagged:
            context += "[Ambiguous, check context]: " + "; ".join(flagged) + "\n"
        return {
            "original": text,
            "normalized": normalized,
            "tokens": [t.as_dict() for t in tokens],
            "llm_context": context.rstrip("\n"),
        }
