"""Human-in-the-loop lexicon review.

Reviewers (real names are NOT required; a pseudonym is fine) approve, reject or edit entries.
Decisions are appended to a review log. An entry becomes `reviewed` when at least two different
reviewers approved it and nobody rejected or edited it; any rejection or edit marks it `disputed`
for discussion. This implements the rule in governance/DATA_GOVERNANCE.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

LOG_HEADER = "# form\tindonesian\treviewer\tdecision\tsuggested\tnote\ttimestamp"
DECISIONS = ("approve", "reject", "edit")


def record(log_path: Path, form: str, indonesian: str, reviewer: str, decision: str,
           suggested: str = "", note: str = "") -> None:
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    if not reviewer.strip():
        raise ValueError("reviewer (a pseudonym is fine) is required")
    p = Path(log_path)
    new = not p.exists()
    clean = lambda s: s.replace("\t", " ").replace("\n", " ").strip()
    with open(p, "a", encoding="utf-8") as fh:
        if new:
            fh.write(LOG_HEADER + "\n")
        fh.write("\t".join([clean(form), clean(indonesian), clean(reviewer), decision, clean(suggested), clean(note),
                            datetime.now(timezone.utc).isoformat(timespec="seconds")]) + "\n")


def read_log(log_path: Path) -> List[Dict[str, str]]:
    p = Path(log_path)
    if not p.exists():
        return []
    keys = ["form", "indonesian", "reviewer", "decision", "suggested", "note", "timestamp"]
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t") + [""] * 7
        out.append(dict(zip(keys, c[:7])))
    return out


def apply_reviews(tsv_path: Path, log_path: Path, min_reviewers: int = 2) -> Dict[str, int]:
    log = read_log(log_path)
    lines = Path(tsv_path).read_text(encoding="utf-8").split("\n")
    summary = {"reviewed": 0, "disputed": 0, "unchanged": 0}
    for i, line in enumerate(lines):
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 4:
            continue
        mine = [d for d in log if d["form"] == cols[0].strip() and d["indonesian"] == cols[3].strip()]
        approvals = {d["reviewer"] for d in mine if d["decision"] == "approve"}
        objections = {d["reviewer"] for d in mine if d["decision"] in ("reject", "edit")}
        status = cols[4].strip() if len(cols) > 4 and cols[4].strip() else "unreviewed"
        new = "disputed" if objections else ("reviewed" if len(approvals) >= min_reviewers else status)
        if new == status:
            summary["unchanged"] += 1
            continue
        while len(cols) < 5:
            cols.append("")
        cols[4] = new
        lines[i] = "\t".join(cols)
        summary[new] += 1
    Path(tsv_path).write_text("\n".join(lines), encoding="utf-8")
    return summary


def run_session(tsv_path: Path, log_path: Path, reviewer: str,
                ask: Callable[[str], str] = input, say: Callable[[str], None] = print,
                limit: Optional[int] = None) -> int:
    """Interactive review of entries this reviewer has not yet judged. Returns decisions made."""
    done = {(d["form"], d["indonesian"]) for d in read_log(log_path) if d["reviewer"] == reviewer}
    todo = []
    for line in Path(tsv_path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        status = c[4].strip() if len(c) > 4 and c[4].strip() else "unreviewed"
        if len(c) >= 4 and status != "reviewed" and (c[0].strip(), c[3].strip()) not in done:
            todo.append(c)
    n = 0
    for c in todo[: limit or len(todo)]:
        say(f"\n{c[0]}  [{c[1]}, {c[2]}]  =  {c[3]}")
        while True:
            a = ask("[a]pprove  [e]dit  [r]eject  [s]kip  [q]uit > ").strip().lower()
            if a in ("a", "approve"):
                record(log_path, c[0], c[3], reviewer, "approve"); n += 1; break
            if a in ("e", "edit"):
                s = ask("Correct Indonesian meaning: ").strip()
                record(log_path, c[0], c[3], reviewer, "edit", suggested=s, note=ask("Note (optional): ")); n += 1; break
            if a in ("r", "reject"):
                record(log_path, c[0], c[3], reviewer, "reject", note=ask("Why? ")); n += 1; break
            if a in ("s", "skip"):
                break
            if a in ("q", "quit"):
                return n
    return n


def import_log(src_path: Path, dest_log: Path, lexicon_tsv: Path) -> Dict[str, int]:
    """Merge a review log exported from the web review page (or a colleague) into the main log.

    Skips exact duplicates, rows for entries that are not in the lexicon, and invalid rows.
    """
    known = set()
    for line in Path(lexicon_tsv).read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        if line.strip() and not line.startswith("#") and len(c) >= 4:
            known.add((c[0].strip(), c[3].strip()))
    existing = {(d["form"], d["indonesian"], d["reviewer"], d["decision"], d["suggested"]) for d in read_log(dest_log)}
    counts = {"added": 0, "duplicates": 0, "unknown_entries": 0, "invalid": 0}
    for d in read_log(src_path):
        if d["decision"] not in DECISIONS or not d["reviewer"].strip():
            counts["invalid"] += 1
            continue
        if (d["form"], d["indonesian"]) not in known:
            counts["unknown_entries"] += 1
            continue
        key = (d["form"], d["indonesian"], d["reviewer"], d["decision"], d["suggested"])
        if key in existing:
            counts["duplicates"] += 1
            continue
        record(dest_log, d["form"], d["indonesian"], d["reviewer"], d["decision"], d["suggested"], d["note"])
        existing.add(key)
        counts["added"] += 1
    return counts
