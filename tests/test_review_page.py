"""End-to-end check of web/review.html in a headless browser (skipped if Playwright is unavailable)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from wanda import review

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "src" / "wanda" / "data" / "jv_id_seed.tsv"


@unittest.skipUnless(importlib.util.find_spec("playwright"), "playwright not installed")
class TestReviewPage(unittest.TestCase):
    def test_review_export_and_import(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as d, sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception:
                self.skipTest("no browser available")
            pg = b.new_page(accept_downloads=True)
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto((ROOT / "web" / "review.html").as_uri())
            self.assertTrue(pg.is_disabled("button:has-text('Benar')"))
            pg.fill("#who", "ani")
            first = pg.inner_text(".form")
            pg.click("button:has-text('Benar')")
            second = pg.inner_text(".form")
            self.assertNotEqual(first, second)
            pg.fill("#fix", "kata perbaikan")
            pg.click("button:has-text('Perbaiki')")
            with pg.expect_download() as dl:
                pg.click("summary")
                pg.click("#dl")
            out = Path(d) / "log.tsv"
            dl.value.save_as(str(out))
            b.close()
            self.assertEqual(errs, [])
            log = review.read_log(out)
            self.assertEqual([x["decision"] for x in log], ["approve", "edit"])
            self.assertEqual(log[1]["suggested"], "kata perbaikan")
            counts = review.import_log(out, Path(d) / "main.tsv", SEED)
            self.assertEqual(counts["added"], 2)


if __name__ == "__main__":
    unittest.main()
