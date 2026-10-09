# Public Release Licensing Gate

Machine-readable release gate for the Shenzhen data provenance & redistribution-rights audit.
This file states the licensing posture that must hold before this repository is published as final.
It records decisions; it grants no rights and changes no licence state.

```
AUDIT_ID                     = SZ-PROVENANCE-RIGHTS-v1
REPO                         = paid-shenzhen-lst-reproducibility
AUDIT_DATE                   = 2026-10-09
AUDIT_TYPE                   = release-engineering / provenance (NOT legal advice)

FILES_INVENTORIED            = 313
FILES_CONTAINING_SZ_DATA     = 98
DATA_TABLES_ANALYSED         = 6            # data/shenzhen/*.csv (A/B/C/targets/split/mask)
FROZEN_DUPLICATE_GROUPS      = 20
UPSTREAM_SOURCES             = 11
UPSTREAM_WITH_PROVIDER_KNOWN = 1            # UP-05 roads (OpenStreetMap, INFERRED only)
UPSTREAM_PROVIDER_UNKNOWN    = 10
VARIABLES_ASSESSED           = 17
VARIABLES_CONFIRMED          = 9            # author ids/indices/labels/flags
VARIABLES_UNRESOLVED         = 8            # LST/NDVI/DEM/SVF/Road_Dens/X_BD/X_BH/X_VolDens

CODE_LICENSING_CONCLUSION    = MIT_CANDIDATE_SUPPORTED
CODE_VENDORED_THIRD_PARTY    = NO
CODE_COPYLEFT_DEPENDENCY     = NO
DATA_CC_BY_4_0_ELIGIBILITY   = UNRESOLVED     # third-party-derived values; not the author's to relicense
PUBLIC_ACCESS_EQUALS_CC      = NO             # "publicly accessible" is NOT treated as a licence
PROCESSED_EQUALS_OWNED       = NO             # "processed" is NOT treated as a relicensing right

CHANGCHUN_ROWLEVEL_TABLE     = EXCLUDE_FROM_PUBLIC_RELEASE   # gitignored; reviewer-only
RAW_SHENZHEN_RASTERS         = REPLACE_WITH_RECIPE_OR_HASH   # not present; provenance + frozen values
RAW_CHANGCHUN_PRODUCTS       = REPLACE_WITH_RECIPE_OR_HASH   # not present; recipe only

EXTERNAL_RIGHTS_VERIFICATION = PARTIALLY_PERFORMED   # official-domain WebSearch only; page fetch blocked
EXTERNAL_SOURCE_USED         = https://www.openstreetmap.org/copyright (accessed 2026-10-09; ODbL/OSMF)

RECOMMENDED_ARCHITECTURE     = C              # MIT code + no blanket data licence + file-specific notices
ARCHITECTURE_PATH            = C -> B -> A    # promote author-owned subsets as upstream rights get confirmed

LICENCE_ASSIGNED_IN_ROUND    = NONE           # no LICENSE file created; LICENSE_STATUS.md unchanged
CITATION_LICENSE_FIELD       = ABSENT         # CITATION.cff carries no license field (correct at this stage)
ZENODO_TOUCHED               = NO
GIT_MUTATION_PERFORMED       = NO             # no add/commit/push/tag/Release by this audit
FROZEN_RELEASE_POLLUTED      = NO             # new files are under docs/ only
PUBLIC_MANIFEST_EXPECTED_DIRTY = YES          # MANIFEST_SHA256.csv intentionally NOT regenerated

GATE_STATUS                  = BLOCKED_PENDING_AUTHOR_ACTION
BLOCKING_ITEMS               = 6
```

## Blocking items (must be closed by the author; never auto-PASS)

| # | Item | Owner | State |
|---|---|---|---|
| 1 | Decide the code licence (MIT proposed); add real `LICENSE`; update `LICENSE_STATUS.md` | Author | OPEN |
| 2 | Adopt Option-C notices (MIT for code; no licence granted for third-party-derived tables/figures) | Author | OPEN |
| 3 | If UP-05 is OpenStreetMap: add "© OpenStreetMap contributors" and settle Derivative-DB vs Produced-Work for `Road_Dens` | Author | OPEN |
| 4 | Identify Shenzhen upstream provider(s) + terms (UP-01…UP-04, UP-06, UP-07) | Author | OPEN |
| 5 | Confirm Changchun third-party licence (row-level table stays excluded until then) | Author | OPEN |
| 6 | Re-run this audit and update the matrix/gate once any upstream term is confirmed | Author | OPEN |

## What this gate does NOT do

- It does **not** assign a licence, create a `LICENSE` file, or edit `LICENSE_STATUS.md`.
- It does **not** add a `license` field to `CITATION.cff`.
- It does **not** delete or move any file, and it does **not** modify any frozen numerical artefact.
- It does **not** touch Zenodo, create a tag/Release, or perform any git mutation.

*Companion artefacts: `SHENZHEN_DATA_FILE_INVENTORY.csv`, `SHENZHEN_VARIABLE_PROVENANCE.csv`,
`UPSTREAM_DATA_RIGHTS_MATRIX.csv`, `AUTHOR_CREATED_MATERIALS_MATRIX.csv`, `CODE_LICENSING_AUDIT.md`,
`SHENZHEN_LICENSING_MATRIX.csv`, `SHENZHEN_LICENSING_REVIEW.md`.*

## Subsequent status (dated addendum, 2026-10-09)

The machine-readable block above is the pre-implementation audit record and is retained unchanged.
After it was written, **Option C was implemented** (see `LICENSING_IMPLEMENTATION_RECORD.md`). As a
result, some present-tense statements above no longer describe the current tree:

- **Blocking item 1** — the author adopted **MIT for author-owned code only**; the code licence is at
  `LICENSES/MIT-CODE.txt` (there is deliberately **no root `LICENSE`** file), and `LICENSE_STATUS.md`
  was updated. The code-licence decision is therefore **resolved**; the remaining open question is the
  exact presentation wording, and the **data** side is deliberately left unresolved (no blanket licence).
- **Blocking item 2** — Option-C notices are implemented (`docs/LICENSING.md`,
  `data/shenzhen/RIGHTS_NOTICE.md`, `figures_source/RIGHTS_NOTICE.md`, `data/README_DATA.md`).
- **`LICENCE_ASSIGNED_IN_ROUND = NONE`** in the block was true of the audit round; it is now superseded
  by the implementation round.
- Items 3–6 (OSM `Road_Dens` classification, Shenzhen upstream terms, Changchun licence, re-run) remain
  **OPEN** and unchanged. `GATE_STATUS` therefore stays **BLOCKED_PENDING_AUTHOR_ACTION** on those items.
