"""Clean plain-text corpora (for example text extracted from a Wikipedia dump) for n-gram training.

Wanda never downloads or bundles corpora. You supply the text, you check its licence, and the
cleaner writes a NOTICE file next to the output recording the source and licence terms you declare.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterable, List

_TAGS = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+|www\.\S+")
_WIKI = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]|\{\{[^}]*\}\}|={2,}[^=]+={2,}")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_LETTER_RATIO_MIN = 0.8


def clean_text(text: str) -> str:
    text = _TAGS.sub(" ", text)
    text = _WIKI.sub(lambda m: m.group(1) or " ", text)
    text = _URL.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def sentences(text: str, min_words: int = 4) -> List[str]:
    out = []
    for s in _SENT.split(clean_text(text)):
        s = s.strip()
        if not s:
            continue
        words = s.split()
        letters = sum(ch.isalpha() or ch.isspace() for ch in s)
        if len(words) >= min_words and letters / len(s) >= _LETTER_RATIO_MIN:
            out.append(s)
    return out


def build_corpus(inputs: Iterable[Path], out_path: Path, source: str, licence: str, min_words: int = 4) -> dict:
    seen, kept, total = set(), [], 0
    for p in inputs:
        for s in sentences(Path(p).read_text(encoding="utf-8", errors="replace"), min_words):
            total += 1
            key = s.lower()
            if key not in seen:
                seen.add(key)
                kept.append(s)
    out_path = Path(out_path)
    out_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    notice = out_path.with_suffix(out_path.suffix + ".NOTICE.md")
    notice.write_text(
        f"# Corpus notice\n\n* File: {out_path.name}\n* Source: {source}\n* Licence declared by the person who prepared it: {licence}\n"
        f"* Prepared: {date.today().isoformat()}\n* Sentences kept: {len(kept)} (of {total} candidates; duplicates removed)\n\n"
        "Attribution and share-alike duties of the source licence still apply to this text and may apply to "
        "models trained on it. Check them before publishing a model. This corpus is not part of Wanda.\n",
        encoding="utf-8")
    return {"sentences": len(kept), "candidates": total, "output": str(out_path), "notice": str(notice)}
