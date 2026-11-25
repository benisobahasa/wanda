import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from wanda import Normalizer
from wanda import adapters, asr, benchmark, calibration, lexicon_db, review, semantic
from wanda.dialect import DialectDetector
from wanda.lexicon import Lexicon, validate_tsv
from wanda.morphology import analyze
from wanda.ngram import NGramLM
from wanda.phonemes import g2p, ipa, phonemic_distance
from wanda.rescore import rescore_nbest
from wanda.service import Service

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"


class TestPhonemes(unittest.TestCase):
    def test_documented_rules(self):
        self.assertEqual(ipa("ora"), "ɔrɔ")
        self.assertEqual(ipa("mangan"), "maŋan")
        self.assertEqual(ipa("kula"), "kulɔ")
        self.assertEqual(ipa("bapak"), "bapaʔ")
        self.assertEqual(ipa("dhahar"), "ɖahar")
        self.assertEqual(ipa("nyuwun"), "ɲuwun")

    def test_diacritic_vowels(self):
        self.assertEqual(g2p("sétan")[1], "e")
        self.assertEqual(g2p("bèn")[1], "ɛ")

    def test_unknown_profile(self):
        with self.assertRaises(ValueError):
            g2p("ora", "nowhere")

    def test_phonemic_distance_collapses_a_o_spelling(self):
        self.assertEqual(phonemic_distance("kulo", "kula"), 0.0)
        self.assertGreater(phonemic_distance("kula", "turu"), 0.5)


class TestVariants(unittest.TestCase):
    def test_variant_spellings_match(self):
        n = Normalizer()
        self.assertEqual(n.normalize("menapa"), "apa")
        self.assertEqual(n.normalize("punopo"), "apa")

    def test_validate_variants_column(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("wedhus\tngoko\tpantura-rembang\tkambing\tunreviewed\twedus,wedos\n"
                    "xyz\tngoko\tstandard\tabc\tunreviewed\trumah\n")
        problems = validate_tsv(Path(f.name))
        self.assertEqual(len(problems), 1)
        self.assertIn("rumah", problems[0])


class TestDialect(unittest.TestCase):
    def setUp(self):
        self.d = DialectDetector()

    def test_detects_regional_dialects(self):
        self.assertEqual(self.d.detect("kepriwe kabare inyong kencot").top, "banyumasan")
        self.assertEqual(self.d.detect("gak arek koen").top, "jawa-timur")
        self.assertEqual(self.d.detect("kowe wis mangan").top, "standard")

    def test_register_and_unknown(self):
        self.assertEqual(self.d.detect("kulo mboten ngertos").register, "krama")
        r = self.d.detect("selamat pagi semua")
        self.assertEqual((r.top, r.confidence), ("unknown", 0.0))


class TestMorphology(unittest.TestCase):
    def test_suffix_hints(self):
        self.assertEqual(analyze("omahe")[0].hint, "rumahnya")
        self.assertEqual(analyze("omahku")[0].hint, "rumahku")
        self.assertEqual(analyze("mangane")[0].hint, "makannya")

    def test_prefixes(self):
        self.assertEqual(analyze("dituku")[0].hint, "dibeli")
        self.assertEqual(analyze("nuku")[0].hint, "meN-beli")
        self.assertEqual(analyze("ndelok")[0].stem, "delok")

    def test_unknown_stem_gives_nothing(self):
        self.assertEqual(analyze("blablabla"), [])


class TestNGramAndRescore(unittest.TestCase):
    def setUp(self):
        self.lm = NGramLM().train(["aku ora ngerti", "kowe wis mangan", "aku ora ngerti kowe"] * 5)

    def test_prefers_seen_word_order(self):
        self.assertGreater(self.lm.logprob("aku ora ngerti"), self.lm.logprob("ngerti ora aku"))

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lm.json"
            self.lm.save(p)
            lm2 = NGramLM.load(p)
            self.assertAlmostEqual(self.lm.logprob("kowe wis mangan"), lm2.logprob("kowe wis mangan"), places=9)

    def test_rescoring_uses_lm(self):
        n = Normalizer()
        hyps = [("aku ngerti ora", 0.8), ("aku ora ngerti", 0.8)]
        self.assertEqual(rescore_nbest(hyps, n, lm=self.lm)[0][0], "aku ora ngerti")


class TestCalibration(unittest.TestCase):
    def test_ece_and_table(self):
        self.assertEqual(calibration.ece([1.0, 1.0], [True, True]), 0.0)
        self.assertAlmostEqual(calibration.ece([0.9] * 10, [True] * 5 + [False] * 5), 0.4)
        t = calibration.reliability_table([0.1, 0.5, 0.95], [False, True, True])
        self.assertEqual(sum(r["n"] for r in t), 3)

    def test_platt_is_monotonic(self):
        conf = [0.76, 0.8, 0.85, 0.9, 0.95, 1.0] * 5
        ok = [False, False, True, True, True, True] * 5
        s = calibration.PlattScaler().fit(conf, ok)
        self.assertGreater(s.predict(0.95), s.predict(0.76))

    def test_report_on_sample(self):
        r = calibration.calibration_report(EVAL / "words_sample.tsv", Normalizer())
        self.assertEqual(r["total"], 25)
        self.assertGreater(r["rewritten"], 0)


class TestBenchmark(unittest.TestCase):
    def test_report_states_data_status(self):
        res = benchmark.run_benchmark(EVAL)
        self.assertGreaterEqual(len(res["datasets"]), 2)
        for d in res["datasets"]:
            self.assertEqual(d["status"], "synthetic")
            self.assertLess(d["systems"]["Wanda"]["wer"], d["systems"]["raw STT"]["wer"])
        md = benchmark.to_markdown(res)
        self.assertIn("synthetic", md)
        with tempfile.TemporaryDirectory() as d:
            paths = benchmark.write_reports(res, Path(d))
            self.assertTrue(all(p.exists() for p in paths))

    def test_harm_rate_is_zero_on_clean_indonesian(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("# status: synthetic\norang itu pulang dan makan\torang itu pulang dan makan\n")
        res = benchmark.run_benchmark(Path(f.name))
        self.assertEqual(res["datasets"][0]["systems"]["Wanda"]["harm_rate"], 0.0)


class TestAdaptersAndAsr(unittest.TestCase):
    def test_payload_shapes(self):
        g = adapters.build_payload("aku ora ngerti")
        self.assertEqual([m["role"] for m in g["messages"]], ["system", "user"])
        self.assertIn("saya tidak tahu", g["messages"][1]["content"])
        o = adapters.build_payload("aku ora ngerti", "openai", "m1")
        self.assertEqual(o["model"], "m1")
        a = adapters.build_payload("aku ora ngerti", "anthropic", "m2", "en")
        self.assertIn("system", a)
        self.assertEqual(a["messages"][0]["role"], "user")
        with self.assertRaises(ValueError):
            adapters.build_payload("x", "nope")

    def test_process_audio_with_fake_stt(self):
        fake = asr.FunctionAdapter(lambda path: [("oro ngerti", 0.80), ("ora ngerti", 0.78)])
        out = asr.process_audio("dummy.wav", fake)
        self.assertEqual(out["best"], "ora ngerti")
        self.assertEqual(out["normalized"], "tidak tahu")


class TestSemantic(unittest.TestCase):
    def test_lexical_baseline(self):
        b = semantic.LexicalSimilarity()
        self.assertGreater(b.similarity("makan", "makanan"), b.similarity("makan", "tidur"))
        ranked = semantic.rank_candidates(["tidur", "makanan"], "saya mau makan", b)
        self.assertEqual(ranked[0][0], "makanan")


class TestLexiconDb(unittest.TestCase):
    def test_build_query_export(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "lex.sqlite"
            n = lexicon_db.build_db(None, db)
            self.assertEqual(n, len(Lexicon.default()))
            hit = lexicon_db.query(db, "kulo")
            self.assertEqual(hit[0]["form"], "kula")
            self.assertIn("kulo", hit[0]["variants"])
            self.assertEqual(hit[0]["ipa"], "kulɔ")
            self.assertEqual(lexicon_db.stats(db)["entries"], n)
            out = Path(d) / "out.tsv"
            self.assertEqual(lexicon_db.export_tsv(db, out), n)
            self.assertEqual(validate_tsv(out), [])


class TestReview(unittest.TestCase):
    def _tsv(self, d):
        p = Path(d) / "lex.tsv"
        p.write_text("# header\nwedhus\tngoko\tpantura-rembang\tkambing\tunreviewed\twedus\nkucing\tngoko\tstandard\tkucing\tunreviewed\n", encoding="utf-8")
        return p

    def test_two_approvals_make_reviewed_and_objection_disputes(self):
        with tempfile.TemporaryDirectory() as d:
            tsv, log = self._tsv(d), Path(d) / "log.tsv"
            review.record(log, "wedhus", "kambing", "ani", "approve")
            review.record(log, "wedhus", "kambing", "budi", "approve")
            review.record(log, "kucing", "kucing", "ani", "approve")
            review.record(log, "kucing", "kucing", "budi", "reject", note="kucing bukan Jawa")
            s = review.apply_reviews(tsv, log)
            self.assertEqual((s["reviewed"], s["disputed"]), (1, 1))
            text = tsv.read_text(encoding="utf-8")
            self.assertIn("wedhus\tngoko\tpantura-rembang\tkambing\treviewed\twedus", text)
            self.assertIn("kucing\tngoko\tstandard\tkucing\tdisputed", text)
            self.assertEqual(validate_tsv(tsv), [])

    def test_same_reviewer_twice_is_not_enough(self):
        with tempfile.TemporaryDirectory() as d:
            tsv, log = self._tsv(d), Path(d) / "log.tsv"
            review.record(log, "wedhus", "kambing", "ani", "approve")
            review.record(log, "wedhus", "kambing", "ani", "approve")
            self.assertEqual(review.apply_reviews(tsv, log)["reviewed"], 0)

    def test_scripted_session(self):
        with tempfile.TemporaryDirectory() as d:
            tsv, log = self._tsv(d), Path(d) / "log.tsv"
            answers = iter(["a", "e", "kucing rumah", "catatan"])
            n = review.run_session(tsv, log, "ani", ask=lambda q: next(answers), say=lambda s: None)
            self.assertEqual(n, 2)
            self.assertEqual([x["decision"] for x in review.read_log(log)], ["approve", "edit"])

    def test_reviewer_required(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                review.record(Path(d) / "l.tsv", "a", "b", " ", "approve")


class TestService(unittest.TestCase):
    def test_handlers(self):
        s = Service()
        self.assertEqual(s.handle("GET", "/health")[1]["status"], "ok")
        self.assertEqual(s.handle("POST", "/v1/normalize", {"text": "aku ora ngerti"}), (200, {"normalized": "saya tidak tahu"}))
        self.assertEqual(s.handle("POST", "/v1/normalize", {"text": "oro ngerti", "strict": True})[1]["normalized"], "oro tahu")
        self.assertEqual(s.handle("POST", "/v1/ipa", {"text": "ora"})[1]["words"][0]["ipa"], "ɔrɔ")
        self.assertEqual(s.handle("POST", "/v1/morph", {"word": "omahe"})[1]["analyses"][0]["hint"], "rumahnya")
        self.assertEqual(s.handle("POST", "/v1/dialect", {"text": "inyong kencot"})[1]["dialect"], "banyumasan")
        r = s.handle("POST", "/v1/rescore", {"hypotheses": [{"text": "oro ngerti", "score": 0.8}, {"text": "ora ngerti", "score": 0.78}]})
        self.assertEqual(r[1]["ranked"][0]["text"], "ora ngerti")
        self.assertEqual(s.handle("POST", "/v1/llm-payload", {"text": "aku ora ngerti", "provider": "anthropic"})[0], 200)

    def test_errors(self):
        s = Service()
        self.assertEqual(s.handle("POST", "/v1/normalize", {})[0], 400)
        self.assertEqual(s.handle("POST", "/v1/normalize", {"text": "x" * 20000})[0], 413)
        self.assertEqual(s.handle("POST", "/v1/normalize", {"text": "a", "min_confidence": 5})[0], 400)
        self.assertEqual(s.handle("POST", "/v1/nope", {"text": "a"})[0], 404)
        self.assertEqual(s.handle("POST", "/v1/ipa", {"text": "a", "profile": "zz"})[0], 400)
        self.assertEqual(s.handle("POST", "/v1/rescore", {"hypotheses": [{"text": 1}]})[0], 400)


class TestHttpServer(unittest.TestCase):
    def test_roundtrip(self):
        from wanda.api import make_server
        srv = make_server("127.0.0.1", 0)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{port}"
            self.assertEqual(json.load(urllib.request.urlopen(base + "/health"))["status"], "ok")
            req = urllib.request.Request(base + "/v1/normalize", data=json.dumps({"text": "kowe wis mangan"}).encode(), method="POST")
            self.assertEqual(json.load(urllib.request.urlopen(req))["normalized"], "kamu sudah makan")
            bad = urllib.request.Request(base + "/v1/normalize", data=b"not json", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(bad)
            self.assertEqual(cm.exception.code, 400)
        finally:
            srv.shutdown()
            srv.server_close()


try:
    import fastapi  # noqa: F401
    from fastapi.testclient import TestClient
    HAVE_FASTAPI = True
except Exception:
    HAVE_FASTAPI = False


@unittest.skipUnless(HAVE_FASTAPI, "fastapi not installed")
class TestFastApi(unittest.TestCase):
    def test_endpoints(self):
        from wanda.api_fastapi import create_app
        c = TestClient(create_app())
        self.assertEqual(c.get("/health").json()["status"], "ok")
        self.assertEqual(c.post("/v1/normalize", json={"text": "aku ora ngerti"}).json()["normalized"], "saya tidak tahu")
        self.assertEqual(c.post("/v1/normalize", json={}).status_code, 400)



class TestCliFriendlyErrors(unittest.TestCase):
    def test_missing_database_does_not_create_one(self):
        from wanda.cli import main
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d) / "nope.sqlite"
            self.assertEqual(main(["db", "query", "kulo", "--db", str(missing)]), 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
