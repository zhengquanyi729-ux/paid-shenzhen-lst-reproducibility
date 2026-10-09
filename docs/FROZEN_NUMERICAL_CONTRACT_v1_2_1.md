# FROZEN NUMERICAL CONTRACT — v1.2

The exact published numbers this package reproduces, where each lives, and its comparison class
(see `NUMERICAL_TOLERANCE_POLICY.md`). **No value in this file may change.** Every row below was
recomputed from the shipped tables in the clean-room test (`CLEANROOM_TEST_REPORT_v1_2_1.md`).

## 1. Stage-04 primary endpoint — Region C, candidate `S03-H10-GREEDY`

Source: `PAID/stage04_validation/reports/s04_validation_results.json`.

| quantity | frozen value | class |
|---|---|---|
| Baseline A RMSE_C | `2.841519144671417` | continuous (1e-9) |
| H10 RMSE_C | `2.462447828502684` | continuous (1e-9) |
| ΔRMSE (Baseline A − candidate) | `0.379071316168733` | continuous (1e-9) |
| permutation p (N_PERM = 199) | `0.005` (minimum attainable) | exact rational |
| 95% block-bootstrap CI (N_BOOT = 1000) | `[0.276067201358972, 0.481358279348766]` | continuous (1e-9) |
| Region-C n | `2987` | exact integer |

## 2. Stage-04 R = 25 conservative re-carve

| quantity | frozen value | class |
|---|---|---|
| R = 25 ΔRMSE | `0.137499076805151` | continuous (1e-9) |
| R = 25 permutation p | `0.085` | exact rational |
| R = 25 n_C | `791` | exact integer |
| R = 15 buffer n | `3407` | exact integer |
| R = 25 buffer n | `5603` | exact integer |

## 3. Placebo `S03-H01-LIN7` — definitional identity with Baseline A

| quantity | frozen value | class |
|---|---|---|
| ΔRMSE (R = 15) | `0.0` | definitional identity (exact) |
| permutation p | `1.0` | definitional identity (exact) |
| 95% CI | `[0.0, 0.0]` | definitional identity (exact) |
| ΔRMSE (R = 25) | `0.0` | definitional identity (exact) |

Proved by specification + prediction identity, not by two independent refits.

## 4. Frozen candidate canon hashes

Source: `PAID/stage03_discovery/registry/frozen_candidates.json`.

| candidate | SHA-256 |
|---|---|
| `S03-H11-REFINE` | `629ed98b060d8e0f41f9bcfc7c18d6421e9f66d9172589b26f3fe1e539162207` |
| `S03-H10-GREEDY` | `1715541451024868f13a4933d5a9f7e76240db923abb00bd5672497075f974df` |
| `S03-H10P-GREEDY-MIN` | `5e8bcc5de6d8ebf60ca01794654a8cf4d7f872fcf37efb9b25931162bd8d7f36` |
| `S03-H01-LIN7` | `7a7e172b70cb56481c6ae23afc7a507362a2902a09be1055fafc61596e294aaf` |

## 5. Baseline B (conventional learners) — Region C

Source: `PAID/stage05_paper/reports/baselineB.json`. Note the **deliberate fairness point**: on the
locked region the random forest and gradient-boosted trees *beat* the candidate.

| model | RMSE_C | ΔRMSE vs Baseline A | p |
|---|---|---|---|
| Random forest | `2.0950493813710276` | `+0.7464697633003894` | `0.005` |
| Gradient-boosted trees | `2.091527154536851` | `+0.749991990134566` | `0.005` |
| Candidate `S03-H10-GREEDY` | `2.462447828502684` | `+0.379071316168733` | `0.005` |

### 5.1 Two confidence intervals for the same endpoint — do not conflate them

The candidate's Region-C ΔRMSE CI appears twice, because it is drawn twice from two RNG streams:

- **confirmatory** (Stage-04 validator, the authoritative one): `[0.276067201358972, 0.481358279348766]`;
- **exploratory** (Stage-05 re-draw, `baselineB.json` → `regions.C.h10.ci95`):
  `[0.27266679693326507, 0.47625219791161916]`.

They are two draws of the same estimator, not two results. Any manuscript or figure that quotes a CI
must say **which** one; the Stage-04 value is the confirmatory interval.

## 6. Changchun external replication (post-hoc)

Source: `PAID/stage05_paper/reports/external_replication.json`.

| quantity | value |
|---|---|
| source rows | `100676` |
| rows used (finite in LST/NDVI/DEM/BD/BVD/Height/row/col) | `100647` |
| excluded | `29` |
| matched linear baseline A* CV RMSE | `≈1.2292` |
| greedy re-discovery CV RMSE | `≈1.1229` |
| spatial-holdout candidate RMSE | `≈1.0295` |
| spatial-holdout baseline RMSE | `≈1.2152` |

## 7. Frozen artefacts (byte-identity)

| artefact | frozen value | class |
|---|---|---|
| Region-C analysis table SHA-256 | `b4a709e16d7b75425496fae1cea1ea6c5fd113575fe5f6766ab3389da353eab9` | byte-identity |
| vault manifest plaintext SHA-256 | `b4a709e16d7b75425496fae1cea1ea6c5fd113575fe5f6766ab3389da353eab9` | byte-identity (same object) |
| Region-C rows | `2987` | exact |
| experiment log records | `1259` | exact |
| experiment log SHA-256 | `b10cc702a49fe3eaea06bff1e06a8fe0ac9d0fa55e3a1bd082e8763e61715488` | byte-identity |
| ASCII alias `process_image1.png` vs `过程__image1.png` | `ef7ccd98658889a2775d94cbe206f692b6dac2e1ce154866e354e4c0d7590a6f` | byte-identity |

## 8. Spatial partition (Stage 01)

Region A `19184` · Region B `6182` · Region C `2987` · R = 15 buffer `3407`; 100 m grid, EPSG:32649,
`233 × 362 = 32748` cells; split seed `20260924`.
