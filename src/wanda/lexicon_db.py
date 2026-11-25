"""Multidialect lexicon database (SQLite, standard library only).

The TSV file stays the editable source of truth. This module builds a queryable database from
it (words, dialects, registers, variants, IPA, review log) and can export it back to TSV.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .lexicon import Lexicon
from .phonemes import ipa
from .phonetics import normalize_orthography

SCHEMA = """
CREATE TABLE entries(id INTEGER PRIMARY KEY, form TEXT NOT NULL, norm TEXT NOT NULL, register TEXT, dialect TEXT,
                     indonesian TEXT NOT NULL, status TEXT NOT NULL, ipa TEXT);
CREATE TABLE variants(entry_id INTEGER NOT NULL REFERENCES entries(id), variant TEXT NOT NULL, norm TEXT NOT NULL);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX ix_entries_norm ON entries(norm);
CREATE INDEX ix_variants_norm ON variants(norm);
"""


def build_db(lexicon: Optional[Lexicon], db_path: Path) -> int:
    lex = lexicon or Lexicon.default()
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    for e in lex.entries:
        cur = con.execute("INSERT INTO entries(form, norm, register, dialect, indonesian, status, ipa) VALUES (?,?,?,?,?,?,?)",
                          (e.form, normalize_orthography(e.form), e.register, e.dialect, e.indonesian, e.status, " ".join(ipa(w) for w in e.form.split())))
        for v in e.variants:
            con.execute("INSERT INTO variants(entry_id, variant, norm) VALUES (?,?,?)", (cur.lastrowid, v, normalize_orthography(v)))
    con.execute("INSERT INTO meta VALUES ('built', ?)", (datetime.now(timezone.utc).isoformat(),))
    con.commit()
    con.close()
    return len(lex.entries)


def query(db_path: Path, word: str) -> List[Dict]:
    key = normalize_orthography(word)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute("""SELECT DISTINCT e.id, e.form, e.register, e.dialect, e.indonesian, e.status, e.ipa FROM entries e
                          LEFT JOIN variants v ON v.entry_id = e.id WHERE e.norm = ? OR v.norm = ?""", (key, key)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["variants"] = [x[0] for x in con.execute("SELECT variant FROM variants WHERE entry_id = ?", (r["id"],))]
        del d["id"]
        out.append(d)
    con.close()
    return out


def stats(db_path: Path) -> Dict:
    con = sqlite3.connect(db_path)
    by = lambda col: dict(con.execute(f"SELECT {col}, COUNT(*) FROM entries GROUP BY {col}").fetchall())
    res = {"entries": con.execute("SELECT COUNT(*) FROM entries").fetchone()[0], "variants": con.execute("SELECT COUNT(*) FROM variants").fetchone()[0],
           "by_dialect": by("dialect"), "by_register": by("register"), "by_status": by("status")}
    con.close()
    return res


def export_tsv(db_path: Path, out_path: Path) -> int:
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT id, form, register, dialect, indonesian, status FROM entries ORDER BY id").fetchall()
    lines = ["# form\tregister\tdialect\tindonesian\tstatus\tvariants (optional, comma-separated)"]
    for i, form, reg, dia, gloss, status in rows:
        variants = ",".join(x[0] for x in con.execute("SELECT variant FROM variants WHERE entry_id = ?", (i,)))
        lines.append("\t".join([form, reg, dia, gloss, status, variants]).rstrip("\t") if variants else "\t".join([form, reg, dia, gloss, status]))
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    con.close()
    return len(rows)
