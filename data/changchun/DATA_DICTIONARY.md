# Changchun analysis-ready table — data dictionary

Post-hoc external replication dataset. City: **Changchun, China, 2021**; support: **500 m fishnet**
(**not** scale-matched to the Shenzhen 100 m grid). Source: a third-party GIS dataset; only this slim
analysis-ready table is redistributed (raw products ~6.1 GB are not). See `../../DATA_PROVENANCE.md` §2.

File: `changchun_analysis_ready.csv` — 100,676 rows × 16 columns.

| Column | Meaning | Maps to Shenzhen schema | Note |
|---|---|---|---|
| `id` | fishnet cell id | — | float in source |
| `left`, `top`, `right`, `bottom` | cell bounding coordinates | spatial reference | native CRS of the source |
| `row_index`, `col_index` | fishnet row/col (from the companion grid `研究范围渔网500/changchun.dbf`) | spatial blocks | used for spatial CV / permutation |
| `LST_mean` | land-surface temperature | `LST_mean` (target) | different climate/period — absolute level not comparable |
| `NDVI_mean` | NDVI mean | `NDVI_mean` | |
| `DEM_mean` | DEM mean | `DEM_mean` | |
| `BD` | building density / coverage | → `X_BD` | |
| `BVD` | built-volume density | → `X_VolDens` | |
| `Height_mea` | mean building height | → `X_BH` | |
| `NDWI_mean`, `GDP_mean`, `POP_mean` | extra source columns | (unused) | present in the source, not used in the replication |

## QC rule actually applied

From `PAID/stage05_paper/scripts/s05_04_external_replication.py`: keep rows finite in
`[LST, NDVI, DEM, BD, BVD, Height_mea, row, col]`, with `LST ∈ (0, 70] °C` and `NDVI ∈ [−1, 1]`.
**100,676 → 100,647** rows used.

## What this dataset can and cannot test

- **Absent here:** `SVF_mean` and `Road_Dens`. The frozen Shenzhen expression can therefore only be
  tested on its **expressible projection** (drop the SVF and road-density terms).
- **Support mismatch:** 500 m vs 100 m — the replication is of **relationship structure and direction**,
  never absolute temperature.
- **Status:** explicitly **post hoc**; it is **not** a prospective confirmation and **not** a
  scale-matched replication. See `../../KNOWN_LIMITATIONS.md` L-13 and Results 3 of the manuscript.
