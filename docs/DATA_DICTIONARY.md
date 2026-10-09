# DATA DICTIONARY

This is the reviewer-facing data dictionary. It gives the computational definition, units, spatial support, source and known limitations of every variable used in the manuscript. Where a quantity's exact physical definition or unit could **not** be recovered from the archived source metadata, this is stated explicitly rather than guessed.

The authoritative frozen dictionary shipped with the analysis is `PAID/stage01_protocol/constraints/DATA_DICTIONARY.md` (in the original Chinese); this file is its English counterpart plus the Changchun mapping.

---

## 1. Spatial reference

- **Shenzhen analysis grid:** regular grid of **100 m × 100 m** cells, CRS **EPSG:32649** (WGS 84 / UTM zone 49N). 233 rows × 362 columns = **32,748 cells**, of which **31,760** carry valid analysis data (988 cells are outside the study area / no data).
- Row index increases **northward**, column index **eastward**.
- The full-city rasters used to *build* the table are in **EPSG:32650** (UTM 50N); the study-area rasters are in EPSG:32649. This two-CRS history is documented in `DATA_PROVENANCE.md`.

## 2. Shenzhen variables

Main sample n = **31,760** cells. Realised domain reported as [min, p05, median, p95, max].

| Variable | Computational definition | Unit | Realised domain | Zeros | Reliability |
|---|---|---|---|---|---|
| `LST_mean` (target) | Arithmetic mean of valid 30 m land-surface-temperature pixels in the cell (valid = not −9999 and not 0) | °C | [27.82, 31.18, 38.61, 44.96, 65.92] | 0 | high |
| `NDVI_mean` | Arithmetic mean of valid 30 m NDVI pixels (valid = not −9999) | dimensionless | [−0.283, 0.144, 0.508, 0.855, 0.884] | 0 | medium (city-wide raster has non-physical values) |
| `DEM_mean` | Arithmetic mean of valid 30 m DEM pixels | m (*suspect*) | [3.00, 6.78, 11.68, 15.00, 17.00] | 0 | **low — range 3–17 m is not physically credible for Shenzhen; DEM is used only as a smooth spatial covariate and is never interpreted as terrain** |
| `SVF_mean` | Mean of the 5 m sky-view-factor layer aggregated to the cell (0 = fully occluded, 1 = fully open) | dimensionless | [0.387, 0.550, 0.915, 1.000, 1.000] | 0 | medium (5 m source; requires explicit resampling) |
| `Road_Dens` | Road density — **exact definition/unit not recoverable from archived source metadata** | *unconfirmed* | [0.00, 0.00, 0.00, 23.17, 75.62] | 24,449 (77%) | low |
| `X_BD` | Building-coverage indicator — **exact physical definition not recoverable** (max > 1, so not a [0,1] fraction) | *unconfirmed* | [0.00, 0.00, 0.017, 0.418, 1.770] | 14,220 | low |
| `X_BH` | Building-height indicator — **exact physical definition not recoverable** (max 224 m is not a 100 m-cell mean height; possibly max or sum) | m (*suspect*) | [0.00, 0.00, 6.27, 43.35, 224.03] | 14,220 | low |
| `X_VolDens` | Built-volume density — **exact definition not recoverable**; the identity X_VolDens = X_BD·X_BH is **not confirmed** (ratio p05/median/p95 = 1.04 / 2.02 / 11.30) | *unconfirmed* | [0.00, 0.00, 0.407, 26.90, 193.82] | 14,220 | low |

**Explicit unknowns (not to be guessed):** `X_BD`, `X_BH`, `X_VolDens` and `Road_Dens` — *exact physical definition/unit not recoverable from archived source metadata*. All covariate results rest on quantities whose precise meaning is uncertain; this is a declared limitation of the study. The DEM layer is *not* a credible elevation surface (range 3–17 m) and is not interpreted as terrain.

**LST caveat:** `LST_mean` is land-surface temperature, **not** air temperature and **not** thermal comfort; no surface-urban-heat-island intensity is claimed. Image acquisition time, sensor and retrieval procedure are **unavailable** and are not fabricated anywhere in this package (see `DATA_PROVENANCE.md`).

## 3. Frozen split table — `data/shenzhen/analysis_split.csv`

| Column | Meaning |
|---|---|
| `Grid_ID` | 1…32,748 cell identifier (matches `PAID/stage00_data_audit` grid) |
| `row`, `col` | grid indices (northward / eastward) |
| `in_main` | 1 if the cell is in the valid main sample (31,760), else 0 |
| `zone` | cluster assignment label 1/2/3 (pre-buffer) |
| `role` | post-buffer role: `discovery` (A, 19,184) · `dev_validation` (B, 6,182) · `buffer` (3,407) · `locked` (C, 2,987) · `outside` (988) |

Regional roles and the R = 15-cell (1.5 km) buffer are defined in `PAID/stage01_protocol/PREREGISTRATION.md` and `PAID/stage01_protocol/split/split_manifest.json`.

### Region C (withheld region)

`data/shenzhen/zone_C_analysis_ready.csv` contains the **full 9-column** locked table — `Grid_ID, LST_mean, NDVI_mean, DEM_mean, SVF_mean, Road_Dens, X_BD, X_BH, X_VolDens` — for the 2,987 locked cells, so the primary endpoint can be recomputed (the target alone is not sufficient). It is **byte-identical to the frozen vault plaintext** (SHA-256 `b4a709e1…eab9`, matching `vault_manifest.json` → `plaintext_sha256`). A 2-column extract `data/shenzhen/zone_C_targets.csv` (`Grid_ID, LST_mean`) is also shipped for reference.

Region C is **scientifically spent under Protocol V1** and was reclassified during a post-hoc audit as *a locked-region evaluation under a documented protocol deviation*. It must **not** be used as a fresh, untouched confirmatory holdout. See `PROTOCOL_DEVIATION.md` and `REGION_C_PROVENANCE.md`.

## 4. Changchun external-replication table — `data/changchun/changchun_analysis_ready.csv`

Post-hoc external replication on **Changchun, 2021**, at **500 m** fishnet support (n = 100,676 source cells; 100,647 used after QC; 29 non-finite rows). It is **not scale-matched** to the Shenzhen 100 m grid, and it does **not** contain `SVF_mean` or `Road_Dens`, so the frozen Shenzhen expression can only be tested there on its expressible projection.

| Column | Meaning | Maps to Shenzhen schema |
|---|---|---|
| `id` | fishnet cell id | — |
| `left`, `top`, `right`, `bottom` | cell bounding coordinates | spatial reference |
| `row_index`, `col_index` | fishnet row/col (from the companion grid table) | spatial blocks |
| `LST_mean` | land-surface temperature | `LST_mean` (target) |
| `NDVI_mean` | NDVI mean | `NDVI_mean` |
| `DEM_mean` | DEM mean | `DEM_mean` |
| `BD` | building density/coverage | → `X_BD` |
| `BVD` | built-volume density | → `X_VolDens` |
| `Height_mea` | mean building height | → `X_BH` |
| `NDWI_mean`, `GDP_mean`, `POP_mean` | extra columns present in the source, not used in the replication | (unused) |

QC rule actually applied (from `s05_04_external_replication.py`): keep rows finite in [LST, NDVI, DEM, BD, BVD, Height_mea, row, col], with LST in (0, 70] °C and NDVI in [−1, 1]. 100,676 → 100,647.

This analysis is explicitly **post hoc** and is **not** a prospective confirmation, nor a scale-matched replication.
