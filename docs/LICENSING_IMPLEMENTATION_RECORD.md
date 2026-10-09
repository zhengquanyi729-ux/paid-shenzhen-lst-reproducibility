# Licensing implementation record — Option C

**Date:** 2026-10-09. **Decision adopted:** **OPTION C** (from `docs/SHENZHEN_LICENSING_REVIEW.md`
§12). This record implements the licensing boundary. It changes **no** scientific data value and
**no** Stage 00–05 frozen science, and it performs **no** git mutation.

## What was decided

| Area | Decision |
|---|---|
| **Code** | **MIT.** `LICENSES/MIT-CODE.txt` (MIT, © 2026 Mengxiao Jin, Yu Shao, and Quanyi Zheng) applies to author-owned source code in `PAID/`, `release_tools/`, `verification/`, except where an individual file states otherwise. **Author-owned source code is licensed under the MIT License. See `LICENSES/MIT-CODE.txt`.** |
| **Shenzhen data** | **Public, no blanket author-applied CC-BY-4.0.** The analysis-ready tables stay public for reproducibility; the authors grant **no** blanket data licence. |
| **OpenStreetMap** | **ODbL attribution added; derived-output classification unresolved.** `© OpenStreetMap contributors` + https://www.openstreetmap.org/copyright recorded where OSM-derived content is present; `Road_Dens` is **not** classified as a Produced Work, Derivative Database, or otherwise. |
| **Changchun row-level** | **Excluded.** Third-party row-level table remains reviewer-only / absent from the public tree. |
| **Manuscript** | **Not** covered by MIT; publication rights follow the journal/publisher licence. |
| **Zenodo** | **Not yet released.** No `.zenodo.json` created (a mixed-rights record must be expressed correctly on the Zenodo side later). |

## Files created / changed by this implementation

| File | Change |
|---|---|
| `LICENSES/MIT-CODE.txt` | **New.** Standard MIT text, unmodified; © 2026 the three named authors. (This file was first created as a root `LICENSE` and then moved, byte-for-byte, into `LICENSES/MIT-CODE.txt` so the repository carries no root standard `LICENSE`. The move preserves the file's SHA-256.) |
| `LICENSE_STATUS.md` | **Rewritten** to the resolved-code status (keeps a short history note; links to `docs/LICENSING.md`). |
| `docs/LICENSING.md` | **New.** Full licensing statement (code / Shenzhen data / OSM / Changchun / figures / manuscript). |
| `data/README_DATA.md` | **Added** `## Licensing and redistribution` section. |
| `data/shenzhen/RIGHTS_NOTICE.md` | **New.** Shenzhen data rights notice. |
| `figures_source/RIGHTS_NOTICE.md` | **New.** Figure-source rights notice. |
| `README.md` | **Updated** Licensing/Status sections (tree, status bullet, `## Licensing`). |
| `docs/LICENSING_IMPLEMENTATION_RECORD.md` | **New.** This file. |

## Not changed (deliberately)

- No scientific data value changed; no Stage 00–05 frozen artefact changed.
- `CITATION.cff` **carries no `license` field** (left as-is this round; the software-object vs mixed
  repository ambiguity is resolved at the Zenodo metadata stage).
- No `.zenodo.json` created.
- No GitHub Release, no Zenodo record, no `git add` / `commit` / `push`.

## Presentation fix — root `LICENSE` → `LICENSES/MIT-CODE.txt`

After the initial Option-C implementation, a presentation fix was applied so that the repository
carries **no root standard `LICENSE`** file: the root `LICENSE` was moved, **byte-for-byte
(SHA-256 unchanged)**, to `LICENSES/MIT-CODE.txt`. Every reference in `README.md`,
`LICENSE_STATUS.md`, `docs/LICENSING.md` and this record was retargeted to `LICENSES/MIT-CODE.txt`.
The purpose is to avoid a single root `LICENSE` being read as licensing the whole mixed-rights
repository. `MANIFEST_SHA256.csv` was regenerated and `verification/verify_manifest.py` reports PASS.

## Resulting posture

- Code = MIT (author-owned code only). **Author-owned source code is licensed under the MIT License.
  See `LICENSES/MIT-CODE.txt`.**
- Data + figures + manuscript = file-specific rights notices; **no blanket licence**. **The MIT
  licence does not apply automatically to data, figures, manuscript text, or third-party-derived
  materials.**
- Repository as a whole is **mixed-rights** and must not be described as "MIT licensed".

## Open items (unchanged, still author action)

See `docs/PUBLIC_RELEASE_LICENSING_GATE.md` (GATE_STATUS = BLOCKED_PENDING_AUTHOR_ACTION). The OSM
Derivative-Database-vs-Produced-Work question for `Road_Dens` and the Shenzhen upstream terms remain
**UNRESOLVED** and are not resolved by this implementation.
