# REGION C — provenance of the shipped analysis-ready table

Region C (2,987 locked cells) is the withheld region that the Stage-04 primary endpoint is evaluated on.
The evaluation runs against the target values in Region C, so the reviewer needs those values to
recompute the frozen endpoint. This document states exactly what is shipped, where it came from, and how
its integrity can be checked without the AES key.

---

## 1. What is shipped, and its integrity

| Item | File | Size | SHA-256 |
|---|---|---|---|
| Region-C analysis-ready table | `data/shenzhen/zone_C_analysis_ready.csv` | 339,556 bytes | `b4a709e16d7b75425496fae1cea1ea6c5fd113575fe5f6766ab3389da353eab9` |
| Sealed ciphertext (for reference) | `PAID/stage02_platform/vault/zone_C_targets.enc` | 339,584 bytes | `ef1d8e6e2b2b8d0ce365666071abb5b5560170c8b7cca31ca338735f7fbc731f` |
| Vault manifest | `PAID/stage02_platform/vault/vault_manifest.json` | — | records `plaintext_sha256`, `n_rows`, `columns` |

**The shipped table is the decrypted vault plaintext, verbatim.** Its file SHA-256,
`b4a709e1…eab9`, is **identical** to `vault_manifest.json` → `plaintext_sha256`. This is **byte
identity**, not merely semantic identity: the bytes the Independent Validator recovered from
`zone_C_targets.enc` are the bytes shipped here, unchanged.

The reviewer can check this without the key, because the expected hash is published in the frozen
manifest (`verify_stage04_release.py`, check **C2**):

```bash
python3 release_tools/verify_stage04_release.py     # C2: Region-C file SHA-256 == manifest plaintext
```

### Schema (frozen order)

```
Grid_ID, LST_mean, NDVI_mean, DEM_mean, SVF_mean, Road_Dens, X_BD, X_BH, X_VolDens
```

2,987 rows × 9 columns — the exact column list and row count recorded in `vault_manifest.json`. This is
the target (`LST_mean`) plus the seven pre-specified covariates and the grid id; it is the same schema
used for Regions A and B.

### Why the plaintext is shipped and the key is not

The AES-256-GCM key is **not** in this package (see `REPOSITORY_RECORD.md`, `DATA_PROVENANCE.md` §3).
Shipping the plaintext does **not** weaken the archive: the plaintext hash is already pinned in the
frozen manifest, and Region C is *scientifically spent* (see §3). Keeping the key out is what the
original protocol promised and is preserved. What a reviewer needs to *recompute* the endpoint is the
target values, not the ciphertext; those values are provided with a hash that ties them to the manifest.

---

## 2. How this table was produced (packaging extraction)

The table was produced by a **single** packaging-time decryption of `zone_C_targets.enc` using the
historical validator key held by the author, then written out unchanged. The extraction is logged
separately in `PACKAGING_EXTRACTION_LOG.md`, because the frozen hash-chained experiment log inside
`PAID/` is **never** modified. In short:

* algorithm `AES-256-GCM`, nonce = first 12 bytes of the blob, AAD `PAID-stage02-vault-v1`;
* decrypted plaintext SHA-256 = `b4a709e1…eab9` — matches the manifest;
* the key was used only for this extraction and is not redistributed.

---

## 3. Status of Region C — the wording that is and is not accurate

A post-hoc audit of the frozen log found that Region C plaintext was accessed **more than once** during
Stage-02–04, and that the first such access (a placeholder decryption, log `seq 45`, `2026-09-24T08:52:58`)
preceded the real candidate freeze. The full account, with the evidence, is in `PROTOCOL_DEVIATION.md`
and the archived `A6B_TIMELINE_AUDIT.md` / `A6B_VERDICT.txt` (verdict **CASE C**).

Accurate description:

> Region C is the locked region, evaluated under a **documented protocol deviation**. The evaluation is
> **not a pristine, single-touch, prospective holdout**; it is an evaluation on the locked-out region
> that was **scientifically spent under Protocol V1**.

The following descriptions are **not** used anywhere in this package, because they are contradicted by
the evidence:

* "blind holdout" / "untouched holdout" / "pristine holdout";
* "first access" / "first and only access";
* "unsealed exactly once" / "single irrevocable unsealing" / "single-access dataset".

The audit found **no** evidence that Region C fed into candidate definition, ranking, the endpoint, or
the pass thresholds (contamination = NO; endpoint modified = NO). The endpoint number
(ΔRMSE = +0.3791 °C, p = 0.005, CI [0.2761, 0.4814]) reproduces bit-for-bit from the shipped tables via
`release_tools/verify_stage04_release.py`.

Region C must **not** be reused as a fresh confirmatory holdout — not for selection, revision, refitting
or reconfirmation.

---

## 4. Cross-references

- `PACKAGING_EXTRACTION_LOG.md` — the one extraction event.
- `PROTOCOL_DEVIATION.md` — deviation, access history, verdict.
- `DATA_PROVENANCE.md` §1 — Shenzhen dataset provenance; §3 — what is deliberately absent.
- `REPOSITORY_RECORD.md` — the vault and the withheld key.
- `KNOWN_LIMITATIONS.md` — interpretation limits that follow from the above.
