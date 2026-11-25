# G2P and phoneme encoder rules (v0)

**These rules are a documented starting point, not a validated phonology.** They follow common
descriptions of standard (Solo-Yogya) Javanese. Dialects differ. Native speakers and linguists are
asked to correct every row, especially for Pantura Rembang.

| Rule | Implemented as | Status |
|---|---|---|
| ng, ny | ŋ, ɲ | to review |
| dh, th (retroflex) vs d, t (dental) | ɖ, ʈ vs d̪, t̪ | to review |
| c, j, y | tʃ, dʒ, j | to review |
| kh, sy | x, ʃ | to review |
| e (no accent) | ə | to review |
| é, è | e, ɛ | to review |
| final o | ɔ | to review |
| final a (open syllable) | ɔ (profile switch `final_a_open_o`) | dialect-dependent |
| penultimate open a or o before final ɔ | ɔ | to review |
| word-final k | ʔ | to review |
| o in closed syllables (e.g. omah) | o (not modelled) | known gap |

## Pantura Rembang profile

The `pantura-rembang` profile currently **copies `standard`** as a placeholder. To fill it in, record
for each rule above how it is really pronounced in Rembang (examples with recordings are ideal), then
open a pull request changing `PROFILES` in `src/wanda/phonemes.py`. Mark what you verified here:

| Rule | Standard | Rembang realisation | Verified by |
|---|---|---|---|
| final a | ɔ | _to be filled_ | |
| penultimate a/o | ɔ | _to be filled_ | |
| ... | | | |
