"""Lexicon of Javanese forms mapped to Indonesian glosses.

TSV columns: form, register, dialect, indonesian, status, variants.
`status` is `unreviewed` until reviewers sign off (see governance/DATA_GOVERNANCE.md).
`variants` is an optional comma-separated list of attested spellings or pronunciations
of the same word (for example regional or phonetic variants).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .phonetics import normalize_orthography

_TOKEN = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*", re.UNICODE)
MAX_PHRASE_TOKENS = 4


def phrase_key(form: str) -> Tuple[str, ...]:
    return tuple(normalize_orthography(t) for t in _TOKEN.findall(form))


@dataclass(frozen=True)
class Entry:
    form: str
    register: str
    dialect: str
    indonesian: str
    status: str = "unreviewed"
    variants: Tuple[str, ...] = ()


def _parse_rows(lines: Iterable[str]) -> List[Entry]:
    entries: List[Entry] = []
    rows = (r for r in lines if r.strip() and not r.startswith("#"))
    for row in csv.reader(rows, delimiter="\t"):
        if len(row) < 4:
            continue
        status = row[4].strip() if len(row) > 4 and row[4].strip() else "unreviewed"
        variants = tuple(v.strip() for v in row[5].split(",") if v.strip()) if len(row) > 5 else ()
        entries.append(Entry(row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip(), status, variants))
    return entries


def _read_words(text: str) -> List[str]:
    return [w.strip() for w in text.splitlines() if w.strip() and not w.startswith("#")]


class Lexicon:
    def __init__(self, entries: Iterable[Entry], protected: Iterable[str] = ()):
        self.entries: List[Entry] = list(entries)
        self._index: Dict[str, List[Entry]] = {}
        self._phrases: Dict[Tuple[str, ...], List[Entry]] = {}
        for e in self.entries:
            for form in (e.form, *e.variants):
                key = phrase_key(form)
                if len(key) >= 2:  # multi-word expression
                    bucket = self._phrases.setdefault(key, [])
                else:
                    bucket = self._index.setdefault(normalize_orthography(form), [])
                if e not in bucket:
                    bucket.append(e)
        self.max_phrase_len = max((len(k) for k in self._phrases), default=1)
        # Indonesian words that must never be rewritten (minus any that are also
        # lexicon forms, so deliberate entries still win).
        self.protected: Set[str] = {normalize_orthography(w) for w in protected} - set(self._index)

    def exact(self, norm_form: str) -> List[Entry]:
        return self._index.get(norm_form, [])

    def phrase(self, key: Tuple[str, ...]) -> List[Entry]:
        return self._phrases.get(key, [])

    def forms(self) -> List[str]:
        return list(self._index)

    def __len__(self) -> int:
        return len(self.entries)

    @classmethod
    def from_files(cls, tsv_path: Path, protected_path: Optional[Path] = None) -> "Lexicon":
        entries = _parse_rows(Path(tsv_path).read_text(encoding="utf-8").splitlines())
        protected: List[str] = []
        if protected_path:
            protected = _read_words(Path(protected_path).read_text(encoding="utf-8"))
        return cls(entries, protected)

    @classmethod
    def default(cls) -> "Lexicon":
        pkg = resources.files("wanda") / "data"
        entries = _parse_rows((pkg / "jv_id_seed.tsv").read_text(encoding="utf-8").splitlines())
        protected = _read_words((pkg / "id_common_words.txt").read_text(encoding="utf-8"))
        return cls(entries, protected)


KNOWN_REGISTERS = {"ngoko", "madya", "krama", "krama-inggil"}
KNOWN_STATUS = {"unreviewed", "reviewed", "disputed"}


def validate_tsv(tsv_path: Path, protected_path: Optional[Path] = None) -> List[str]:
    """Return a list of human-readable problems found in a lexicon TSV (empty = OK).

    Meant for non-programmers who edit the file by hand: the most common mistake is
    typing spaces instead of a TAB between columns.
    """
    if protected_path:
        words = _read_words(Path(protected_path).read_text(encoding="utf-8"))
    else:
        pkg = resources.files("wanda") / "data"
        words = _read_words((pkg / "id_common_words.txt").read_text(encoding="utf-8"))
    protected = {normalize_orthography(w) for w in words}
    problems: List[str] = []
    seen: Dict[str, str] = {}
    with open(tsv_path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 4:
                problems.append(f"line {n}: expected 4 to 6 TAB-separated columns, found {len(cols)} (did you type spaces instead of a TAB?)")
                continue
            form, register, dialect, gloss = (c.strip() for c in cols[:4])
            status = cols[4].strip() if len(cols) > 4 and cols[4].strip() else "unreviewed"
            variants = [v.strip() for v in cols[5].split(",") if v.strip()] if len(cols) > 5 else []
            if not form or not gloss:
                problems.append(f"line {n}: form and Indonesian gloss must not be empty")
            for f in [form, *variants]:
                if len(phrase_key(f)) > MAX_PHRASE_TOKENS:
                    problems.append(f"line {n}: '{f}' has more than {MAX_PHRASE_TOKENS} words; shorter expressions only")
            if register not in KNOWN_REGISTERS:
                problems.append(f"line {n}: register '{register}' not one of {sorted(KNOWN_REGISTERS)}")
            if status not in KNOWN_STATUS:
                problems.append(f"line {n}: status '{status}' not one of {sorted(KNOWN_STATUS)}")
            for f in [form, *variants]:
                if normalize_orthography(f) in protected:
                    problems.append(f"line {n}: '{f}' is also a common Indonesian word and would never be rewritten; remove it or discuss in an issue")
            key = normalize_orthography(form)
            if key in seen and seen[key] != gloss:
                problems.append(f"line {n}: '{form}' already listed with a different meaning '{seen[key]}'; Wanda will flag it as ambiguous")
            seen.setdefault(key, gloss)
    return problems
