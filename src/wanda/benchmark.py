"""Automated benchmarking: raw STT output versus Wanda, with per-dialect results and a harm rate.

Dataset TSV: asr_hypothesis <TAB> reference_indonesian [<TAB> dialect]. A line '# status: <x>'
declares where the data came from: 'synthetic' or 'reviewed'. Reports always print that status.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .evaluate import wer
from .normalizer import Normalizer

_WORD = re.compile(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)*", re.UNICODE)


def load_dataset(path: Path) -> dict:
    status, rows = "unspecified", []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("# status:"):
            status = line.split(":", 1)[1].strip()
            continue
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) >= 2:
            rows.append((c[0], c[1], c[2].strip() if len(c) > 2 and c[2].strip() else "unspecified"))
    return {"name": Path(path).stem, "status": status, "rows": rows}


def _harm(hyp: str, ref: str, n: Normalizer):
    ref_tokens = {t.lower() for t in _WORD.findall(ref)}
    correct = harm = 0
    for r in n.analyze(hyp):
        if r.original.lower() in ref_tokens:
            correct += 1
            if r.output.lower() != r.original.lower():
                harm += 1
    return correct, harm


def run_benchmark(path: Path) -> dict:
    p = Path(path)
    files = sorted(f for f in (p.glob("*.tsv") if p.is_dir() else [p]) if not f.name.startswith("words_"))
    systems: Dict[str, Optional[Normalizer]] = {"raw STT": None, "Wanda": Normalizer(), "Wanda (strict)": Normalizer(fuzzy=False)}
    out = {"datasets": []}
    for f in files:
        ds = load_dataset(f)
        res = {"name": ds["name"], "status": ds["status"], "n": len(ds["rows"]), "systems": {}}
        for sname, norm in systems.items():
            per: Dict[str, List[float]] = {}
            allw: List[float] = []
            correct = harm = 0
            for hyp, ref, dia in ds["rows"]:
                w = wer(ref, hyp if norm is None else norm.normalize(hyp))
                allw.append(w)
                per.setdefault(dia, []).append(w)
                if norm is not None:
                    c, h = _harm(hyp, ref, norm)
                    correct += c
                    harm += h
            res["systems"][sname] = {
                "wer": sum(allw) / len(allw) if allw else 0.0,
                "per_dialect": {k: sum(v) / len(v) for k, v in sorted(per.items())},
                "harm_rate": (harm / correct) if (norm is not None and correct) else (0.0 if norm is not None else None),
            }
        out["datasets"].append(res)
    return out


def to_markdown(result: dict) -> str:
    lines = ["# Wanda benchmark report", ""]
    for d in result["datasets"]:
        lines += [f"## {d['name']} ({d['n']} utterances)", ""]
        if d["status"] != "reviewed":
            lines += [f"> **Data status: {d['status']}.** Not community-reviewed; do not cite as real-world accuracy.", ""]
        lines += ["| System | Meaning WER | Harm rate |", "|---|---|---|"]
        for s, m in d["systems"].items():
            hr = "n/a" if m["harm_rate"] is None else f"{m['harm_rate']:.1%}"
            lines.append(f"| {s} | {m['wer']:.3f} | {hr} |")
        dialects = sorted({k for m in d["systems"].values() for k in m["per_dialect"]})
        if len(dialects) > 1 or dialects not in (["unspecified"], []):
            lines += ["", "| Dialect | " + " | ".join(d["systems"]) + " |", "|---|" + "---|" * len(d["systems"])]
            for dia in dialects:
                lines.append(f"| {dia} | " + " | ".join(f"{m['per_dialect'].get(dia, float('nan')):.3f}" for m in d["systems"].values()) + " |")
        lines.append("")
    lines += ["Harm rate = share of tokens that were already correct but were rewritten (lower is better)."]
    return "\n".join(lines) + "\n"


def write_reports(result: dict, outdir: Path) -> List[Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    md, js = outdir / "benchmark.md", outdir / "benchmark.json"
    md.write_text(to_markdown(result), encoding="utf-8")
    js.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return [md, js]
