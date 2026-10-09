# KNOWN LIMITATIONS

A single register of the study's declared limitations, for a reviewer. Each item states the limitation,
its consequence for interpretation, and where the supporting record lives in this package. This mirrors
the manuscript's Limitations section; nothing here is softened or omitted.

---

## A. Protocol-level limitations

**L-1 — The validation architecture was not fully realised (documented protocol deviation).**
A post-hoc audit of the Stage-02 access log found the withheld region (Region C) was decrypted by
validation-side self-tests **before** the Stage-03 candidate freeze, and decrypted **more than once**.
The single-access and untouched-holdout properties the design assumed therefore **do not hold**.
*Consequence:* Stage 04 is a **locked-region evaluation of a post-hoc-selected candidate under a
documented deviation**, not a pristine confirmatory test; it must not be described as fully
confirmatory or prospective.
*Evidence:* `PROTOCOL_DEVIATION.md`; `PAID/stage05_paper/manuscript/A6B_VERDICT.txt`,
`A6B_TIMELINE_AUDIT.md`; `PAID/stage02_platform/logs/experiment_log.jsonl`.

**L-2 — Validator chronology is unresolved.**
The same audit could not establish whether a later modification of the validator's verdict logic
preceded or followed the first Region-C decryption: the change is not represented in the hash chain, and
the two available clocks disagree by ~3 days (`[TIMESTAMP CONFLICT]`).
*Consequence:* the ordering claim "final validation logic frozen before first C access" is
**unprovable** from the archive (this is the basis of verdict CASE C).
*Evidence:* `A6B_TIMELINE_AUDIT.md` §2, T10; `PROTOCOL_DEVIATION.md` §2.3.

**L-3 — Discovery-side isolation is supported.**
The audit records **no** discovery-side read of the withheld region; candidate definition and ranking
used Region A only. *This is a limitation only in the sense that it bounds what can be claimed:* the
problem is on the validation side, not the search.
*Evidence:* `A6B_VERDICT.txt` ("Locked-from-discovery claim valid: YES"); `access_denied` entries in the log.

**L-4 — The contiguity parameter R = 15 is load-bearing.**
The buffer R = 15 cells (1.5 km) can be reconstructed from the archived record (de-trended residual LST
correlogram dropping below r = 0.20), but the alternative criterion R = 25 **changes the primary
inference** (ΔRMSE drops to +0.1375, p = 0.085).
*Consequence:* the headline result is sensitive to this choice.
*Evidence:* `PAID/stage01_protocol/split/split_manifest.json`; `PAID/stage04_validation/reports/s04_validation_results.json` (`criterion_sensitivity`).

**L-5 — Selection bias is only partly controlled.**
Four candidates were frozen out of fifteen searched. Holm–Bonferroni uses the frozen family of four,
but the step from fifteen to four is not fully corrected.

**L-6 — The negative controls are floor tests.**
They can exclude zero-skill models but have limited discriminating power.

**L-7 — The comparator is weak.**
The primary comparison is against Baseline A and is sensitive to the contiguity parameter; both are
quantified in Results 2 and both reduce confidence.

## B. Data-level limitations

**L-8 — `DEM_mean` is not a credible elevation surface** (range 3–17 m, not physical for Shenzhen).
*Consequence:* no terrain interpretation of any candidate is valid; DEM is a smooth spatial covariate at
most. *Evidence:* `DATA_DICTIONARY.md` §2.

**L-9 — Built-form variable definitions are unconfirmed.** The physical definitions of `X_BD`, `X_BH`,
`X_VolDens` are not recoverable from the archived source metadata, and `Road_Dens` units are unverified
(77 % zeros). *Consequence:* built-form results rest on quantities whose meaning is uncertain.
*Evidence:* `DATA_DICTIONARY.md` §2 (explicit-unknowns paragraph).

**L-10 — Acquisition metadata are missing.** Sensor, acquisition date and retrieval procedure for
`LST_mean` are unavailable, so **no diurnal, seasonal or thermal-recovery analysis is possible**. The
package does **not** fabricate them. *Evidence:* `DATA_PROVENANCE.md` §1.

**L-11 — The analysis grid is incomplete relative to the study area.** The supplied community-face layer
has truncated geometry for 18 of 299 polygons, and the grid was intersected with that copy: **3,259 cells
(≈ 32.6 km²)**, mostly in Longhua, Bao'an and Longgang, never entered the analysis. ~99.8 % of those
cells carry valid LST (median 38.9 °C), so they are **omitted data, not empty ground**. The study area is
383 km² against an analysed footprint of 327.5 km² (317.6 km² with valid data).
*Consequence:* the study is reported on the frozen grid; the gap is **disclosed rather than corrected**
(rebuilding the grid would change every downstream partition and result).
*Evidence:* `DATA_PROVENANCE.md` §1; `PAID/stage05_paper/reports/s05_08_area_audit.json`.

## C. Scope and generalisation

**L-12 — Single city, single period.** The prospective discovery-and-evaluation experiment covers one
city and one observation period; the locked-region result reaches at most the framework's L2 level (a
spatially robust relationship); L3 is not met. *Evidence:* manuscript §8.1.

**L-13 — External replication is post hoc and partial.** Changchun (2021, 500 m) is a **post-hoc partial
external replication**, not a prospective confirmation and not scale-matched (500 m vs 100 m); `SVF_mean`
and `Road_Dens` are absent there. The expression's core structure (non-linear NDVI cooling, building
warming, vegetation × building interaction) is partially reproduced, but `exp(DEM)`, SVF and Road_Dens
terms do not transfer. *Evidence:* `DATA_DICTIONARY.md` §4; `PAID/stage05_paper/reports/external_replication.json`.

**L-14 — Baseline B is a self-implemented stand-in.** RF/GBM are implemented without scikit-learn /
XGBoost (absent in the environment). Hyperparameters are fixed and reported, but implementation details
differ from the canonical libraries. *Evidence:* `PAID/stage05_paper/scripts/bmlib.py`.

**L-15 — The Baseline-D ablations are post hoc and exploratory.** They form a **combined-pipeline stress
test**, not a controlled single-factor ablation: they re-use a region already evaluated, and the
unconstrained arm changes hypothesis space, complexity cap and search behaviour together. The comparison
is directional, not confirmatory.

## D. Support and measurement

**L-16 — 100 m support, inherited measurement support.** The 5 m sky-view-factor layer is not a 5 m
temperature observation, and land-surface temperature is **not** air temperature; **no surface urban
heat-island intensity is claimed**. *Evidence:* `DATA_DICTIONARY.md` §2 (LST caveat).

**L-17 — Region C is scientifically spent under Protocol V1.** The reported statistic can be recomputed
in software from the frozen artefacts, but **C cannot be reused** for hypothesis selection, revision,
refitting or reconfirmation.

**L-18 — Two bootstrap intervals exist, and only one is confirmatory.** The **confirmatory** 95 %
spatial-block bootstrap interval for ΔRMSE is the one produced by the frozen Stage-04 validator with its
single shared RNG stream (seed 20260924), namely **[0.2761, 0.4814]**; this is the interval reported in
the manuscript's primary result and reproduced by `release_tools/verify_stage04_release.py`. A second,
**exploratory** interval **[0.2727, 0.4763]** is produced by a Stage-05 re-draw that starts a *fresh*
bootstrap RNG stream; it is a re-sampling check, not an independent confirmation, and the two must not be
pooled or swapped. The difference is a stream-chaining detail of the frozen validator, documented in
`release_tools/release_model.py`.
*Consequence:* quote `[0.2761, 0.4814]` as the result; label `[0.2727, 0.4763]` exploratory if it is
mentioned at all.

---

## E. What is **not** claimed

For the avoidance of doubt, this study does **not** claim: a validated new physical law; a specific
direction for SVF or building height/volume thermal response; a monotone NDVI cooling law as a finding
(it is recovered but bounded); causality; a surface urban heat-island intensity; that Changchun
confirms the Shenzhen expression; or that Region C is an untouched confirmatory holdout.
