# SUBMISSION MANUSCRIPT — version record (v1.2.1)

**This is the submission copy.** In v1.2.1 the historical Stage-05 manuscript inside
`PAID/stage05_paper/manuscript/` is **also** carried to the same corrected wording (its rendered
`.docx`/`.pdf` were regenerated), so the submission copy and the sources of record do not diverge on
prose. No Stage 00–05 *data, candidate, result, number, hash or log entry* is altered by this — it is a
**prose-only** unification.

- **Title:** *Auditable autonomous symbolic discovery of urban thermal relationships with
  admissibility constraints and separated validation*
- **Target journal:** npj Urban Sustainability (Nature Portfolio)
- **Rendered document:** `PAID_Shenzhen_LST_manuscript_npj_FINAL.docx`
- **Markdown sources:** `manuscript_source/` (`manuscript_npj_en.md` plus the section files that
  compose it: `intro_en.md`, `methods_en.md`, `results1_en.md`–`results4_en.md`, `discussion_en.md`,
  `declarations_en.md`, `references_en.md`, `references.bib`).

## Prose patches applied (P1–P11)

Twelve prose corrections were applied and machine-verified (0 banned phrases; required phrases present;
title match) — see `../MANUSCRIPT_PATCH_VERIFICATION.md` and
`../release_tools/verify_manuscript_submission.py`. No number, table, figure, threshold or frozen
result was changed by any patch.

## Author-action prose items resolved in v1.2.1 (P8, P9)

The AI-usage declaration (patch **P8**) is **APPLIED_AND_VERIFIED**: the author recorded case **B** and
the manuscript no longer states the pipeline was "driven by a large language model"; the declaration now
records authoring/writing support and states that reproducing the numbers needs no LLM or network. The
"independent validator" clarification (**P9**) is **RESOLVED (documented)**. See
`../LLM_MANUSCRIPT_CORRECTION.md`, `../LLM_PROVENANCE_AUDIT_v1_2_1.md` and
`../release_tools/verify_manuscript_submission.py`.

The remaining author items (Changchun redistribution licence, code/data licence, author metadata,
repository URL/DOI) are **not** prose and are recorded in `../AUTHOR_ACTION_REQUIRED_v1_2_1.md`.
