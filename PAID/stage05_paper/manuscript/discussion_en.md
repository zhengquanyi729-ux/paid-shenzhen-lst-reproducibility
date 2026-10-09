# Discussion

## 5.1 A passed frozen endpoint is not a scientific law

The discovery stage froze four candidates and the evaluation stage assessed two. The leading candidate, `S03-H10-GREEDY`, met the pre-registered primary endpoint on the withheld region: ΔRMSE +0.3791 °C, permutation p = 0.005 (the minimum attainable value at the 199-permutation budget), and a 95% confidence interval excluding zero, with the effect surviving Holm–Bonferroni correction and holding across all three vegetation strata. Taken alone, this is a positive result.

Four further results show that it should not be read as the discovery of a transferable urban LST law.

First, the effect does not survive a more conservative definition of the locked region. Under the pre-registered alternative contiguity parameter R = 25 cells, ΔRMSE falls to +0.1375 °C and p rises to 0.085. The sign is stable but the significance is not, and the derivation of R = 15 makes that parameter load-bearing.

Second, the comparator is weak. Baseline A transfers poorly to the withheld region: a constant predictor and a pseudo-candidate trained on shuffled targets both beat it. Because ΔRMSE is measured against Baseline A, part of the apparent gain reflects the comparator rather than the candidate.

Third, the interpretable content of the candidate is narrower than its expression suggests. Re-fitting ablated variants shows that removing the DEM terms slightly improves the locked-region performance, while removing `exp(NDVI)` destroys it on every region. The DEM terms are a smooth spatial field (R² = 0.781 against cell coordinates) built on an elevation layer whose range, 3–17 m, is not physically credible for Shenzhen. The terrain reading of the candidate is unsupported.

Fourth, and most directly, a random forest on the same seven covariates outperforms the candidate on the withheld region by roughly a factor of two in ΔRMSE (+0.7465 versus +0.3791) — and a gradient-boosted model reaches +0.7500 — and beats the constant floor by a wide margin where the candidate beats it only modestly. A generic learner therefore captures transferable signal that the selected symbolic form misses.

The appropriate conclusion is the one the framework anticipates and permits: **no portable urban thermal law was established here.** The candidate is an observed improvement over the preregistered comparator, but it is selection-region-specific, sensitive to the spatial criterion, and largely carried by a single vegetation-related term.

## 5.2 Prediction, interpretability and discovery are distinct

The comparison makes a general point concrete. The best predictor on the withheld region is an off-the-shelf forest, which is not a discovery, while the discovered expression is not even the best predictor. Predictive accuracy and scientific content are distinct quantities, and optimising the first does not select for the second. The framework's own warning, that a better score does not equal a new law, is here observed from both directions.

The same distinction governs the constraints. In the exploratory combined-pipeline stress test, removing the admissibility constraints raised the development score but lowered the locked-region score — a result consistent with a regularising role for the constraints — while removing the firewall manufactured an apparent improvement of about a third of a degree Celsius that is consistent with selection leakage. Because the ablated arm also differs in hypothesis space, complexity cap and search behaviour, this is a combined-pipeline stress test, not a controlled isolation of either factor.

## 5.3 What discovery-side isolation achieved

The value of the run lies in what the protocol demonstrates about autonomous discovery, not in the candidate.

The placebo `S03-H01-LIN7` is identical to Baseline A, so its true effect is zero. The evaluation service rejected it on the effect-size conditions while passing both models on the audit and control conditions. This shows, against a live test rather than an argument, that the service does not pass whatever it is given.

Two of the five primary-endpoint conditions are recomputed inside the validator process from region-A and region-B data rather than read from the discovery side's own records. The examined party no longer grades itself.

On the discovery side, the evidence supports one claim and not a stronger one. The access log records no discovery-side read of the withheld region, and candidate generation, fitting and ranking used region-A cross-validation with region B as a development falsification gate. We therefore state that we found no evidence that Region C entered the programmatic candidate-generation or selection process. This is a claim about discovery-side use, and it is the strongest claim the record supports; it is not a claim that the withheld region was untouched, which the audit contradicts.

The fair comparison also yields a result that cuts against the discovery, and it is reported in full. A protocol that can only produce confirmations would be of little value; this run produced a candidate that passed its pre-registered test and still, on the accumulated evidence, did not amount to a law.

## 5.4 What the protocol audit revealed

The audit of the access history was as important as the discovery itself, and its finding is negative.

The intended design froze the withheld region behind encryption and a runtime guard, and intended a single candidate-specific evaluation per candidate. The audit established two facts that break that intent. First, the withheld region was decrypted by validation-side self-tests during Stage 02, before the Stage 03 candidate freeze — the first decryption precedes the freeze in the log sequence — and it was decrypted repeatedly rather than once. One of those self-tests published a placeholder reading computed against genuine locked targets, which is why the region cannot be described as an untouched holdout. Second, the validator's own verdict logic was subsequently modified, to recompute the physics audit and the negative controls in-process; the audit could not establish whether that modification preceded or followed the first decryption, because the change is not represented in the hash chain and the two timestamp sources available disagree by about three days. That unresolved ordering is recorded rather than smoothed over.

None of this shows that the locked target values influenced candidate selection; on the contrary, the discovery-side isolation is supported. What it shows is narrower and more useful: the controls that were meant to protect the withheld region were not themselves frozen and timestamped before execution. A validation architecture can be correct on paper and fail in implementation, and the failure here is of exactly that kind — not a contaminated selection, but an unverifiable protection. The audit therefore changes our claim from pristine confirmatory validation to a separated discovery and locked-region evaluation under a documented protocol deviation.

## 5.5 Implications for autonomous science

The lesson extends beyond this dataset. Cryptography and access controls are insufficient unless validation-side software state and every target access are themselves frozen and independently timestamped before execution. A sealed region whose key is held by a process that can run self-tests against it, and whose validator code can change without entering the ledger, is protected by convention dressed as mechanism. The design that would have avoided this is straightforward — freeze the validator, its hash and the full access policy before the first decryption, and make every decryption an audited event — and it is the change we would make first in any re-run.

Three lines of work would strengthen the result. A prospective replication on an independent time period or a second city — beyond the post-hoc Changchun replication reported here — would test transferability and move the work toward L3. A DEM-free reduced model (`exp(NDVI)`, `SVF`, `Road_Dens`) could be pre-registered and tested prospectively rather than only in the post-hoc analysis reported here. And the constraint and firewall ablations reported here measure rather than assume the value of the admissibility constraints; because they are post-hoc and combined, re-running them prospectively with their own frozen endpoint and a controlled single-factor design would make that comparison confirmatory in intention. The design-counterfactual experiments the framework envisages (Experiment 5) are not attempted here, since they require physical simulation or intervention evidence that the present data cannot supply.

## 5.6 Limitations

**Protocol limitations.** The intended validation architecture was not fully realised in implementation. A post-hoc audit of the Stage 02 access log found that the withheld region (Region C) was decrypted by validation-side self-tests before the Stage 03 candidate freeze, and it was decrypted more than once; the single-access and untouched-holdout properties that the design assumed therefore do not hold. The same audit could not establish whether a later modification of the validator's verdict logic preceded or followed the first decryption, because the change is not represented in the hash chain and the available timestamps disagree by about three days. The discovery-side isolation is supported — the audit records no discovery-side read of the withheld region — but Stage 04 is a locked-region evaluation of a frozen candidate under a documented protocol deviation, not a pristine confirmatory test. The derivation of the contiguity parameter R = 15 is likewise load-bearing: although it can be reconstructed from the archived record, the alternative criterion R = 25 changes the primary inference.

The remaining limitations are empirical and specific to the data.

1. The prospectively specified discovery-and-evaluation experiment covers one city and one observation period; the locked-region result is sensitive to the spatial-separation criterion and should not be interpreted as a robust or transferable relationship. Changchun is a post-hoc partial external replication, not a prospective confirmation.
2. The DEM layer is not a credible elevation surface (range 3–17 m). Any terrain interpretation of a candidate is invalid, and DEM should be treated as a smooth spatial covariate at best.
3. The physical definitions of `X_BD`, `X_BH` and `X_VolDens` are unconfirmed by the data authors, and the units of `Road_Dens` are unverified (77% zeros). Built-form results rest on quantities whose meaning is uncertain.
4. Image acquisition time, sensor and retrieval procedure are unavailable, so no diurnal, seasonal or thermal-recovery analysis is possible.
5. Selection bias is only partly controlled. Four candidates were frozen from fifteen searched, and while Holm–Bonferroni uses the frozen family of four, the step from fifteen to four is not fully corrected.
6. The negative controls are floor tests. They can exclude zero-skill models but have limited discriminating power.
7. The primary result is sensitive to the spatial contiguity parameter, and the comparator is weak; both are quantified in Results 2 and both reduce confidence.
8. Baseline B is a self-implemented stand-in for scikit-learn and XGBoost, chosen because the environment lacks those libraries. Hyperparameters are fixed and reported, but implementation details differ from the canonical libraries.
9. The constraint and firewall ablations (Baseline D) are post-hoc and exploratory, and form a combined-pipeline stress test rather than a controlled single-factor ablation: they re-use a region that had already been evaluated, and the unconstrained arm changes the hypothesis space, the complexity cap and the search behaviour together, so the comparison is directional rather than confirmatory.
10. Region C is scientifically spent under Protocol V1. The reported statistic can be recomputed in software from the frozen artefacts, but C cannot be reused for hypothesis selection, revision, refitting or reconfirmation.
11. The analysis is at 100 m resolution and inherits the measurement support of the source layers. The 5 m sky-view-factor layer is not a 5 m temperature observation, and the surface temperature is not air temperature; no surface urban heat island intensity is claimed.
12. The analysis grid is incomplete relative to the study area. The supplied community-face layer has truncated geometry for 18 of its 299 polygons, and the grid was intersected with that copy rather than with a corrected one: 3,259 cells (32.6 km²) of community area inside the same bounding box, mostly in Longhua, Bao'an and Longgang, never entered the analysis. About 99.8% of those cells carry valid LST (median 38.9 °C), so they are omitted data rather than empty ground. The administrative study area is 383 km² against an analysed footprint of 327.5 km² (317.6 km² with valid data). Rebuilding the grid would change every downstream partition and result, so the study is reported on the frozen grid and the gap is disclosed rather than corrected.
