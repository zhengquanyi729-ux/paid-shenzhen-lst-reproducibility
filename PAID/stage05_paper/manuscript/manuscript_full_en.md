@@TITLE Auditable autonomous symbolic discovery of urban thermal relationships with admissibility constraints and separated validation

@@SUB [Authors to be completed] · [Affiliations to be completed] · [Corresponding author to be completed] · Working draft, Stage 05

## Abstract

**Background.** Agentic, structure-agnostic symbolic search can propose interpretable expressions from data, but on spatially autocorrelated environmental targets a flexible search can exploit the evaluation protocol, and it is rarely possible to separate an agent’s fitting ability from the contribution of its constraints and its evaluation design. We ask what admissibility constraints and the separation of discovery from evaluation actually contribute when an autonomous agent is asked to discover relationships between urban morphology, surface characteristics, and land surface temperature (LST).

**Methods.** Using a 100 m analysis grid of the built-up area of Shenzhen, China (31,760 cells), we partitioned the city into a discovery region A (19,184 cells), a development-validation region B (6,182) and an encrypted region C (2,987), separated by a 1.5 km buffer. A symbolic search with physics-aware admissibility constraints — a curated operator pool, a complexity cap and a numerical-conditioning audit — ran inside a sandbox restricted to the development regions; candidates were frozen and hashed before any candidate-specific evaluation. A subsequent implementation audit found that validation-side self-tests had decrypted Region-C targets before Stage-03 candidate discovery, a documented protocol deviation from the intended single-access design. The frozen candidate was evaluated on the locked region, then benchmarked post hoc against conventional learners (random forest and gradient boosting) and re-examined post hoc on a second city (Changchun, 2021).

**Results.** The leading candidate met the pre-registered primary endpoint on the locked region (ΔRMSE +0.3791 °C against a linear baseline, permutation p = 0.005, 95% CI [0.2761, 0.4814]); p = 0.005 is the minimum attainable value at the permutation budget of 199. The effect did not survive a more conservative contiguity criterion (R = 25: +0.1375 °C, p = 0.085) and rested on a weak comparator; a random forest on the same covariates more than doubled the gain (ΔRMSE +0.7465 °C) and a gradient-boosted model reached +0.7500 °C. On Changchun the analysis, conducted post hoc, produced a partial conceptual overlap while the frozen form did not transfer. In an exploratory combined-pipeline stress test, removing the admissibility constraints improved the development regions but degraded the locked region, and removing the firewall manufactured a spurious +0.35 °C gain that vanished on the development regions.

**Conclusions.** No portable urban thermal law was established. The stronger contribution is methodological: an auditable symbolic-search pipeline with admissibility constraints, evaluated on a separated locked region under a documented protocol deviation, and subjected to post-hoc adversarial benchmarking and a post-hoc external replication. The pipeline returns partial directional concordance and an audited negative methodological finding, not a portable quantitative law.

**Keywords:** physics-aware admissibility constraints; symbolic regression; autonomous scientific discovery; urban land surface temperature; urban morphology and surface characteristics; separated validation; data leakage; spatial cross-validation

@@FIG figures/fig0_study_overview.png | Fig. 0 | Study overview and graphical abstract. (a) The five protocol stages — data and spatial partition, discovery-side sandbox, freeze and hash, separated evaluation, and protocol audit — joined by the frozen product each stage hands to the next. (b) The three adversarial checks applied to the frozen candidates: conventional learners (Baseline B), external replication on Changchun 2021, and the constraint-and-firewall stress test (Baseline D). (c) The verdict, stated at the same weight as the positive primary endpoint: no new urban LST law is established; the reproducible contributions are methodological. The locked-region evaluation is reported under a documented protocol deviation; the Changchun replication and the Stage-05 adversarial benchmarks are post-hoc.

# 1. Introduction

*This section was written only after the discovery candidates had been frozen and evaluated (Stage 03–04). Deferring the literature review until after the freeze is deliberate: consulting prior work before selecting candidates anchors the search towards what is already published, which is exactly the hindsight the discovery–validation separation is meant to exclude. Citations below therefore position the work; they did not guide it. Numbers refer to `references_en.md`.*

## 1.1 Motivation

The surface energy balance of a city is set by the geometry of its buildings, its vegetation and its water, and the resulting land surface temperature (LST) is one of the most consequential and most measured variables in urban climatology [1]. Thermal remote sensing has made LST routinely available at the city scale, and a large literature now relates it to two-dimensional surface descriptors such as the vegetation index and the built-up index [2, 3]. Two-dimensional indices, however, cannot express the vertical structure that controls shading, radiative trapping and ventilation. Where three-dimensional form has been measured — through building height, volume and the sky-view factor — the thermal effect is consistently found to be nonlinear and, in places, dichotomous: the same increase in building height can warm a surface by trapping radiation and cool it by casting shade, and the sign depends on the local context [4].

This structure is what makes LST attractive as a target for automated discovery. The relationships are known to be nonlinear, plausibly interacting, and — because they are only partly formalised — still open to a structure-agnostic symbolic search. At the same time, it is exactly the kind of target on which a purely data-driven search is likely to overfit: the covariates are spatially autocorrelated, heavy-tailed and sometimes zero-inflated, and a flexible search will exploit any leak in the evaluation protocol. The central question of this study is therefore not "what drives LST in this city" but a methodological one: when an autonomous agent is asked to *discover* a relationship of this kind, what do the admissibility constraints and the separation of discovery from evaluation actually contribute, and can that contribution be separated from the agent's ability to fit the data?

## 1.2 Physics-constrained and knowledge-informed machine learning

Integrating prior knowledge into learning algorithms is now a well-developed field, and the ways of doing so have been mapped out in several reviews [5, 6, 7]. A widely used organising scheme distinguishes three routes by which physical knowledge enters a model: through the data, through the architecture as an inductive bias that makes certain physical properties true by construction, and through the loss function as a soft penalty on physically inconsistent solutions [6]. A complementary taxonomy classifies the same space along three questions — which type of knowledge is used, how it is represented, and where in the learning pipeline it is inserted [5]. The earliest and still most common formalisation is the physics-informed neural network, in which a partial-differential-equation residual is added to the training objective [8]; a stronger form imposes the constraint architecturally so that, for example, conservation laws hold exactly by construction rather than approximately by penalty [9]. In the Earth and environmental sciences the same ideas appear under the names of theory-guided data science [7] and physics-guided machine learning [10], and hybridisation is argued to have a regularising effect: physics discards implausible models and thereby promotes simpler, sparser structures that generalise better [11, 12].

Two observations motivate the present study. First, in this literature the constraints are almost always assumed to be beneficial, and they are evaluated by whether the constrained model performs better than its unconstrained counterpart. The complementary question — what the constraints cost, and on which data they earn their keep — is rarely asked, because the constraints are usually enforced inside a single training run rather than exposed as a variable that can be stressed and measured. Second, the reported gains are frequently obtained on the same data used to choose the model, and the distinction between fitting a physically plausible model and discovering a transferable one is easy to blur when the evaluation region has been seen. This study treats both as empirical questions. The admissibility constraints are implemented as an explicit hypothesis-space restriction — a curated operator pool, a pre-registered complexity cap, and a numerical-conditioning audit — and the whole constraint set is then stressed in an ablation. The evaluation withholds a region from the discovery process and freezes the candidates before any candidate-specific evaluation of that region; a post-hoc audit of the access history, reported here, found that this separation was not perfect in implementation.

## 1.3 Automated model discovery and symbolic regression

Automated search for interpretable expressions predates the current interest in language models. Evolutionary symbolic regression was shown to recover natural laws from experimental data nearly two decades ago [13], and sparse regression over a library of candidate terms recovers governing equations of dynamical systems from data [14]. More recent methods combine symbolic search with learned representations and with physics-inspired heuristics such as dimensional analysis and symmetry detection, and can recover the Feynman equations from sampled data [15, 16]. Benchmarking of contemporary methods shows that no single symbolic-regression algorithm dominates, and that performance is highly problem-dependent [17]. Alongside this, artificial intelligence is increasingly used across the whole scientific process rather than as a single fitting tool, from hypothesis generation to experiment design [18], which raises the question of what it means for such a system to produce *understanding* rather than merely accurate prediction [19].

The framework studied here belongs to this line but differs from a conventional symbolic-regression application in three ways. The search runs inside a sandbox that is restricted to the development data; every candidate must pass admissibility and falsification gates before it may be frozen; and the frozen candidates are evaluated on a region withheld from the search, under a protocol whose access history is written to an auditable log. The object of study is the pipeline, not just the expression it returns.

## 1.4 The validation problem

The evaluation hazards in this setting are well documented outside the machine-learning literature. Selecting a model on data and then reporting statistics on the same data is circular analysis, and it invalidates inference even when every individual step is legitimate [20]; the general phenomenon of information leaking from the test set into training has been formalised and catalogued [21]. Environmental data are spatially autocorrelated, so random cross-validation places near neighbours in both training and test folds and yields optimistically biased error estimates; spatially blocked cross-validation mitigates this [22] and can reveal models whose apparent skill is largely autocorrelation [23]. The critique is not unanimous — it has been argued that spatial cross-validation lacks a formal basis and that design-based inference from probability samples is preferable [24] — but the disagreement itself sharpens the requirement that any accuracy claim specify its evaluation design. The same logic motivates pre-registration, which separates predictions made in advance from explanations constructed afterwards [25].

The gap this paper addresses is not that guarding a held-out region is difficult, but that a validation architecture can be certified on paper and still fail in implementation. Controls that protect a withheld region — software state, keys, access histories and self-tests — must themselves be frozen, timestamped and independently auditable, and if they are not, the protection is a claim rather than a property. The present study builds such an architecture, audits it, and reports where the audit found the architecture to fall short of its own intention.

## 1.5 This study

The study is an end-to-end test of an auditable symbolic-search pipeline with physics-aware admissibility constraints on a single, well-documented problem: urban morphology and surface characteristics in relation to LST across the built-up area of Shenzhen, China. Its contributions are methodological, and one of them is deliberately negative (Fig. 0 gives the overall design).

(i) Discovery and evaluation are separated by construction and then audited. The region used for evaluation is withheld from the discovery sandbox, candidates are frozen and hashed before any candidate-specific evaluation, and every access is written to a hash-chained, append-only log (Fig. 1 gives the design). A post-hoc implementation audit of that log, reported here, found that the separation was not perfect in implementation: validation-side self-tests had decrypted the withheld region before the candidates were frozen. The paper reports this protocol deviation rather than the stronger, single-access claim it replaces.

(ii) Admissibility constraints are used as a search-space prior and then stressed in an exploratory, combined-pipeline ablation. Removing them improves the development metrics while lowering the locked-region score, and it lets the search populate the candidate set with expressions that the numerical-conditioning audit rejects outright. Because the ablated arm also changes the hypothesis space, the complexity cap and the search behaviour, the results are consistent with a regularising role for the constraints rather than a controlled single-factor demonstration.

(iii) The firewall is stressed as well. Allowing the agent to select on the locked region manufactures an apparent improvement of a third of a degree Celsius that vanishes on the development regions, and refitting the selected expression on all available data reduces the locked-region reading to a training error. The ablation illustrates one concrete failure mode the firewall prevented in this run (Fig. 6).

(iv) The discovered structure is tested for post-hoc replication on an independent city. An independent run of the same search, conducted post hoc, recovered a partial conceptual overlap — a nonlinear vegetation-cooling pivot, building warming and a vegetation–building interaction — while the specific frozen expression did not transfer: it could not be tested verbatim where Changchun lacks SVF and Road_Dens, and its expressible nonlinear components did not transfer quantitatively (Fig. 5). The external analysis is not scale-matched (Shenzhen is analysed at 100 m, Changchun at 500 m), so geographic transfer and the difference in spatial support cannot be fully separated. Consistently with (ii) and (iii), the honest conclusion is that the pipeline yields partial directional concordance and an audited negative methodological finding, not a portable quantitative law.

A validation architecture can be correct on paper and still fail in implementation. The contribution of this study is to have built such an architecture, to have subjected it to a post-hoc implementation audit, and to report that audit's negative finding about the architecture itself: trust in autonomous science depends on locking not only the data but the validator's software state and its access history before execution.

The remainder of the paper is organised as follows. Section 2 describes the data, the admissibility constraints, the separation of discovery from evaluation, and the discovery loop. Section 3 reports the discovery process and the candidate registry. Section 4 reports the locked-region evaluation of the frozen candidates. Section 5 reports the post-hoc external replication. Section 6 compares the candidate against conventional and ablated baselines. Section 7 discusses what the protocol did and did not establish, and Section 8 states its limitations.

# 2. Methods

*Auditable autonomous symbolic discovery of urban thermal relationships (PAID). Working draft, Stage 05. Numbers are those actually produced by the frozen pipeline (Stages 00–04) and the post-hoc Baseline B comparison (Stage 05); sources are listed under Data and code availability.*

## 2.1 Study area and analysis grid

The study covers the built-up area of Shenzhen, China (approximately 383 km² across seven districts). All variables were aggregated to a regular 100 m × 100 m grid (EPSG:32649), giving 32,748 grid cells, of which 31,760 entered the analysis after quality screening (relaxed mask: 32,246). The response variable is the grid-cell mean land surface temperature, LST_mean ( °C). LST is a radiometric surface temperature and is not interchangeable with near-surface air temperature or human thermal comfort; we therefore avoid the term surface urban heat island, since no strictly defined urban/non-urban reference is available.

One boundary caveat applies to that grid. It was generated by intersecting the 100 m lattice with the community-face layer supplied for the project (299 polygons), 18 of which carry truncated vertex arrays in the supplied copy (2–18 vertices each, while their area and perimeter attributes retain the original values). The grid therefore omits 3,259 cells (32.6 km²) of community area that lies inside the same bounding box, concentrated in those 18 communities, mainly in the Longhua, Bao'an and Longgang districts; cross-checking against the LST raster shows that 99.8% of those cells carry valid LST with a median of 38.9 °C, statistically indistinguishable from the 31,760 analysed cells (99.8%, 38.6 °C). Because the grid was frozen in Stage 01 and every partition, hash and validation result derives from it, the analysis is reported on the grid as delivered; the administrative study area (383 km²) is accordingly larger than the analysed footprint (327.5 km², of which 317.6 km² carries valid data).

Seven pre-specified covariates were used: NDVI_mean (vegetation), SVF_mean (sky view factor, 5 m source aggregated to 100 m), DEM_mean, Road_Dens, and three built-form metrics (X_BD, X_BH, X_VolDens). The analysis table (32,687 rows × 9 columns) was shown to be reproducible from the 0_论文data rasters by pixel-centre zonal means (agreement ≤ 0.01 at 98.66% of cells for LST). Several data-quality limitations are carried through the whole study and are stated in the Limitations: the DEM range is only 3–17 m and is not a credible Shenzhen elevation surface; the physical definitions of X_BD, X_BH and X_VolDens are unconfirmed by the data authors; and NDVI/road layers show non-physical values in the full-city rasters.

## 2.2 Admissibility constraints

Before any search, a set of computable constraints was frozen and released to the discovery agents; no information about the expected sign or functional form of any relationship was released. These are physics-aware admissibility constraints — dimensional consistency, numeric conditioning, geometric plausibility and measurement-boundary rules — not governing physical equations; they restrict the admissible hypothesis space rather than encode the LST process. The constraints include dimensional consistency (candidate expressions must be dimensionally consistent or non-dimensionalised), a numerical-conditioning gate (variables are standardised to O(1), and any term whose maximum absolute value on region A exceeds 10³ is rejected), a mass/geometric plausibility check on built-form terms, and an explicit prohibition on treating the 5 m SVF layer as a 5 m temperature observation. Full energy closure (Rn + QF = H + LE + G + S) is not computable from these data and was not attempted. The discovery stage applied seven physical-audit checks; four of them (PA3, PA4, PA5, PA7) are hard gates that determine the verdict, and the remaining three are informational.

## 2.3 Discovery–validation separation and spatial partition

To keep the evaluation data out of the search, the sample was split by connected k-means clustering of grid-cell centroids (k = 5, seed 20260924) into three regions:

- **A (discovery)** — 19,184 cells (67.7%): the region used for candidate selection.
- **B (development validation)** — 6,182 cells (21.8%): used for method screening and robustness; because it participates in development, it is not treated as independent confirmation.
- **C (withheld evaluation region)** — 2,987 cells (10.5%): the target values were encrypted (AES-256-GCM) and were to be released only for a candidate-specific evaluation after candidates were frozen. A further 3,407 cells form a one-cell-width spatial buffer (R = 15 cells ≈ 1.5 km) between C and the discovery regions (Fig. 1).

@@FIG figures/fig1_protocol_split.png | Fig. 1 | Design of the discovery–validation firewall. The built-up area of Shenzhen partitioned at 100 m cells into region A (discovery, 19,184 cells), region B (development validation, 6,182), the locked region C (2,987) and a one-cell-width buffer (R = 15 cells ≈ 1.5 km, 3,407 cells); each 100 m cell is drawn as one square, and the 988 out-of-scope / no-data cells form a named neutral class (isolated pockets below a four-cell minimum mapping unit are merged into the surrounding region for legibility) carrying no data. Administrative district boundaries inside the study area follow the authors’ community-face polygons and are drawn as vector lines over the cell mosaic; the inset locates the study footprint within Shenzhen’s nine districts. The partition is the connected-k-means split (k = 5, seed 20260924). Design only; no analysis is shown.

Which region each agent could read, and which data entered each decision, are recovered from the Stage 02 access log and guard code rather than assumed: the runtime guard is enforced at the sandbox level (file visibility), and the per-role permissions and actual use are reported from that log (Section 2.4). The audit of that log, reported in Section 4 and the Discussion, found that the withheld region was decrypted by validation-side self-tests before candidate freeze — a documented protocol deviation from the intended single-access design. Region C is accordingly described here as a withheld evaluation region, not as a pristine untouched holdout.

The block size R = 15 was derived before the search from a distance-dependent autocorrelation analysis of the LST field on the frozen grid. LST was detrended with a third-order two-dimensional polynomial (R² = 0.4348; residual SD = 3.3093 °C), and the residual correlogram was evaluated as a function of lag. The block size was set to the largest lag at which residual dependence becomes negligible, taken as the point where the absolute lag correlation falls below 0.20, evaluated separately along the row, column and diagonal directions within two NDVI strata (low vegetation gave 15 cells, medium vegetation 11), and taking the conservative maximum across strata and directions; the value was then rounded to the nearest five cells, giving R = 15 (≈ 1.5 km). Two preregistered alternatives were also recorded: a threshold of 1/e gives R = 10, and a threshold of 0.10 gives R = 25. Because R = 25 changes the primary inference from p = 0.005 to p = 0.085 (Section 4.5), the choice of R is a load-bearing parameter of Protocol V1.

All locked-target artefacts, the partition, the endpoints and the analysis budget were frozen with SHA-256 manifests before the search began; any later modification would constitute a new pre-registration. The protocol intended a single candidate-specific evaluation per candidate; the audit reported below establishes that this intent was not fully realised in implementation.

## 2.4 Agent roles and permissions

Five agent roles were implemented. A Discovery agent proposes features, scales, hypotheses and mathematical expressions using only region A. An Experiment agent writes code, runs the permitted methods and measures development performance. A Falsification agent searches for counterexamples, spatial confounding, spurious correlation and negative controls. A Physics Auditor independently audits dimensional, geometric and computable physical constraints. An Independent Validator runs as a separate process outside the sandbox, holds the withheld targets, and publishes complete pass/fail results without acting on discovery-side parameter requests.

Runtime enforcement used an audit-hook access guard with a write allowlist and hard deny-prefixes, inode-identity checks (to defeat hard-links and renamed copies), and a read allowlist. The allowlist governs file visibility at the sandbox level; the per-role read permissions and what each agent actually used are recorded in the Stage 02 access log. Every action was written to a hash-chained, append-only log (1,259 entries after Stage 04), and the log's integrity was verified by recomputing the chain. The access log is the basis of the post-hoc implementation audit reported in Section 4.

## 2.5 Autonomous discovery loop

Discovery proceeded in three rounds under a frozen budget of 5,000 model fits (3,151 used). Round 1 tested 12 pre-registered hypotheses (H01–H09 families, including the linear baseline). Round 2 ran a full-pool greedy symbolic search over the frozen operator set, producing a high-complexity candidate (S03-H10-GREEDY, expression complexity 14) and its parsimony prefix (S03-H10P-GREEDY-MIN, complexity 6). Round 3 applied local hill-climbing refinement (S03-H11-REFINE, complexity 15). Candidate expressions were represented as small abstract-syntax trees over {var, const, add, sub, mul, div, neg, inv, log, exp}, with a maximum allowed complexity of 15. The development metric was the region-A spatial-block cross-validated RMSE, computed on connected folds (k = 5, seed 20260924) with per-fold standardisation by the training-fold mean and standard deviation.

Fifteen candidates were evaluated. Four were frozen: three discovery candidates and one placebo (S03-H01-LIN7, which is identical to Baseline A). The frozen selection, including the placebo, was registered before any candidate-specific evaluation.

## 2.6 Evaluation protocol

The frozen primary endpoint required all five of the following to hold on region C:

1. ΔRMSE > 0, where ΔRMSE = RMSE_C(Baseline A) − RMSE_C(candidate) and Baseline A is the OLS model on the seven covariates fitted on region A only;
2. a permutation p-value < 0.05 from 199 spatial-block permutations that permute the block-mean values while preserving within-block residuals;
3. a 95% confidence interval for ΔRMSE, from 1,000 spatial-block bootstrap resamples, that excludes zero;
4. a physics audit pass; and
5. negative controls not fooled.

Because Baseline A is fitted on region A only, it is a deliberately frozen, but not necessarily strong, comparator on region C; ΔRMSE > 0 measures improvement over that specific baseline, not over all reasonable predictors. (The comparative behaviour of Baseline A on region C is a result, reported in Sections 4.5 and 7.1.)

The permutation p-value is computed as p = (1 + #{null ≥ observed}) / (1 + B) with B = 199 spatial-block permutations. With this budget the smallest attainable value is 1 / (1 + 199) = 0.005; the reported p = 0.005 therefore means "significant at the resolution of the permutation budget", not a precise magnitude far below the 0.05 threshold.

Conditions 4 and 5 are recomputed independently inside the validator process (the hard gates PA3/PA4/PA5/PA7 on region A and controls NC1–NC3 on region B); no self-reported verdict from the discovery side is accepted. The validator also asserts that the permutation is not the identity (observed correlation between true and permuted targets = 0.402, well below the 0.9 refusal threshold).

Region C was excluded from discovery-side roles: we found no evidence that Region C entered the programmatic candidate-generation or selection process, which used region-A cross-validation, with region B serving only as a development falsification gate. Region C was, however, decrypted before candidate freeze by validation-side self-tests in Stage 02, and a post-hoc implementation audit of the access log identified this as a documented protocol deviation from the intended single-access design. Stage 04 is therefore reported as a Region-C evaluation of a frozen candidate under a documented protocol deviation. The candidate was generated and selected without programmatic access to Region C, but Region C was not an untouched holdout because validation-side self-tests accessed it before candidate freeze.

Multiplicity was controlled by Holm–Bonferroni over the frozen candidate family (m = 4). Secondary analyses comprised NDVI-tercile stratification, target measurement-error sensitivity (±0.5 K and ±1.0 K Gaussian perturbation, 20 draws each), and a criterion-sensitivity test that re-drew region C with a more conservative contiguity parameter (R = 25 cells). No imputation was performed in region C.

## 2.7 Baseline models

Baselines were compared on identical data, identical folds and identical metrics, as required for a fair comparison.

**Baseline A** is the frozen OLS model on the seven covariates (region-A spatial-block CV RMSE = 3.1577 °C). Baseline A is the pre-registered comparator; meeting the primary endpoint means improving on this specific baseline, not outperforming all reasonable predictors. (Its comparative behaviour on region C is a result, reported in Sections 4.5 and 7.1.)

**Baseline B** comprises a random forest and a gradient-boosted regressor on the same seven covariates. Because the execution environment provides no scikit-learn, XGBoost or SciPy and has no network access, both learners were implemented from scratch in NumPy (CART regression trees with variance-reduction splits; bagging with feature subsampling for the forest; squared-loss boosting with depth-4 trees and learning rate 0.05 for the boosted model). Trees are invariant to monotone rescaling of individual features, so no standardisation was applied. A second forest used an augmented feature set (the seven covariates plus the engineered transforms used by the strongest candidate). A negative control repeated the forest fit with the region-A targets randomly permuted. Hyperparameters were fixed before evaluation (forest: 300 trees, max depth 12, min leaf 10, mtry = 3; boosting: 300 rounds, depth 4, learning rate 0.05; seed 20260924).

## 2.8 Post-hoc analyses

Because region C was evaluated before Stage 05, all region-C numbers reported for the baselines and for the post-hoc expression analyses are exploratory and are labelled as such; they do not constitute new confirmatory tests. The expression review examined the DEM dependence of the leading candidate by re-fitting ablated variants on region A and re-scoring them on B and C.

## 2.9 Reproducibility

Each stage writes a SHA-256 manifest of its products, and each stage script is deterministic given the frozen seeds. The discovery–validation chain can be re-executed end to end from the frozen split; Stage 03 verification reproduces all four frozen candidate hashes, and Stage 04 verification re-derived the published statistic bit-for-bit against a second, independently written implementation at run time. Region C is scientifically spent under Protocol V1: the reported statistic can be recomputed in software from the frozen artefacts, but C cannot be reused for hypothesis selection, revision, refitting or reconfirmation. The Stage 05 Baseline B pipeline is checkpointed and its random seeds are fixed.

## Data and code availability

Raw rasters and the analysis table are the author-provided Shenzhen dataset. All analysis code, frozen manifests, encrypted-vault metadata, stage reports and the validation-side audit artefacts are organised under `PAID/` (Stages 00–05). Stage 05 products: `stage05_paper/reports/baselineB.json`, `stage05_paper/reports/BASELINE_B.md`, `stage05_paper/figures/` and `stage05_paper/scripts/`. The reproducibility package includes the experiment log, the stage manifests and validator versions, the post-hoc implementation audit report, and the documented protocol deviation identified by that audit.

# 3. Results 1 — The discovery process

*Every number in this section is a region-A development metric unless stated otherwise. Region A is the region the search selected on, so these values carry selection bias and are optimistic; the candidate-specific evaluation is reported in Results 2. Region C was excluded from the discovery search and was not reachable from the discovery sandbox.*

## 3.1 Search scope, budget and the frozen dev metric

The discovery agent ran inside the Stage 02 access guard with only two regions visible at the sandbox level: the discovery region A (19,184 cells) and the development-validation region B (6,182 cells). Region C was not reachable from the sandbox; the guard recorded 965 opens and 0 denials for the whole run, and the search used 3,151 of the frozen 5,000-fit budget. No candidate could be registered or edited by the discovery side: the registry and reports sit outside the sandbox and are written only by the freeze step.

The development metric was fixed in Stage 01: connected spatial-block cross-validation on region A, with k = 5 blocks (sizes 2,544 / 5,143 / 3,713 / 4,096 / 3,688, seed 20260924) and pooled out-of-fold RMSE in °C. Variables are standardised on the training fold inside each fit, so no cross-fold leakage enters the metric. Complexity is counted as the number of expression-tree nodes plus the number of terms, capped at 15.

Baseline A is the frozen ordinary-least-squares model on the seven covariates (`NDVI_mean`, `DEM_mean`, `SVF_mean`, `Road_Dens`, `X_BD`, `X_BH`, `X_VolDens`), fitted on region A only. Its region-A cross-validated RMSE is 3.1577 °C. This value is the reference against which every candidate is scored, and it is also the placebo in the validation stage (Section 4.1).

## 3.2 Three rounds of autonomous exploration

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

@@FIG figures/fig3_search.png | Fig. 3 | The greedy search improves the development metric with diminishing returns. (a) Region-A cross-validated RMSE against the number of terms, with the Baseline A reference and staggered term labels. (b) All fifteen candidates, complexity against region-A CV RMSE, coloured by status; one off-scale marker denotes the A-CV = 23.2 outlier. Region-A CV is the selection metric, not a generalisation estimate.

**Round 3 — local refinement.** From the best round-2 expression, single-step hill-climbing (add / swap / drop) accepted the change that reduced CV RMSE the most.

| Action | Position | Term | Terms | A-CV RMSE (°C) | Expression |
|---|---|---|---|---|---|
| replace | 1 | `DEM` | 5 | 2.9166 | `exp(NDVI) + DEM + SVF + Road_Dens + (NDVI*DEM)` |
| replace | 2 | `NDVI²` | 5 | 2.9139 | `exp(NDVI) + DEM + (NDVI*NDVI) + Road_Dens + (NDVI*DEM)` |

## 3.3 The candidate registry

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

## 3.4 Physics audit and numerical conditioning

Each candidate passed a seven-check audit, but the checks differ in strength and we do not present them as a uniform gate. Four are hard gates that can reject a candidate: energy-closure / causal over-reach (PA3), no directional presupposition (PA4), measurement boundary (PA5), and numerical conditioning and term scale (PA7). Three are informational and cannot reject: dimensional consistency (PA1 — every variable is standardised, so all terms are dimensionless by construction), geometric legality (PA2 — flags the unresolved `X_BD` / `X_BH` / `DEM` definitions for author clarification), and statistical-integrity fields (PA6 — always written by the experiment agent).

Both rejections came from the conditioning gate PA7. `S03-H07-VEGBLD-RATIO` carries the ratio term `NDVI/X_BD`, whose maximum absolute value on region A is 4,932; `S03-H09-EXP-BUILD` carries `exp(X_BD)`, whose maximum is 53,363. With inputs standardised to O(1), a term spanning three orders of magnitude removes any interpretation from a single linear coefficient, and per-fold re-standardisation amplifies it into extrapolation. The root cause is structural: `Road_Dens` (77% zeros) and `X_BD`, `X_BH`, `X_VolDens` (heavy-tailed) are strongly zero-inflated, so ratio and exponential forms of them explode at small region-A standard deviations. This is a systematic risk imposed by the data distribution, not an incidental search error, and it is the audit layer's job to intercept it.

## 3.5 Falsification and negative controls

Two kinds of check were run, of deliberately different strength. The floor controls (NC1, per-cell target shuffling; NC2, spatial-block permutation of block means; NC3, Gaussian random targets) have weak discriminating power: they destroy all structure, so their RMSE is close to the target standard deviation and any model with more skill than the constant mean passes. They can exclude zero-skill models but cannot detect overfitting. Every audit-passing candidate is recorded as not fooled by these controls.

The more discriminating check is a region-B spatial-block permutation of the block means, which yields a permutation p-value for ΔB; because region B participated in method screening, this remains a development reference rather than a confirmatory test. Under it, `S03-H10-GREEDY` (p = 0.005) and `S03-H11-REFINE` (p = 0.005) are the only candidates whose region-B improvement is significant, while the parsimony candidate `S03-H10P-GREEDY-MIN` is not (ΔB = −0.3412, p = 0.175).

One implementation defect in this layer is worth recording because it is instructive: the block permutation was initially written to permute the block *index order* and then resolve values by label, which returned each block its own value and reduced the permutation to the identity (measured correlation 1.000). The same construct had also entered the Stage 02 validator, where it would have forced the permutation p-value to 1.0 and made the primary endpoint impossible to pass — a false-negative-only defect. It was found during Stage 03 verification and fixed by permuting the block-mean *values*; the corrected region-B correlation is 0.086 and the permutation test recovers its discriminating power. An implementation audit later found that the access log cannot establish that this fix predated the first Region-C access, so the timing of the fix relative to that access is recorded as unresolved rather than asserted (see Section 4 and the Discussion).

## 3.6 Frozen candidates

The preregistered selection rule froze every candidate with `status = passed_dev_gain` (audit passed, not fooled, A-CV better than Baseline A), taking the eight best by A-CV, plus the Baseline A specification itself as a placebo reference. In this run four were frozen, below the cap of eight.

| ID | Role | Expression | Cx | A-CV | ΔA | ΔB | canon_hash |
|---|---|---|---|---|---|---|---|
| `S03-H11-REFINE` | discovery | `exp(NDVI) + DEM + (NDVI*NDVI) + Road_Dens + (NDVI*DEM)` | 15 | 2.9139 | +0.2438 | +0.0997 | `629ed98b060d…` |
| `S03-H10-GREEDY` | discovery | `exp(NDVI) + exp(DEM) + SVF + Road_Dens + (NDVI*DEM)` | 14 | 2.9560 | +0.2016 | +0.1222 | `171554145102…` |
| `S03-H10P-GREEDY-MIN` | discovery | `exp(NDVI) + exp(DEM)` | 6 | 3.0655 | +0.0921 | −0.3412 | `5e8bcc5de6d8…` |
| `S03-H01-LIN7` | placebo | `NDVI + DEM + SVF + Road_Dens + X_BD + X_BH + X_VolDens` | 14 | 3.1577 | +0.0000 | +0.0000 | `7a7e172b70cb…` |

For each discovery candidate the registry records an unpresupposed effect direction from a ±1 standard-deviation finite difference: `S03-H10-GREEDY` gives DEM +1.95, NDVI −4.49, Road_Dens +0.80 and SVF −1.57 °C per SD; `S03-H11-REFINE` gives DEM +2.54, NDVI −4.92 and Road_Dens +0.48 °C per SD. The negative NDVI direction is the vegetation-cooling sign. The 95% spatial-block bootstrap confidence intervals on the region-A CV RMSE are [2.5263, 3.0093] for `S03-H10-GREEDY` and [2.5126, 2.9175] for `S03-H11-REFINE`, and the residual Moran's I is 0.79 and 0.77 respectively — i.e. spatial autocorrelation is not removed, so the block CV likely understates the true uncertainty.

## 3.7 Marginal returns, selection bias and robustness

The gain from added complexity is small. Moving from the two-term model to the five-term refinement lowers the region-A CV RMSE only from 3.0655 to 2.9139 °C (0.152 °C; Fig. 3). Most of the explanatory power is concentrated in the first one or two terms, both built on a non-linear transform of NDVI with a negative direction, consistent with vegetation cooling; more elaborate structure earns little on the development set.

The three frozen discovery candidates differ in how well they generalise to region B. `S03-H10-GREEDY` improves on both region A (ΔA = +0.2016) and region B (ΔB = +0.1222); `S03-H11-REFINE` has the largest region-A gain but a slightly smaller region-B gain (ΔB = +0.0997) and sits at the complexity cap; `S03-H10P-GREEDY-MIN` is the simplest but worsens region B (ΔB = −0.3412), suggesting its region-A gain is largely noise.

A read-only A/B robustness battery, run before the candidate-specific evaluation and touching no region-C data, shows that the region-A gains are stable to the fold seed (four seeds) and to the block granularity (k = 5, 8, 12), and remain positive under ±0.5 K and ±1.0 K target noise in every draw. That only shows stability: because baseline and candidate see the same perturbed targets, the noise test is not a significance test. The discriminating quantity is the region-A-only inference, where `S03-H10-GREEDY` and `S03-H11-REFINE` have confidence intervals excluding zero and permutation p = 0.005, while `S03-H10P-GREEDY-MIN` has a confidence interval including zero (p = 0.335) — corroborating its negative ΔB and indicating its evaluation budget should not be spent. The preregistered freeze rule was not changed after seeing this.

## 3.8 Determinism

The whole discovery run is deterministic under the frozen seeds. A deterministic re-run performed after correcting a cross-stage side effect (a Stage 02 clean-room step that had also wiped the shared discovery work tree) reproduced all fifteen candidates and their cross-validation values identically, and reproduced all four frozen `canon_hash` values verbatim. Rebuilt files differ from the first run only in their `ran_at` timestamp, which enters the file hash but not any candidate's content.

# 4. Results 2 — Locked-region evaluation of frozen candidates

*All numbers below come from the Stage 04 candidate-specific evaluation of the frozen candidates. The evaluation was produced by a validator process running outside the discovery sandbox. Region C is scientifically spent under Protocol V1: the reported statistic can be recomputed in software from the frozen artefacts, but C cannot be reused for hypothesis selection, revision, refitting or reconfirmation.*

## 4.1 Evaluation scope

Two of the four frozen candidates were evaluated under the conservative scope approved before the event: the leading discovery candidate `S03-H10-GREEDY` and the placebo reference `S03-H01-LIN7`. The placebo is identical to Baseline A, so its true ΔRMSE on any region is zero by construction; it exists to test whether the evaluation service discriminates, or simply passes whatever it is given. The remaining two frozen candidates (`S03-H11-REFINE`, `S03-H10P-GREEDY-MIN`) were not evaluated and retain their evaluation budget.

## 4.2 Primary endpoint

Baseline A is the frozen OLS model on the seven covariates fitted on region A only (region-A spatial-block CV RMSE = 3.1577 °C). On the 2,987 locked cells, Baseline A has RMSE 2.8415 °C.

| Candidate | Role | RMSE_C (Baseline A) | RMSE_C (candidate) | ΔRMSE | perm. p | 95% CI | Verdict |
|---|---|---|---|---|---|---|---|
| `S03-H10-GREEDY` | discovery | 2.8415 | 2.4624 | **+0.3791** | 0.005 | [0.2761, 0.4814] | Pass |
| `S03-H01-LIN7` | placebo | 2.8415 | 2.8415 | +0.0000 | 1.000 | [0.0000, 0.0000] | Fail (as expected) |

The primary endpoint required all five of ΔRMSE > 0, permutation p < 0.05, a 95% CI excluding zero, a physics-audit pass, and negative controls not fooled. `S03-H10-GREEDY` satisfied all five conditions. `S03-H01-LIN7` failed the first three and was correctly rejected. This endpoint is not reported here as a pristine confirmatory test: because the withheld region had been decrypted before candidate freeze (Section 2.6, and the protocol audit below), this stage is a locked-region evaluation of a frozen candidate under a documented protocol deviation.

Two of the five conditions (the physics audit and the negative controls) are recomputed independently inside the validator process rather than read from the discovery side's own JSON. For `S03-H10-GREEDY` the recomputed audit passes (maximum standardised term magnitude 8.71, well below the conditioning threshold of 10³) and the recomputed negative controls are not fooled. The validator reproduced the primary statistic bit-for-bit against a second, independently written implementation (ΔRMSE agreement < 10⁻⁹).

The placebo outcome is the central methodological result of the stage. Because the placebo is exactly the baseline, any evaluation service that passed it would be unable to distinguish a real improvement from a null one. The service rejected it on the three quantitative conditions while passing both models on the audit and control conditions, which isolates the rejection to the effect size rather than to a mechanical failure.

@@FIG figures/fig2_baselineB.png | Fig. 2 | The candidate does not beat a conventional learner on the locked region. (a) Locked-region ΔRMSE against Baseline A with 95% spatial-block bootstrap confidence intervals, sorted. (b) Region-A CV, B and C RMSE trajectories, showing the inversion: the candidate leads on the selection region and is overtaken on the locked region (C, post-hoc).

## 4.3 Protocol audit of Region-C access

A post-hoc implementation audit of the Stage 02 access log and guard code examined whether the withheld region influenced the study before the candidate-specific evaluation. The audit established the following facts. The discovery sandbox exposed only regions A and B; the access log records no discovery-side read of Region C, and candidate generation, fitting and ranking used region-A cross-validation with region B as a development falsification gate. Region C was decrypted by validation-side self-tests in Stage 02, before the Stage 03 candidate freeze, and the first such decryption precedes the freeze in the log sequence. The withheld region was decrypted repeatedly, not once, across those self-tests and the Stage 04 evaluation. The audit could not establish, from the log and manifests alone, whether the later modification of the validator's own verdict logic preceded or followed the first decryption, because that code change is not represented in the hash chain and the two timestamp sources available disagree by about three days. We found no evidence of programmatic candidate-selection contamination, but the early validation-side access invalidates the stronger claim of a pristine untouched holdout.

## 4.4 Multiplicity

Multiplicity was controlled by Holm–Bonferroni over the pre-registered frozen family (m = 4: three discovery candidates and one placebo). This family is more conservative than the two candidates actually evaluated, because it counts the two candidates whose evaluation budget remains unspent.

| Candidate | Uncorrected p | Holm threshold | Reject null |
|---|---|---|---|
| `S03-H10-GREEDY` | 0.005 | 0.0125 | Yes |
| `S03-H01-LIN7` | 1.000 | 1.000 | No |

The leading candidate remains significant after correction.

## 4.5 Stratification, measurement error and uncertainty

**NDVI strata.** Using global tercile thresholds on region A (0.381 and 0.684), the locked region splits into 1,008 low-, 1,637 mid- and 342 high-vegetation cells. The candidate's ΔRMSE is positive in all three strata, and every stratum's 95% CI excludes zero (Table below). No stratum reverses sign, so the aggregate effect is not the product of one dominant cover type.

| Stratum | n | RMSE (Baseline A) | RMSE (candidate) | ΔRMSE | 95% CI |
|---|---|---|---|---|---|
| Low vegetation | 1,008 | 3.4002 | 3.1629 | +0.2373 | [0.1113, 0.3689] |
| Mid vegetation | 1,637 | 2.5638 | 2.0589 | +0.5049 | [0.3498, 0.6438] |
| High vegetation | 342 | 2.2317 | 1.7841 | +0.4475 | [0.2756, 0.6221] |

**Measurement error.** Perturbing the locked targets with independent Gaussian noise of ±0.5 K and ±1.0 K (20 draws each) leaves ΔRMSE positive in every draw, with p < 0.05 in all draws and an effect size far larger than the perturbation interval width (mean ΔRMSE +0.3718, width 0.0121 at ±0.5 K; mean +0.3535, width 0.0272 at ±1.0 K). This shows stability under measurement error; it is not itself a significance test, since the baseline and the candidate see the same perturbed targets.

## 4.6 The result is criterion-sensitive and rests on a weak baseline

Two secondary findings materially limit the interpretation, and both are reported alongside the positive primary endpoint.

**Criterion sensitivity.** Stage 01 pre-registered a more conservative contiguity parameter, R = 25 cells (2.5 km), as a robustness check. Re-drawing the locked region with R = 25 reduces it to 791 cells; the effect shrinks to ΔRMSE = +0.1375 °C with permutation p = 0.085. The sign is unchanged, but the effect is no longer significant. The primary result therefore depends on the spatial criterion used to define the locked region.

**Baseline weakness.** Baseline A transfers poorly to region C. The constant predictor (region-A mean LST) achieves RMSE 2.6028 °C on region C, and a pseudo-candidate fitted on row-shuffled region-A targets achieves 2.6151 °C; both beat Baseline A's 2.8415 °C. Part of ΔRMSE > 0 therefore reflects a weak comparator rather than a strong candidate. The candidate (2.4624 °C) does beat the constant floor, so its gain is not mere shrinkage to the mean, but that comparison was not the pre-registered endpoint.

@@FIG figures/fig4_validation.png | Fig. 4 | The locked-region improvement is positive under the primary specification but criterion-sensitive and comparator-dependent. (a) ΔRMSE across specifications — the primary endpoint, the conservative R = 25 criterion, three NDVI strata, and ±0.5 K and ±1.0 K target-noise draws — with confidence intervals where available. (b) Reference ladder placing the candidate against the constant floor and a row-shuffled pseudo-candidate. Both reservations, the R = 25 criterion and the weak comparator, are shown explicitly.

## 4.7 Expression review: the effect does not depend on DEM

The leading candidate uses `exp(NDVI)`, `exp(DEM)`, `SVF`, `Road_Dens` and an interaction `NDVI×DEM`. Because the DEM layer is not a credible elevation surface (region-A range 3–17 m), the DEM terms were examined by re-fitting ablated variants on region A and rescoring them (post-hoc) on region C.

| Variant | Complexity | ΔA-CV | ΔB | ΔC (post-hoc) | C p |
|---|---|---|---|---|---|
| full (`S03-H10-GREEDY`) | 14 | +0.2016 | +0.1222 | +0.3791 | 0.005 |
| no DEM terms | 7 | −0.1038 | +0.0802 | **+0.4326** | 0.005 |
| drop `exp(DEM)` | 11 | −0.0280 | −0.2602 | **+0.4451** | 0.005 |
| DEM terms only | 7 | −1.0141 | −3.1843 | −0.6150 | 1.000 |
| drop `exp(NDVI)` | 11 | −0.4344 | −1.0427 | **−0.1074** | 1.000 |

Removing the DEM terms does not reduce the locked-region gain; it slightly increases it. Removing the `exp(NDVI)` term instead destroys the gain on all three regions (ΔC = −0.1074, p = 1.000, CI includes zero). The DEM terms are additionally a smooth spatial field rather than terrain: an OLS of DEM on `[row, col, row², col²]` gives R² = 0.781 on region A. The interpretable content of the candidate is therefore carried by `exp(NDVI)`, and the DEM terms behave as a selection-region artefact. A DEM-free reduced model (`exp(NDVI)`, `SVF`, `Road_Dens`; complexity 7) achieves ΔC = +0.4326 at p = 0.005.

## 4.8 Evaluation registry

The evaluation is not repeatable. `S03-H10-GREEDY` and `S03-H01-LIN7` now each have `validation_runs = 1`; `S03-H11-REFINE` and `S03-H10P-GREEDY-MIN` remain at 0. The change to the frozen registry is confined to the two evaluated candidates, and the candidate definitions themselves are unchanged (verified by re-computing their canonical hashes).

The primary endpoint was met by one candidate, with two material caveats (criterion sensitivity and a weak comparator). The interpretation is taken up in the Discussion, where a further fair-comparison result sharpens it.

# 5. Results 3 — Post-hoc partial replication on an independent city (Changchun, 2021)

*Replication was carried out post hoc on a spatially disjoint dataset from a second Chinese city (Changchun, 2021); the analysis was conducted post hoc and is a partial external replication, not a prospective confirmation. The frozen candidate was not re-selected here: the expression structure is held fixed and only its coefficients are refit, so every number below is an out-of-sample transfer test rather than a new discovery. Because the two cities share only a subset of covariates, the replication is deliberately partial, and the gaps are reported alongside the agreements.*

## 5.1 External data and harmonisation

The replication dataset is a 500 m fishnet for Changchun (2021) with 100,676 cells, carrying `LST_mean`, `NDVI_mean`, `DEM_mean` and three building variables (`BD`, `BVD`, `Height_mean`) that we mapped one-to-one onto the Shenzhen schema `X_BD`, `X_VolDens` and `X_BH`. After excluding 29 cells with non-finite LST, covariate or coordinate values, 100,647 cells are used. The target has mean 26.68 °C, sd 1.62 °C and range [11.2, 43.1] °C; absolute temperature is not comparable to Shenzhen because the climatic and observational contexts are not harmonised (incomplete Shenzhen acquisition metadata prevent temporal or seasonal comparability), so all comparisons are made within-city, on the same folds.

Two covariates of the Shenzhen schema, `SVF_mean` (sky-view factor) and `Road_Dens`, do not exist in Changchun. The frozen expression `exp(NDVI) + exp(DEM) + SVF + Road_Dens + (NDVI·DEM)` therefore cannot be reproduced verbatim; only its expressible projections — those built from the five shared variables — can be tested. We report this as a structural limitation, not as a result.

The external analysis is not a scale-matched replication: Shenzhen is analysed at 100 m and Changchun at 500 m, so geographic transfer and the difference in spatial support (aggregation and the modifiable areal unit problem) cannot be fully separated. The search algorithm and operator grammar are the same where the method is re-run, but the available feature space is not, for the reason above.

Spatial folds follow the same connected k-means rule on row/col coordinates (k = 5, seed 20260924), giving fold sizes [21256, 22027, 19386, 18823, 19155]. A matched linear baseline (**Baseline A\***, OLS on the five available covariates) provides the within-city reference: **A\*-CV RMSE = 1.2292 °C**.

## 5.2 Transfer of the frozen form

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

## 5.3 The NDVI pivot reproduces; the DEM term does not

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

## 5.4 Independent re-discovery on the new city

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

## 5.5 Direct coefficient transfer is not meaningful

Transferring coefficients across cities fails for a structural reason: the covariate ranges barely overlap. Shenzhen's mean DEM is 11.1 m, while Changchun's DEM lies in [129, 622] m, so the two distributions are almost disjoint. Under direct transfer, `exp(NDVI)` retains only weak rank agreement (Pearson r = 0.256, Spearman ρ = 0.388, affine-recalibrated RMSE = 1.569); the `H10P` form scores ρ = 0.204 with an affine-recalibrated RMSE of 26.6 °C, a degenerate result caused by `exp()` extrapolating far outside its fitted range. Only the *shape* of the NDVI term survives cross-city transfer, and only weakly.

## 5.6 Summary

The external replication is **partial, and partial in an informative way**, and it was conducted post hoc. An independent post-hoc run on the second city recovered a nonlinear NDVI effect plus a vegetation×building interaction, with building terms entering warming — a partial conceptual overlap with the Shenzhen picture, not a verbatim replication. The *specific* frozen form does not transfer: `exp(NDVI)` yields only a small gain, `exp(DEM)` is unstable and unhelpful, DEM drops out, and SVF/Road_Dens are unavailable, so the frozen form can only be tested on its expressible projections. The two covariates that cannot be tested are exactly the two the frozen form depends on most, which is itself part of the result. Taken with Results 2 and 4, the replication reinforces the standing conclusion of the manuscript: the pipeline yields only **partial cross-city directional concordance, not replication of a transferable quantitative structure**.

@@FIG figures/fig5_external.png | Fig. 5 | Post-hoc partial external replication on Changchun 2021. Shenzhen is analysed at 100 m and Changchun at 500 m, so this is not a scale-matched replication. (a) Δ CV RMSE against the matched linear baseline A* for the frozen-form projections. (b) Single-variable pivot test: linear, quadratic and exponential NDVI, and exp(DEM). (c) Signed direction per shared covariate, with DEM flagged as non-reproducing. Changchun is external, post-hoc data; partial agreement is not confirmation.

# 6. Results 4 — Fair comparison with conventional models

*The comparison uses the same data, the same frozen spatial folds and the same metric for every model. Region C was already evaluated in Stage 04, so all region-C numbers here are post-hoc and exploratory; they do not constitute new confirmatory tests.*

## 6.1 Compared models

The framework defines four baselines. All four are reported here: **Baseline A**, the frozen OLS model on the seven covariates; **Baseline B**, a post-hoc adversarial benchmark comprising a random forest and a gradient-boosted regressor on the same seven covariates; **Baseline C**, the symbolic-regression search over the preset operator space, which is the search that produced the candidates themselves; and **Baseline D**, an exploratory combined-pipeline stress test — an autonomous agent with the same base model and tool whitelist but with the admissibility constraints and the firewall removed. Baseline D is an ablation rather than a predictor and is reported separately in §6.6.

Baseline B was implemented from scratch in NumPy (CART regression trees with variance-reduction splits; a bagged forest and a squared-loss boosted model) because the execution environment provides no scikit-learn, XGBoost or SciPy and has no network access. Hyperparameters were fixed before evaluation: forest of 300 trees (max depth 12, minimum leaf size 10, three features per split), boosting with 300 rounds (depth 4, learning rate 0.05), seed 20260924. Tree models are invariant to monotone rescaling of individual features, so no standardisation was applied. An augmented forest added the engineered transforms used by the strongest candidate (`exp(NDVI)`, `exp(DEM)`, `NDVI×DEM`) to the seven covariates.

## 6.2 Region-A development metric and validation regions

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

## 6.3 The comparison inverts between selection and validation

On the region-A development metric, the candidate is the best model: `S03-H10-GREEDY` has the lowest A-CV RMSE (2.9560), followed by the random forest (2.9867), Baseline A (3.1577) and the DEM-free reduced model (3.2614). This is expected, because the candidate was selected by minimising a metric of exactly this type on region A.

On the locked region C the ordering inverts. Both Baseline B models outperform the candidate by roughly a factor of two in ΔRMSE: the random forest reaches RMSE 2.0950 °C (ΔRMSE +0.7465) and the boosted model 2.0915 °C (ΔRMSE +0.7500), against the candidate's 2.4624 °C (ΔRMSE +0.3791). All are significant at p = 0.005, so the difference between them is not a matter of significance but of magnitude (Fig. 2). The augmented forest, which is given the candidate's own engineered features, is not better than the plain forest (ΔRMSE +0.7191), so the gap is not explained by a missing transform.

The random forest also beats the constant floor by a wide margin on region C (2.0950 versus 2.6028) whereas the candidate beats it only modestly (2.4624). A generic learner on the seven covariates therefore captures predictive signal in region C that the selected symbolic form misses. The candidate's advantage over Baseline A is observed under the primary locked-region specification but is not robust to all spatial criteria.

## 6.4 Feature importance and negative control

Feature importance from the random forest (impurity-based, seven covariates) ranks `NDVI_mean` first (0.424), followed by `SVF_mean` (0.164), `DEM_mean` (0.154), `X_BH` (0.095), `X_VolDens` (0.079), `X_BD` (0.053) and `Road_Dens` (0.031). This agrees with the expression review: vegetation is the dominant signal, and `DEM_mean` is a mid-ranked contributor rather than the leading one.

A negative control repeated the random-forest fit with the region-A targets randomly permuted before training. The shuffled-target model reaches RMSE 2.6528 °C on region C (and 2.6876 °C for the boosted variant), approximately the constant floor, against 2.0950 °C for the true forest. The gap shows the forest's advantage comes from real signal rather than target leakage or a positional artefact of the spatial split.

## 6.5 The parsimony candidate

The frozen parsimony candidate `S03-H10P-GREEDY-MIN` (`exp(NDVI)` and `exp(DEM)`, complexity 6) improved on Baseline A in region A (A-CV 3.0655) but worsened the region-B RMSE (ΔB = −0.3412), and its region-A confidence interval includes zero. In the unified comparison its profile matches the other weak candidates. Its validation attempt remains unspent, and on this evidence it should not be spent.

## 6.6 Baseline D — the unconstrained, firewall-off agent

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

@@FIG figures/fig6_baselineD.png | Fig. 6 | (Exploratory combined-pipeline stress test.) In this run the admissibility constraints were associated with better locked-region behaviour, and the firewall prevented one concrete selection-leakage failure mode. (a) Region-A CV, B and C RMSE for Baseline A, the unconstrained agent (Baseline D, Arm 1) and the constrained candidate. (b) Firewall-off ladder: honest selection, selection directly on C, and refitting on the union of A, B and C. (c) Population profile of the unconstrained search (audit-rejected and over-cap fractions). Arm 2 touches region C only as an explicit ablation and writes nothing to the frozen logs.

# 7. Discussion

## 7.1 A passed frozen endpoint is not a scientific law

The discovery stage froze four candidates and the evaluation stage assessed two. The leading candidate, `S03-H10-GREEDY`, met the pre-registered primary endpoint on the withheld region: ΔRMSE +0.3791 °C, permutation p = 0.005 (the minimum attainable value at the 199-permutation budget), and a 95% confidence interval excluding zero, with the effect surviving Holm–Bonferroni correction and holding across all three vegetation strata. Taken alone, this is a positive result.

Four further results show that it should not be read as the discovery of a transferable urban LST law.

First, the effect does not survive a more conservative definition of the locked region. Under the pre-registered alternative contiguity parameter R = 25 cells, ΔRMSE falls to +0.1375 °C and p rises to 0.085. The sign is stable but the significance is not, and the derivation of R = 15 makes that parameter load-bearing.

Second, the comparator is weak. Baseline A transfers poorly to the withheld region: a constant predictor and a pseudo-candidate trained on shuffled targets both beat it. Because ΔRMSE is measured against Baseline A, part of the apparent gain reflects the comparator rather than the candidate.

Third, the interpretable content of the candidate is narrower than its expression suggests. Re-fitting ablated variants shows that removing the DEM terms slightly improves the locked-region performance, while removing `exp(NDVI)` destroys it on every region. The DEM terms are a smooth spatial field (R² = 0.781 against cell coordinates) built on an elevation layer whose range, 3–17 m, is not physically credible for Shenzhen. The terrain reading of the candidate is unsupported.

Fourth, and most directly (Fig. 2), a random forest on the same seven covariates outperforms the candidate on the withheld region by roughly a factor of two in ΔRMSE (+0.7465 versus +0.3791) — and a gradient-boosted model reaches +0.7500 — and beats the constant floor by a wide margin where the candidate beats it only modestly. A generic learner therefore captures transferable signal that the selected symbolic form misses.

The appropriate conclusion is the one the framework anticipates and permits: **no portable urban thermal law was established here.** The candidate is an observed improvement over the preregistered comparator, but it is selection-region-specific, sensitive to the spatial criterion, and largely carried by a single vegetation-related term.

## 7.2 Prediction, interpretability and discovery are distinct

The comparison makes a general point concrete. The best predictor on the withheld region is an off-the-shelf forest, which is not a discovery, while the discovered expression is not even the best predictor. Predictive accuracy and scientific content are distinct quantities, and optimising the first does not select for the second. The framework's own warning, that a better score does not equal a new law, is here observed from both directions.

The same distinction governs the constraints. In the exploratory combined-pipeline stress test, removing the admissibility constraints raised the development score but lowered the locked-region score — a result consistent with a regularising role for the constraints — while removing the firewall manufactured an apparent improvement of about a third of a degree Celsius that is consistent with selection leakage. Because the ablated arm also differs in hypothesis space, complexity cap and search behaviour, this is a combined-pipeline stress test, not a controlled isolation of either factor (Fig. 6).

## 7.3 What discovery-side isolation achieved

The value of the run lies in what the protocol demonstrates about autonomous discovery, not in the candidate.

The placebo `S03-H01-LIN7` is identical to Baseline A, so its true effect is zero. The evaluation service rejected it on the effect-size conditions while passing both models on the audit and control conditions. This shows, against a live test rather than an argument, that the service does not pass whatever it is given.

Two of the five primary-endpoint conditions are recomputed inside the validator process from region-A and region-B data rather than read from the discovery side's own records. The examined party no longer grades itself.

On the discovery side, the evidence supports one claim and not a stronger one. The access log records no discovery-side read of the withheld region, and candidate generation, fitting and ranking used region-A cross-validation with region B as a development falsification gate. We therefore state that we found no evidence that Region C entered the programmatic candidate-generation or selection process. This is a claim about discovery-side use, and it is the strongest claim the record supports; it is not a claim that the withheld region was untouched, which the audit contradicts.

The fair comparison also yields a result that cuts against the discovery, and it is reported in full. A protocol that can only produce confirmations would be of little value; this run produced a candidate that passed its pre-registered test and still, on the accumulated evidence, did not amount to a law.

## 7.4 What the protocol audit revealed

The audit of the access history was as important as the discovery itself, and its finding is negative.

The intended design froze the withheld region behind encryption and a runtime guard, and intended a single candidate-specific evaluation per candidate. The audit established two facts that break that intent. First, the withheld region was decrypted by validation-side self-tests during Stage 02, before the Stage 03 candidate freeze — the first decryption precedes the freeze in the log sequence — and it was decrypted repeatedly rather than once. One of those self-tests published a placeholder reading computed against genuine locked targets, which is why the region cannot be described as an untouched holdout. Second, the validator's own verdict logic was subsequently modified, to recompute the physics audit and the negative controls in-process; the audit could not establish whether that modification preceded or followed the first decryption, because the change is not represented in the hash chain and the two timestamp sources available disagree by about three days. That unresolved ordering is recorded rather than smoothed over.

None of this shows that the locked target values influenced candidate selection; on the contrary, the discovery-side isolation is supported. What it shows is narrower and more useful: the controls that were meant to protect the withheld region were not themselves frozen and timestamped before execution. A validation architecture can be correct on paper and fail in implementation, and the failure here is of exactly that kind — not a contaminated selection, but an unverifiable protection. The audit therefore changes our claim from pristine confirmatory validation to a separated discovery and locked-region evaluation under a documented protocol deviation.

## 7.5 Implications for autonomous science

The lesson extends beyond this dataset. Cryptography and access controls are insufficient unless validation-side software state and every target access are themselves frozen and independently timestamped before execution. A sealed region whose key is held by a process that can run self-tests against it, and whose validator code can change without entering the ledger, is protected by convention dressed as mechanism. The design that would have avoided this is straightforward — freeze the validator, its hash and the full access policy before the first decryption, and make every decryption an audited event — and it is the change we would make first in any re-run.

Three lines of work would strengthen the result. A prospective replication on an independent time period or a second city — beyond the post-hoc Changchun replication reported here — would test transferability and move the work toward L3. A DEM-free reduced model (`exp(NDVI)`, `SVF`, `Road_Dens`) could be pre-registered and tested prospectively rather than only in the post-hoc analysis reported here. And the constraint and firewall ablations reported here measure rather than assume the value of the admissibility constraints; because they are post-hoc and combined, re-running them prospectively with their own frozen endpoint and a controlled single-factor design would make that comparison confirmatory in intention. The design-counterfactual experiments the framework envisages (Experiment 5) are not attempted here, since they require physical simulation or intervention evidence that the present data cannot supply.

# 8. Limitations

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

# Declarations

*Draft. To be completed with author and funding information before submission.*

## Data availability

The frozen analysis-ready data and derived artefacts required to audit and reproduce the reported analyses have been prepared as the PAID Reviewer Reproducibility Package v1.2.1 and will be deposited at {{DATA_ARCHIVE_DOI}}; during peer review they will be accessible through {{DATA_REVIEWER_LINK}}. The release contains the complete 32,748-cell Shenzhen spatial split and the exact frozen analysis-ready covariate and land-surface-temperature tables used for Regions A, B and C, together with the candidate registries, Stage-04 evaluation artefacts, Stage-05 benchmark outputs, figure-source data and protocol-audit records. The complete Region-C analysis-ready table is provided solely for reproducibility of the locked-region evaluation. Region C is scientifically spent under Protocol V1 and must not be interpreted as an independent or pristine confirmatory holdout. The approximately 857-MB original Shenzhen source-raster archive is not included in the core release because redistribution rights and source metadata are incomplete; instead, the exact frozen analysis-ready values used in the manuscript and a source-data provenance inventory are provided. Changchun row-level analysis-ready data are distributed only to the extent permitted by the applicable third-party data terms; where redistribution is not permitted, the archive provides the analysis code, schema, provenance, hashes and derived outputs.

## Code availability

The code required to audit and reproduce the frozen analyses reported in this study has been prepared for release at {{CODE_REPOSITORY_URL}} and will be archived at {{CODE_ARCHIVE_DOI}} under release {{RELEASE_TAG}} (commit {{CODE_COMMIT_SHA}}). The archive preserves the historical PAID Stage 00–05 implementation together with a portable reviewer-verification layer. The portable layer verifies the frozen spatial partition, candidate hashes, Region-C Stage-04 statistics, the R=25 sensitivity analysis, Stage-05 conventional baselines, the external-replication outputs where the associated data may be redistributed, figure-source artefacts and release manifests without relying on the original local directory structure or the historical AES key. Historical scripts are retained for provenance and are not retrospectively altered. Verification and recomputation of the published numerical results from the frozen release artefacts require no LLM or network access. The role of any LLM in workflow development or scientific decision-making is described separately in the AI-usage disclosure and MODEL_AND_AGENT_DISCLOSURE.md.

## AI usage disclosure

The scientific discovery and validation pipeline reported in this study was executed as deterministic Python software. Large-language-model tools were used during workflow development and manuscript authoring, but no language-model service was called by the archived scientific execution pipeline at run time. Candidate evaluation, model fitting, spatial validation, permutation tests, bootstrap inference and all reported numerical results are reproducible from the released code, frozen data and random seeds without language-model or network access.

## Ethics

The study uses publicly derived urban environmental data and involves no human or animal subjects.

## Author contributions

To be completed (CRediT).

## Competing interests

The authors declare no competing interests.

## Funding

To be completed.

## Acknowledgements

To be completed.

@@PB

# References

[1] Oke, T. R. (1982). The energetic basis of the urban heat island. *Quarterly Journal of the Royal Meteorological Society*, 108(455), 1–24. https://doi.org/10.1002/qj.49710845502

[2] Weng, Q. (2009). Thermal infrared remote sensing for urban climate and environmental studies: Methods, applications, and trends. *ISPRS Journal of Photogrammetry and Remote Sensing*, 64(4), 335–344. https://doi.org/10.1016/j.isprsjprs.2009.03.007

[3] Weng, Q., Lu, D., & Schubring, J. (2004). Estimation of land surface temperature–vegetation abundance relationship for urban heat island studies. *Remote Sensing of Environment*, 89(4), 467–483. https://doi.org/10.1016/j.rse.2003.11.005

[4] Xu, F., Shen, Y., Zheng, M., Zhang, X., Zuo, Y., Wang, X., & Zhang, M. (2025). Characterizing the thermal effects of urban morphology through unsupervised clustering and explainable AI. *Remote Sensing*, 17(18), 3211. https://doi.org/10.3390/rs17183211

[5] Karniadakis, G. E., Kevrekidis, I. G., Lu, L., Perdikaris, P., Wang, S., & Yang, L. (2021). Physics-informed machine learning. *Nature Reviews Physics*, 3(6), 422–440. https://doi.org/10.1038/s42254-021-00314-5

[6] von Rueden, L., Mayer, S., Beckh, K., Georgiev, B., Giesselbach, S., Heese, R., Kirsch, B., Pfrommer, J., Pick, A., Ramamurthy, R., Walczak, M., Garcke, J., Bauckhage, C., & Schuecker, J. (2023). Informed machine learning – A taxonomy and survey of integrating prior knowledge into learning systems. *IEEE Transactions on Knowledge and Data Engineering*, 35(1), 614–633. https://doi.org/10.1109/TKDE.2021.3079836

[7] Karpatne, A., Atluri, G., Faghmous, J. H., Steinbach, M., Banerjee, A., Ganguly, A., Shekhar, S., Samatova, N., & Kumar, V. (2017). Theory-guided data science: A new paradigm for scientific discovery from data. *IEEE Transactions on Knowledge and Data Engineering*, 29(10), 2318–2331. https://doi.org/10.1109/TKDE.2017.2720168

[8] Raissi, M., Perdikaris, P., & Karniadakis, G. E. (2019). Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations. *Journal of Computational Physics*, 378, 686–707. https://doi.org/10.1016/j.jcp.2018.10.045

[9] Beucler, T., Pritchard, M., Rasp, S., Ott, J., Baldi, P., & Gentine, P. (2021). Enforcing analytic constraints in neural networks emulating physical systems. *Physical Review Letters*, 126(9), 098302. https://doi.org/10.1103/PhysRevLett.126.098302

[10] Camps-Valls, G., Džeroski, S., Fernández-Torres, M.-Á., Gentine, P., Levi, D., Martínez, J., Martin-Jungblut, C., Martínez-Ramón, M., Reichstein, M., Rivas-Malpica, D., Svendsen, D. H., Tuia, D., Valero, S., & Viana, S. (2020). Living in the physics and machine learning interplay for Earth observation. arXiv:2010.09031. https://arxiv.org/abs/2010.09031

[11] Reichstein, M., Camps-Valls, G., Stevens, B., Jung, M., Denzler, J., Carvalhais, N., & Prabhat. (2019). Deep learning and process understanding for data-driven Earth system science. *Nature*, 566(7743), 195–204. https://doi.org/10.1038/s41586-019-0912-1

[12] Willard, J., Jia, X., Xu, S., Steinbach, M., & Kumar, V. (2022). Integrating scientific knowledge with machine learning for engineering and environmental systems. *ACM Computing Surveys*, 55(3), 53. https://doi.org/10.1145/3514228

[13] Schmidt, M., & Lipson, H. (2009). Distilling free-form natural laws from experimental data. *Science*, 324(5923), 81–85. https://doi.org/10.1126/science.1165893

[14] Brunton, S. L., Proctor, J. L., & Kutz, J. N. (2016). Discovering governing equations from data by sparse identification of nonlinear dynamical systems. *Proceedings of the National Academy of Sciences*, 113(15), 3932–3937. https://doi.org/10.1073/pnas.1517384113

[15] Udrescu, S.-M., & Tegmark, M. (2020). AI Feynman: A physics-inspired method for symbolic regression. *Science Advances*, 6(16), eaay2631. https://doi.org/10.1126/sciadv.aay2631

[16] Cranmer, M., Sanchez-Gonzalez, A., Battaglia, P., Xu, R., Cranmer, K., Spergel, D., & Ho, S. (2020). Discovering symbolic models from deep learning with inductive biases. In *Advances in Neural Information Processing Systems 33* (pp. 17429–17442). arXiv:2006.11287. https://arxiv.org/abs/2006.11287

[17] La Cava, W., Orzechowski, P., Burlacu, B., de França, F. O., Virgolin, M., Jin, Y., Kommenda, M., & Moore, J. H. (2021). Contemporary symbolic regression methods and their relative performance. In *Proceedings of the NeurIPS 2021 Datasets and Benchmarks Track*. arXiv:2107.14351. https://arxiv.org/abs/2107.14351

[18] Wang, H., Fu, T., Du, Y., Gao, W., Huang, K., Liu, Z., Chandak, P., Liu, S., Van Katwyk, P., Deac, A., Anandkumar, A., Bergen, K., Gomes, C. P., Ho, S., Kohli, P., Lasenby, J., Leskovec, J., Liu, T.-Y., Manrai, A., … Zitnik, M. (2023). Scientific discovery in the age of artificial intelligence. *Nature*, 620(7972), 47–60. https://doi.org/10.1038/s41586-023-06221-2

[19] Krenn, M., Pollice, R., Guo, S. Y., Aldeghi, M., Cervera-Lierta, A., Friederich, P., Gomes, G., Häse, F., Jinich, A., Nigam, A., Yao, Z., & Aspuru-Guzik, A. (2022). On scientific understanding with artificial intelligence. *Nature Reviews Physics*, 4(12), 761–769. https://doi.org/10.1038/s42254-022-00518-3

[20] Kriegeskorte, N., Simmons, W. K., Bellgowan, P. S. F., & Baker, C. I. (2009). Circular analysis in systems neuroscience: The dangers of double dipping. *Nature Neuroscience*, 12(5), 535–540. https://doi.org/10.1038/nn.2303

[21] Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data*, 6(4), 15. https://doi.org/10.1145/2382577.2382579

[22] Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40(8), 913–929. https://doi.org/10.1111/ecog.02881

[23] Ploton, P., Mortier, F., Réjou-Méchain, M., Barbier, N., Picard, N., Rossi, V., Dormann, C., Cornu, G., Viennois, G., Bayol, N., Lyapustin, A., Gourlet-Fleury, S., & Pélissier, R. (2020). Spatial validation reveals poor predictive performance of large-scale ecological mapping models. *Nature Communications*, 11, 4540. https://doi.org/10.1038/s41467-020-18321-y

[24] Wadoux, A. M. J.-C., Heuvelink, G. B. M., de Bruin, S., & Brus, D. J. (2021). Spatial cross-validation is not the right way to evaluate map accuracy. *Ecological Modelling*, 457, 109692. https://doi.org/10.1016/j.ecolmodel.2021.109692

[25] Nosek, B. A., Ebersole, C. R., DeHaven, A. C., & Mellor, D. T. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences*, 115(11), 2600–2606. https://doi.org/10.1073/pnas.1708274114
