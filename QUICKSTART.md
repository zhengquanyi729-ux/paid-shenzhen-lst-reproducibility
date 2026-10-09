# QUICKSTART — verify the key results

All commands below are run **from the repository root**, are **Portable** (they derive their own root,
need **no AES key, no network and no author paths**), and use only `numpy`, `pandas`, `matplotlib` and
`Pillow` — see `requirements-lock.txt` for the exact, certified versions.

The `PAID/` Stage 00–05 scripts are the **historical record** and are **not** part of this path: they
import absolute author paths and will not run on your machine. Use `release_tools/` instead.

## 0. Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt
```

Certified on **Python 3.10.12** (see the header of `requirements-lock.txt`). `environment.yml` is an
optional convenience equivalent.

## 1. Verify the tree integrity (all file hashes)

```bash
python verification/verify_manifest.py
# expect: RESULT: PASS (all listed hashes verified)
```

`MANIFEST_SHA256.csv` in this repository is the manifest **for this public tree** (it lists the files
shipped here). Some unlisted, informational entries may be reported because this repository is under
version control; only a `MISSING` or `HASH …` line is a real failure.

## 2. Run the portable verification layer

```bash
python release_tools/run_all_release.py
```

## Public path vs. confidential reviewer path (important)

There are **two** verification paths, and they are not the same:

- **PUBLIC path — this repository.** The portable layer runs everything that depends only on shipped,
  public-safe material. **One** verifier, `CHANGCHUN_NUMERICS` (`verify_changchun_release.py`), needs
  the **reviewer-only Changchun row-level table**, which is deliberately **not** in this public
  repository (its redistribution licence is unconfirmed). On this public tree that verifier therefore
  cannot complete its restricted-data check, so a full run reports it as failing/skipped — **the public
  tree is not a 13/13 run**. This is expected, not a defect.
- **CONFIDENTIAL reviewer path — the reviewer package.** The reviewer distribution includes the slim
  Changchun table, so it runs the full thirteen verifiers and reports `13/13 … ALL PASS`. That result
  belongs to the reviewer package; it is not claimed here.

Everything that does **not** depend on the restricted table — release integrity, archive paths, the
frozen split, the candidate registry, the Stage-04 statistics, the Stage-05 chain, the figures, the
submission wording, the internal-reference and availability checks, and the two scans — runs on this
public tree.

## 3. Individual verifiers

```bash
python release_tools/verify_stage01_release.py        # frozen A/B/C split + R = 15 buffer
python release_tools/verify_stage03_release.py        # the four frozen candidate hashes
python release_tools/verify_stage04_release.py        # Δ = +0.379071…, p = 0.005, CI, placebo, R = 25
python release_tools/verify_stage05_release.py        # Baseline A/B/D + cross-reports (S05_RF=1 adds ~20 s)
python release_tools/verify_figures_release.py        # 7 figures × 4 formats + docx embeds
python release_tools/verify_manuscript_submission.py  # submission wording gates
python release_tools/verify_internal_references.py    # no dangling cross-reference
python release_tools/verify_availability_statements.py
python release_tools/scan_secrets.py                  # expect: 0 findings
python release_tools/scan_absolute_paths.py           # expect: 0 matches in the reviewer layer
```

`verify_changchun_release.py` is shipped for completeness but cannot run here without the restricted
Changchun table (see above).

## Where the headline numbers live

| Number | File |
|---|---|
| ΔRMSE = +0.3791 °C, p = 0.005, CI [0.2761, 0.4814] | `PAID/stage04_validation/reports/s04_validation_results.json` |
| R = 25 sensitivity (+0.1375, p = 0.085) | same file (`criterion_sensitivity`) |
| RF / GBM ΔRMSE (+0.7465 / +0.7500) | `PAID/stage05_paper/reports/baselineB.json` |
| Baseline-D ablations | `PAID/stage05_paper/reports/baselineD.json` |
| Spatial split (A/B/buffer/C) | `PAID/stage01_protocol/split/split_manifest.json` |

## Inspect the protocol deviation

```bash
cat PAID/stage05_paper/manuscript/A6B_VERDICT.txt          # CASE C
less PAID/stage05_paper/manuscript/A6B_TIMELINE_AUDIT.md
wc -l PAID/stage02_platform/logs/experiment_log.jsonl      # frozen at 1259 records
```

Then read `docs/PROTOCOL_DEVIATION.md` and `docs/REGION_C_PROVENANCE.md`.
