# DATA AVAILABILITY — note for the reviewer

This package is the **reviewer-only** distribution. It differs in one respect from the proposed public
deposit: it also contains the slim Changchun external-replication table, which stays reviewer-only
until the third-party licence is confirmed (`THIRD_PARTY_DATA_REVIEW.md`). Everything else here is
intended for the public deposit unchanged.

## What the reviewer has, and where

| Data | File in this package | Size | Notes |
|---|---|---|---|
| Frozen analysis grid + split (A/B/buffer/C), 32,748 cells | `data/shenzhen/analysis_split.csv` | ~0.9 MB | cell-level zone + row/col |
| Analysis spatial mask | `data/shenzhen/spatial_mask.csv` | ~0.6 MB | which cells are in the study area |
| Region A (discovery) covariates + LST | `data/shenzhen/zone_A_open.csv` | ~2.0 MB | used to refit Baseline A |
| Region B (dev-validation) covariates + LST | `data/shenzhen/zone_B_devval.csv` | ~0.6 MB | |
| Region C (locked) **full 9-column** table | `data/shenzhen/zone_C_analysis_ready.csv` | 339,556 B | byte-identical to the frozen vault plaintext (SHA-256 `b4a709e1…eab9`) |
| Region C (locked) slim targets | `data/shenzhen/zone_C_targets.csv` | ~74 KB | Grid_ID + LST_mean only |
| Changchun external replication (slim) | `data/changchun/changchun_analysis_ready.csv` | ~7 MB | **reviewer-only** (licence) |

All frozen split statistics can be recomputed from these files with
`release_tools/verify_stage01_release.py`; the primary endpoint with
`release_tools/verify_stage04_release.py`; the Changchun replication with
`release_tools/verify_changchun_release.py`.

## What is deliberately not here

- **AES key** to the sealed Region-C vault (`validator_key.bin`) — withheld by design; not needed,
  because the plaintext targets ship as `zone_C_analysis_ready.csv`.
- **Raw Shenzhen rasters** (~857 MB) — redistribution rights unconfirmed.
- **Raw Changchun satellite products** (~6.1 GB) — size + unconfirmed licence.

Full inventory and reasons: `RAW_DATA_INVENTORY.csv`, `DATA_PROVENANCE.md`.

## Integrity

Every shipped file is listed with its SHA-256 in `MANIFEST_SHA256.csv`; re-check with
`python3 verification/verify_manifest.py`. The Region-C table is additionally pinned to the frozen
vault manifest plaintext hash (`release_tools/verify_stage04_release.py`, check **C2**).

## Region-C status (important)

Region C is **scientifically spent under Protocol V1**: it is a locked-region evaluation under a
documented protocol deviation, **not** a pristine/untouched holdout. It must not be reused for
selection, revision, refitting or reconfirmation. The plaintext is provided so the published statistic
can be recomputed, not so the region can be re-used as fresh confirmation. See
`REGION_C_PROVENANCE.md` and `PROTOCOL_DEVIATION.md`.
