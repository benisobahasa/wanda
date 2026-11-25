"""Rule-based grapheme-to-phoneme (G2P) and phoneme encoder for Javanese, v0.

IMPORTANT: this is a simplified, documented rule set, NOT a validated phonology.
Dialects differ (for example the realisation of final /a/), and the rules below follow
descriptions of standard (Solo-Yogya) Javanese. See docs/G2P_RULES.md: native speakers
and linguists are asked to review and correct every rule before it is relied on.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple

# Per-dialect switches. 'pantura-rembang' is a placeholder that copies 'standard' until a
# native speaker documents the real realisation in docs/G2P_RULES.md.
PROFILES: Dict[str, Dict[str, bool]] = {
    "standard": {"final_a_open_o": True},
    "pantura-rembang": {"final_a_open_o": True},
}

# Short names accepted for a profile or dialect tag.
PROFILE_ALIASES: Dict[str, str] = {"rembang": "pantura-rembang", "pantura": "pantura-rembang"}

_DIGRAPHS = ("ng", "ny", "dh", "th", "kh", "sy")
_CONS = {
    "b": "b", "c": "tʃ", "d": "d̪", "dh": "ɖ", "f": "f", "g": "g", "h": "h", "j": "dʒ",
    "k": "k", "kh": "x", "l": "l", "m": "m", "n": "n", "ng": "ŋ", "ny": "ɲ", "p": "p",
    "q": "k", "r": "r", "s": "s", "sy": "ʃ", "t": "t̪", "th": "ʈ", "v": "f", "w": "w",
    "y": "j", "z": "z",
}
_VOWELS = {"a": "a", "i": "i", "u": "u", "o": "o", "e": "ə", "é": "e", "è": "ɛ", "ê": "ə"}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def _graphemes(word: str) -> List[Tuple[str, str]]:
    w = unicodedata.normalize("NFC", word.lower())
    out: List[Tuple[str, str]] = []
    i = 0
    while i < len(w):
        two = w[i : i + 2]
        if two in _DIGRAPHS:
            out.append((two, "C")); i += 2
        elif w[i] in _VOWELS:
            out.append((w[i], "V")); i += 1
        elif w[i] == "x":
            out.append(("ks", "C")); i += 1
        elif w[i] in _CONS:
            out.append((w[i], "C")); i += 1
        else:
            i += 1  # apostrophes, hyphens, unknown symbols
    return out


def g2p(word: str, profile: str = "standard") -> List[str]:
    """Return a list of IPA phonemes for one Javanese word."""
    profile = PROFILE_ALIASES.get(profile, profile)
    if profile not in PROFILES:
        raise ValueError(f"unknown profile {profile!r}; choose from {sorted(PROFILES)}")
    opts = PROFILES[profile]
    gs = _graphemes(word)
    ph: List[str] = []
    for g, kind in gs:
        ph.append("ks" if g == "ks" else (_VOWELS[g] if kind == "V" else _CONS[g]))
    if not gs:
        return ph
    vowel_idx = [i for i, (_, k) in enumerate(gs) if k == "V"]
    if gs[-1][1] == "V":
        fi = len(gs) - 1
        g = gs[fi][0]
        if g == "o" or (g == "a" and opts["final_a_open_o"]):
            ph[fi] = "ɔ"
            # Penultimate open syllable /a/ or /o/ also becomes [ɔ] (vowel harmony).
            if len(vowel_idx) >= 2:
                pv = vowel_idx[-2]
                if fi - pv == 2 and gs[pv][0] in ("a", "o"):
                    ph[pv] = "ɔ"
    elif gs[-1][0] == "k":
        ph[-1] = "ʔ"  # word-final k is a glottal stop
    return ph


def ipa(word: str, profile: str = "standard") -> str:
    return "".join(g2p(word, profile))


def ipa_text(text: str, profile: str = "standard") -> List[Dict[str, str]]:
    return [{"word": m.group(0), "ipa": ipa(m.group(0), profile)} for m in _WORD.finditer(text)]


_SUB: Dict[Tuple[str, str], float] = {}
for _a, _b, _c in [
    ("a", "ɔ", 0.2), ("o", "ɔ", 0.3), ("e", "ɛ", 0.3), ("e", "ə", 0.5), ("ɛ", "ə", 0.5),
    ("u", "o", 0.5), ("i", "e", 0.5), ("b", "p", 0.4), ("d̪", "t̪", 0.4), ("ɖ", "ʈ", 0.4),
    ("g", "k", 0.4), ("d̪", "ɖ", 0.3), ("t̪", "ʈ", 0.3), ("tʃ", "dʒ", 0.4), ("k", "ʔ", 0.4), ("s", "ʃ", 0.3),
]:
    _SUB[(_a, _b)] = _SUB[(_b, _a)] = _c


def phonemic_distance(a: str, b: str, profile: str = "standard") -> float:
    """Length-normalised weighted distance between two words in phoneme space (0 = identical)."""
    x, y = g2p(a, profile), g2p(b, profile)
    if not x and not y:
        return 0.0
    prev = [float(j) for j in range(len(y) + 1)]
    for i, pa in enumerate(x, start=1):
        cur = [float(i)]
        for j, pb in enumerate(y, start=1):
            sub = 0.0 if pa == pb else _SUB.get((pa, pb), 1.0)
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + sub))
        prev = cur
    return prev[-1] / max(len(x), len(y))
