import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from wanda import worksheet
from wanda.dialect import DialectDetector
from wanda.lexicon import Lexicon, validate_tsv
from wanda.phonemes import g2p
from wanda.service import Service

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "src" / "wanda" / "data" / "jv_id_seed.tsv"


def fill(path, answers):
    """Fill dialect_form (and optionally variants/notes) for given standard forms; return the rewritten file."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "standard_form")
    for r in rows[hi + 1:]:
        if r[0] in answers:
            for k, v in answers[r[0]].items():
                r[worksheet.COLUMNS.index(k)] = v
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        csv.writer(fh).writerows(rows)


class TestWorksheet(unittest.TestCase):
    def test_generate_matches_standard_entries(self):
        lex = Lexicon.default()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "w.csv"
            n = worksheet.make_worksheet(lex, out)
            self.assertEqual(n, sum(1 for e in lex.entries if e.dialect == "standard"))
            rows = worksheet.read_worksheet(out)
            self.assertEqual(len(rows), n)
            self.assertEqual(rows[0]["dialect_form"], "")

    def test_import_adds_only_what_was_typed(self):
        with tempfile.TemporaryDirectory() as d:
            lex = Path(d) / "lex.tsv"
            shutil.copy(SEED, lex)
            before = len(Lexicon.from_files(lex))
            out = Path(d) / "w.csv"
            worksheet.make_worksheet(Lexicon.from_files(lex), out)
            fill(out, {
                "mangan": {"dialect_form": "TESBENTUK-A", "dialect_variants": "tesvarian1; tesvarian2", "pronunciation_note": "catatan lafal"},
                "turu": {"dialect_form": "="},
                "omah": {"dialect_form": "rumah"},       # a protected Indonesian word
                "ngombe": {"dialect_form": "tesbentukb", "notes": "contoh"},
            })
            dry = worksheet.import_worksheet(out, lex, "pantura-rembang", dry_run=True)
            self.assertEqual(len(Lexicon.from_files(lex)), before)  # dry run changes nothing
            res = worksheet.import_worksheet(out, lex, "pantura-rembang", notes_dir=Path(d) / "notes")
            self.assertEqual((res["added"], res["confirmed_same"]), (2, 1))
            self.assertEqual(res["skipped_protected"], ["rumah"])
            self.assertEqual(dry["added"], 2)
            self.assertEqual(res["problems"], [])
            self.assertEqual(validate_tsv(lex), [])
            new = Lexicon.from_files(lex)
            self.assertEqual(len(new), before + 2)
            hit = [e for e in new.entries if e.form == "TESBENTUK-A"][0]
            self.assertEqual((hit.dialect, hit.status, hit.indonesian, hit.variants), ("pantura-rembang", "unreviewed", "makan", ("tesvarian1", "tesvarian2")))
            self.assertTrue((Path(d) / "notes" / "pantura-rembang.md").exists())
            again = worksheet.import_worksheet(out, lex, "pantura-rembang")
            self.assertEqual((again["added"], again["duplicates"]), (0, 2))

    def test_missing_columns_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "bad.csv"
            bad.write_text("a,b\n1,2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                worksheet.read_worksheet(bad)

    def test_shipped_worksheet_is_valid_and_unfilled(self):
        rows = worksheet.read_worksheet(ROOT / "worksheets" / "pantura-rembang.csv")
        self.assertGreater(len(rows), 50)
        self.assertTrue(all(r["dialect_form"] == "" for r in rows))


class TestAliases(unittest.TestCase):
    def test_g2p_alias(self):
        self.assertEqual(g2p("ora", "rembang"), g2p("ora", "pantura-rembang"))

    def test_api_accepts_alias(self):
        self.assertEqual(Service().handle("POST", "/v1/ipa", {"text": "ora", "profile": "rembang"})[0], 200)

    def test_detector_merges_alias_tags(self):
        from wanda.lexicon import Entry
        lex = Lexicon([Entry("tesbentuk", "ngoko", "rembang", "makan"), Entry("tesdua", "ngoko", "pantura-rembang", "minum")])
        r = DialectDetector(lex).detect("tesbentuk tesdua")
        self.assertEqual((r.top, r.confidence), ("pantura-rembang", 1.0))


if __name__ == "__main__":
    unittest.main()
