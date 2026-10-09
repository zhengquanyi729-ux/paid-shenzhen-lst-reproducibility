# Public-release exclusions

This file records **everything that was deliberately left out** of the public repository, and why. The
source was the verified reviewer package `PAID_REVIEWER_RELEASE_v1_2_1.zip`
(SHA-256 `146722cac3f7fe163bdc65e9940cb924ff27f8a3b2052c7dc6998697e41efe76`). Only public-safe code and
documentation were carried across.

Rule applied throughout: **if it was uncertain whether a file is public-safe, it was not copied.**

## 1. Restricted / non-redistributable data

| Item | Where it was | Why excluded |
|---|---|---|
| `data/changchun/changchun_analysis_ready.csv` | reviewer package `data/changchun/` | Third-party row-level table; **redistribution licence unconfirmed**; reviewer-only. See `THIRD_PARTY_DATA_REVIEW.md`. |
| Raw Shenzhen source rasters (~857 MB) | not in the package | Redistribution rights unconfirmed; not redistributed anywhere. |
| Raw Changchun satellite products (~6.1 GB) | not in the package | Third-party licence unconfirmed + size. |

## 2. Secrets, keys, credentials

| Item | Status |
|---|---|
| `validator_key.bin` (AES vault key) | **Never present** — withheld by design in the reviewer package too; excluded from any public deposit. |
| Any `*.key`, `*.pem`, `*.p12`, `*.pfx`, `id_rsa*`, `*.keystore`, `*.secret` | None present. |
| Any API token / credential / password / private key | None present. |

## 3. Archives and machine cruft

| Item | Status |
|---|---|
| `PAID_REVIEWER_RELEASE_v1_2_1.zip` (and any `PAID_REVIEWER_RELEASE_*.zip`) | **Not copied.** Also listed in `.gitignore`. |
| `.DS_Store`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, IDE files | None present; covered by `.gitignore`. |

## 4. Reviewer-only / internal documents (not public-safe)

| Item | Where it was | Why excluded |
|---|---|---|
| `AUTHOR_ACTION_REQUIRED_v1_2_1.md` | package root | Author-private working note; replaced by a cleaned public copy, `docs/AUTHOR_ACTION_REQUIRED_PUBLIC.md`. |
| `UPLOAD_INSTRUCTIONS_v1_2_1.md` | package root | Internal upload steps; not part of a public repository. |
| `REVIEWER_ACCESS_INSTRUCTIONS.md` | package root | Reviewer-distribution instructions; not for public readers. |
| `DATA_AVAILABILITY_FOR_REVIEW.md` | package root | A "reviewer-private" availability note; a public availability statement is carried instead in `docs/DATA_AVAILABILITY.md`. |
| `STAGE05_NOTES_zh.md` | `PAID/stage05_paper/manuscript/` | Internal Chinese working notes. |
| `REVISION_MATRIX_zh.md`, `REVISION_MATRIX_zh_v2.md` | `PAID/stage05_paper/manuscript/` | Internal Chinese revision matrices. |
| `REVISION_ADDENDUM_V2_1.md` | `PAID/stage05_paper/manuscript/` | Internal revision working note. |
| `SECTION_REVISION_LOG.md` | `PAID/stage05_paper/manuscript/` | Internal revision log. |
| `FINAL_CLEANUP_QA.md` | `PAID/stage05_paper/manuscript/` | Internal cleanup QA note. |

## 5. Reviewer-package bookkeeping files not carried over

These are package-internal records of the reviewer build. They are not part of a public repository and
were left out: `RELEASE_QA_v1_2_1.md`, `CLEANROOM_TEST_REPORT_v1_2_1.md`, `RELEASE_VARIANT_DIFF.md`,
`REPOSITORY_RECORD.md`, `MANUSCRIPT_PATCH_VERIFICATION.md`, `LLM_MANUSCRIPT_CORRECTION.md`,
`MANIFEST_SHA256.csv` (the reviewer manifest), `RELEASE_FILE_INVENTORY.csv`, and the mirror
`requirements*.txt` variants (`requirements.txt`, `requirements-core.txt`, `requirements-historical.txt`)
that describe the reviewer-package build. The public repository carries `requirements-lock.txt` (the
certified environment) plus a convenience `environment.yml`.

## 6. What this means for the public tree

With the exclusions above, the public repository:
- contains **no** raw rasters, **no** third-party row-level table, **no** AES key and **no** secret;
- **cannot** run one verifier — `CHANGCHUN_NUMERICS` — because its restricted input is absent;
- states the licence and identifiers **only** as placeholders, never as confirmed facts.
