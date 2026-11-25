# Morphological analyzer rules (v0)

Wanda strips at most one prefix and one suffix, then accepts the analysis only if the stem is in
the lexicon. It reports a hint for Indonesian only when the mapping is regular.

| Affix | Type | Indonesian hint |
|---|---|---|
| di- | passive prefix | di- |
| tak-, dak- | 1st person actor | ku- |
| kok-, ko- | 2nd person actor | kau- |
| ng-, ny-, m-, n- (with stem-initial restoration) | active nasal prefix | meN- (shown as a pattern, not a surface form) |
| ke-, sa- | prefixes | no hint |
| -e, -ne, -ane, -ipun | definite or possessive | -nya |
| -ku, -mu | possessive | -ku, -mu |
| -an | nominal | -an |
| -ake, -ke, -en, -i | applicative and others | no hint |

Examples: omahe becomes rumahnya, omahku becomes rumahku, dituku becomes dibeli, nuku becomes meN-beli.

Known gaps: infixes (-um-, -in-), reduplication, circumfixes (ke-...-an, pa-...-an), stems not
in the lexicon, and krama-specific affixes. Every rule here needs review by Javanese speakers and
linguists. The analyzer is not part of `normalize`; it is reported separately.
