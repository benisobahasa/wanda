# Roadmap

## Done by v0.3 (tested, early)
Normalizer, variants, rule-based G2P/IPA, dialect detection, morphology v0, n-gram LM, N-best
rescoring, ASR adapter layer, LLM payload builders, local JSON API, calibration tools, benchmark
pipeline, SQLite lexicon database, review workflow (terminal and web page), multi-word expressions,
corpus cleaning and LM evaluation tools, ASR validation tool, browser app and project site.

## Before the fellowship (now to early 2027)
* Publish repository and site; add Pantura Rembang words and variants to the lexicon.
* Recruit first native-speaker reviewers from at least two dialect areas; fill in `docs/G2P_RULES.md`.

## Fellowship year (June 2027 to May 2028)
* **Months 1 to 3:** stewardship council; consent and licence options finalised with speakers; review
  the lexicon with `wanda review` to a few thousand entries; fix the evaluation protocol.
* **Months 4 to 6:** consented pilot recordings in three dialect areas; first real benchmark against open
  Javanese speech models; real calibration; publish results including failures.
* **Months 7 to 9:** run `wanda asr-eval` on consented recordings to validate the Whisper adapters; train and
  evaluate an n-gram model on licensed text (`docs/CORPUS.md`); extend morphology and multi-word expressions
  with reviewed entries.
* **Months 10 to 12:** v1.0 with reviewed data, two-language documentation, open evaluation set, and a
  handover plan for community maintenance.

## Only if evidence supports it
Neural embeddings or semantic similarity as plug-ins, evaluated on dialect data first.

## Principles
Ship small and open. Publish negative results. Never trade community control for convenience.
