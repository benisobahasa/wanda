# Dialect tags

| Tag | Meaning | Aliases | Status |
|---|---|---|---|
| `standard` | Standard Javanese forms | | seed entries, unreviewed |
| `banyumasan` | Banyumasan | | a few seed entries, unreviewed |
| `jawa-timur` | East Javanese | | a few seed entries, unreviewed |
| `pantura-rembang` | Pantura (north coast) dialect of Rembang | `rembang`, `pantura` | **no entries yet**: to be contributed by native speakers |

Tags are free text in the lexicon TSV, so any new dialect only needs a new tag. Aliases are accepted by
the dialect detector and the G2P profiles.

## Adding a dialect's words
1. `wanda dialect-worksheet --dialect pantura-rembang -o worksheet.csv` (a ready file is in `worksheets/`).
2. A native speaker fills `dialect_form` (or `=` when the form is the same), plus variants and notes.
3. `wanda dialect-import worksheet.csv --dialect pantura-rembang --dry-run`, then again without `--dry-run`.
4. Other speakers review the new entries (`web/review.html` or `wanda review`).

Pronunciation and spelling notes from the worksheet are saved under `docs/dialect_notes/<dialect>.md`.
For the sound system, also fill the Rembang table in [G2P_RULES.md](G2P_RULES.md).
