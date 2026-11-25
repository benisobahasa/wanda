"""The browser app must give exactly the same answers as the Python package."""
import json, shutil, subprocess, unittest
from pathlib import Path
from wanda import Normalizer
from wanda.lexicon import Lexicon

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("node"), "node not installed")
class TestWebParity(unittest.TestCase):
    def test_same_output_as_python(self):
        n = Normalizer()
        words = [e.form for e in Lexicon.default().entries]
        mutated = []
        for w in words:
            mutated += [w.upper(), w[:-1] + "o", w.replace("a", "o", 1), w + "h", w[1:], w.replace("e", "i", 1)]
        samples = mutated + ["Kowe wis mangan durung? Aku kencot", "kulo mboten ngertos", "orang itu pulang", "Aku ora ngerti, kepriwe kabare.", "Matur nuwun, kulo mboten wonten", "SUGENG ENJING pak", "piye kabare? ora sah", "matur, nuwun sewu", "nuwun sewu\nsugeng dalu"]
        js = "const P=require('./web/data.js')||0;const {create}=require('./web/wanda.js');const n=create();" \
             "const s=JSON.parse(require('fs').readFileSync(0,'utf8'));console.log(JSON.stringify(s.map(x=>n.normalize(x))));"
        out = subprocess.run(["node", "-e", js], input=json.dumps(samples), capture_output=True, text=True, cwd=ROOT, check=True).stdout
        got = json.loads(out)
        bad = [(s, a, b) for s, a, b in zip(samples, got, (n.normalize(x) for x in samples)) if a != b]
        self.assertEqual(bad[:5], [])


if __name__ == "__main__":
    unittest.main()
