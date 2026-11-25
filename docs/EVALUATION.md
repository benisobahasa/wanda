# Evaluation plan

`eval/sample_eval.tsv` is **synthetic** and written to match the lexicon. It shows that
the mechanism works. It says nothing about real-world accuracy.

## What real evaluation needs
* A held-out set of real utterances from several dialect areas, recorded with consent,
  transcribed by native speakers, with Indonesian meaning references.
* Reviewed by at least two community reviewers (status `reviewed`).
* No overlap with the lexicon authors' own examples.

## Metrics
1. **Meaning WER**: word error rate of Wanda output against the Indonesian reference,
   versus the raw STT transcript (already implemented).
2. **Harm rate**: share of correct Indonesian words that Wanda wrongly rewrites. Must stay near zero.
3. **Dialect gap**: meaning WER per dialect, to see who the tool still fails.
4. **Downstream task accuracy**: answer quality of an LLM given raw versus Wanda-annotated text,
   judged by native speakers on a fixed prompt set.

## Baselines
Raw STT output; existing open Javanese ASR models (for example wav2vec2 and Whisper fine-tunes)
as the STT stage, with and without Wanda on top.

## Tooling (v0.2)
* `wanda benchmark eval -o reports` compares raw STT, Wanda and strict Wanda per dataset and per
  dialect, with a harm rate. Each dataset declares `# status: synthetic` or `# status: reviewed`;
  reports print a warning for anything not reviewed.
* `wanda calibrate eval/words_sample.tsv` prints a reliability table, expected calibration error
  and a Platt fit. Wanda's confidence values are hand-set similarities, not probabilities, until
  calibrated on real labelled data.
* The bundled sample files are synthetic and written to match the lexicon. Their numbers (for example
  a near-zero error rate) prove the mechanism works and nothing about real accuracy.

## Collecting labelled data for calibration and benchmarks
* **Word-level file** (`words_*.tsv`): `word <TAB> expected Indonesian`, with `=` for words that must stay
  unchanged. Include real mistakes made by speech recognizers, plus Indonesian words that Wanda must not touch.
* **Utterance file** (`*.tsv` in `eval/`): `asr_hypothesis <TAB> reference_indonesian <TAB> dialect`, with a
  `# status: reviewed` line only after two native speakers have checked it.
* Keep evaluation data separate from anything used to write lexicon entries or tune costs, and cover every
  dialect you claim to support. Report numbers per dialect, never only an average.
