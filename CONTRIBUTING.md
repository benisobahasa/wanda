# Contributing

## Without coding (most needed)
* Review entries in `src/wanda/data/jv_id_seed.tsv`. Mark wrong ones, add missing
  forms, dialects and registers. Open an issue or a pull request.
* Tell us which words your community says differently.

## Contribute your dialect's words (no coding)
Fill `worksheets/pantura-rembang.csv` (or generate one for your dialect with `wanda dialect-worksheet`) and send it to the
maintainers, or import it yourself with `wanda dialect-import`. See `docs/DIALECTS.md`.

## Review words as a speaker (no coding)
```bash
wanda review --reviewer yourpseudonym      # approve, edit or reject entries one by one
wanda apply-reviews                        # two approvals => reviewed; any objection => disputed
```
Your decisions are saved in `review_log.tsv`. A pseudonym is fine; real names are not required.

Prefer a browser? Open the review page (`web/review.html`, or `/review.html` on the project site), review words,
and download the log. Maintainers merge logs with `wanda import-reviews yourfile.tsv`.

## Code
```bash
pip install -e .
PYTHONPATH=src python -m unittest discover -s tests
wanda check                                  # validate the lexicon
```
* Keep dependencies at zero for the core package.
* Every behaviour change needs a test. Prefer not rewriting over rewriting wrongly.
* Do not add data you do not have the right to share. Read `governance/DATA_GOVERNANCE.md`.

## Conduct
Be respectful. Language communities are not datasets. Harassment, discrimination
and extractive behaviour toward speakers are grounds for removal from the project.
