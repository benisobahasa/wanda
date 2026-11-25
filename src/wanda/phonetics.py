"""Orthography-aware units and a weighted edit distance.

The substitution costs below encode confusions that are common when a speech
recognizer trained mostly on standard Indonesian hears Javanese (for example
a/o alternation, voiced/unvoiced pairs, dropped final glottal 'k' or 'h').
They are hand-set starting values. They are meant to be tuned against
community-reviewed evaluation data (see docs/EVALUATION.md), not trusted as-is.
"""
from __future__ import annotations

import unicodedata
from typing import List

DIGRAPHS = ("ng", "ny", "dh", "th", "kh", "sy")


def normalize_orthography(word: str) -> str:
    """Lowercase, strip diacritics (é è ê -> e) and apostrophes."""
    w = unicodedata.normalize("NFD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return w.replace("'", "").replace("\u2019", "")


def to_units(word: str) -> List[str]:
    """Split into phoneme-like units, keeping digraphs such as ng, ny, dh, th."""
    w = normalize_orthography(word)
    units: List[str] = []
    i = 0
    while i < len(w):
        if w[i : i + 2] in DIGRAPHS:
            units.append(w[i : i + 2])
            i += 2
        else:
            units.append(w[i])
            i += 1
    return units


_SUB: dict = {}


def _pair(a: str, b: str, cost: float) -> None:
    _SUB[(a, b)] = cost
    _SUB[(b, a)] = cost


for _a, _b, _c in [
    ("a", "o", 0.35),
    ("u", "o", 0.5),
    ("e", "i", 0.5),
    ("d", "dh", 0.2),
    ("t", "th", 0.2),
    ("dh", "th", 0.5),
    ("k", "kh", 0.2),
    ("s", "sy", 0.3),
    ("b", "p", 0.5),
    ("d", "t", 0.5),
    ("g", "k", 0.5),
    ("c", "j", 0.5),
]:
    _pair(_a, _b, _c)

_CHEAP_INDEL = {"h": 0.3, "k": 0.3}


def sub_cost(a: str, b: str) -> float:
    if a == b:
        return 0.0
    return _SUB.get((a, b), 1.0)


def indel_cost(u: str) -> float:
    return _CHEAP_INDEL.get(u, 1.0)


def weighted_distance(a: List[str], b: List[str]) -> float:
    """Weighted Levenshtein distance over phoneme-like units."""
    prev = [0.0]
    for ub in b:
        prev.append(prev[-1] + indel_cost(ub))
    for ua in a:
        cur = [prev[0] + indel_cost(ua)]
        for j, ub in enumerate(b, start=1):
            cur.append(
                min(
                    prev[j] + indel_cost(ua),
                    cur[j - 1] + indel_cost(ub),
                    prev[j - 1] + sub_cost(ua, ub),
                )
            )
        prev = cur
    return prev[-1]


def similarity(a: str, b: str) -> float:
    """1.0 = identical, 0.0 = nothing in common (length-normalised)."""
    ua, ub = to_units(a), to_units(b)
    longest = max(len(ua), len(ub))
    if longest == 0:
        return 1.0
    return max(0.0, 1.0 - weighted_distance(ua, ub) / longest)
