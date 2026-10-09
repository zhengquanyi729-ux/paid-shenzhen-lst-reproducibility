# NUMERICAL TOLERANCE POLICY — v1.2.1

Every numeric comparison in `release_tools/` falls into exactly one of four classes. The class
determines the acceptance rule; no verifier is allowed to loosen a rule to make a check pass.

## 1. Continuous quantities — absolute tolerance 1e-9

RMSE values, ΔRMSE values and bootstrap confidence-interval endpoints are compared with an
**absolute tolerance of 1e-9**. The frozen record carries them to ≥15 significant digits, so a
faithful recomputation reproduces them exactly; 1e-9 is far below any scientifically meaningful
difference and only absorbs last-bit BLAS variation.

Examples: Baseline A RMSE_C 2.841519144671417; H10 RMSE_C 2.462447828502684; ΔRMSE
0.379071316168733; CI [0.276067201358972, 0.481358279348766]; R = 25 ΔRMSE 0.137499076805151.

## 2. Definitional identities — exact, by construction (the placebo rule)

The placebo `S03-H01-LIN7` is, **by specification**, the same seven-covariate standardised linear
model as Baseline A. A definitional identity is not a floating-point coincidence, so this release does
**not** check it by two independent refits (v1.1 did, and that comparison was fragile to
BLAS-level rounding and conceptually wrong). Instead the verifier proves:

1. **specification identity** — placebo covariate list == Baseline-A list (same list, same set,
   all raw variables, standardised, intercept), fitted on the same Region A (`n_fit` equal); then
2. **prediction identity** — `predict(placebo, C)` equals `predict(BaselineA, C)` element-wise
   (observed `max|Δprediction| = 0`, asserted `≤ 1e-12`); and then
3. **identity of endpoints** — because the placebo *is* the reference model, its improvement is
   zero by construction:

```
ΔRMSE ≡ 0        permutation p ≡ 1        95% CI ≡ [0, 0]        R = 25 Δ ≡ 0
```

These are asserted **exactly** (`== 0.0`, `== 1.0`, `list == [0.0, 0.0]`), not within a tolerance,
and are cross-checked against the frozen report entry, which records the same `0.0 / 1.0 / [0,0]`.

## 3. Counts, probabilities and hashes — exact integers / hex strings

Row counts, buffer counts, permutation counts, generated p-values that are ratios of integers
(e.g. `p = (1 + #{null ≥ obs}) / (1 + N_PERM)`, N_PERM = 199), and every SHA-256 are compared
**exactly**. A p-value of 0.005 is the minimum attainable value under 199 permutations; it is a
rational number and is compared as such, not to 1e-9 of a float.

## 4. Byte-identity — SHA-256 equality

Region-C table vs the frozen vault plaintext (`b4a709e1…eab9`), figure files vs the manifest, and
the ASCII alias `process_image1.png` vs its `过程__image1.png` source are compared by **SHA-256
equality** — byte-identical or not, never "close".

## Where the frozen numbers live (the contract)

See `FROZEN_NUMERICAL_CONTRACT_v1_2_1.md` for the exact values, their source files, and the class
each belongs to. Nothing in this policy permits a change to a frozen number.
