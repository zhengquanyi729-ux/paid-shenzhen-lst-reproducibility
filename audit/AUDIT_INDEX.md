# AUDIT INDEX — where the protocol-deviation evidence lives

This folder is a pointer index. The audit artefacts themselves are **kept in place inside `PAID/`** (not
copied) so their relative paths and hashes stay exactly as frozen. Everything below is shipped in this
package unless marked otherwise.

## 1. The deviation verdict and timeline (read these first)

| Artefact | Path | What it establishes |
|---|---|---|
| One-page verdict | `PAID/stage05_paper/manuscript/A6B_VERDICT.txt` | CASE C; selection contamination NO; endpoint modified NO; validator-logic change UNRESOLVED; single-access claim NO; locked-from-discovery YES |
| Full timeline audit | `PAID/stage05_paper/manuscript/A6B_TIMELINE_AUDIT.md` | T1–T11 event table, the `[TIMESTAMP CONFLICT]`, the ≥22 Region-C decryptions, the code-change-without-log-entry finding |
| Reviewer-facing summary | `PROTOCOL_DEVIATION.md` (package root) | plain-language account + consequences for interpretation |

## 2. Primary evidence

| Evidence | Path | Frozen marker |
|---|---|---|
| Hash-chained experiment log | `PAID/stage02_platform/logs/experiment_log.jsonl` | 1,259 records; SHA-256 `b10cc702…5488`; append-only (`seq`,`hash`,`prev`) |
| Sealed Region-C vault | `PAID/stage02_platform/vault/zone_C_targets.enc` | SHA-256 `ef1d8e6e…731f` (AES-256-GCM) |
| Vault manifest | `PAID/stage02_platform/vault/vault_manifest.json` | records `n_rows = 2987` |
| Validator (post-change) | `PAID/stage02_platform/agents/independent_validator.py` | SHA-256 `523889c6…932a` = Stage-02 manifest |
| Endpoint specification | `PAID/stage01_protocol/protocol/validation_protocol.json` | SHA-256 `a04220a7…4a75`, unchanged since Stage 01 |
| Pre-registration | `PAID/stage01_protocol/PREREGISTRATION.md` | SHA-256 `56f3e79a…70b4`, unchanged |
| Validation script | `PAID/stage04_validation/scripts/s04_01_validate.py` | SHA-256 `0c015e11…caaf` = Stage-04 manifest |
| Frozen candidate registry | `PAID/stage03_discovery/registry/frozen_candidates.json` | post-unsealing regeneration → V4 tripwire FAIL (expected) |
| Unseal authorisation | `PAID/stage04_validation/registry/approved_unseal.json` | per-candidate `validation_runs ≤ 1` (semantics contradicted by T4/T5) |
| Region-C evaluation results | `PAID/stage04_validation/reports/s04_validation_results.json` | ΔRMSE +0.3791, p = 0.005, CI [0.2761, 0.4814] |

## 3. Stage manifests (hash-verified)

`PAID/stage00_data_audit/manifest/`, `PAID/stage01_protocol/manifest/stage01_hashes.txt`,
`PAID/stage02_platform/manifests/`, `PAID/stage03_discovery/manifests/`,
`PAID/stage04_validation/manifests/stage04_hashes.txt`,
`PAID/stage05_paper/manifests/stage05_hashes.txt`.

## 4. What the audit did NOT do (boundary statement)

The A-6B audit was **read-only**: it did **not** decrypt Region C, did **not** re-run any stage, did
**not** modify any frozen product, and did **not** modify the manuscript. Where the two clocks conflict,
it records both readings and **does not adjudicate**.

## 5. How to reproduce the audit's key checks

```bash
# frozen log length and first timestamp
wc -l PAID/stage02_platform/logs/experiment_log.jsonl      # expect 1259
# hashes of the pivotal files (compare against the manifests)
sha256sum PAID/stage01_protocol/protocol/validation_protocol.json \
          PAID/stage02_platform/agents/independent_validator.py \
          PAID/stage02_platform/vault/zone_C_targets.enc
# the intentional tripwire: expect 7/8 (V4 FAIL by design)
python3 PAID/stage03_discovery/scripts/s03_05_verify.py
```
