# Results 3 — Post-hoc partial replication on an independent city (Changchun, 2021)

*Replication was carried out post hoc on a spatially disjoint dataset from a second Chinese city (Changchun, 2021); the analysis was conducted post hoc and is a partial external replication, not a prospective confirmation. The frozen candidate was not re-selected here: the expression structure is held fixed and only its coefficients are refit, so every number below is an out-of-sample transfer test rather than a new discovery. Because the two cities share only a subset of covariates, the replication is deliberately partial, and the gaps are reported alongside the agreements.*

## 3.1 External data and harmonisation

The replication dataset is a 500 m fishnet for Changchun (2021) with 100,676 cells, carrying `LST_mean`, `NDVI_mean`, `DEM_mean` and three building variables (`BD`, `BVD`, `Height_mean`) that we mapped one-to-one onto the Shenzhen schema `X_BD`, `X_VolDens` and `X_BH`. After excluding 29 cells with non-finite LST, covariate or coordinate values, 100,647 cells are used. The target has mean 26.68 °C, sd 1.62 °C and range [11.2, 43.1] °C; absolute temperature is not comparable to Shenzhen because the climatic and observational contexts are not harmonised (incomplete Shenzhen acquisition metadata prevent temporal or seasonal comparability), so all comparisons are made within-city, on the same folds.

Two covariates of the Shenzhen schema, `SVF_mean` (sky-view factor) and `Road_Dens`, do not exist in Changchun. The frozen expression `exp(NDVI) + exp(DEM) + SVF + Road_Dens + (NDVI·DEM)` therefore cannot be reproduced verbatim; only its expressible projections — those built from the five shared variables — can be tested. We report this as a structural limitation, not as a result.

The external analysis is not a scale-matched replication: Shenzhen is analysed at 100 m and Changchun at 500 m, so geographic transfer and the difference in spatial support (aggregation and the modifiable areal unit problem) cannot be fully separated. The search algorithm and operator grammar are the same where the method is re-run, but the available feature space is not, for the reason above.

Spatial folds follow the same connected k-means rule on row/col coordinates (k = 5, seed 20260924), giving fold sizes [21256, 22027, 19386, 18823, 19155]. A matched linear baseline (**Baseline A\***, OLS on the five available covariates) provides the within-city reference: **A\*-CV RMSE = 1.2292 °C**.

## 3.2 Transfer of the frozen form

Each frozen projection was refit on Changchun and scored by the same spatial block CV. Table 1 gives the results.

**Table 1 — Frozen-form transfer (structure fixed, coefficients refit on Changchun).**

| Expression | cx | CV RMSE | Δ vs A\* |
|---|---|---|---|
| `NDVI + DEM + X_BD + X_BH + X_VolDens` (A\*) | 10 | 1.2292 | 0.0000 |
| `NDVI + DEM + X_BD + X_BH + X_VolDens + exp(NDVI)` | 13 | **1.1992** | **+0.0301** |
| `NDVI + DEM + X_BD + X_BH + X_VolDens + exp(NDVI) + exp(DEM) + (NDVI·DEM)` | 20 | 1.2779 | −0.0486 |
| `exp(NDVI) + exp(DEM) + (NDVI·DEM) + X_BD + X_BH + X_VolDens` | 16 | 1.3254 | −0.0962 |
| `NDVI + (NDVI·NDVI)` | 6 | 1.5246 | −0.2953 |
| `exp(NDVI)` | 3 | 1.5725 | −0.3433 |
| `NDVI` | 2 | 1.6271 | −0.3979 |
| `DEM` | 2 | 1.6631 | −0.4338 |
| `exp(NDVI) + exp(DEM)` | 6 | 1.8340 | −0.6048 |
| `exp(DEM)` | 3 | 1.9419 | −0.7127 |

Two things stand out. First, adding the nonlinear NDVI term to the matched linear baseline **improves** it on the new city (Δ = +0.0301), so the NDVI nonlinearity carries over as a useful addition. Second, the *full* frozen nonlinear core — adding `exp(DEM)` and the `NDVI·DEM` interaction on top — does **not** improve on the baseline (Δ = −0.0486): the extra terms cost more than they return once SVF and Road_Dens are gone. Every projection built from NDVI and DEM alone scores worse than the five-covariate linear baseline, so the frozen form is not self-sufficient without the two missing covariates.

## 3.3 The NDVI pivot reproduces; the DEM term does not

Table 2 isolates the role of each driver by fitting single-variable forms.

**Table 2 — Single-variable pivot test (CV RMSE, °C).**

| Form | CV RMSE |
|---|---|
| `NDVI` | 1.6271 |
| `NDVI + (NDVI·NDVI)` | 1.5246 |
| `exp(NDVI)` | 1.5725 |
| `DEM` | 1.6631 |
| `exp(DEM)` | 1.9419 |

The nonlinear NDVI pivot reproduces in direction and in ordering: `exp(NDVI)` (1.5725) beats linear `NDVI` (1.6271), and the quadratic `NDVI+NDVI²` (1.5246) is the best single-variable form. `exp(DEM)` is the **worst** single-variable form (1.9419), worse even than linear `DEM`, which mirrors the Stage-04 finding that the DEM term was a region-A-specific artefact rather than a terrain effect.

The direction reproduction is summarised in Table 3, where each entry is the change in predicted LST per +1 A-region SD of the variable (finite difference on the fitted model), in °C, together with within-city bivariate correlations.

**Table 3 — Effect directions and bivariate correlation, Shenzhen vs Changchun.**

| Variable | Shenzhen (linear) | Shenzhen (H10P) | Changchun (linear) | Changchun (exp form) | Changchun bivariate r |
|---|---|---|---|---|---|
| NDVI_mean | −3.75 | −4.49 | +0.12 | −2.05 | −0.293 |
| DEM_mean | +2.83 | +1.95 | −0.29 | −0.00 | −0.065 |
| X_BD | +1.09 | — | +1.74 | — (absent) | +0.654 |
| X_BH | +0.30 | — | +0.78 | — (absent) | +0.531 |
| X_VolDens | −0.52 | — | −0.00 | — (absent) | +0.573 |

Vegetation is associated with cooler surfaces (bivariate r = −0.293; −2.05 °C per SD under the exponential form, same sign as Shenzhen's −4.49). Building density and height are associated with warmer surfaces (r = 0.654 and 0.531; positive fitted directions). DEM does not reproduce (r = −0.065, ≈ 0 under the exponential form). Note that the *linear* NDVI coefficient flips sign on Changchun (+0.12) while the exponential form keeps the correct sign: the variable's fitted effect is captured by its nonlinear shape, not by a single slope.

## 3.4 Independent re-discovery on the new city

To test whether the *method*, not just the frozen form, recovers the same structure, we ran the Stage-03 greedy forward search — same operator set, same complexity cap of 15, same spatial-block rule — on Changchun. The algorithm and operator grammar were identical, but the candidate space differed because two covariates (SVF and Road_Dens) are unavailable on Changchun. It selected

> `X_BD + X_BH + (NDVI·NDVI) + NDVI + (NDVI·X_BD)` (cx = 14)

by the stepwise path in Table 4.

**Table 4 — Independent greedy search on Changchun.**

| step | term added | n_terms | CV RMSE |
|---|---|---|---|
| 1 | `X_BD` | 1 | 1.2485 |
| 2 | `X_BH` | 2 | 1.2088 |
| 3 | `NDVI²` | 3 | 1.1902 |
| 4 | `NDVI` | 4 | 1.1623 |
| 5 | `NDVI·X_BD` | 5 | **1.1229** |

The independent search re-finds a **nonlinear NDVI pivot** (NDVI + NDVI²) and a **vegetation×building interaction** (NDVI·X_BD), together with building terms — a partial conceptual overlap with the Shenzhen search rather than replication of the same symbolic or qualitative structure. It does **not** re-select `exp(NDVI)` or `exp(DEM)`, and it drops DEM entirely. Its CV RMSE of 1.1229 beats the matched linear baseline of 1.2292, and on an unbiased spatial holdout (train col ≤ 380, test col ≥ 420, with a 40-cell buffer) it scores 1.0295 against the baseline's 1.2152. That performance reflects a post-hoc city-specific search rather than replication of the frozen Shenzhen structure.

## 3.5 Direct coefficient transfer is not meaningful

Transferring coefficients across cities fails for a structural reason: the covariate ranges barely overlap. Shenzhen's mean DEM is 11.1 m, while Changchun's DEM lies in [129, 622] m, so the two distributions are almost disjoint. Under direct transfer, `exp(NDVI)` retains only weak rank agreement (Pearson r = 0.256, Spearman ρ = 0.388, affine-recalibrated RMSE = 1.569); the `H10P` form scores ρ = 0.204 with an affine-recalibrated RMSE of 26.6 °C, a degenerate result caused by `exp()` extrapolating far outside its fitted range. Only the *shape* of the NDVI term survives cross-city transfer, and only weakly.

## 3.6 Summary

The external replication is **partial, and partial in an informative way**, and it was conducted post hoc. An independent post-hoc run on the second city recovered a nonlinear NDVI effect plus a vegetation×building interaction, with building terms entering warming — a partial conceptual overlap with the Shenzhen picture, not a verbatim replication. The *specific* frozen form does not transfer: `exp(NDVI)` yields only a small gain, `exp(DEM)` is unstable and unhelpful, DEM drops out, and SVF/Road_Dens are unavailable, so the frozen form can only be tested on its expressible projections. The two covariates that cannot be tested are exactly the two the frozen form depends on most, which is itself part of the result. Taken with Results 2 and 4, the replication reinforces the standing conclusion of the manuscript: the pipeline yields only **partial cross-city directional concordance, not replication of a transferable quantitative structure**.
