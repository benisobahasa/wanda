# Data Governance (draft v0.1)

Applies to any speech recordings, transcripts or word lists contributed to Wanda.
This is a working draft to be reviewed with speaker communities and a legal
adviser before use. It is not legal advice.

## Principles
1. **Consent first.** No one's voice or words are used without informed, written
   (or recorded) consent in a language they understand (Indonesian or Javanese).
2. **Contributors choose the licence** from the options on the consent form.
3. **Withdrawal.** Contributors can ask for removal at any time. We remove their
   data from the working dataset within 30 days and from future releases. Models
   or releases already published cannot be recalled; contributors are told this up front.
4. **No sale, no hidden use.** Data is never sold. It is used only for the stated
   purposes: improving open dialect-understanding tools and open evaluation sets.
5. **Minimum data.** Collect speech and the words needed. No names, no location
   beyond region or dialect, no sensitive topics. Prompts are neutral (everyday phrases).
6. **Attribution.** Contributors are credited unless they prefer to stay anonymous.
7. **Review before release.** Community reviewers check lexicon entries and
   evaluation items before they are marked `reviewed`.

## Stewardship council
A small group (target 5 to 7) of Javanese speakers from different dialect areas,
including at least one linguist and one non-technical community member, that:
approves licence options, handles withdrawal requests, and signs off dataset releases.
Until the council exists, maintainers act as interim stewards and must say so in
every release note.

## Storage and privacy
* Raw audio stored encrypted, access limited to named stewards.
* Public releases contain only data whose contributors chose a public licence.
* Voice recordings are personal data. Before collecting at scale, check
  Indonesia's personal data protection law (Law No. 27 of 2022) with a legal adviser.
* Do not collect from minors without a parent or guardian's consent.

## Release status of data
`unreviewed` -> `reviewed` (two community reviewers agree) -> `released`.
