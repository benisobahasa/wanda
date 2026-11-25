# Training an n-gram model on text you are allowed to use

Wanda ships no corpus and no trained model. You prepare text, check its licence, train, and
evaluate. All steps run offline.

## 1. Get text you may use
Example: the Javanese Wikipedia dump (jvwiki) from dumps.wikimedia.org, converted to plain text with a
tool such as WikiExtractor. Wikipedia text is CC BY-SA: attribution and share-alike duties apply, and it
is unclear whether they extend to a model trained on the text. **Ask a legal adviser before publishing a
model.** Never train on private messages, recordings or anything you do not have the right to use.

## 2. Clean it
```bash
wanda corpus-clean extracted/*.txt -o corpus.txt \
  --source "jv.wikipedia.org dump 2026-11" --licence "CC BY-SA 4.0"
```
This removes markup and URLs, drops short or non-text lines, removes duplicates and writes
`corpus.txt.NOTICE.md` recording the source and licence you declared.

## 3. Train and evaluate
```bash
head -n -2000 corpus.txt > train.txt ; tail -n 2000 corpus.txt > heldout.txt
wanda lm-train train.txt -o lm.json --order 3
wanda lm-eval --lm lm.json heldout.txt          # perplexity; lower is better
wanda rescore hyps.tsv --lm lm.json             # use it to re-rank hypotheses
wanda serve --lm lm.json                        # or serve it through the API
```

## Cautions
* Wikipedia is formal written Javanese. A model trained on it will favour standard, written forms
  and may down-rank dialect spellings and spoken forms. Check per-dialect results with `wanda benchmark`
  before turning the language model on.
* Do not commit corpora or models to the repository. Keep `corpus.txt.NOTICE.md` with any model you share.
