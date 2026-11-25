"""Rule-based Javanese affix analysis, v0.

Strips a prefix and/or suffix and accepts the analysis only when the remaining stem is in the
lexicon. Surface hints for Indonesian are produced only where the mapping is regular
(-e/-ne -> -nya, -ku, -mu, di-). Nasal prefixes are reported as 'meN-'. These rules are a
starting point for review by Javanese speakers and linguists (see docs/MORPHOLOGY.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .lexicon import Lexicon
from .phonetics import normalize_orthography

PREFIXES: Dict[str, Optional[str]] = {"di": "di", "tak": "ku", "dak": "ku", "kok": "kau", "ko": "kau", "ke": None, "sa": None}
NASALS: Dict[str, List[str]] = {"ng": ["", "k", "g", "h"], "ny": ["", "s", "c"], "m": ["", "b", "p", "w"], "n": ["", "t", "th", "d", "dh"]}
SUFFIXES: Dict[str, Optional[str]] = {"ane": "nya", "ne": "nya", "ipun": "nya", "e": "nya", "ku": "ku", "mu": "mu", "ake": None, "ke": None, "en": None, "an": "an", "i": None}
MIN_STEM = 3


@dataclass
class Analysis:
    word: str
    stem: str
    gloss: str
    prefix: Optional[str]
    prefix_kind: Optional[str]  # 'affix' | 'nasal' | None
    suffix: Optional[str]
    hint: Optional[str]

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _hint(gloss: str, prefix: Optional[str], kind: Optional[str], suffix: Optional[str]) -> Optional[str]:
    """Indonesian surface hint, or None when the mapping is not regular enough to guess."""
    if " " in gloss:
        return None
    suf = ""
    if suffix:
        if SUFFIXES.get(suffix) is None:
            return None
        suf = SUFFIXES[suffix] or ""
    if kind == "nasal":
        return f"meN-{gloss}{suf}"
    pre = ""
    if prefix:
        if PREFIXES.get(prefix) is None:
            return None
        pre = PREFIXES[prefix] or ""
    return pre + gloss + suf


def analyze(word: str, lexicon: Optional[Lexicon] = None) -> List[Analysis]:
    lex = lexicon or Lexicon.default()
    w = normalize_orthography(word)
    starts: List[Tuple[Optional[str], Optional[str], List[str]]] = [(None, None, [w])]
    for p in PREFIXES:
        if w.startswith(p):
            starts.append((p, "affix", [w[len(p):]]))
    for n, restore in NASALS.items():
        if w.startswith(n):
            rest = w[len(n):]
            starts.append((n, "nasal", [r + rest for r in restore]))
    found: List[Analysis] = []
    for prefix, kind, rests in starts:
        for rest in rests:
            options: List[Tuple[Optional[str], str]] = [(None, rest)]
            options += [(s, rest[: -len(s)]) for s in SUFFIXES if rest.endswith(s)]
            for suffix, stem in options:
                if len(stem) < MIN_STEM or (prefix is None and suffix is None):
                    continue
                hits = lex.exact(stem)
                if not hits:
                    continue
                gloss = hits[0].indonesian
                found.append(Analysis(word, stem, gloss, prefix, kind, suffix, _hint(gloss, prefix, kind, suffix)))
    found.sort(key=lambda a: (-len(a.stem), (a.prefix is not None) + (a.suffix is not None)))
    seen, uniq = set(), []
    for a in found:
        key = (a.stem, a.prefix, a.suffix)
        if key not in seen:
            seen.add(key); uniq.append(a)
    return uniq
