# RELEASE NOTES — v1.2 → v1.2.1

**Scope.** v1.2.1 is a **final consistency patch**. It changes **manuscript prose, availability
statements, citation metadata and internal references only**. It does **not** rerun or change any
science: no frozen Stage 00–05 output is modified, no number is recomputed differently, and no result
threshold moves. The frozen numbers and their sources are stated in
`FROZEN_NUMERICAL_CONTRACT_v1_2_1.md`.

---

## v1.2.1 repairs

**1. AI/LLM-usage disclosure corrected (author case B).** The submission manuscript declared that the
discovery and validation roles are "software components driven by a large language model", which
mischaracterised the released artefact (0 model/network calls in the released code). The author has
recorded the authoring-time position (**case B**): large-language-model tools were used during the
development and writing of the work, but no language model forms part of the released scientific
pipeline. The declaration was rewritten and the manuscript **sources of record and rendered
`.docx`/`.pdf` were regenerated** so they no longer diverge. See `LLM_PROVENANCE_AUDIT_v1_2_1.md`,
`LLM_MANUSCRIPT_CORRECTION.md`, `MODEL_AND_AGENT_DISCLOSURE.md`.

**2. "prospectively selected candidate" removed (patch P10).** The phrase was removed from all current
manuscript prose and replaced with the two-sentence Region-C form ("a Region-C evaluation of a frozen
candidate under a documented protocol deviation…"). It is now a **banned phrase** in
`release_tools/verify_manuscript_submission.py`.

**3. References production note removed (patch P11).** The internal note in `references_en.md`
("Citation style is generic numeric (no journal-specific format fixed yet) … verified by web search")
was removed from the source, the composed markdown and the rendered document. The phrase is now banned.

**4. Data-availability statement rewritten.** It now states the **complete 32,748-cell Shenzhen spatial
split**, the exact analysis-ready tables **actually used for Regions A, B and C**, and the Region-C
wording (n = 2,987, "scientifically spent under Protocol V1", not a pristine holdout), and it no longer
over-claims per-region tables "for all 32,748 cells". See `FINAL_DATA_AVAILABILITY_PLACEHOLDER_v1_2_1.txt`.

**5. Code-availability statement rewritten.** It describes Stages 00–05 plus the portable verification
layer, states that no model/network is called by the released code, and adds the sentence
"**No model is required to reproduce the reported numerical results from the frozen release
artefacts.**" See `FINAL_CODE_AVAILABILITY_PLACEHOLDER_v1_2_1.txt`.

**6. Citation metadata corrected (`CITATION.cff`).** The exact manuscript title is used; "3D urban form"
→ "urban morphology and surface characteristics"; "a locked spatial validation region" → "a separated
spatial evaluation architecture with a documented protocol deviation". Version → 1.2.1.

**7. Leftover v1.1 references removed; internal references repaired.** Dangling v1.1-named links and
unversioned links (bare `RELEASE_QA`, `UPLOAD_INSTRUCTIONS`, `CLEANROOM_TEST_REPORT`,
`LLM_PROVENANCE_AUDIT` and `AUTHOR_ACTION_REQUIRED` names carrying no version suffix) were repointed to
their `*_v1_2_1` files; two new verifiers enforce this — `release_tools/verify_internal_references.py`
and `release_tools/verify_availability_statements.py`.

**8. Report files renamed** to the `*_v1_2_1` names (`CLEANROOM_TEST_REPORT_v1_2_1.md`,
`RELEASE_QA_v1_2_1.md`, `LLM_PROVENANCE_AUDIT_v1_2_1.md`, `AUTHOR_ACTION_REQUIRED_v1_2_1.md`,
`MANUSCRIPT_FINAL_GREP_v1_2_1.md`).

---

## Carried from v1.2 (brief)

ASCII-only archive paths + `verify_archive_paths.py`; the definitional placebo identity (`S03-H01-LIN7`
≡ Baseline A by specification); split readiness flags; a submission copy separated from the historical
manuscript; the frozen numerical contract + tolerance policy; a pinned certified environment; and the
completeness pass over the documentation set. See the v1.2 sections preserved below in
`FROZEN_NUMERICAL_CONTRACT_v1_2_1.md` and `NUMERICAL_TOLERANCE_POLICY.md`.

## What did **not** change

- **Any frozen number.** The Stage-04 headline (Baseline A 2.841519144671417 · H10 2.462447828502684 ·
  Δ 0.379071316168733 · p 0.005 · CI [0.276067201358972, 0.481358279348766] · R25 0.137499076805151 /
  p 0.085), the candidate canon hashes, the Region-C plaintext SHA-256 (`b4a709e1…eab9`), the
  experiment-log record count (1,259) and every Stage-05 value are reproduced to the frozen tolerance.
- **Any Stage 00–05 data / candidate / result / log.** Unchanged. Only manuscript **prose** and
  reviewer-facing documentation changed.
- **The protocol deviation.** Region C remains *scientifically spent under Protocol V1* and Stage 04
  remains a locked-region evaluation under a documented deviation — not a pristine confirmatory test.

## Still open (author action required)

The items in `AUTHOR_ACTION_REQUIRED_v1_2_1.md`: A-2 Changchun redistribution licence, A-3 code/data
licence, A-4 authors/CRediT/funding, A-5 repository URL/DOI · commit SHA. A-1 (LLM provenance) is
**resolved** in this build. None blocks technical reproducibility; all block
`JOURNAL_REVIEW_PACKAGE_READY`.

---

## Deprecated files

The former v1.1-named documents **`RELEASE_NOTES_v1_1`** and **`MANUSCRIPT_PATCHES_v1_1`** (`.md`)
are **not** shipped (their content is superseded by this file and `MANUSCRIPT_PATCH_VERIFICATION.md`).
One version of each reviewer document ships; versioned names carry the current `*_v1_2_1` suffix.
