# Results 4 — Fair comparison with conventional models

*The comparison uses the same data, the same frozen spatial folds and the same metric for every model. Region C was already evaluated in Stage 04, so all region-C numbers here are post-hoc and exploratory; they do not constitute new confirmatory tests.*

## 4.1 Compared models

The framework defines four baselines. All four are reported here: **Baseline A**, the frozen OLS model on the seven covariates; **Baseline B**, a post-hoc adversarial benchmark comprising a random forest and a gradient-boosted regressor on the same seven covariates; **Baseline C**, the symbolic-regression search over the preset operator space, which is the search that produced the candidates themselves; and **Baseline D**, an exploratory combined-pipeline stress test — an autonomous agent with the same base model and tool whitelist but with the admissibility constraints and the firewall removed. Baseline D is an ablation rather than a predictor and is reported separately in §4.6.

Baseline B was implemented from scratch in NumPy (CART regression trees with variance-reduction splits; a bagged forest and a squared-loss boosted model) because the execution environment provides no scikit-learn, XGBoost or SciPy and has no network access. Hyperparameters were fixed before evaluation: forest of 300 trees (max depth 12, minimum leaf size 10, three features per split), boosting with 300 rounds (depth 4, learning rate 0.05), seed 20260924. Tree models are invariant to monotone rescaling of individual features, so no standardisation was applied. An augmented forest added the engineered transforms used by the strongest candidate (`exp(NDVI)`, `exp(DEM)`, `NDVI×DEM`) to the seven covariates.

## 4.2 Region-A development metric and validation regions

| Model | A-CV RMSE | B RMSE | C RMSE | ΔC vs Baseline A | C perm. p | C 95% CI |
|---|---|---|---|---|---|---|
| Baseline A (OLS) | 3.1577 | 2.5425 | 2.8415 | — | — | — |
| Candidate `S03-H10-GREEDY` | **2.9560** | 2.4203 | 2.4624 | +0.3791 | 0.005 | [0.2727, 0.4763] |
| Candidate, DEM-free | 3.2614 | 2.4623 | 2.4090 | +0.4326 | 0.005 | [0.2128, 0.6419] |
| Random forest (Baseline B) | 2.9867 | 2.2544 | **2.0950** | **+0.7465** | 0.005 | [0.5651, 0.9235] |
| Gradient boosting (Baseline B) | 3.3219 | 2.5215 | **2.0915** | **+0.7500** | 0.005 | [0.5577, 0.9331] |
| Random forest, augmented | — | 2.4391 | 2.1224 | +0.7191 | 0.005 | [0.5305, 0.9043] |
| Constant floor (region-A mean) | — | 4.4960 | 2.6028 | +0.2388 | 0.985 | [0.0180, 0.4483] |

The primary-endpoint inference is the Stage-04 95% CI [0.2761, 0.4814] (Results 2). The interval shown for the candidate here ([0.2727, 0.4763]) is an exploratory re-bootstrap computed in Stage 05 for the same frozen candidate; it is reported for completeness. No Stage-05 output is modified.

## 4.3 The comparison inverts between selection and validation

On the region-A development metric, the candidate is the best model: `S03-H10-GREEDY` has the lowest A-CV RMSE (2.9560), followed by the random forest (2.9867), Baseline A (3.1577) and the DEM-free reduced model (3.2614). This is expected, because the candidate was selected by minimising a metric of exactly this type on region A.

On the locked region C the ordering inverts. Both Baseline B models outperform the candidate by roughly a factor of two in ΔRMSE: the random forest reaches RMSE 2.0950 °C (ΔRMSE +0.7465) and the boosted model 2.0915 °C (ΔRMSE +0.7500), against the candidate's 2.4624 °C (ΔRMSE +0.3791). All are significant at p = 0.005, so the difference between them is not a matter of significance but of magnitude. The augmented forest, which is given the candidate's own engineered features, is not better than the plain forest (ΔRMSE +0.7191), so the gap is not explained by a missing transform.

The random forest also beats the constant floor by a wide margin on region C (2.0950 versus 2.6028) whereas the candidate beats it only modestly (2.4624). A generic learner on the seven covariates therefore captures predictive signal in region C that the selected symbolic form misses. The candidate's advantage over Baseline A is observed under the primary locked-region specification but is not robust to all spatial criteria.

## 4.4 Feature importance and negative control

Feature importance from the random forest (impurity-based, seven covariates) ranks `NDVI_mean` first (0.424), followed by `SVF_mean` (0.164), `DEM_mean` (0.154), `X_BH` (0.095), `X_VolDens` (0.079), `X_BD` (0.053) and `Road_Dens` (0.031). This agrees with the expression review: vegetation is the dominant signal, and `DEM_mean` is a mid-ranked contributor rather than the leading one.

A negative control repeated the random-forest fit with the region-A targets randomly permuted before training. The shuffled-target model reaches RMSE 2.6528 °C on region C (and 2.6876 °C for the boosted variant), approximately the constant floor, against 2.0950 °C for the true forest. The gap shows the forest's advantage comes from real signal rather than target leakage or a positional artefact of the spatial split.

## 4.5 The parsimony candidate

The frozen parsimony candidate `S03-H10P-GREEDY-MIN` (`exp(NDVI)` and `exp(DEM)`, complexity 6) improved on Baseline A in region A (A-CV 3.0655) but worsened the region-B RMSE (ΔB = −0.3412), and its region-A confidence interval includes zero. In the unified comparison its profile matches the other weak candidates. Its validation attempt remains unspent, and on this evidence it should not be spent.

## 4.6 Baseline D — the unconstrained, firewall-off agent

Baseline D is a combined-pipeline stress test rather than a controlled single-factor ablation. Removing "the constraints" also removes the pre-registered term pool, the complexity cap of 15 and the audit, and replaces the search with free-form random search plus hill-climbing; the ablation therefore stresses the whole design (hypothesis space, complexity cap and search behaviour together), so its results are exploratory and cannot isolate the causal effect of the constraints alone. **Arm 1** removes the admissibility constraints while keeping the firewall: the hypothesis space is unbounded, and the agent runs free-form random search plus hill-climbing with the same operator set (`+ − × ÷ exp log neg inv`) on region A, selecting by the same region-A spatial-block CV. **Arm 2** removes the firewall: the agent is allowed to select a candidate directly on the withheld region C (argmin C-RMSE), which is exactly the selection-on-test-set that the firewall exists to forbid. The experiment writes to none of the frozen Stage 02/03/04 logs or registries; region C is touched only for this explicit ablation and no frozen result is changed.

**Arm 1 — removing the constraints does not help, it overfits.** With N = 150 seeds plus hill-climbing (351 unique expressions evaluated), the best region-A expression is

> `exp(NDVI) + DEM + (NDVI·NDVI) + (Road_Dens − X_BH) − ((NDVI·DEM) + (NDVI + SVF))` (cx = 22)

**Table 5 — Arm 1: unconstrained optimum vs the constrained discovery.**

| Model | A-CV RMSE | B RMSE | C RMSE |
|---|---|---|---|
| Baseline A (7-cov OLS) | 3.1577 | 2.5425 | 2.8415 |
| **Baseline D, Arm 1 optimum** | **2.8663** | **2.3082** | 2.6251 |
| Constrained candidate `S03-H10-GREEDY` | 2.9560 | 2.4203 | **2.4624** |

The unconstrained search does improve the development metrics: it beats the constrained candidate on both region A (2.8663 vs 2.9560) and region B (2.3082 vs 2.4203). But it is **worse on the locked region** (2.6251 vs 2.4624). Removing the constraints lets the search fit the development regions harder and more specifically, and that specificity does not generalise. The constraints — a curated operator pool, a complexity cap and the audit — restrict the hypothesis space, and the exploratory results are consistent with a regularising role for them. The population profile supports this reading: of the 351 unique expressions, 156 (44%) are rejected by the physical audit, all of them for PA7 (term-scale blow-up such as `exp(X_BD)` or `NDVI/X_BD`), and 264 (75%) exceed the complexity cap of 15. The constraint is doing real filtering, not arbitrary raising of the bar.

**Arm 2 — removing the firewall manufactures a false gain.** If selection is moved onto region C, the selected expression reaches region-C RMSE **2.2747 °C**, an apparent improvement of **0.3503 °C** over the honest Arm-1 selection — yet that expression's region-A CV (3.2907) and region-B RMSE (2.6793) are both mediocre. The "gain" is selection leakage, not discovery. Carried one step further, refitting the Arm-1 expression on all of A ∪ B ∪ C collapses the region-C number to 2.5414 °C, a training error masquerading as a held-out result.

**Reading.** Baseline D shows that, in this exploratory stress test, the constrained pipeline's contribution is not a higher development score — the unconstrained agent scores better on regions A and B — but the association with candidates that lie inside an admissible set and were selected without the withheld region entering the search. Under those conditions the constrained candidate generalises better to region C. This illustrates "prediction is not discovery", and is consistent with a regularising role for the constraints; because the ablated arm differs in hypothesis space, complexity cap and search behaviour, it does not isolate the causal effect of the constraints alone. As with all region-C numbers in this section, these are post-hoc and exploratory.
