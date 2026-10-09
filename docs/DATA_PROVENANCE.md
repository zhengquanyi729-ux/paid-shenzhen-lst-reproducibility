# DATA PROVENANCE

This document records where each dataset came from, how it was processed, and its **redistribution status**. It exists so that a reviewer can tell exactly what is in this package, what is not, and why.

---

## 1. Shenzhen — author-provided source archive (~857 MB)

The manuscript states: *"The raw rasters and the analysis table are the author-provided Shenzhen dataset (approximately 857 MB), held outside the published repository."* That statement is accurate but incomplete, so this section makes it concrete.

**Redistribution status: NOT redistributed here.** The rights to redistribute the raw source layers are unconfirmed. Instead this package ships the **exact frozen analysis-ready values** used in the manuscript plus this provenance inventory.

Source inventory (author archive, ≈ 857 MB, 100+ files):

*Full-city rasters (EPSG:32650 / UTM 50N, 30 m):*
`DEM_30m_Final.tif`, `LST_30m_Final new.tif`, `NDVI_30m_Final.tif`, `archi_30m_Final.tif`, `road_30m_Final.tif`.

*Study-area rasters (`0_论文data/`, EPSG:32649 / UTM 49N):*
`DEM_shenzhen.tif`, `LST_shenzhen.tif`, `NVDI_shenzhen.tif` (note: filename misspelled), `Road_shenzhen.tif`, `arch_shenzhen.tif`, and `SVF_Shenzhen.tif` (**5 m** sky-view factor, ~135 MB — the single largest layer).

*Vectors (`研究边界/`):* `grid_utm.shp` (the 100 m analysis grid), `studyarea.shp` (299 community polygons), building layers, plus `road/`.

*Analysis table:* `data_原始.csv` (32,687 rows × 9 columns).

### Processing history (see `PAID/stage00_data_audit` and `PAID/stage01_protocol`)

1. **Two-CRS structure.** Full-city layers are EPSG:32650; the study-area layers are EPSG:32649. Combining the two without reprojection is a known pitfall; the analysis uses the EPSG:32649 study-area layers.
2. **100 m analysis grid.** `grid_utm.shp` = 32,748 cells of 100 m × 100 m. The per-100 m analysis table was derived from the 30 m rasters by a **pixel-centre** zonal mean (S00.4). This reconstruction matches `data_原始.csv` at 98.7 % (LST) / 99.4 % (NDVI, DEM) of cells; the CSV is slightly *more complete* at the valid-data edge and is treated as the source of truth there.
3. **Valid sample.** 32,748 cells → **31,760** with valid analysis data (988 cells outside the study area / no data; plus flag-annotated boundary cells).
4. **Spatial split.** Connected k-means (k = 5, seed 20260924) → A (discovery, 19,184) / B (dev-validation, 6,182) / C (locked, 2,987), with a 1.5 km (R = 15 cells) buffer (3,407 cells) applied only against C.

### Known provenance limitations (declared, not fixed)

- **Missing acquisition metadata.** The sensor, acquisition date, and retrieval algorithm/procedure for `LST_mean` are **unavailable**; no diurnal, seasonal or thermal-recovery analysis is possible. This package does **not** guess them.
- **Imperfect DEM.** The DEM layer covers only 3–17 m, which is not credible for Shenzhen; it is used only as a smooth spatial covariate.
- **Grid incompleteness (~32.6 km²).** The analysis copy `研究边界/studyarea.shp` contains 18 records whose geometry is truncated in the delivered shapefile (while the `SHAPE.AREA` attribute keeps the original value). Because `grid_utm.shp` was intersected with that truncated copy, **3,259 cells (≈ 32.6 km²)** of community area inside the same bounding box never entered the analysis — mostly in Longhua, Bao'an and Longgang. ~99.8 % of those cells carry valid LST, so they are omitted data, not empty ground. Rebuilding the grid would change every downstream partition and result, so the study is reported on the frozen grid and the gap is **disclosed rather than corrected**. Full audit: `PAID/stage05_paper/reports/s05_08_area_audit.json`.
- **Unconfirmed variable definitions** (`X_BD`, `X_BH`, `X_VolDens`, `Road_Dens`) — see `DATA_DICTIONARY.md`.

---

## 2. Changchun — external replication dataset

- **City / period / support:** Changchun, China, **2021**, **500 m** fishnet.
- **Source:** a third-party GIS dataset (≈ 6.1 GB including B3/B4/B5 satellite GeoTIFFs). The replication reads the 500 m attribute table `changchun(Arch+NDWI+LST+NDVI+DEM+GDP+pop).dbf` plus the companion grid `研究范围渔网500/changchun.dbf` (row/col indices).
- **In this package:** the **slim analysis-ready table** `data/changchun/changchun_analysis_ready.csv` (100,676 rows; only the columns used, plus cell coordinates) is included. **Raw Changchun satellite products are not redistributed.**
- **Redistribution status:** treated as **reviewer-only** until the third-party licence is confirmed; confirm before any public deposit.
- **Mismatch with Shenzhen (material):** 500 m vs 100 m support (not scale-matched); **`SVF_mean` and `Road_Dens` are absent**; LST absolute level differs (different climate/period). The replicated quantities are *relationship structure and direction*, never absolute temperature. The analysis is **explicitly post hoc** — it is not a prospective confirmation.

---

## 3. What is deliberately absent

| Item | Reason |
|---|---|
| Raw Shenzhen rasters (~857 MB) | redistribution rights unconfirmed |
| Raw Changchun satellite products (~6.1 GB) | size + unconfirmed licence (slim table provided instead) |
| `PAID/stage05_paper/cache/` checkpoints (`.npz`, cached JSON) | regenerable intermediates |
| `__pycache__`, `.DS_Store`, OS files | not part of the scientific record |
| `PAID/stage02_platform/vault/validator_key.bin` | the AES key to the encrypted withheld-region vault; withheld by design (see `REPOSITORY_RECORD.md`) |

Nothing in this section was removed from the **frozen** record: the frozen manifests of Stage 00–05 remain intact and are shipped unchanged inside `PAID/`.

For a machine-readable version of this section — every non-redistributed source layer, its type, support and reason for exclusion — see `RAW_DATA_INVENTORY.csv`.
