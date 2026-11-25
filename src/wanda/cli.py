from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .evaluate import evaluate_tsv
from .lexicon import Lexicon, validate_tsv
from .normalizer import Normalizer


def _seed() -> Path:
    return Path(str(resources.files("wanda") / "data" / "jv_id_seed.tsv"))


def _out(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _text(args) -> str:
    return args.text if args.text is not None else sys.stdin.read().strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wanda", description="Wanda: understanding Javanese and dialect speech (Phono-Semantic Intelligence Layer)")
    p.add_argument("--version", action="version", version=f"wanda {__version__}")
    p.add_argument("--lexicon", help="custom lexicon TSV (default: bundled seed)")
    p.add_argument("--protected", help="custom file of Indonesian words never to rewrite")
    p.add_argument("--min-confidence", type=float, default=0.75)
    p.add_argument("--strict", action="store_true", help="exact lexicon matches only")
    s = p.add_subparsers(dest="cmd", required=True)

    for name, h in [("normalize", "rewrite dialect words to Indonesian"), ("annotate", "JSON with per-token decisions and LLM context"),
                    ("dialect", "detect dialect and speech level from lexicon cues"), ("ipa", "grapheme-to-phoneme (IPA), v0 rules")]:
        c = s.add_parser(name, help=h); c.add_argument("text", nargs="?", help="text (reads stdin if omitted)")
        if name == "ipa":
            c.add_argument("--profile", default="standard")
    m = s.add_parser("morph", help="affix analysis of one word"); m.add_argument("word")
    e = s.add_parser("eval", help="WER before/after on a TSV file"); e.add_argument("file")
    s.add_parser("stats", help="lexicon size and review status")
    c = s.add_parser("check", help="validate a lexicon TSV file"); c.add_argument("file", nargs="?")

    b = s.add_parser("benchmark", help="benchmark raw STT vs Wanda on TSV datasets (file or folder)")
    b.add_argument("path"); b.add_argument("-o", "--out", default="reports")
    k = s.add_parser("calibrate", help="reliability table, ECE and Platt fit from a word-level TSV"); k.add_argument("file")
    k.add_argument("--save", help="write the fitted Platt parameters to this JSON file")
    ae = s.add_parser("asr-eval", help="run an STT engine over consented recordings: raw vs Wanda WER")
    ae.add_argument("manifest"); ae.add_argument("--engine", choices=["faster-whisper", "transformers"], default="faster-whisper")
    ae.add_argument("--model"); ae.add_argument("--language"); ae.add_argument("--lm"); ae.add_argument("-o", "--out")
    cc = s.add_parser("corpus-clean", help="clean plain text into a training corpus and write a NOTICE file")
    cc.add_argument("inputs", nargs="+"); cc.add_argument("-o", "--out", required=True)
    cc.add_argument("--source", required=True, help="where the text comes from, e.g. 'jv.wikipedia.org dump 2026-11'")
    cc.add_argument("--licence", required=True, help="licence of the text, e.g. 'CC BY-SA 4.0'"); cc.add_argument("--min-words", type=int, default=4)
    le = s.add_parser("lm-eval", help="perplexity of a trained n-gram model on held-out text"); le.add_argument("--lm", required=True); le.add_argument("file")
    dw = s.add_parser("dialect-worksheet", help="write a spreadsheet for a native speaker to fill in a dialect's words")
    dw.add_argument("-o", "--out", default="worksheet.csv"); dw.add_argument("--format", choices=["csv", "tsv"], default="csv")
    di = s.add_parser("dialect-import", help="import a filled dialect worksheet into the lexicon (as unreviewed)")
    di.add_argument("file"); di.add_argument("--dialect", default="pantura-rembang"); di.add_argument("--dry-run", action="store_true")
    di.add_argument("--notes-dir", default="docs/dialect_notes")
    ir = s.add_parser("import-reviews", help="merge a review log exported from the web review page")
    ir.add_argument("file"); ir.add_argument("--log", default="review_log.tsv")

    t = s.add_parser("lm-train", help="train an n-gram language model on a text file")
    t.add_argument("corpus"); t.add_argument("-o", "--out", required=True); t.add_argument("--order", type=int, default=3)
    r = s.add_parser("rescore", help="re-rank hypotheses from a TSV (text<TAB>score)")
    r.add_argument("file"); r.add_argument("--lm"); r.add_argument("--lm-weight", type=float, default=0.1)
    l = s.add_parser("llm", help="build a ready-to-send LLM request payload (nothing is sent)")
    l.add_argument("text", nargs="?"); l.add_argument("--provider", default="generic", choices=["generic", "openai", "anthropic"])
    l.add_argument("--model"); l.add_argument("--language", default="id", choices=["id", "en"])

    d = s.add_parser("db", help="SQLite lexicon database")
    ds = d.add_subparsers(dest="db_cmd", required=True)
    x = ds.add_parser("build"); x.add_argument("--db", default="wanda-lexicon.sqlite")
    x = ds.add_parser("query"); x.add_argument("word"); x.add_argument("--db", default="wanda-lexicon.sqlite")
    x = ds.add_parser("stats"); x.add_argument("--db", default="wanda-lexicon.sqlite")
    x = ds.add_parser("export"); x.add_argument("out"); x.add_argument("--db", default="wanda-lexicon.sqlite")

    v = s.add_parser("review", help="interactive lexicon review by a speaker (pseudonym is fine)")
    v.add_argument("--reviewer", required=True); v.add_argument("--log", default="review_log.tsv"); v.add_argument("--limit", type=int)
    a = s.add_parser("apply-reviews", help="update entry status from the review log (2 approvals = reviewed)")
    a.add_argument("--log", default="review_log.tsv"); a.add_argument("--min-reviewers", type=int, default=2)

    sv = s.add_parser("serve", help="run the JSON API on localhost")
    sv.add_argument("--host", default="127.0.0.1"); sv.add_argument("--port", type=int, default=8080)
    sv.add_argument("--lm"); sv.add_argument("--cors", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    lex_path = Path(args.lexicon) if args.lexicon else _seed()
    lex = Lexicon.from_files(lex_path, Path(args.protected) if args.protected else None) if (args.lexicon or args.protected) else Lexicon.default()
    norm = Normalizer(lex, min_confidence=args.min_confidence, fuzzy=not args.strict)
    c = args.cmd

    if c == "normalize":
        print(norm.normalize(_text(args)))
    elif c == "annotate":
        _out(norm.annotate(_text(args)))
    elif c == "dialect":
        from .dialect import DialectDetector
        _out(DialectDetector(lex).detect(_text(args)).as_dict())
    elif c == "ipa":
        from .phonemes import ipa_text
        _out(ipa_text(_text(args), args.profile))
    elif c == "morph":
        from .morphology import analyze
        _out([a.as_dict() for a in analyze(args.word, lex)])
    elif c == "eval":
        _out(evaluate_tsv(Path(args.file), norm))
    elif c == "stats":
        by = {}
        for en in lex.entries:
            by[en.status] = by.get(en.status, 0) + 1
        _out({"entries": len(lex), "by_status": by})
    elif c == "check":
        problems = validate_tsv(Path(args.file) if args.file else lex_path, Path(args.protected) if args.protected else None)
        for pr in problems:
            print(pr)
        print("OK" if not problems else f"{len(problems)} problem(s) found")
        return 1 if problems else 0
    elif c == "benchmark":
        from .benchmark import run_benchmark, to_markdown, write_reports
        res = run_benchmark(Path(args.path))
        write_reports(res, Path(args.out))
        print(to_markdown(res))
    elif c == "calibrate":
        from .calibration import calibration_report
        rep = calibration_report(Path(args.file), norm)
        _out(rep)
        if args.save:
            Path(args.save).write_text(json.dumps({**rep["platt"], "ece": rep["ece"], "n": rep["rewritten"]}, indent=2), encoding="utf-8")
    elif c == "asr-eval":
        from . import asr
        from .ngram import NGramLM
        try:
            if args.engine == "faster-whisper":
                adapter = asr.FasterWhisperAdapter(args.model or "small", args.language or "jw")
            else:
                adapter = asr.TransformersWhisperAdapter(args.model or "openai/whisper-small", args.language or "javanese")
        except ImportError as e:
            print(f"{e}. Install the optional engine first (see docs/ASR_VALIDATION.md).", file=sys.stderr)
            return 1
        rep = asr.evaluate_adapter(adapter, Path(args.manifest), norm, NGramLM.load(Path(args.lm)) if args.lm else None)
        if args.out:
            Path(args.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
        _out({k: v for k, v in rep.items() if k != "items"})
    elif c == "corpus-clean":
        from .corpus import build_corpus
        _out(build_corpus([Path(x) for x in args.inputs], Path(args.out), args.source, args.licence, args.min_words))
    elif c == "lm-eval":
        from .ngram import NGramLM
        _out(NGramLM.load(Path(args.lm)).evaluate(Path(args.file).read_text(encoding="utf-8").splitlines()))
    elif c == "dialect-worksheet":
        from .worksheet import make_worksheet
        print(f"wrote {make_worksheet(lex, Path(args.out), args.format)} rows to {args.out}")
    elif c == "dialect-import":
        from .worksheet import import_worksheet
        res = import_worksheet(Path(args.file), lex_path, args.dialect, args.dry_run, Path(args.notes_dir))
        _out(res)
        if res["problems"]:
            return 1
    elif c == "import-reviews":
        from .review import import_log
        _out(import_log(Path(args.file), Path(args.log), lex_path))
    elif c == "lm-train":
        from .ngram import NGramLM
        lm = NGramLM(order=args.order).train(Path(args.corpus).read_text(encoding="utf-8").splitlines())
        lm.save(Path(args.out)); print(f"trained on {len(lm.vocab)} word types; saved to {args.out}")
    elif c == "rescore":
        from .ngram import NGramLM
        from .rescore import rescore_nbest
        lm = NGramLM.load(Path(args.lm)) if args.lm else None
        pairs = []
        for line in Path(args.file).read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and not line.startswith("#"):
                pairs.append((parts[0], float(parts[1])))
        _out([{"text": t, "score": round(sc, 4)} for t, sc in rescore_nbest(pairs, norm, lm=lm, lm_weight=args.lm_weight)])
    elif c == "llm":
        from .adapters import build_payload
        _out(build_payload(_text(args), args.provider, args.model, args.language, norm))
    elif c == "db":
        from . import lexicon_db as db
        if args.db_cmd != "build" and not Path(args.db).exists():
            print(f"database not found: {args.db}. Run `wanda db build` first.", file=sys.stderr)
            return 1
        if args.db_cmd == "build":
            print(f"built {args.db} with {db.build_db(lex, Path(args.db))} entries")
        elif args.db_cmd == "query":
            _out(db.query(Path(args.db), args.word))
        elif args.db_cmd == "stats":
            _out(db.stats(Path(args.db)))
        else:
            print(f"exported {db.export_tsv(Path(args.db), Path(args.out))} entries to {args.out}")
    elif c == "review":
        from .review import apply_reviews, run_session
        n = run_session(lex_path, Path(args.log), args.reviewer, limit=args.limit)
        print(f"{n} decision(s) recorded in {args.log}. Run `wanda apply-reviews` to update entry status.")
    elif c == "apply-reviews":
        from .review import apply_reviews
        _out(apply_reviews(lex_path, Path(args.log), args.min_reviewers))
    elif c == "serve":
        from .api import serve
        from .ngram import NGramLM
        from .service import Service
        serve(args.host, args.port, Service(lex, NGramLM.load(Path(args.lm)) if args.lm else None), args.cors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
