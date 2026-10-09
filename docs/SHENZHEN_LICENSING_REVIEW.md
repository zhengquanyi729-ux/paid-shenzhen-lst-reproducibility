# Shenzhen data provenance & redistribution-rights review

**Audit type:** release-engineering / provenance audit. **This is not legal advice.** It records what
evidence exists for each shipped file, separates *public distribution* from *relicensing*, and states
what remains unresolved. It grants no rights and changes no licence state.

**Repository:** `paid-shenzhen-lst-reproducibility` (public tree, pre-release).
**Audit date:** 2026-10-09. **External rights verification:** PARTIALLY PERFORMED — a WebSearch against
official-domain sources only (the direct page fetch was blocked by the sandbox egress policy; see §6).

**Bottom line.** The code is an MIT candidate (author-written, permissive dependencies, no copyleft — see
`CODE_LICENSING_AUDIT.md`). The **data** cannot yet be relicensed: no Shenzhen upstream source records a
licence, attribution, sensor, acquisition date or retrieval algorithm, and one layer (roads) merely
*infers* OpenStreetMap. The recommended architecture is therefore **Option C** — MIT for code, **no
blanket data licence**, file-specific notices — with the author able to promote the author-owned
subsets later.

---

## 1. Scope

Everything in the public tree that *encodes* Shenzhen data or Shenzhen-derived values: the six
`data/shenzhen/*.csv` tables, their frozen duplicates under `PAID/`, the masks and id-lists, the vault
ciphertext, the boundary-derived JSON, the seven figures, the manuscript, and the source code. The
inventory (`SHENZHEN_DATA_FILE_INVENTORY.csv`) covers **all 313 files**. Third-party Changchun material
is in scope only to confirm its exclusion. Raw Shenzhen rasters (~857 MB) and raw Changchun products
(~6.1 GB) are **not present** in the tree and are assessed through their provenance records.

## 2. Audit method

Local evidence first: file hashes and sizes; per-file roles; the frozen Stage-00 metadata
(`s00_01_metadata.json`), vector comparison (`s00_05_vector.json`), the data dictionary, the provenance
and region-C documents, and the publication audit. Then, because the network was available, a
**first-party-only** rights check (provider sites / official licence pages) for any identifiable
upstream. Each file was classified into raw / transformed / derived / model output / author metadata,
and each upstream marked with a three-layer rights verdict (public distribution, author relicensing,
CC-BY-4.0 eligibility). Anything not evidenced was left **UNRESOLVED** rather than guessed.

## 3. Files reviewed

See `SHENZHEN_DATA_FILE_INVENTORY.csv` (313 rows, with SHA-256, size, tabular shape, probable role,
`contains_shenzhen_data`, and duplicate groups). The data-bearing core:

| Role | Files |
|---|---|
| ANALYSIS_READY | `zone_A_open.csv` (19,184×9), `zone_B_devval.csv` (6,182×9), `zone_C_analysis_ready.csv` (2,987×9), `zone_C_targets.csv` (2,987×2), + frozen `PAID/` copies |
| SPATIAL_SPLIT | `analysis_split.csv` (32,748×6) |
| MASK_OR_INDEX | `spatial_mask.csv` (25,366×4), `grid_validity.csv`, `analysis_mask.csv`, `valid_ids_*.txt` |
| MODEL_OUTPUT | `experiment_log.jsonl` (1,259 records), candidate registries/manifests |
| FIGURE_SOURCE | 7 figures × pdf/svg/png/tif + `figures_source/` |
| PROVENANCE_METADATA | 119 documentation/metadata files |
| CODE_OR_CONFIG | 94 scripts/config files |

Twenty duplicate groups were found (e.g. DUP-06: Region A appears three times — `data/`, the frozen
`split/`, and the sandbox `inputs/` — byte-identical). Duplicates share one SHA-256 and one rights
verdict.

## 4. Upstream sources

Eleven distinct upstream sources are catalogued in `UPSTREAM_DATA_RIGHTS_MATRIX.csv`. Only **one** has
any provenance token at all:

| ID | Source | Provider identity | Confidence |
|---|---|---|---|
| UP-01 | Shenzhen LST raster | UNKNOWN | UNKNOWN |
| UP-02 | Shenzhen NDVI raster | UNKNOWN | UNKNOWN |
| UP-03 | Shenzhen DEM raster | UNKNOWN | UNKNOWN |
| UP-04 | Shenzhen buildings | UNKNOWN (fields: `Height`, `id` only) | UNKNOWN |
| UP-05 | Shenzhen roads | **OpenStreetMap (INFERRED)** | LOW |
| UP-06 | Shenzhen SVF (5 m) | UNKNOWN | UNKNOWN |
| UP-07 | Shenzhen boundaries | UNKNOWN | UNKNOWN |
| UP-08 | 100 m grid | **AUTHORS** | HIGH |
| UP-09 | `data_原始.csv` | AUTHORS over third-party layers | LOW |
| UP-10 | Changchun dataset | UNKNOWN | UNKNOWN |
| UP-11 | Changchun companion grid | UNKNOWN | UNKNOWN |

The only identification is **UP-05**: the road shapefiles carry OSM-specific fields
(`osm_id, code, fclass, name, ref, oneway, maxspeed, layer, bridge, tunnel`) and a regional
(Guangdong-scale) bounding box. This is an *inference from field names*, not a documented source
line — the delivered files carry no LICENSE, README or attribution string.

## 5. Variable-level provenance

Per-variable status is in `SHENZHEN_VARIABLE_PROVENANCE.csv` (17 variables). Summary:

- **CONFIRMED (9):** `Grid_ID`, `row`, `col`, `in_main`, `zone`, `role`, `use_main`, `use_relaxed`,
  `exclusion` — all author-constructed identifiers, indices, labels or flags.
- **UNRESOLVED (8):** `LST_mean`, `NDVI_mean`, `DEM_mean`, `SVF_mean`, `Road_Dens`, `X_BD`, `X_BH`,
  `X_VolDens`.

Even where the **unit** is stated (e.g. LST in °C), the **source, sensor, retrieval algorithm, product
version and acquisition date are absent** from the archive, so the variable is UNRESOLVED — the audit
does not fill these with domain common sense. `Road_Dens`, `X_BD`, `X_BH` and `X_VolDens` have
**unrecoverable definitions/units**; `DEM_mean` has a unit that is nominally metres but physically
implausible (realised 3–17 m) and is explicitly not interpreted as terrain.

## 6. Redistribution-rights evidence

**Local evidence.** `s00_01_metadata.json` records, for every Shenzhen raster, that there is
**no** datetime tag, **no** software tag, **no** make/model tag — `acquisition_time_recovered = false`,
`sensor_recovered = false`, `retrieval_algorithm_recovered = false`. No licence or terms-of-use
document accompanied any source layer in the author's working copy (confirmed for Changchun in
`THIRD_PARTY_DATA_REVIEW.md` and, by the same absence, for the Shenzhen layers).

**External evidence (first-party only).** The only upstream that can be named is OpenStreetMap. The
official page **openstreetmap.org/copyright** (accessed 2026-10-09) states that OpenStreetMap data are
licensed under the **Open Data Commons Open Database License (ODbL) v1.0** by the OpenStreetMap
Foundation. Paraphrased rule: you may copy, distribute and adapt the data, including commercially,
**provided you attribute "© OpenStreetMap contributors" and share alike** — a **Derivative Database**
must be distributed under ODbL, whereas a **Produced Work** (e.g. a rendered result) may carry any
licence with attribution. (Direct page fetch was blocked by the sandbox egress allow-list; the facts
were taken from the official-domain search result and are recorded as such.)

**What that does *not* settle here.** The linkage of this study's road layer to OSM is only inferred;
the delivered copy carries no attribution string; and whether the shipped per-cell `Road_Dens` column
is a *Derivative Database* or a *Produced Work* under ODbL is **UNRESOLVED**. Accordingly UP-05's three
rights layers are all UNRESOLVED (with the note that, *if* ODbL is confirmed to apply to a derivative
database, relicensing to CC-BY-4.0 would be **NO**).

## 7. Public distribution vs relicensing

These are **different questions**, and the audit keeps them apart:

- **Public distribution** = may the *bytes as they are* be made publicly available? For the Shenzhen
  layers this is **UNRESOLVED** (provider/terms unknown). For the frozen analysis-ready tables the
  study already treats them as public-intended, but "already decided to publish" is **not** the same as
  "the upstream permits it".
- **Relicensing** = may the author apply a **new** licence (e.g. CC-BY-4.0) to the shipped bytes? For
  every third-party-derived value this is **NO/UNRESOLVED**: the author does not acquire a new licensing
  right merely by processing data. **"Processed" does not equal "owned".** Likewise, "publicly
  accessible" is **not** a licence and is **not** treated as a CC translation — an openly visible
  dataset is still UNRESOLVED unless its terms say otherwise.

## 8. Files safe to retain (as they are)

- **All author code** (`release_tools/`, `PAID/**/*.py`, `verification/`) — MIT candidate.
- **Pure author metadata:** `valid_ids_main.txt`, `valid_ids_relaxed.txt`, `vault_manifest.json`,
  the manifests, the documentation set, the manuscript text, the repository root metadata.
- **Author partition labels / role flags** inside `analysis_split.csv` / `spatial_mask.csv` (the
  labels are author work; see the caveat on extent in §10).

## 9. Files requiring exclusion

- `data/changchun/changchun_analysis_ready.csv` — **already excluded** (gitignored; not in the tree).
  Third-party row-level data, licence unconfirmed; reviewer-only. Action: **EXCLUDE_FROM_PUBLIC_RELEASE**.
- Raw Shenzhen rasters (~857 MB) and raw Changchun products (~6.1 GB) — **not present**; action:
  **REPLACE_WITH_RECIPE_OR_HASH** (provenance inventory + frozen values + source SHA-256s).

## 10. Files with unresolved rights

- All six `data/shenzhen/*.csv` tables and their frozen duplicates — third-party-derived **values**;
  author-owned **selection/order** only. Kept public, **no relicence asserted**.
- All seven figures — author rendering over third-party-derived values (Produced-Work question for the
  road panel).
- `PAID/stage05_paper/reports/shenzhen_admin_studyarea.json` — RLE outline derived from the
  third-party boundary; flagged **AUTHOR_REVIEW_REQUIRED**.
- `analysis_split.csv`, `spatial_mask.csv`, the mask files — author-derived, but the **cell extent**
  was intersected with the third-party study-area boundary (UP-07), so the extent carries upstream
  rights.

## 11. Code licensing

**`MIT_CANDIDATE_SUPPORTED`** — see `CODE_LICENSING_AUDIT.md`. All code is author-written (the
"copied from" markers point at the authors' own PAID code), no third-party source is vendored, and
every runtime dependency (`numpy`, `pandas`, `matplotlib`, `Pillow`, `python-docx`, `cryptography`,
`imageio`) is permissive — **no copyleft anywhere**. MIT on the code does **not** relicense the data.

## 12. Candidate licensing architecture

| Option | Meaning | Assessment against the evidence |
|---|---|---|
| **A** | MIT (code) + CC-BY-4.0 (all data) | **Not supportable now.** CC-BY-4.0 on the data presupposes the author may relicense every value; the third-party-derived values are UNRESOLVED, and one layer (roads) may be ODbL share-alike. |
| **B** | MIT + CC-BY-4.0 only for author-owned files, upstream terms for third-party-derived | **Premature.** Correct *shape*, but the "upstream terms for third-party-derived" branch is empty because no upstream terms are documented (only an OSM inference). |
| **C** | MIT (code) + **no blanket data licence** + file-specific notices | **Recommended.** Matches the evidence: code = MIT; author-owned metadata = CC-BY-4.0 candidate; third-party-derived tables/figures = kept public with **no licence granted yet**, each with a notice pointing to this audit. Honest and publishable now. |
| **D** | MIT (code) + exclude all unconfirmable Shenzhen row/grid data | **Over-broad.** Would withdraw the very tables the reproducibility package exists to ship, defeating the study's purpose, when the tables are already public-intended. |
| **E** | No licence yet; postpone | **Under-delivers.** The code side is clearly releasable (MIT), and the repository is otherwise public-safe; a blanket freeze is unnecessary. |

**Recommended: Option C**, with a documented path to **B → A** for the author-owned subsets once (i)
the Shenzhen upstream providers/terms are identified, and (ii) the ODbL Derivative-Database-vs-Produced-Work
question for `Road_Dens` is settled.

## 13. Release decision

- **Code:** clear to release under the author-selected permissive licence (MIT candidate).
- **Data:** release **as currently configured** — the analysis-ready tables and figures stay public
  (they are required for the paper) **but carry no new licence**; the Changchun row-level table stays
  excluded; raw sources stay out and are represented by recipe/hash.
- **No relicence of third-party-derived values is asserted.**

## 14. Author actions required

1. **Decide the code licence** (MIT proposed) and, if chosen, add a real `LICENSE` file and update
   `LICENSE_STATUS.md`; do not claim a licence in `CITATION.cff` before this. [Dated note, 2026-10-09:
   **DONE** — MIT adopted for author-owned code only, at `LICENSES/MIT-CODE.txt` (no root `LICENSE`),
   `LICENSE_STATUS.md` updated; `CITATION.cff` still carries no `license` field. See
   `LICENSING_IMPLEMENTATION_RECORD.md`.]
2. **Adopt Option C notices:** add file-specific provenance/licensing notices (or a `NOTICE`/`LICENCES`
   file) stating MIT-for-code and no-licence-granted for the third-party-derived tables/figures. [Dated
   note, 2026-10-09: **DONE** — `docs/LICENSING.md`, `data/shenzhen/RIGHTS_NOTICE.md`,
   `figures_source/RIGHTS_NOTICE.md`, `data/README_DATA.md`.]
3. **Attribution if OSM applies:** if UP-05 is confirmed as OpenStreetMap, add
   "© OpenStreetMap contributors" attribution and determine whether `Road_Dens` is a Derivative
   Database (ODbL share-alike) or a Produced Work.
4. **Shenzhen upstream:** identify the provider(s) and terms for UP-01…UP-04, UP-06, UP-07; only then
   can the tables/figures move from "no relicence" to a stated licence.
5. **Changchun licence:** confirm the third-party terms; keep the row-level table excluded until then
   (already the case).
6. **Re-run this audit** after any upstream term is confirmed, and update `SHENZHEN_LICENSING_MATRIX.csv`
   and `PUBLIC_RELEASE_LICENSING_GATE.md`.

---

*Artefacts: `SHENZHEN_DATA_FILE_INVENTORY.csv`, `SHENZHEN_VARIABLE_PROVENANCE.csv`,
`UPSTREAM_DATA_RIGHTS_MATRIX.csv`, `AUTHOR_CREATED_MATERIALS_MATRIX.csv`, `CODE_LICENSING_AUDIT.md`,
`SHENZHEN_LICENSING_MATRIX.csv`, `PUBLIC_RELEASE_LICENSING_GATE.md`.*
