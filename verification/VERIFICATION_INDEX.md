# VERIFICATION INDEX

All checkable claims in this package, the command that checks each one, and the expected result.
Run from the release root. See `../QUICKSTART.md` for the guided path.

Expected results were observed on a copy of this package (Python 3.10.12).

| # | Claim checked | Command | Expected |
|---|---|---|---|
| 1 | **Release integrity** — every listed file matches its recorded SHA-256 | `python3 verification/verify_manifest.py` | `RESULT: PASS (all listed hashes verified)` |
| 2 | **Frozen candidate registry** — the four frozen candidate hashes reproduce | `python3 PAID/stage03_discovery/scripts/s03_05_verify.py` | **7 of 8 pass**; V4 fails **by design** (see below) |
| 3 | **Stage-04 published statistics** — ΔRMSE, p, CI recompute | `python3 PAID/stage04_validation/scripts/s04_03_verify.py` | `== Stage 04 verify: PASS (7/7) ==` (V5 delta ≈ 0.379071, p = 0.005) |
| 4 | **Full Stage-05 chain** — baselines, figures, cross-checks | `python3 PAID/stage05_paper/scripts/s05_03_manifest_verify.py` | `== Stage 05 verify: PASS (11/11) ==` |
| 5 | **Figures regenerate** | `python3 PAID/stage05_paper/scripts/s05_02_figures.py` then `s05_06_study_overview.py` | fig1–fig6 (~12 s) + fig0 (~3 s); PNG/TIFF byte-identical |
| 6 | **Protocol deviation** — the collision of the clocks and the access history | `cat PAID/stage05_paper/manuscript/A6B_VERDICT.txt`; `less …/A6B_TIMELINE_AUDIT.md` | CASE C as documented |
| 7 | **No LLM / network in the released code** | `grep -rniE "openai\|anthropic\|import requests\|import httpx\|api[_-]?key" --include=*.py PAID/` | no matches |
| 8 | **Archive portability** — member paths ASCII, normalized, traversal-free, unique; manifest resolves | `python3 release_tools/verify_archive_paths.py` | `ARCHIVE_PATHS: PASS` |
| 9 | **Submission wording** — banned phrases absent, required phrases present, title matches | `python3 release_tools/verify_manuscript_submission.py` | `MANUSCRIPT_SUBMISSION: PASS` |
| 10 | **Internal references** — no dangling release-document cross-reference | `python3 release_tools/verify_internal_references.py` | `INTERNAL_REFERENCES: PASS` (BROKEN_INTERNAL_REFERENCES=0) |
| 11 | **Availability statements** — data/code availability correct and consistent | `python3 release_tools/verify_availability_statements.py` | `AVAILABILITY_STATEMENTS: PASS` |

Checks 1–11 plus the Stage-01/03/04/05, Changchun, figures and scans are what
`release_tools/run_all_release.py` runs (thirteen verifiers).

## Why check #2 shows 7/8 and why that is correct

`V4 (“unsealing budget intact”)` is an intentional **tripwire**. After the authorised unsealing of
`S03-H10-GREEDY` and the placebo `S03-H01-LIN7`, their `validation_runs` equal 1 **by design**, so the
frozen registry has (legitimately) changed and V4 fires. V2 confirms all four frozen candidate hashes
reproduce, and V1/V3/V5–V8 pass. A 7/8 here is the **expected, healthy** outcome — not a defect.

## Caveat: the verifiers rewrite their own check-log files

The verification scripts are **read-only with respect to every frozen scientific result** (the candidate
registry, the Stage-04 results JSON, the hash-chained log, the spatial split). However, a few of them
rewrite **their own** check files in place — exactly three:

- `PAID/stage04_validation/reports/verification.json`
- `PAID/stage05_paper/reports/verification.json`
- `PAID/stage05_paper/manifests/stage05_hashes.txt`

(Running them also creates `__pycache__/` directories.)

If you need to preserve the **shipped byte-level hashes**, work on a copy of the package. The
hash-chained experiment log is **never** modified by these commands. Consequently, if you re-run the
verifiers and then re-run check #1, you may see those two files reported as changed — that is the
expected effect of the verifiers writing their own logs, not a corruption of frozen science.

## What each check protects

- #1 protects the whole shipping record against silent bit-rot or tampering.
- #2 protects the claim that the frozen candidates are the ones actually searched and evaluated.
- #3 protects the headline numbers (ΔRMSE, p, CI) and the R = 25 sensitivity.
- #4 ties the paper's baselines, figures and cross-checks back to Stage-04 bit-for-bit.
- #5 shows the figures are produced from shipped artefacts, not pasted images.
- #6 is the honesty gate: the deviation is fully public and re-checkable.
- #7 supports the "no LLM needed to reproduce" claim in `MODEL_AND_AGENT_DISCLOSURE.md`.
