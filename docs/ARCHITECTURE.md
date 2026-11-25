# Architecture

```
          +-----------+     +-----------------------------------------+     +---------+
audio --> |  any STT  | --> |                 Wanda                   | --> | any LLM |
          | (asr.py)  |     |  normalizer   exact + phonetic match    |     |(adapters|
          +-----------+     |  lexicon      forms, variants, status   |     |  .py)   |
             N-best  ------>|  phonemes     IPA / G2P (rules v0)      |     +---------+
                            |  dialect      cues -> dialect, register |
                            |  morphology   affix analysis (v0)       |
                            |  rescore+ngram  re-rank hypotheses      |
                            |  calibration  confidence vs accuracy    |
                            +-----------------------------------------+
                               |            |             |
                       api / api_fastapi  lexicon_db   review + benchmark
                       (JSON for apps)    (SQLite)     (speakers, reports)
```

* The editable source of truth is the lexicon TSV; everything else is derived from it
  (`scripts/build_web.py` generates the browser data, `wanda db build` generates SQLite).
* The browser app (`web/wanda.js`) implements the normalizer in JavaScript and is tested against the
  Python version for identical output.
* Core code has no third-party dependencies. Optional extras: `api` (FastAPI), `asr` (faster-whisper),
  `semantic` (sentence-transformers).
* Nothing is sent over the network by Wanda. LLM and ASR adapters build requests or call libraries
  that you install and configure yourself.
