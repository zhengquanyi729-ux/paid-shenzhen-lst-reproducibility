# MANUSCRIPT FINAL GREP — v1.2.1

**Scope.** The final submission manuscript: `manuscript_submission/PAID_Shenzhen_LST_manuscript_npj_FINAL.docx` and its patched markdown sources in `manuscript_submission/manuscript_source/`. Case-sensitive substring counts, reported separately for the docx (the rendered submission document) and the markdown source set. Enforced by `release_tools/verify_manuscript_submission.py` (run by `run_all_release.py`); a non-zero banned count or a missing required phrase fails the release.

## Banned phrases (each must be 0 in docx and in sources)

| Phrase | docx | sources |
|---|---|---|
| `same qualitative skeleton` | 0 | 0 |
| `real, transferable signal` | 0 | 0 |
| `real but selection-region-specific` | 0 | 0 |
| `locked-region result is real but fragile` | 0 | 0 |
| `L2 level (a spatially robust relationship)` | 0 | 0 |
| `differ in climate and time of year` | 0 | 0 |
| `Verification note` | 0 | 0 |
| `Retrieval method: web search only` | 0 | 0 |
| `validated negative result` | 0 | 0 |
| `reproducible directional pattern` | 0 | 0 |
| `independent audit` | 0 | 0 |
| `prospectively selected candidate` | 0 | 0 |
| `prospectively-selected candidate` | 0 | 0 |
| `no journal-specific format fixed yet` | 0 | 0 |

Fourteen banned phrases; all zero in both the docx and the sources.

## Required phrases (each must be >= 1 in docx and in sources)

| Phrase | docx | sources |
|---|---|---|
| `locked-region evaluation under a documented protocol deviation` | 2 | 3 |
| `partial conceptual overlap` | 3 | 6 |
| `post-hoc implementation audit` | 5 | 11 |
| `No portable urban thermal law was established` | 1 | 1 |

## Title

`Auditable autonomous symbolic discovery of urban thermal relationships with admissibility constraints and separated validation` — present in the docx paragraphs: **TRUE**.

## Note on the historical file

In v1.2.1 the correction is a **prose-only unification**: the same corrected wording was carried to the
manuscript **sources of record** under `PAID/stage05_paper/manuscript/` and their rendered `.docx`/`.pdf`
were regenerated, so the sources of record and the submission copy no longer diverge. This gate itself
still checks only `manuscript_submission/`; no Stage 00–05 data, candidate, result, number, hash or log
entry was altered.

## Author-action prose items — resolved in v1.2.1

The AI-usage declaration (patch **P8**) is **APPLIED_AND_VERIFIED**, not held open: the author recorded
case **B** and the submission copy no longer contains the phrase "driven by a large language model". The
"independent validator" clarification (**P9**) is **RESOLVED (documented)**. See
`MANUSCRIPT_PATCH_VERIFICATION.md`, `LLM_MANUSCRIPT_CORRECTION.md` and `LLM_PROVENANCE_AUDIT_v1_2_1.md`.
