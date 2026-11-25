import unittest
from pathlib import Path

from wanda import Normalizer
import tempfile
from wanda.lexicon import validate_tsv
from wanda.evaluate import evaluate_tsv, wer
from wanda.phonetics import similarity, to_units
from wanda.rescore import rescore_nbest

ROOT = Path(__file__).resolve().parents[1]


class TestPhonetics(unittest.TestCase):
    def test_digraph_units(self):
        self.assertEqual(to_units("mangan"), ["m", "a", "ng", "a", "n"])
        self.assertEqual(to_units("gedhé"), ["g", "e", "dh", "e"])

    def test_similarity_orders_sensibly(self):
        self.assertGreater(similarity("oro", "ora"), similarity("oro", "turu"))
        self.assertEqual(similarity("ora", "ora"), 1.0)


class TestNormalizer(unittest.TestCase):
    def setUp(self):
        self.n = Normalizer()

    def test_basic_ngoko(self):
        self.assertEqual(self.n.normalize("aku ora ngerti"), "saya tidak tahu")

    def test_case_and_punctuation_kept(self):
        self.assertEqual(self.n.normalize("Kowe wis mangan?"), "Kamu sudah makan?")

    def test_krama_with_spelling_variant(self):
        self.assertEqual(self.n.normalize("kulo mboten ngertos"), "saya tidak tahu")

    def test_dialect_banyumasan(self):
        self.assertEqual(self.n.normalize("kepriwe, inyong kencot"), "bagaimana, saya lapar")

    def test_fuzzy_asr_error(self):
        self.assertEqual(self.n.normalize("kowe wis mangen durung"), "kamu sudah makan belum")

    def test_protected_indonesian_untouched(self):
        s = "orang itu pulang dan kata dia kota besar"
        self.assertEqual(self.n.normalize(s), s)

    def test_strict_mode_skips_fuzzy(self):
        self.assertEqual(Normalizer(fuzzy=False).normalize("oro ngerti"), "oro tahu")

    def test_unknown_left_alone(self):
        self.assertEqual(self.n.normalize("kabare"), "kabare")

    def test_annotate_contains_context(self):
        a = self.n.annotate("aku ora ngerti")
        self.assertEqual(a["normalized"], "saya tidak tahu")
        self.assertIn("aku -> saya", a["llm_context"])
        self.assertTrue(all("kind" in t for t in a["tokens"]))


class TestRescore(unittest.TestCase):
    def test_prefers_known_words(self):
        n = Normalizer()
        ranked = rescore_nbest([("oro ngerti", 0.80), ("ora ngerti", 0.78)], n)
        self.assertEqual(ranked[0][0], "ora ngerti")


class TestEval(unittest.TestCase):
    def test_wer(self):
        self.assertEqual(wer("a b c", "a b c"), 0.0)
        self.assertAlmostEqual(wer("a b c", "a x c"), 1 / 3)

    def test_sample_improves(self):
        r = evaluate_tsv(ROOT / "eval" / "sample_eval.tsv", Normalizer())
        self.assertLess(r["wanda_wer"], r["baseline_wer"])


class TestValidate(unittest.TestCase):
    def _check(self, text):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write(text)
        return validate_tsv(Path(f.name))

    def test_bundled_seed_is_valid(self):
        seed = ROOT / "src" / "wanda" / "data" / "jv_id_seed.tsv"
        self.assertEqual(validate_tsv(seed), [])

    def test_catches_spaces_instead_of_tabs(self):
        problems = self._check("wedhus ngoko pantura-rembang kambing unreviewed\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("TAB", problems[0])

    def test_catches_bad_register_and_protected_word(self):
        problems = self._check("rumah\tngoko\tstandard\trumah\tunreviewed\nxyz\tbiasa\tstandard\tabc\tunreviewed\n")
        self.assertEqual(len(problems), 2)


if __name__ == "__main__":
    unittest.main()
