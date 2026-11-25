import tempfile
import unittest
from pathlib import Path

from wanda import Normalizer
from wanda import lexicon_db
from wanda.lexicon import validate_tsv


class TestPhrases(unittest.TestCase):
    def setUp(self):
        self.n = Normalizer()

    def test_phrase_beats_words(self):
        self.assertEqual(self.n.normalize("sugeng enjing"), "selamat pagi")
        self.assertEqual(self.n.normalize("piye kabare"), "apa kabar")

    def test_case_and_punctuation_preserved(self):
        self.assertEqual(self.n.normalize("Matur nuwun, kulo mboten wonten."), "Terima kasih, saya tidak ada.")
        self.assertEqual(self.n.normalize("SUGENG ENJING pak"), "SELAMAT PAGI pak")

    def test_phrase_does_not_span_punctuation(self):
        self.assertEqual(self.n.normalize("matur, nuwun sewu"), "matur, permisi")

    def test_phrase_reported_in_tokens(self):
        t = self.n.analyze("aku ora sah")[1]
        self.assertEqual((t.kind, t.output, t.original), ("phrase", "tidak usah", "ora sah"))
        self.assertEqual(self.n.normalize("aku ora sah"), "saya tidak usah")

    def test_validate_allows_phrases_but_not_long_ones(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("a b c d e\tngoko\tstandard\tx\tunreviewed\nsugeng wengi\tkrama\tstandard\tselamat malam\tunreviewed\n")
        problems = validate_tsv(Path(f.name))
        self.assertEqual(len(problems), 1)
        self.assertIn("more than", problems[0])

    def test_db_query_phrase(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "x.sqlite"
            lexicon_db.build_db(None, db)
            hit = lexicon_db.query(db, "Matur Nuwun")
            self.assertEqual(hit[0]["indonesian"], "terima kasih")
            self.assertEqual(len(hit[0]["ipa"].split()), 2)


if __name__ == "__main__":
    unittest.main()
