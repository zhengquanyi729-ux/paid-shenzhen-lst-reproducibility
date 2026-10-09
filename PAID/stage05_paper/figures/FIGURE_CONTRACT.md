# Stage 05 figure contract

One figure = one conclusion. Written before any plotting code, per the
figure-first rule. Backend: Python/matplotlib, exclusive. Export contract for
every figure: vector **PDF + SVG** and **600-dpi PNG + TIFF**, 183 mm double
column unless noted, Arial-metric sans, base 7 pt, colour-blind-safe palette,
bold lowercase panel letters.

Shared visual grammar (fixed across all seven figures):
A = discovery (blue) · B = dev-validation (orange) · C = locked (black) ·
buffer (light grey). Candidate = blue; Baseline A = black; random forest =
orange; gradient boosting = yellow; "reproduces / eligible" = green; "rejected /
does not transfer" = orange.

---

## Fig 0 — Study overview (also the graphical abstract)
**Conclusion.** No new urban LST law is validated here; what the protocol returns
is methodological — physical constraints act as an inductive-bias regulariser,
and the validation firewall is a falsifiable necessity (removing it manufactures
a +0.35 °C gain out of leakage).
**Archetype.** Three-band summary schematic. **Evidence.** all frozen products
(read live, nothing recomputed): split csv, `candidate_registry.json`,
`s04_validation_results.json`, `baselineB.json`, `external_replication.json`,
`baselineD.json`.
**Panels.** (a) the five-stage protocol pipeline as numbered cards (data &
partition → discovery sandbox → freeze & hash → firewall → independent
validation) joined by **shafted arrows**; (b) three orange adversarial-check
cards (conventional learners / external replication / constraint & firewall
ablation); (c) a grey verdict strip with the honest bottom line and the post-hoc
caveats. Bands are linked by labelled vertical arrows — (a)→(b) "the frozen
candidates are then stress-tested", (b)→(c) "the three checks jointly determine
the verdict" — so the causal chain is drawn, not implied.
**Review risk.** Must summarise, not over-claim: it carries the adverse results
at the same weight as the positive primary endpoint, and states in-figure that
locked-region readings and Changchun 2021 are post-hoc.

## Fig 1 — Design: the discovery–validation firewall
**Conclusion.** The protocol is a spatial partition (A/B development, C locked,
R=15 buffer) plus a cryptographic firewall: the search sees only A+B; C is
encrypted, candidates are frozen and hashed, and each is unsealed once.
**Archetype.** Study-area map, single panel (120 mm). **Evidence.** split csv
(32 748 cells; 31 760 in scope), read live.
**Panels.** (a) the A/B/buffer/C partition rasterised at 100-m cells, equal
aspect, muted colour-blind-safe palette (steel blue A · amber B · slate C · light
grey buffer · pale grey out-of-scope), with a 1-km scale bar, north arrow, a
four-class legend carrying cell counts, and an italic note for the 988
out-of-scope / no-data cells. A second schematic panel was removed — the firewall
flow (sandbox search · SHA-256 freeze · single unseal · Holm) is already carried
by Fig 0 and the text, so repeating it here would duplicate.
**Review risk.** Must not read as data analysis; it is design only. Keep axes as
grid indices labelled in 100-m cells, not coordinates. Out-of-scope / no-data
cells are drawn as a named neutral class — never filled, and never implied to
carry data.

## Fig 2 — The candidate does not beat a conventional learner on the locked region
**Conclusion.** Ranked on the selection region the candidate wins; on the locked
region a plain random forest out-predicts it (ΔC +0.75 vs +0.38).
**Archetype.** Forest plot + slope chart. **Evidence.** `baselineB.json` regions.
**Panels.** (a) locked-region ΔRMSE vs Baseline A with 95% spatial-block
bootstrap CI, sorted; (b) A-CV → B → C RMSE trajectories showing the inversion.
**Review risk.** This is an unfavourable result — present it prominently, do not
soften. Label C "post-hoc".

## Fig 3 — Search improves development RMSE with diminishing returns
**Conclusion.** The greedy search descends from 3.371 to 2.956 °C in five terms
(marginal gain collapses after term 2); the pool contains chaotic candidates that
the audit removes.
**Archetype.** Trajectory + scatter. **Evidence.** `candidate_registry.json`,
`experiment_trajectory.json`.
**Panels.** (a) A-CV vs number of terms, baseline line, staggered term labels;
(b) all 15 candidates, complexity (with cap 15) vs A-CV, status colour, one
off-scale marker for the A-CV=23.2 outlier.
**Review risk.** Do not imply the trajectory generalises; label A-CV as the
selection metric.

## Fig 4 — The locked-region result is real but fragile
**Conclusion.** Δ=+0.38 °C, p=0.005, CI>0, and it survives strata and 1-K noise,
but the R=25 criterion is not significant, and a constant floor already beats the
weak Baseline A.
**Archetype.** Specification curve + reference ladder. **Evidence.**
`s04_validation_results.json`.
**Panels.** (a) ΔRMSE across specifications (primary, R=25, three NDVI strata,
±0.5/±1.0 K noise) with CI where available; (b) reference ladder placing the
candidate against the constant floor and the row-shuffled pseudo-candidate.
**Review risk.** Both reservations (R=25, weak baseline) must be visible in the
figure, not only in text.

## Fig 5 — External replication is partial
**Conclusion.** On Changchun 2021 the qualitative structure reproduces (nonlinear
NDVI cooling, building warming, vegetation×building interaction) but the frozen
form does not transfer; exp(DEM)/SVF/Road_Dens are not recovered.
**Archetype.** Forest + bar + signed-direction bars. **Evidence.**
`external_replication.json`.
**Panels.** (a) Δ CV vs matched Baseline A* for frozen-form projections;
(b) pivot test (linear vs exp vs quadratic NDVI, and exp(DEM)); (c) bivariate
direction per shared covariate, flagging DEM as non-reproducing.
**Review risk.** Changchun is external, post-hoc data — state it. Do not present
partial agreement as confirmation.

## Fig 6 — Constraints are a regulariser and the firewall is load-bearing
**Conclusion.** Removing the physical constraints helps on the development
regions but hurts on C (the constraints regularise); removing the firewall
manufactures a +0.35 °C gain that is pure selection leakage.
**Archetype.** Crossing line chart + ladder + proportion bars. **Evidence.**
`baselineD.json`.
**Panels.** (a) A-CV/B/C RMSE for Baseline A, the unconstrained agent and the
constrained candidate; (b) firewall-off ladder (honest / select-on-C / refit-on-
all); (c) population profile (audit-rejected and over-cap fractions).
**Review risk.** Arm 2 touches C only as an explicit ablation demonstration; note
that it writes nothing to the frozen logs.
