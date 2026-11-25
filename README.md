# Wanda: Phono-Semantic Intelligence Layer

*Formerly named PSIL. The method is still called the Phono-Semantic Intelligence Layer.*

Open-source middleware that sits between speech-to-text (STT) and a language model,
so that Javanese and dialect-mixed Indonesian speech is understood instead of
mangled. Community-governed data, no cloud dependency, no payment, no tracking.

**Status: v0.3, early but working.** 71 automated tests pass (optional tests for FastAPI, Playwright and Whisper skip when those tools are missing). The lexicon is a small
unreviewed seed (107 entries), the evaluation files are synthetic, and the phonology and
morphology rules are first drafts for native speakers to review. This is a starting
point for community work, not a finished product. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Use it (no install)

Open `web/index.html` in any browser (double-click works, offline), or use the hosted page
at https://benisobahasa.github.io/wanda/ once deployed. Paste Javanese or dialect
text, tap **Pahami**, and see the Indonesian meaning with every rewrite highlighted. Text never
leaves your device. People can suggest new or corrected words from the same page.
The browser code (`web/wanda.js`) is tested against the Python package for identical output.

## The problem

STT systems trained mostly on standard Indonesian garble Javanese and dialect
speech. The LLM downstream then answers the garbled text, not what the person
said. Existing open Javanese ASR models improve transcription, but they do not
tell the LLM what a dialect word *means*, and they do not give the speakers any
say over their data.

## What it does

```
audio -> [any STT] -> transcript -> [Wanda] -> transcript + meaning + notes -> [any LLM]
```

```bash
pip install -e .
wanda normalize "Kowe wis mangan durung? Aku kencot"
# Kamu sudah makan belum? Saya lapar

wanda annotate "kulo mboten ngertos"      # JSON: every decision, confidence, ambiguity
wanda --strict normalize "oro ngerti"     # exact lexicon matches only
wanda eval eval/sample_eval.tsv           # WER before/after (synthetic sample)
wanda check                               # validate the lexicon file after you edit it
wanda serve --port 8080                   # local JSON API (see docs/API.md)
wanda benchmark eval -o reports           # raw STT vs Wanda report
```

As a library:

```python
from wanda import Normalizer
n = Normalizer()
n.annotate("kulo mboten ngertos")["llm_context"]   # paste into your LLM prompt
```

Design rules: conservative by default (rewrite only above a confidence
threshold), known Indonesian words are protected, ambiguous words are flagged
rather than guessed, and every decision is reported.

## Modules (v0.3)

| Module | What it does | Honest status |
|---|---|---|
| `phonemes` | IPA phoneme encoder and G2P (`wanda ipa`) | Rule-based v0; needs linguist review ([docs/G2P_RULES.md](docs/G2P_RULES.md)) |
| `dialect` | Dialect and speech-level detection (`wanda dialect`) | Lexicon cues only; weak until the lexicon grows |
| `morphology` | Affix analysis, e.g. omahe, rumahnya (`wanda morph`) | Rule-based v0 ([docs/MORPHOLOGY.md](docs/MORPHOLOGY.md)) |
| `ngram` | Trainable n-gram language model (`wanda lm-train`) | Works; no corpus or model is bundled |
| `rescore` | N-best re-ranking: lexicon coverage plus optional LM (`wanda rescore`) | Works |
| `asr` | Adapter layer for any speech-to-text; optional Whisper adapters; `wanda asr-eval` | Tested with a fake STT only; validate on real audio ([docs/ASR_VALIDATION.md](docs/ASR_VALIDATION.md)) |
| `adapters` | Ready-to-send payloads for LLM APIs (`wanda llm`) | Works; sends nothing itself |
| `api`, `api_fastapi` | JSON API (`wanda serve`); FastAPI app (optional) | Built-in server tested; FastAPI app untested here |
| `calibration` | Reliability table, ECE, Platt scaling (`wanda calibrate`) | Tools work; need real labelled data |
| `review` | Speaker review: terminal (`wanda review`) and web page (`web/review.html`), merged with `wanda import-reviews` | Works; tested end to end in a browser |
| phrases | Multi-word expressions (matur nuwun, sugeng enjing, ...) in the lexicon | Works; only a few seed phrases |
| `corpus` | Corpus cleaning with a licence NOTICE (`wanda corpus-clean`, `wanda lm-eval`) | Works; no corpus bundled ([docs/CORPUS.md](docs/CORPUS.md)) |
| `lexicon_db` | SQLite lexicon with dialects, registers, variants, IPA (`wanda db ...`) | Works |
| `benchmark` | Raw STT vs Wanda, per dialect, with a harm rate (`wanda benchmark`) | Works; datasets synthetic until reviewed |
| `semantic` | Similarity and embedding backends | Lexical baseline only; neural backend optional and unevaluated |

Contextual embeddings are plug-ins on purpose: Wanda does not train its own, and any model
you add must be evaluated on dialect data first.

## Adding your dialect

Wanda has no Pantura Rembang words yet, on purpose: they must come from native speakers, not guesses.
Fill the ready spreadsheet in `worksheets/` and import it with `wanda dialect-import` (see [docs/DIALECTS.md](docs/DIALECTS.md)).

## Website

The project site and browser app live in `web/` and are published with GitHub Pages at
https://benisobahasa.github.io/wanda/ (Settings, Pages, Source: GitHub Actions; the workflow
`.github/workflows/pages.yml` deploys it on every push to `main`). It is a plain static site, so you can also
upload `web/` to any other host or add a custom domain in the Pages settings.
After editing the lexicon run `python scripts/build_web.py` so the site data matches.

## Limits you should know about

* Lexicon is mostly word-level (a few seed phrases only), and morphology is rule-based v0.
* The seed lexicon was written by the project author and is marked `unreviewed`.
  Speaker and linguist review is the first milestone.
* Phonetic costs are hand-set, to be tuned on community-reviewed data.
* The bundled eval file is synthetic and shows the mechanism, not real accuracy.
* No audio handling of its own. Wanda works on STT text (and N-best lists); the Whisper adapters are optional and unverified on real audio.

## Data and community

Contributions of words, corrections and recordings follow
[governance/DATA_GOVERNANCE.md](governance/DATA_GOVERNANCE.md): consent first,
contributors choose the licence, withdrawal is honoured, data is never sold.

## Licence

Code: MPL-2.0 (see `LICENSE`). Seed lexicon: CC0-1.0 (`src/wanda/data/LICENSE-CC0.txt`).
Community-contributed data is licensed as each contributor chooses on the consent form.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Native speakers do not need to code:
reviewing `jv_id_seed.tsv` is the most valuable contribution.
