# Public-release audit — paid-shenzhen-lst-reproducibility

This audit records how the public repository was assembled from the verified reviewer package, what
was carried across, what was excluded, and the results of the safety scans. It is the evidence file for
the staging round.

**Date of staging:** 2026-10-09 · **Scope:** local directory creation and organisation only — no
`git add`, `git commit`, `git push`, no GitHub publish, no release.

---

## 1. Source release

| | |
|---|---|
| Source archive | `PAID_REVIEWER_RELEASE_v1_2_1.zip` |
| Source size | 45,547,655 bytes |
| **Source SHA-256** | `146722cac3f7fe163bdc65e9940cb924ff27f8a3b2052c7dc6998697e41efe76` |
| Verification | **Matches** the known-correct final-release hash. |
| Extraction | Extracted **once**, read-only, into a scratch directory outside the Git repository. The source release was not modified. |

## 2. Files copied

The public repository preserves the release's **machine-consumed** layout so the portable verification
layer resolves its paths, and consolidates human documentation under `docs/`.

| Area | What was carried | Notes |
|---|---|---|
| `PAID/` | The Stage 00–05 implementation — all Python (scripts, agents, libs, renderers), protocol text, configuration, prompt specifications, the candidate registry, frozen manifests, reports, and the manuscript figures (7 × pdf/png/svg/tif). | Historical record; path-strings inside it are frozen provenance. |
| `PAID/stage05_paper/manuscript/` | English manuscript sources + rendered `.docx`/`.pdf`, plus the `A6B_*` protocol-deviation audit files. | Internal Chinese working notes excluded (see §3). |
| `release_tools/` | The 18-file portable verifier layer, verbatim. | Re-scanned: no secret, no author path. |
| `verification/` | `verify_manifest.py` + `VERIFICATION_INDEX.md`, verbatim. | No keys. |
| `data/` | Public Shenzhen analysis-ready tables (6 files) + `README_DATA.md`; Changchun `DATA_DICTIONARY.md` + `_export_checks.json` (metadata only). | Restricted Changchun table excluded (see §3). |
| `audit/` | `AUDIT_INDEX.md`. | Pointer index; artefacts live in `PAID/`. |
| `figures_source/` | `README.md` + `FIGURE_SOURCE_INDEX.csv`. | |
| `manuscript_submission/` | The submission-facing manuscript copy + markdown sources. | Public-intended per the release. |
| `docs/` | Curated provenance/policy/deviation/limitation documents (see `docs/`). | Copies; see §5. |
| Root files | `README.md`, `QUICKSTART.md`, `LICENSE_STATUS.md`, `requirements-lock.txt`, `environment.yml`, `.gitignore`, `.gitattributes`, `MANIFEST_SHA256.csv`, the `FINAL_*_AVAILABILITY*` files. No root `CITATION.cff` and no `LICENSE` file (see §10). | `requirements-lock.txt` copied from the certified release; `environment.yml` generated (§6). |

`MANIFEST_SHA256.csv` was **regenerated for this public tree**: it lists only the files present here
(310 entries). It is intentionally **not** byte-identical to the reviewer-package manifest. See
`PUBLIC_RELEASE_LIMITATIONS.md`.

## 3. Files excluded

Full detail in `PUBLIC_RELEASE_EXCLUSIONS.md`. Summary:

- **Restricted data** — `data/changchun/changchun_analysis_ready.csv` (third-party row-level table,
  licence unconfirmed; reviewer-only); raw Shenzhen rasters (~857 MB); raw Changchun products (~6.1 GB).
- **Secrets/keys** — `validator_key.bin` and any `*.key`/`*.pem`/credential/token: none present.
- **Archives/cruft** — `PAID_REVIEWER_RELEASE_*.zip`; `.DS_Store`, `__pycache__/`, `*.pyc`,
  `.pytest_cache/`, IDE files: none present.
- **Reviewer-only / internal documents** — `AUTHOR_ACTION_REQUIRED_v1_2_1.md` (replaced by a cleaned
  public copy), `UPLOAD_INSTRUCTIONS_v1_2_1.md`, `REVIEWER_ACCESS_INSTRUCTIONS.md`,
  `DATA_AVAILABILITY_FOR_REVIEW.md` (public statement carried instead), and the internal Chinese
  working files (`STAGE05_NOTES_zh.md`, `REVISION_MATRIX_zh*.md`, `REVISION_ADDENDUM_V2_1.md`,
  `SECTION_REVISION_LOG.md`, `FINAL_CLEANUP_QA.md`).

## 4. Restricted-data exclusion statement

> **The Changchun row-level table (`data/changchun/changchun_analysis_ready.csv`) is excluded from the
> public repository because redistribution permission has not been confirmed.**

Consequently the public tree does **not** run the Changchun row-level verifier
(`release_tools/verify_changchun_release.py`); the 13/13 `RELEASE VERIFICATION: ALL PASS` result belongs
to the confidential reviewer package, not to this public repository. See
`PUBLIC_RELEASE_LIMITATIONS.md`.

## 5. Documentation consolidation

The reviewer package keeps its documents at the archive root; this repository collects the public ones
under `docs/` (per the target structure). Cross-references written relative to the reviewer-package root
should be read as repository-root-relative. The machine-consumed paths the verifiers depend on are kept
at their expected locations.

## 6. `requirements-lock.txt` and `environment.yml`

- `requirements-lock.txt` was **copied from the certified release** — not re-resolved, not upgraded, no
  substitutions. Certified: Python 3.10.12, numpy 2.2.6, pandas 2.3.3, matplotlib 3.10.8, Pillow 12.1.1
  (plus the transitive/BLAS pins).
- `environment.yml` is a generated **convenience** file (`name: paid-shenzhen-lst`, `conda-forge`, pip
  section aligned to the lock file). `requirements-lock.txt` remains canonical.

## 7. Safety scans (run on the assembled public tree)

| Scan | Tool / command | Result |
|---|---|---|
| Secret scan | `release_tools/scan_secrets.py` (266 text files) | **PASS** — 0 findings (no key-material filenames, no private-key / cloud-token / API-key patterns) |
| Secret grep | credential-name patterns (`api_key`, `apikey`, cloud-token names, private-key markers, `password`, `credential`) | Only benign hits: `.gitignore` patterns and the scanner's own code/docs. No secrets. |
| Absolute-path scan | `release_tools/scan_absolute_paths.py` (73 reviewer-layer files) | **PASS** — 0 matches in the reviewer layer |
| Absolute-path grep (whole tree) | author-machine and sandbox-root path prefixes; see `docs/ARCHIVE_PORTABILITY_REPORT.md` | 13 files, **all** inside the frozen `PAID/` historical record; 0 in the reviewer layer |
| Large-file scan | `find . -type f -size +20M` | **0 files over 20 MB** |
| Manifest integrity | `verification/verify_manifest.py` | **RESULT: PASS (all listed hashes verified)** |

## 8. Large files (>20 MB)

**None.** The largest files, all below the threshold and all public-intended, are:

| Size | File | Purpose / rights |
|---|---|---|
| 15.8 MB | `PAID/stage05_paper/figures/fig1_protocol_split.svg` | Paper Figure 1, vector export; public figure |
| 4.4 MB | `PAID/stage05_paper/manuscript/PAID_Shenzhen_LST_manuscript.docx` | Frozen manuscript record; public figure/text |
| 4.4 MB | `manuscript_submission/PAID_Shenzhen_LST_manuscript_npj_FINAL.docx` | Submission copy |
| 4.4 MB | `PAID/stage05_paper/manuscript/PAID_Shenzhen_LST_manuscript_npj.docx` | npj variant |
| 3.5 MB | `PAID/stage05_paper/figures/fig0_study_overview.tif` | Graphical abstract (TIFF) |

## 9. Public repository tree

```
paid-shenzhen-lst-reproducibility/
├── README.md  QUICKSTART.md  LICENSE_STATUS.md
├── environment.yml  requirements-lock.txt  MANIFEST_SHA256.csv  .gitignore
├── FINAL_DATA_AVAILABILITY_PLACEHOLDER_v1_2_1.txt  FINAL_DATA_AVAILABILITY.txt
├── FINAL_CODE_AVAILABILITY_PLACEHOLDER_v1_2_1.txt  FINAL_CODE_AVAILABILITY.txt
├── PAID/                      (Stage 00–05 historical implementation)
├── release_tools/             (portable verifier layer)
├── verification/              (verify_manifest.py + index)
├── data/  { shenzhen/  changchun/  README_DATA.md }
├── audit/  figures_source/  manuscript_submission/
└── docs/
```

## 10. Unresolved licence items

- **Code / data licence:** not assigned. There is **no `LICENSE` file**; `LICENSE_STATUS.md` states
  that licensing is pending and grants no rights. Proposed terms (MIT / CC-BY-4.0) are placeholders
  only. Change A-3.
- **Changchun third-party licence:** not confirmed → the row-level table is excluded. Change A-2.
- **Identifiers:** no repository URL, DOI or archive record is claimed. There is **no root
  `CITATION.cff`**; the draft `docs/CITATION_TEMPLATE.cff` deliberately leaves the optional
  identifier fields out. Change A-5.

No fabricated licence, DOI, URL or attribution appears anywhere in this repository.
