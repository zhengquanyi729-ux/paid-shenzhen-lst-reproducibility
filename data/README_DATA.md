# DATA — what is in this folder

Two analysis-ready tables support the manuscript. **Raw source rasters are not redistributed.** Full
provenance and redistribution status are in `../DATA_PROVENANCE.md`; variable definitions are in
`../DATA_DICTIONARY.md`.

## `shenzhen/`

The Shenzhen study's analysis-ready extracts. The source table is the author-provided
`data_原始.csv` (32,687 rows × 9 columns) held outside the repository; the frozen split and the
per-region covariate tables below are the versions actually used.

| File | Rows × cols | Contents |
|---|---|---|
| `analysis_split.csv` | 32,748 × 6 | `Grid_ID,row,col,in_main,zone,role` — the frozen spatial partition for every grid cell. `role` ∈ {discovery, dev_validation, buffer, locked, outside}. |
| `zone_A_open.csv` | 19,184 × 9 | Region A (discovery) covariates + target `LST_mean`. |
| `zone_B_devval.csv` | 6,182 × 9 | Region B (dev-validation) covariates + target. |
| `zone_C_analysis_ready.csv` | 2,987 × 9 | Region C (locked) **full** table `Grid_ID,LST_mean,NDVI_mean,DEM_mean,SVF_mean,Road_Dens,X_BD,X_BH,X_VolDens` — **the table the primary endpoint is recomputed from** (byte-identical to the frozen vault plaintext, SHA-256 `b4a709e1…eab9`). |
| `zone_C_targets.csv` | 2,987 × 2 | Region C (locked) `Grid_ID, LST_mean` only — kept for reference. |
| `spatial_mask.csv` | 25,366 × 4 | `Grid_ID,row,col,role` for the cells inside the discovery+dev surface (A∪B), used by the search. |

Columns of the covariate tables are, in order:
`Grid_ID,LST_mean,NDVI_mean,DEM_mean,SVF_mean,Road_Dens,X_BD,X_BH,X_VolDens`.

**Region C special rule.** `zone_C_analysis_ready.csv` is shipped so the primary statistic can be
recomputed in software: the endpoint needs the target *and the seven covariates*, which is why the full
9-column table ships (the 2-column `zone_C_targets.csv` alone is not enough). It is **not** an
invitation to reuse Region C: under Protocol V1 the region is **scientifically spent**, and it must not
enter hypothesis selection, revision, refitting or reconfirmation (see `../PROTOCOL_DEVIATION.md` and
`../REGION_C_PROVENANCE.md`). The cell values are the ones the validator decrypted from the sealed
vault; the vault ciphertext and its key are also preserved under `PAID/stage02_platform/vault/`
(`zone_C_targets.enc`, `validator_key.bin` — the latter withheld from any public deposit; see
`REPOSITORY_RECORD.md`).

## `changchun/`

| File | Rows × cols | Contents |
|---|---|---|
| `changchun_analysis_ready.csv` | 100,676 × 16 | Slim Changchun (2021, 500 m fishnet) analysis table: only the columns used by the replication, plus cell coordinates and fishnet indices. |
| `_export_checks.json` | — | Export provenance: 100,676 source records, 100,672 with valid LST, 4 excluded for non-finite LST. |
| `DATA_DICTIONARY.md` | — | Changchun column mapping to the Shenzhen schema + the QC rule. |

The raw Changchun satellite products (~6.1 GB) are **not** redistributed. This table is treated as
**reviewer-only** until the third-party licence is confirmed (see `../DATA_PROVENANCE.md` §2).

## Notes for a reviewer

- Shenzhen grid: 100 m × 100 m, EPSG:32649, 233 × 362 = 32,748 cells; 31,760 valid. `row` increases
  northward, `col` eastward.
- Changchun grid: 500 m fishnet, **not** scale-matched to Shenzhen.
- Neither table contains `SVF_mean`/`Road_Dens` for Changchun (absent there) — see `DATA_DICTIONARY.md` §4.
- The frozen split manifest (authoritative role assignment with the R = 15 buffer) is
  `PAID/stage01_protocol/split/split_manifest.json`.
