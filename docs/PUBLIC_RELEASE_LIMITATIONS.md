# Public-release limitations

What a reader of this **public** repository should know before treating any command as a guarantee.

## 1. The Changchun row-level verifier cannot run here (by design)

`release_tools/verify_changchun_release.py` recomputes the six frozen Changchun external-replication
numbers from the slim analysis-ready table `data/changchun/changchun_analysis_ready.csv`. That table is
**third-party row-level data whose redistribution licence is unconfirmed**, so it is **not** in this
public repository (see `THIRD_PARTY_DATA_REVIEW.md` and `PUBLIC_RELEASE_EXCLUSIONS.md`).

Consequences:

- The scientific verifier is shipped **unmodified** (per the release design); it is simply not runnable
  here without the restricted input.
- A full `python release_tools/run_all_release.py` therefore reports the `CHANGCHUN_NUMERICS` verifier
  as failing/skipped. **The public tree is not a 13/13 run.** The 13/13 `RELEASE VERIFICATION: ALL PASS`
  result is a property of the **confidential reviewer package**, which includes the restricted table.
- Everything else in the portable layer — release integrity, archive paths, the frozen split, the
  candidate registry, the Stage-04 statistics, the Stage-05 chain, the figures, the submission wording,
  the internal-reference and availability checks, and the two scans — runs on this public tree.
- A derivation recipe (source identifiers + exact QC/derivation steps) lets a third party regenerate
  the excluded table from the original source: see `THIRD_PARTY_DATA_REVIEW.md` and
  `data/changchun/DATA_DICTIONARY.md`.

## 2. `MANIFEST_SHA256.csv` here is the public-tree manifest

The reviewer package ships a manifest over the **full** reviewer tree. This repository ships a manifest
regenerated over the **public subset** actually present here. It is therefore not byte-identical to the
reviewer manifest, and it intentionally does not list the excluded Changchun table.

`verification/verify_manifest.py` is a verbatim copy of the release checker. Because this repository is
under version control, running it may print *unlisted* informational lines for files that are not in the
manifest (including `.git/` objects); only `MISSING` or `HASH …` lines indicate a real problem.

## 3. Documentation was consolidated into `docs/`

In the reviewer package, documentation files sit at the archive root. In this repository they are
collected under `docs/` for a clean public tree. Cross-references inside those documents that were
written relative to the reviewer-package root (`release_tools/…`, `PAID/…`, `data/…`) should be read as
**repository-root-relative** when moving between files. The machine-consumed paths that the verifiers
depend on (`PAID/`, `data/`, `release_tools/`, `verification/`, `audit/`, `figures_source/`,
`manuscript_submission/`, and the `FINAL_*_AVAILABILITY*` files at the root) are kept at their expected
locations so the portable layer resolves them.

## 4. Open items are stated, not hidden

- Licence: **not assigned** — there is no `LICENSE` file; `LICENSE_STATUS.md` states that licensing is
  pending and grants no rights.
- Identifiers: **none asserted** — no repository URL, DOI or archive record is claimed; there is no
  root `CITATION.cff`.
- Author metadata: **not entered** — the draft `docs/CITATION_TEMPLATE.cff` carries `[author …]`
  placeholders.

See `AUTHOR_ACTION_REQUIRED_PUBLIC.md`.
