import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from wanda import asr, corpus, review
from wanda.calibration import PlattScaler
from wanda.cli import main
from wanda.ngram import NGramLM

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "src" / "wanda" / "data" / "jv_id_seed.tsv"


class TestCorpus(unittest.TestCase):
    def test_cleaning_and_notice(self):
        raw = ("<doc id=1>\n== Judul ==\nAku ora ngerti [[apa|apa]] sing kedadean ing kene. https://example.org\n"
               "Aku ora ngerti apa sing kedadean ing kene.\nShort.\n12345 67890 11111 22222\n</doc>")
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / "in.txt", Path(d) / "corpus.txt"
            src.write_text(raw, encoding="utf-8")
            r = corpus.build_corpus([src], out, "test source", "CC BY-SA 4.0")
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(r["sentences"], 1)
            self.assertEqual(len(lines), 1)
            self.assertNotIn("http", lines[0])
            self.assertIn("CC BY-SA 4.0", Path(r["notice"]).read_text(encoding="utf-8"))

    def test_lm_evaluate(self):
        lm = NGramLM().train(["aku ora ngerti", "kowe wis mangan"] * 4)
        ev = lm.evaluate(["aku ora ngerti"])
        self.assertEqual(ev["sentences"], 1)
        self.assertLess(ev["perplexity"], lm.evaluate(["mangan ngerti aku"])["perplexity"])


class TestAsrEval(unittest.TestCase):
    def test_evaluate_with_fake_adapter(self):
        table = {"a.wav": [("oro ngerti", 0.8), ("ora ngerti", 0.78)], "b.wav": [("kowe wis mangen", 0.9)]}
        fake = asr.FunctionAdapter(lambda p: table[Path(p).name])
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "manifest.tsv"
            m.write_text("# status: synthetic\na.wav\ttidak tahu\tstandard\nb.wav\tkamu sudah makan\tbanyumasan\n", encoding="utf-8")
            rep = asr.evaluate_adapter(fake, m)
        self.assertEqual((rep["n"], rep["status"]), (2, "synthetic"))
        self.assertLess(rep["wanda_wer"], rep["raw_wer"])
        self.assertEqual(set(rep["per_dialect"]), {"standard", "banyumasan"})

    @unittest.skipUnless(importlib.util.find_spec("faster_whisper") is None, "faster-whisper is installed")
    def test_cli_friendly_error_when_engine_missing(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.tsv"
            m.write_text("a.wav\tx\n", encoding="utf-8")
            self.assertEqual(main(["asr-eval", str(m)]), 1)


class TestImportReviews(unittest.TestCase):
    def test_merge_dedupe_and_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            src, dest = Path(d) / "from_web.tsv", Path(d) / "main.tsv"
            review.record(src, "kula", "saya", "ani", "approve")
            review.record(src, "kula", "saya", "ani", "approve")
            review.record(src, "tidakada", "x", "ani", "approve")
            review.record(src, "mboten", "tidak", "budi", "edit", suggested="bukan")
            c = review.import_log(src, dest, SEED)
            self.assertEqual(c, {"added": 2, "duplicates": 1, "unknown_entries": 1, "invalid": 0})
            self.assertEqual(review.import_log(src, dest, SEED)["added"], 0)


class TestPlattIO(unittest.TestCase):
    def test_roundtrip(self):
        s = PlattScaler(1.5, -0.5)
        self.assertEqual(PlattScaler.from_dict(json.loads(json.dumps(s.to_dict()))).predict(0.9), s.predict(0.9))

    def test_cli_calibrate_save(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "cal.json"
            self.assertEqual(main(["calibrate", str(ROOT / "eval" / "words_sample.tsv"), "--save", str(out)]), 0)
            self.assertIn("a", json.loads(out.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
