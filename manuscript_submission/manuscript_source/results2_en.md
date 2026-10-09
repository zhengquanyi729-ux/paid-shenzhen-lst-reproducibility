# Results 2 — Locked-region evaluation of frozen candidates

*All numbers below come from the Stage 04 candidate-specific evaluation of the frozen candidates. The evaluation was produced by a validator process running outside the discovery sandbox. Region C is scientifically spent under Protocol V1: the reported statistic can be recomputed in software from the frozen artefacts, but C cannot be reused for hypothesis selection, revision, refitting or reconfirmation.*

## 2.1 Evaluation scope

Two of the four frozen candidates were evaluated under the conservative scope approved before the event: the leading discovery candidate `S03-H10-GREEDY` and the placebo reference `S03-H01-LIN7`. The placebo is identical to Baseline A, so its true ΔRMSE on any region is zero by construction; it exists to test whether the evaluation service discriminates, or simply passes whatever it is given. The remaining two frozen candidates (`S03-H11-REFINE`, `S03-H10P-GREEDY-MIN`) were not evaluated and retain their evaluation budget.

## 2.2 Primary endpoint

Baseline A is the frozen OLS model on the seven covariates fitted on region A only (region-A spatial-block CV RMSE = 3.1577 °C). On the 2,987 locked cells, Baseline A has RMSE 2.8415 °C.

| Candidate | Role | RMSE_C (Baseline A) | RMSE_C (candidate) | ΔRMSE | perm. p | 95% CI | Verdict |
|---|---|---|---|---|---|---|---|
| `S03-H10-GREEDY` | discovery | 2.8415 | 2.4624 | **+0.3791** | 0.005 | [0.2761, 0.4814] | Pass |
| `S03-H01-LIN7` | placebo | 2.8415 | 2.8415 | +0.0000 | 1.000 | [0.0000, 0.0000] | Fail (as expected) |

The primary endpoint required all five of ΔRMSE > 0, permutation p < 0.05, a 95% CI excluding zero, a physics-audit pass, and negative controls not fooled. `S03-H10-GREEDY` satisfied all five conditions. `S03-H01-LIN7` failed the first three and was correctly rejected. This endpoint is not reported here as a pristine confirmatory test: because the withheld region had been decrypted before candidate freeze (Section 2.6, and the protocol audit below), this stage is a locked-region evaluation of a frozen candidate under a documented protocol deviation.

Two of the five conditions (the physics audit and the negative controls) are recomputed independently inside the validator process rather than read from the discovery side's own JSON. For `S03-H10-GREEDY` the recomputed audit passes (maximum standardised term magnitude 8.71, well below the conditioning threshold of 10³) and the recomputed negative controls are not fooled. The validator reproduced the primary statistic bit-for-bit against a second, independently written implementation (ΔRMSE agreement < 10⁻⁹).

The placebo outcome is the central methodological result of the stage. Because the placebo is exactly the baseline, any evaluation service that passed it would be unable to distinguish a real improvement from a null one. The service rejected it on the three quantitative conditions while passing both models on the audit and control conditions, which isolates the rejection to the effect size rather than to a mechanical failure.

## 2.3 Protocol audit of Region-C access

A post-hoc implementation audit of the Stage 02 access log and guard code examined whether the withheld region influenced the study before the candidate-specific evaluation. The audit established the following facts. The discovery sandbox exposed only regions A and B; the access log records no discovery-side read of Region C, and candidate generation, fitting and ranking used region-A cross-validation with region B as a development falsification gate. Region C was decrypted by validation-side self-tests in Stage 02, before the Stage 03 candidate freeze, and the first such decryption precedes the freeze in the log sequence. The withheld region was decrypted repeatedly, not once, across those self-tests and the Stage 04 evaluation. The audit could not establish, from the log and manifests alone, whether the later modification of the validator's own verdict logic preceded or followed the first decryption, because that code change is not represented in the hash chain and the two timestamp sources available disagree by about three days. We found no evidence of programmatic candidate-selection contamination, but the early validation-side access invalidates the stronger claim of a pristine untouched holdout.

## 2.4 Multiplicity

Multiplicity was controlled by Holm–Bonferroni over the pre-registered frozen family (m = 4: three discovery candidates and one placebo). This family is more conservative than the two candidates actually evaluated, because it counts the two candidates whose evaluation budget remains unspent.

| Candidate | Uncorrected p | Holm threshold | Reject null |
|---|---|---|---|
| `S03-H10-GREEDY` | 0.005 | 0.0125 | Yes |
| `S03-H01-LIN7` | 1.000 | 1.000 | No |

The leading candidate remains significant after correction.

## 2.5 Stratification, measurement error and uncertainty

**NDVI strata.** Using global tercile thresholds on region A (0.381 and 0.684), the locked region splits into 1,008 low-, 1,637 mid- and 342 high-vegetation cells. The candidate's ΔRMSE is positive in all three strata, and every stratum's 95% CI excludes zero (Table below). No stratum reverses sign, so the aggregate effect is not the product of one dominant cover type.

| Stratum | n | RMSE (Baseline A) | RMSE (candidate) | ΔRMSE | 95% CI |
|---|---|---|---|---|---|
| Low vegetation | 1,008 | 3.4002 | 3.1629 | +0.2373 | [0.1113, 0.3689] |
| Mid vegetation | 1,637 | 2.5638 | 2.0589 | +0.5049 | [0.3498, 0.6438] |
| High vegetation | 342 | 2.2317 | 1.7841 | +0.4475 | [0.2756, 0.6221] |

**Measurement error.** Perturbing the locked targets with independent Gaussian noise of ±0.5 K and ±1.0 K (20 draws each) leaves ΔRMSE positive in every draw, with p < 0.05 in all draws and an effect size far larger than the perturbation interval width (mean ΔRMSE +0.3718, width 0.0121 at ±0.5 K; mean +0.3535, width 0.0272 at ±1.0 K). This shows stability under measurement error; it is not itself a significance test, since the baseline and the candidate see the same perturbed targets.

## 2.6 The result is criterion-sensitive and rests on a weak baseline

Two secondary findings materially limit the interpretation, and both are reported alongside the positive primary endpoint.

**Criterion sensitivity.** Stage 01 pre-registered a more conservative contiguity parameter, R = 25 cells (2.5 km), as a robustness check. Re-drawing the locked region with R = 25 reduces it to 791 cells; the effect shrinks to ΔRMSE = +0.1375 °C with permutation p = 0.085. The sign is unchanged, but the effect is no longer significant. The primary result therefore depends on the spatial criterion used to define the locked region.

**Baseline weakness.** Baseline A transfers poorly to region C. The constant predictor (region-A mean LST) achieves RMSE 2.6028 °C on region C, and a pseudo-candidate fitted on row-shuffled region-A targets achieves 2.6151 °C; both beat Baseline A's 2.8415 °C. Part of ΔRMSE > 0 therefore reflects a weak comparator rather than a strong candidate. The candidate (2.4624 °C) does beat the constant floor, so its gain is not mere shrinkage to the mean, but that comparison was not the pre-registered endpoint.

## 2.7 Expression review: the effect does not depend on DEM

The leading candidate uses `exp(NDVI)`, `exp(DEM)`, `SVF`, `Road_Dens` and an interaction `NDVI×DEM`. Because the DEM layer is not a credible elevation surface (region-A range 3–17 m), the DEM terms were examined by re-fitting ablated variants on region A and rescoring them (post-hoc) on region C.

| Variant | Complexity | ΔA-CV | ΔB | ΔC (post-hoc) | C p |
|---|---|---|---|---|---|
| full (`S03-H10-GREEDY`) | 14 | +0.2016 | +0.1222 | +0.3791 | 0.005 |
| no DEM terms | 7 | −0.1038 | +0.0802 | **+0.4326** | 0.005 |
| drop `exp(DEM)` | 11 | −0.0280 | −0.2602 | **+0.4451** | 0.005 |
| DEM terms only | 7 | −1.0141 | −3.1843 | −0.6150 | 1.000 |
| drop `exp(NDVI)` | 11 | −0.4344 | −1.0427 | **−0.1074** | 1.000 |

Removing the DEM terms does not reduce the locked-region gain; it slightly increases it. Removing the `exp(NDVI)` term instead destroys the gain on all three regions (ΔC = −0.1074, p = 1.000, CI includes zero). The DEM terms are additionally a smooth spatial field rather than terrain: an OLS of DEM on `[row, col, row², col²]` gives R² = 0.781 on region A. The interpretable content of the candidate is therefore carried by `exp(NDVI)`, and the DEM terms behave as a selection-region artefact. A DEM-free reduced model (`exp(NDVI)`, `SVF`, `Road_Dens`; complexity 7) achieves ΔC = +0.4326 at p = 0.005.

## 2.8 Evaluation registry

The evaluation is not repeatable. `S03-H10-GREEDY` and `S03-H01-LIN7` now each have `validation_runs = 1`; `S03-H11-REFINE` and `S03-H10P-GREEDY-MIN` remain at 0. The change to the frozen registry is confined to the two evaluated candidates, and the candidate definitions themselves are unchanged (verified by re-computing their canonical hashes).

The primary endpoint was met by one candidate, with two material caveats (criterion sensitivity and a weak comparator). The interpretation is taken up in the Discussion, where a further fair-comparison result sharpens it.
