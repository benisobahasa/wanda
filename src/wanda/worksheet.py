"""Dialect worksheets: a spreadsheet a native speaker fills in, then imports into the lexicon.

`make_worksheet` lists every standard entry with empty columns for how the dialect says it.
`import_worksheet` turns the filled rows into lexicon entries tagged with the dialect (status
`unreviewed`, so other speakers still review them). Nothing is invented: only what a speaker types is imported.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional

from .lexicon import Lexicon, validate_tsv
from .phonetics import normalize_orthography

COLUMNS = ["standard_form", "register", "indonesian", "dialect_form", "dialect_variants", "pronunciation_note", "notes"]
INSTRUCTIONS = [
    "# PETUNJUK. Isi hanya kolom dialect_form dan seterusnya. Kolom lain jangan diubah.",
    "# dialect_form: kata ini diucapkan atau ditulis apa di dialek Anda? Tulis tanda sama dengan (=) jika sama dengan bentuk standar.",
    "# Kosongkan baris jika Anda tidak yakin atau tidak memakai kata itu. Jangan menebak.",
    "# dialect_variants: ejaan atau lafal lain yang Anda dengar. Pisahkan dengan titik koma (;).",
    "# pronunciation_note: catatan lafal (misalnya vokal akhir). notes: catatan lain atau contoh kalimat.",
    "# Baris dengan tanda pagar di awal diabaikan. Simpan sebagai CSV (UTF-8) lalu jalankan: wanda dialect-import file.csv",
]


def make_worksheet(lexicon: Lexicon, out_path: Path, fmt: str = "csv") -> int:
    rows = [e for e in lexicon.entries if e.dialect == "standard"]
    delim = "\t" if fmt == "tsv" else ","
    enc = "utf-8" if fmt == "tsv" else "utf-8-sig"  # the BOM makes Excel read UTF-8 correctly
    with open(out_path, "w", encoding=enc, newline="") as fh:
        w = csv.writer(fh, delimiter=delim)
        for line in INSTRUCTIONS:
            w.writerow([line])
        w.writerow(COLUMNS)
        for e in rows:
            w.writerow([e.form, e.register, e.indonesian, "", "", "", ""])
    return len(rows)


def read_worksheet(path: Path) -> List[Dict[str, str]]:
    p = Path(path)
    delim = "\t" if p.suffix.lower() == ".tsv" else ","
    out: List[Dict[str, str]] = []
    header: Optional[List[str]] = None
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for row in csv.reader(fh, delimiter=delim):
            if not row or not "".join(row).strip() or row[0].lstrip().startswith("#"):
                continue
            if header is None:
                header = [c.strip() for c in row]
                missing = [c for c in COLUMNS if c not in header]
                if missing:
                    raise ValueError(f"worksheet is missing columns: {missing}")
                continue
            row = row + [""] * (len(header) - len(row))
            out.append({h: v.strip() for h, v in zip(header, row)})
    return out


def import_worksheet(path: Path, lexicon_tsv: Path, dialect: str = "pantura-rembang",
                     dry_run: bool = False, notes_dir: Optional[Path] = None) -> dict:
    lex = Lexicon.from_files(Path(lexicon_tsv))
    existing = {(normalize_orthography(e.form), e.indonesian) for e in lex.entries}
    protected = Lexicon.default().protected | lex.protected
    res = {"added": 0, "confirmed_same": 0, "empty": 0, "duplicates": 0, "skipped_protected": [], "invalid": [], "problems": []}
    new_lines: List[str] = []
    notes: List[Dict[str, str]] = []
    for r in read_worksheet(path):
        form = r.get("dialect_form", "")
        if r.get("pronunciation_note") or r.get("notes"):
            notes.append({"standard_form": r["standard_form"], "dialect_form": form, "pronunciation": r.get("pronunciation_note", ""), "notes": r.get("notes", "")})
        if not form:
            res["empty"] += 1
            continue
        if form == "=":
            res["confirmed_same"] += 1
            continue
        if re.search(r"[\t\n]", form) or not re.search(r"\w", form):
            res["invalid"].append(form)
            continue
        key = (normalize_orthography(form), r["indonesian"])
        if key in existing:
            res["duplicates"] += 1
            continue
        if normalize_orthography(form) in protected:
            res["skipped_protected"].append(form)
            continue
        variants = [v.strip() for v in re.split(r"[;,]", r.get("dialect_variants", "")) if v.strip() and v.strip() != form]
        line = "\t".join([form, r["register"], dialect, r["indonesian"], "unreviewed"] + ([",".join(variants)] if variants else []))
        new_lines.append(line)
        existing.add(key)
        res["added"] += 1
    if dry_run:
        return res
    if new_lines:
        lines = Path(lexicon_tsv).read_text(encoding="utf-8").split("\n")
        at = next((i for i, l in enumerate(lines) if l.startswith("# -----")), len(lines))
        lines[at:at] = new_lines
        Path(lexicon_tsv).write_text("\n".join(lines), encoding="utf-8")
        res["problems"] = validate_tsv(Path(lexicon_tsv))
    if notes and notes_dir:
        d = Path(notes_dir)
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{dialect}.md"
        head = "" if f.exists() else f"# Notes for dialect: {dialect}\n\n| standard | {dialect} | pronunciation | notes |\n|---|---|---|---|\n"
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(head + "".join(f"| {n['standard_form']} | {n['dialect_form']} | {n['pronunciation']} | {n['notes']} |\n" for n in notes))
        res["notes_written"] = len(notes)
    return res
