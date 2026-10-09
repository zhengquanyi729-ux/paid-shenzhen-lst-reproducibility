# Results 1 — The discovery process

*Every number in this section is a region-A development metric unless stated otherwise. Region A is the region the search selected on, so these values carry selection bias and are optimistic; the candidate-specific evaluation is reported in Results 2. Region C was excluded from the discovery search and was not reachable from the discovery sandbox.*

## 1.1 Search scope, budget and the frozen dev metric

The discovery agent ran inside the Stage 02 access guard with only two regions visible at the sandbox level: the discovery region A (19,184 cells) and the development-validation region B (6,182 cells). Region C was not reachable from the sandbox; the guard recorded 965 opens and 0 denials for the whole run, and the search used 3,151 of the frozen 5,000-fit budget. No candidate could be registered or edited by the discovery side: the registry and reports sit outside the sandbox and are written only by the freeze step.

The development metric was fixed in Stage 01: connected spatial-block cross-validation on region A, with k = 5 blocks (sizes 2,544 / 5,143 / 3,713 / 4,096 / 3,688, seed 20260924) and pooled out-of-fold RMSE in °C. Variables are standardised on the training fold inside each fit, so no cross-fold leakage enters the metric. Complexity is counted as the number of expression-tree nodes plus the number of terms, capped at 15.

Baseline A is the frozen ordinary-least-squares model on the seven covariates (`NDVI_mean`, `DEM_mean`, `SVF_mean`, `Road_Dens`, `X_BD`, `X_BH`, `X_VolDens`), fitted on region A only. Its region-A cross-validated RMSE is 3.1577 °C. This value is the reference against which every candidate is scored, and it is also the placebo in the validation stage (Section 2.1).

## 1.2 Three rounds of autonomous exploration

The search proceeded in three rounds. Round 1 was a human-specified hypothesis agenda; only Rounds 2–3 were algorithmic search (greedy forward selection, then hill-climbing) inside the frozen operator set. Fifteen candidates were evaluated in total (twelve preregistered hypotheses, two greedy-search products, one local-refinement product).

**Round 1 — preregistered hypothesis agenda (12 candidates).** Hand-specified, falsifiable hypotheses in ascending complexity: a linear reference over all seven covariates; four single-variable quadratic responses; the building trio (`X_BD`, `X_BH`, `X_VolDens`); three interaction pairs (vegetation×building, sky-view×building, road×vegetation); and three functional forms (a vegetation-to-building ratio, a log of volume density, and an exponential of building coverage).

**Round 2 — greedy forward selection (no pre-screen).** Starting from a pool of roughly 98 terms, each step admitted the term that reduced the region-A block CV RMSE the most, until the complexity cap was reached. No correlation pre-screen was applied, to avoid prescreening bias.

| Step | Term added | Terms | A-CV RMSE (°C) |
|---|---|---|---|
| 1 | `exp(NDVI)` | 1 | 3.3706 |
| 2 | `exp(DEM)` | 2 | 3.0655 |
| 3 | `SVF` | 3 | 2.9892 |
| 4 | `Road_Dens` | 4 | 2.9677 |
| 5 | `NDVI×DEM` | 5 | 2.9560 |

The first term alone is worse than Baseline A; the second term (`exp(DEM)`) is the first point at which the model beats the frozen baseline, and it defines the parsimony candidate. Subsequent terms yield diminishing returns.

**Round 3 — local refinement.** From the best round-2 expression, single-step hill-climbing (add / swap / drop) accepted the change that reduced CV RMSE the most.

| Action | Position | Term | Terms | A-CV RMSE (°C) | Expression |
|---|---|---|---|---|---|
| replace | 1 | `DEM` | 5 | 2.9166 | `exp(NDVI) + DEM + SVF + Road_Dens + (NDVI*DEM)` |
| replace | 2 | `NDVI²` | 5 | 2.9139 | `exp(NDVI) + DEM + (NDVI*NDVI) + Road_Dens + (NDVI*DEM)` |

## 1.3 The candidate registry

All fifteen candidates are retained, including failures (the registry is append-only). ΔA is Baseline A's region-A CV RMSE minus the candidate's; ΔB is the candidate's improvement in region B. Region B was not used for selection, but because it was used for method screening it is a development reference, not independent confirmation.

| ID | Round | Expression | Cx | A-CV | ΔA | ΔB | Audit | Status |
|---|---|---|---|---|---|---|---|---|
| `S03-H01-LIN7` | R1 | `NDVI + DEM + SVF + Road_Dens + X_BD + X_BH + X_VolDens` | 14 | 3.1577 | +0.0000 | +0.0000 | pass | passed, no gain |
| `S03-H02-QUAD-NDVI` | R1 | `NDVI + NDVI²` | 6 | 3.2552 | −0.0975 | −0.1467 | pass | passed, no gain |
| `S03-H02-QUAD-XBD` | R1 | `X_BD + X_BD²` | 6 | 4.4405 | −1.2829 | −0.5114 | pass | passed, no gain |
| `S03-H02-QUAD-XVOL` | R1 | `X_VolDens + X_VolDens²` | 6 | 4.6112 | −1.4535 | −1.0721 | pass | passed, no gain |
| `S03-H02-QUAD-SVF` | R1 | `SVF + SVF²` | 6 | 4.1940 | −1.0363 | +0.0839 | pass | passed, no gain |
| `S03-H03-BUILD3` | R1 | `X_BD + X_BH + X_VolDens` | 6 | 4.4080 | −1.2504 | −0.5699 | pass | passed, no gain |
| `S03-H04-VEG-BUILD` | R1 | `NDVI + X_BD + (NDVI*X_BD)` | 8 | 3.6521 | −0.4944 | −0.3322 | pass | passed, no gain |
| `S03-H05-SVF-BUILD` | R1 | `SVF + X_BD + (SVF*X_BD)` | 8 | 4.2352 | −1.0776 | −0.0907 | pass | passed, no gain |
| `S03-H06-ROAD-VEG` | R1 | `Road_Dens + NDVI + (Road_Dens*NDVI)` | 8 | 3.7704 | −0.6127 | −0.6221 | pass | passed, no gain |
| `S03-H07-VEGBLD-RATIO` | R1 | `(NDVI/X_BD) + X_BD` | 6 | 4.5106 | −1.3530 | −1.5637 | **fail** | rejected (physics) |
| `S03-H08-VOLDENS-LOG` | R1 | `log(X_VolDens²)` | 5 | 5.0635 | −1.9059 | −1.8984 | pass | passed, no gain |
| `S03-H09-EXP-BUILD` | R1 | `exp(X_BD) + SVF` | 5 | 23.1743 | −20.0167 | −0.2919 | **fail** | rejected (physics) |
| `S03-H10-GREEDY` | R2 | `exp(NDVI) + exp(DEM) + SVF + Road_Dens + (NDVI*DEM)` | 14 | 2.9560 | +0.2016 | +0.1222 | pass | **passed dev gain** |
| `S03-H10P-GREEDY-MIN` | R2 | `exp(NDVI) + exp(DEM)` | 6 | 3.0655 | +0.0921 | −0.3412 | pass | **passed dev gain** |
| `S03-H11-REFINE` | R3 | `exp(NDVI) + DEM + (NDVI*NDVI) + Road_Dens + (NDVI*DEM)` | 15 | 2.9139 | +0.2438 | +0.0997 | pass | **passed dev gain** |

Status counts: three candidates improved on Baseline A (all beating it on the development metric), ten passed the audit but did not improve, and two were rejected. The best development score is `S03-H11-REFINE` at 2.9139 °C, 0.2438 °C (7.7%) below Baseline A.

## 1.4 Physics audit and numerical conditioning

Each candidate passed a seven-check audit, but the checks differ in strength and we do not present them as a uniform gate. Four are hard gates that can reject a candidate: energy-closure / causal over-reach (PA3), no directional presupposition (PA4), measurement boundary (PA5), and numerical conditioning and term scale (PA7). Three are informational and cannot reject: dimensional consistency (PA1 — every variable is standardised, so all terms are dimensionless by construction), geometric legality (PA2 — flags the unresolved `X_BD` / `X_BH` / `DEM` definitions for author clarification), and statistical-integrity fields (PA6 — always written by the experiment agent).

Both rejections came from the conditioning gate PA7. `S03-H07-VEGBLD-RATIO` carries the ratio term `NDVI/X_BD`, whose maximum absolute value on region A is 4,932; `S03-H09-EXP-BUILD` carries `exp(X_BD)`, whose maximum is 53,363. With inputs standardised to O(1), a term spanning three orders of magnitude removes any interpretation from a single linear coefficient, and per-fold re-standardisation amplifies it into extrapolation. The root cause is structural: `Road_Dens` (77% zeros) and `X_BD`, `X_BH`, `X_VolDens` (heavy-tailed) are strongly zero-inflated, so ratio and exponential forms of them explode at small region-A standard deviations. This is a systematic risk imposed by the data distribution, not an incidental search error, and it is the audit layer's job to intercept it.

## 1.5 Falsification and negative controls

Two kinds of check were run, of deliberately different strength. The floor controls (NC1, per-cell target shuffling; NC2, spatial-block permutation of block means; NC3, Gaussian random targets) have weak discriminating power: they destroy all structure, so their RMSE is close to the target standard deviation and any model with more skill than the constant mean passes. They can exclude zero-skill models but cannot detect overfitting. Every audit-passing candidate is recorded as not fooled by these controls.

The more discriminating check is a region-B spatial-block permutation of the block means, which yields a permutation p-value for ΔB; because region B participated in method screening, this remains a development reference rather than a confirmatory test. Under it, `S03-H10-GREEDY` (p = 0.005) and `S03-H11-REFINE` (p = 0.005) are the only candidates whose region-B improvement is significant, while the parsimony candidate `S03-H10P-GREEDY-MIN` is not (ΔB = −0.3412, p = 0.175).

One implementation defect in this layer is worth recording because it is instructive: the block permutation was initially written to permute the block *index order* and then resolve values by label, which returned each block its own value and reduced the permutation to the identity (measured correlation 1.000). The same construct had also entered the Stage 02 validator, where it would have forced the permutation p-value to 1.0 and made the primary endpoint impossible to pass — a false-negative-only defect. It was found during Stage 03 verification and fixed by permuting the block-mean *values*; the corrected region-B correlation is 0.086 and the permutation test recovers its discriminating power. An implementation audit later found that the access log cannot establish that this fix predated the first Region-C access, so the timing of the fix relative to that access is recorded as unresolved rather than asserted (see Section 4 and the Discussion).

## 1.6 Frozen candidates

The preregistered selection rule froze every candidate with `status = passed_dev_gain` (audit passed, not fooled, A-CV better than Baseline A), taking the eight best by A-CV, plus the Baseline A specification itself as a placebo reference. In this run four were frozen, below the cap of eight.

| ID | Role | Expression | Cx | A-CV | ΔA | ΔB | canon_hash |
|---|---|---|---|---|---|---|---|
| `S03-H11-REFINE` | discovery | `exp(NDVI) + DEM + (NDVI*NDVI) + Road_Dens + (NDVI*DEM)` | 15 | 2.9139 | +0.2438 | +0.0997 | `629ed98b060d…` |
| `S03-H10-GREEDY` | discovery | `exp(NDVI) + exp(DEM) + SVF + Road_Dens + (NDVI*DEM)` | 14 | 2.9560 | +0.2016 | +0.1222 | `171554145102…` |
| `S03-H10P-GREEDY-MIN` | discovery | `exp(NDVI) + exp(DEM)` | 6 | 3.0655 | +0.0921 | −0.3412 | `5e8bcc5de6d8…` |
| `S03-H01-LIN7` | placebo | `NDVI + DEM + SVF + Road_Dens + X_BD + X_BH + X_VolDens` | 14 | 3.1577 | +0.0000 | +0.0000 | `7a7e172b70cb…` |

For each discovery candidate the registry records an unpresupposed effect direction from a ±1 standard-deviation finite difference: `S03-H10-GREEDY` gives DEM +1.95, NDVI −4.49, Road_Dens +0.80 and SVF −1.57 °C per SD; `S03-H11-REFINE` gives DEM +2.54, NDVI −4.92 and Road_Dens +0.48 °C per SD. The negative NDVI direction is the vegetation-cooling sign. The 95% spatial-block bootstrap confidence intervals on the region-A CV RMSE are [2.5263, 3.0093] for `S03-H10-GREEDY` and [2.5126, 2.9175] for `S03-H11-REFINE`, and the residual Moran's I is 0.79 and 0.77 respectively — i.e. spatial autocorrelation is not removed, so the block CV likely understates the true uncertainty.

## 1.7 Marginal returns, selection bias and robustness

The gain from added complexity is small. Moving from the two-term model to the five-term refinement lowers the region-A CV RMSE only from 3.0655 to 2.9139 °C (0.152 °C). Most of the explanatory power is concentrated in the first one or two terms, both built on a non-linear transform of NDVI with a negative direction, consistent with vegetation cooling; more elaborate structure earns little on the development set.

The three frozen discovery candidates differ in how well they generalise to region B. `S03-H10-GREEDY` improves on both region A (ΔA = +0.2016) and region B (ΔB = +0.1222); `S03-H11-REFINE` has the largest region-A gain but a slightly smaller region-B gain (ΔB = +0.0997) and sits at the complexity cap; `S03-H10P-GREEDY-MIN` is the simplest but worsens region B (ΔB = −0.3412), suggesting its region-A gain is largely noise.

A read-only A/B robustness battery, run before the candidate-specific evaluation and touching no region-C data, shows that the region-A gains are stable to the fold seed (four seeds) and to the block granularity (k = 5, 8, 12), and remain positive under ±0.5 K and ±1.0 K target noise in every draw. That only shows stability: because baseline and candidate see the same perturbed targets, the noise test is not a significance test. The discriminating quantity is the region-A-only inference, where `S03-H10-GREEDY` and `S03-H11-REFINE` have confidence intervals excluding zero and permutation p = 0.005, while `S03-H10P-GREEDY-MIN` has a confidence interval including zero (p = 0.335) — corroborating its negative ΔB and indicating its evaluation budget should not be spent. The preregistered freeze rule was not changed after seeing this.

## 1.8 Determinism

The whole discovery run is deterministic under the frozen seeds. A deterministic re-run performed after correcting a cross-stage side effect (a Stage 02 clean-room step that had also wiped the shared discovery work tree) reproduced all fifteen candidates and their cross-validation values identically, and reproduced all four frozen `canon_hash` values verbatim. Rebuilt files differ from the first run only in their `ran_at` timestamp, which enters the file hash but not any candidate's content.
