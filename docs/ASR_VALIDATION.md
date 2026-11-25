# Validating a speech-to-text engine with Wanda on real recordings

The Whisper adapters are optional and have **not** been verified on real audio in this repository.
Run this on your own consented recordings before relying on them.

## 1. Consent first
Only use recordings from speakers who gave informed consent (see `governance/CONSENT_FORM_TEMPLATE.md`).
Do not commit audio to the repository.

## 2. Prepare a manifest
Tab-separated, one recording per line: `audio_path`, `reference_indonesian`, optional `dialect`.
The reference is the Indonesian MEANING of what was said, written by a native speaker.
```
# status: reviewed        (use 'synthetic' or 'unreviewed' if that is what it is)
rec001.wav	saya tidak tahu	pantura-rembang
rec002.wav	kamu sudah makan belum	standard
```
Relative paths are resolved against the manifest's folder.

## 3. Install an engine and run
```bash
pip install faster-whisper            # or: pip install transformers torch
wanda asr-eval manifest.tsv --engine faster-whisper --model small --language jw -o asr_report.json
```
Whisper's code for Javanese is `jw`. You can also pass `--lm lm.json` to re-rank with your n-gram model.

## 4. Read the result
The report gives, overall and per dialect: the engine's own transcript error rate against the
Indonesian meaning, and Wanda's error rate after rewriting. Report both, include failures, and say how many
recordings and speakers you used. A handful of recordings from one speaker proves little.
Engines that return only one hypothesis give the N-best re-ranker nothing to choose between.
