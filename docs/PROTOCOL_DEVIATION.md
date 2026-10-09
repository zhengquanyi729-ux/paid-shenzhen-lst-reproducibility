# PROTOCOL DEVIATION — Region C, access history, and the status of the locked-region evaluation

This document is the reviewer-facing account of a **documented protocol deviation** discovered by a
post-hoc audit of the archived, hash-chained experiment log and file inventory. It is included in full,
unredacted, because the credibility of the whole study rests on it. It states **only verified facts** and
marks explicitly where the archive is **unresolved**. Nothing here is corrected, reconstructed or
softened.

Primary evidence inside this package:

- `PAID/stage05_paper/manuscript/A6B_VERDICT.txt` — the one-page verdict (CASE C).
- `PAID/stage05_paper/manuscript/A6B_TIMELINE_AUDIT.md` — the full read-only timeline audit (T1–T11).
- `PAID/stage02_platform/logs/experiment_log.jsonl` — the append-only, hash-chained log (frozen at
  **1,259 records**; SHA-256 `b10cc702…5488`).
- The Stage manifests under `PAID/stage0*/manifests/` and `PAID/stage02_platform/vault/vault_manifest.json`.

---

## 1. What the protocol promised (frozen before any Region C access)

`PAID/stage01_protocol/PREREGISTRATION.md` and
`PAID/stage01_protocol/protocol/validation_protocol.json` froze, at Stage 01 (before any access to
Region C):

- the **spatial partition** A (discovery, 19,184) / B (dev-validation, 6,182) / C (locked, 2,987),
  with a 1.5 km (R = 15 cells) buffer (3,407) around C;
- the **primary endpoint**: Region-C ΔRMSE against Baseline A;
- the **pass conditions**: ΔRMSE > 0 **and** a 199-block spatial-permutation p < 0.05 **and** a 95 % CI
  excluding 0 **and** the physics audit passing **and** the negative controls not being fooled;
- the statement that *after unsealing, the model, metric, hypotheses and stopping rule may not be
  changed*.

The endpoint specification file has **not changed since Stage 01** (SHA-256 `a04220a7…4a75`, matching
the Stage-01 manifest).

## 2. What the audit found

### 2.1 Confirmed: discovery-side isolation held

- The discovery sandbox denies Region C by name and prefix (`zone_c`, `vault`, `validator_key`,
  `data_原始`, `lst_30m`); denial events are logged (`access_denied`).
- The discovery-side roles read only Regions A/B; the sandbox work tree contains only A/B open data.
- Candidate **definition and ranking used only Region A** (spatial-block cross-validation,
  `cv_rmse`); Region B served only as a `not_fooled` gate; Region C never entered selection.
- The three layers above are each supported by code and by log entries.

**Verdict line: locked-from-discovery = YES.**

### 2.2 Confirmed and unfavourable: Region C plaintext was accessed more than once

The Stage-02 end-to-end self-test ran the Independent Validator, which — after hash checks — called
`decrypt_vault()` and published a **placeholder** candidate (`SMOKE-0001`, i.e. the Baseline-A
specification). That publication is a genuine decryption of Region C plaintext.

- Log records show the placeholder being decrypted and published repeatedly, plus `dry_run=True`
  unseal/validate cycles. The audit counts **at least 22 distinct Region-C plaintext decryptions**
  (14 `validation_published` for the placeholder + 8 `unsealed_validated`, including dry runs).
- The **first** of these, log `seq 45`, is timestamped `2026-09-24T08:52:58` — **before** the real
  candidates were frozen (Stage-03 freeze). Its returned value was the Baseline-A reference
  (`rmse_baselineA = 2.8415…`, Δ = 0.0, p = 1.0), i.e. it carried no information usable to design or
  select a candidate.

**Verdict lines: single-access claim valid = NO** and, strictly, the chain `first C decrypt <
candidate freeze` is **violated at its first link** (by a placeholder decryption).

Any wording of the form *"unsealed exactly once"*, *"first and only access"*, *"a single irrevocable
unsealing"* or *"one authorised access"* is therefore **false** and has been withdrawn from the
manuscript.

### 2.3 Unresolved: when the final validation logic was frozen relative to first C access

`PAID/stage02_platform/agents/independent_validator.py` contains a substantive change: two of the five
pass conditions (`physics_audit_pass`, `negative_controls_not_fooled`) were changed from *reading a
candidate-JSON self-reported verdict* to *recomputing independently inside the validator process* on
A/B data (`audit_independent` / `controls_independent`). The thresholds did not change; **who computes**
changed, in the direction of *stricter*. The current file's SHA-256 matches the Stage-02 manifest.

The audit could **not** establish whether this change preceded or followed the first Region-C decryption,
because:

1. **Code changes are not written to the hash chain** — there is no log entry for the edit; and
2. the two available clocks **disagree by ~2.5–3 days**: the in-log `ts` values place all scientific
   events on `2026-09-24` (first decrypt 08:52:58; formal unsealing 13:11–13:12), whereas the filesystem
   `mtime` values place the entire Stage-03/04/05 batch on `2026-09-27` (validator edited 02:58:24,
   unsealing approved 03:00:59, results written 03:03:14).

Under the "log `ts`" reading, the change cannot be located at all. Under the "`mtime`" reading, it
*precedes* the formal unsealing — but that reading contradicts the hash chain's own timestamps. Per the
pre-registered rule, this is marked **`[TIMESTAMP CONFLICT]`** and **not adjudicated**:
both readings are stated, neither is chosen.

**Verdict line: validator verdict logic modified after first C access = UNRESOLVED.**

Note on direction (not a substitute for provability): the change makes passing **harder**; all recorded
verdicts are unchanged under it. But "the change did not help the result" does not prove "the change
post-dates the access", and the audit does not present it as if it did.

### 2.4 Confirmed: endpoint and selection were not contaminated

- `validation_protocol.json` hash unchanged; its mtime (`09-24 08:45:42`) precedes the first decrypt
  (`08:52:58`). Endpoint semantics constant from Stage 01.
- Candidate ordering (`s03_03_freeze.py`) uses only Region-A CV; B is a pass/fail gate; C never appears.
- Permutation (199 blocks) and bootstrap (1,000) rules are implemented identically on the discovery and
  validation sides, with a degenerate-identity guard.

**Verdict lines: selection contamination = NO; endpoint modified after first C access = NO.**

## 3. The verdict

From `A6B_VERDICT.txt`:

```
CASE: C
Selection contamination: NO
Endpoint modified after first C access: NO
Validator verdict logic modified after first C access: UNRESOLVED
Single-access claim valid: NO
Locked-from-discovery claim valid: YES
```

**CASE C** means: the key link `final validation-rule freeze < first C decrypt` **cannot be proven**
from the archive, and the two clocks contradict each other about it. In addition, there is one
**provable and unfavourable** fact — the very first Region-C plaintext decryption preceded the real
candidate freeze (a placeholder decryption, scientifically inert but still an access).

The audit notes that under a stricter reading this provable ordering violation would push the case
toward CASE B ("a reportable deviation exists"). **CASE B and CASE C land in the same place**: Stage 04
must not be described as *fully confirmatory* or *prospective*. The difference is only whether the
placeholder decryption is classified as a *proven ordering violation* (B) or as *unadjudicable* (C).

## 4. What this means for the results — and what it does not

**What it does not mean.** The audit found **no evidence** that Region C fed back into candidate
definition, candidate selection, the endpoint, or the pass thresholds. The headline number
(ΔRMSE = +0.3791 °C, p = 0.005, CI [0.2761, 0.4814]) is reproduced bit-for-bit by the shipped
verification (`PAID/stage04_validation/scripts/s04_03_verify.py`, `PAID/stage05_paper/scripts/s05_03_manifest_verify.py`).

**What it does mean.** The locked-region evaluation is **not a pristine, single-touch,
prospective holdout**. It is, accurately:

> *an evaluation on the locked-out region that was selected post hoc and carries a documented protocol
> deviation.*

Region C is described throughout as **scientifically spent under Protocol V1**. It must **not** be
reused as a fresh, untouched confirmatory holdout — not for selection, revision, refitting or
reconfirmation.

## 5. Why the deviation is disclosed rather than corrected

Rebuilding the archive, re-running the search, or re-freezing a "clean" split would erase the very
evidence that makes the study auditable, and would not restore the pristine-holdout status that the
original plan assumed. The study is therefore reported **on the frozen artefacts, with the deviation
declared**. This is consistent with the package's governing principles: frozen Stage 00–05 results are
preserved unchanged; the audit log, manifests and deviation evidence are never overwritten; and the
availability statements describe what the archive actually contains.

## 6. Pointers for a reviewer who wants to check this directly

```bash
cat  PAID/stage05_paper/manuscript/A6B_VERDICT.txt
less PAID/stage05_paper/manuscript/A6B_TIMELINE_AUDIT.md
wc -l PAID/stage02_platform/logs/experiment_log.jsonl     # frozen: 1259
python3 - <<'PY'
import json
n=0; first=None
for line in open('PAID/stage02_platform/logs/experiment_log.jsonl'):
    r=json.loads(line); n+=1
    if r.get('ts'): first=first or r['ts']
print('records:', n, 'first ts:', first)
PY
```

The log is **never modified** by the verification scripts; re-running them refreshes only their own
`reports/verification.json` / `manifests/stage05_hashes.txt` check files (see `QUICKSTART.md`).
