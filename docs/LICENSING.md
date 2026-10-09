# Licensing and reuse

This repository mixes code, data, figures, manuscript text and third-party-derived material. **No
single licence covers all of it.** The correct statement of scope is:

> Code is licensed under MIT. Data and non-code materials are governed by file-specific rights
> notices and upstream terms.

The repository must **not** be described as "MIT licensed" as a whole.

---

## 1. Code

**Author-owned source code is licensed under the MIT License. See `LICENSES/MIT-CODE.txt`.** This
applies to author-owned source code in the following directories:

- `PAID/`
- `release_tools/`
- `verification/`

except where an individual file explicitly states otherwise. The operative licence text is the
[`LICENSES/MIT-CODE.txt`](../LICENSES/MIT-CODE.txt) file. The audit that supports this decision (author-written code, no vendored
third-party source, no copyleft dependency) is `docs/CODE_LICENSING_AUDIT.md`.

This MIT grant covers source code only. **The MIT licence does not apply automatically to data,
figures, manuscript text, or third-party-derived materials.** It does **not** extend to `data/`,
`figures_source/`, `manuscript_submission/`, or any third-party-derived artefact or material carrying
separate upstream terms.

## 2. Shenzhen analysis-ready data

The Shenzhen analysis-ready tables are **publicly accessible for transparency and reproducibility**,
but the authors **do not apply a blanket CC-BY-4.0 relicence** to these tables because several upstream
source terms and relicensing rights remain unresolved.

Public availability does **not** mean that all upstream rights are waived, and it is **not** treated as
a licence. Users must consult the following before redistribution or relicensing:

- `docs/SHENZHEN_LICENSING_MATRIX.csv`
- `docs/UPSTREAM_DATA_RIGHTS_MATRIX.csv`
- `docs/SHENZHEN_VARIABLE_PROVENANCE.csv`

**No additional blanket licence is granted by the authors for files whose upstream rights remain
unresolved.** Per-file rights notices (e.g. `data/shenzhen/RIGHTS_NOTICE.md`) govern the data
directories.

## 3. OpenStreetMap-derived content

Where OpenStreetMap-derived content is present, it is attributed as required:

> **© OpenStreetMap contributors** — https://www.openstreetmap.org/copyright

OpenStreetMap data is licensed under the **Open Data Commons Open Database License (ODbL)** by the
OpenStreetMap Foundation (source: the official OSM copyright page, https://www.openstreetmap.org/copyright,
accessed 2026-10-09).

The provenance audit identifies the `Road_Dens` field as **probably OSM-derived**, but its
classification as a *Produced Work*, a *Derivative Database*, or another derived representation has
**not yet been conclusively established** from the archived provenance. Accordingly:

- the whole Shenzhen table is **not** claimed to be ODbL;
- the whole Shenzhen table is **not** claimed to be CC-BY;
- `Road_Dens` is **not** claimed to be definitively a Produced Work (nor definitively a Derivative
  Database).

Status: **ODbL source attribution confirmed; derived-output classification unresolved.** See
`docs/UPSTREAM_DATA_RIGHTS_MATRIX.csv` (UP-05).

## 4. Changchun data

The Changchun row-level analysis-ready table is **third-party data whose redistribution licence is
unconfirmed**. It is **not included** in this public repository (reviewer-only); only its data
dictionary and a derivation recipe ship. See `docs/THIRD_PARTY_DATA_REVIEW.md`.

## 5. Figures

The figures themselves are author-created visualisations, but the underlying numbers derive from
upstream-sourced variables, so **underlying data rights may differ**. The whole `figures_source/`
directory is **not** offered under CC-BY-4.0. See `figures_source/RIGHTS_NOTICE.md`.

## 6. Manuscript

The manuscript text is **not covered by the MIT software licence**. Publication rights will follow the
journal/publisher licence selected at publication. See `manuscript_submission/`.

## 7. How to read the file-specific notices

| Path | Notice |
|---|---|
| `LICENSES/MIT-CODE.txt` | MIT License — author-owned source code |
| `LICENSE_STATUS.md` | Status change notice (code resolved; data file-specific) |
| `data/README_DATA.md` § Licensing and redistribution | Data-level statement |
| `data/shenzhen/RIGHTS_NOTICE.md` | Shenzhen data rights notice |
| `figures_source/RIGHTS_NOTICE.md` | Figure rights notice |
| `docs/SHENZHEN_LICENSING_MATRIX.csv` | Per-file public-release action + proposed licence |
| `docs/UPSTREAM_DATA_RIGHTS_MATRIX.csv` | Per-upstream-source three-layer rights |
| `docs/SHENZHEN_VARIABLE_PROVENANCE.csv` | Per-variable provenance status |
| `docs/PUBLIC_RELEASE_LICENSING_GATE.md` | Release gate + blocking items |

*This document is a factual licensing statement produced by a release-engineering audit; it is not
legal advice.*
