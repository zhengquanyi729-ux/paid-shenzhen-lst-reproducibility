# LLM PROVENANCE AUDIT — v1.2.1

**Question.** (a) Does reproducing the results in this package require a large language model (LLM) or
any external service? (b) Does the manuscript's description of "AI usage" match the artefact that is
actually released?

**Method.** Static inspection of the **released** code path only: `PAID/` (Stages 00–05) plus
`release_tools/` (the portable reviewer layer), followed by an **author decision** on the
offline/authoring-time question that the code cannot answer. The audit asks only what the
*distributed artefact* requires to reproduce the published numbers, and whether the *manuscript
wording* agrees with it.

---

## 0. Author decision gate (read this first)

The provenance of run-time behaviour is settled by the code; the provenance of **authoring-time** tool
use cannot be settled from the tree and is therefore an author decision. In this build the author has
recorded the following decision:

> **Decision: CASE B — large-language-model tools were used during the development and writing of this
> work, but no language model forms part of the released scientific pipeline.** The author states that
> no language model was used to design the protocol, to generate or rank candidate expressions, to run
> the validation, or to compute any reported result; no task-specific conclusion was supplied by a
> model. The LLM involvement was confined to authoring/writing support.

The release tooling therefore does **not** infer this from the code (per the governing instruction);
it records the author's decision and enforces the corresponding manuscript wording. The manuscript
AI-usage declaration has been rewritten to match CASE B (the exact text is quoted in §3).

**Release-level status of this item: `LLM_PROVENANCE: RESOLVED (CASE B)`.** The readiness domain is set
`LLM_PROVENANCE_RESOLVED = True` in `release_tools/run_all_release.py` because the manuscript wording
and the released artefact now agree. This is a factual, author-supplied declaration; it does **not**
assert that any party is free of pretraining exposure (see §5).

---

## 1. Evidence — no model, no network in the released code

| Probe | Command | Result |
|---|---|---|
| LLM / API clients (all files) | `grep -rniE "openai\|anthropic\|langchain\|cohere\|ollama\|gemini\|huggingface\|completions?\.create\|chat\.completion\|api[_-]?key\|bearer \|gpt-[0-9]\|claude-[0-9]" PAID/ release_tools/` | **0 matches** |
| LLM / API clients (*.py) | `grep -rniE "openai\|anthropic\|langchain\|api[_-]?key\|gpt-\|claude-\|completion\(" --include=*.py PAID/ release_tools/` | **0 matches** |
| Network clients | `grep -rniE "import requests\|import urllib\|import httpx\|import socket\|urlopen\|\.post\(.*http" --include=*.py PAID/ release_tools/` | **0 call sites**; the two literal `socket`/`urllib` strings in `access_guard.py` are a **deny list** (see below) |
| Cached model output | `find PAID -iname "*response*" -o -iname "*completion*"` | none (only `experiment_log.jsonl`, the hash-chained audit log) |
| Model-call sites | static read of `roles.py`, `core.py`, `s03_02_symreg_search.py`, `independent_validator.py` | none — pure numpy/pandas arithmetic + `cryptography` for the vault |
| Portable layer | static read of all `release_tools/*.py` | none — pure numpy/pandas hashing/arithmetic, no I/O beyond the archive root |

The two `socket`/`urllib` hits in `PAID/stage02_platform/sandbox/access_guard.py` are **not** calls to a
network; they are entries in the sandbox's **capability deny-list** (`socket.connect`,
`socket.getaddrinfo`, `socket.gethostbyname`, `urllib.Request`, `subprocess.Popen`, …) that raise
`AccessDenied('[sandbox] capability blocked: …')`. The sandbox does not merely avoid the network — it
**actively blocks** it. That is the opposite of an LLM dependency.

**Consequence.** Reproducing the reported numbers requires no model:

- **Class 1 — frozen-result verification** (recompute every published number/hash from the shipped
  data): no LLM. This is what `release_tools/run_all_release.py` does.
- **Class 2 — full agent replay** (re-run the search and validation end-to-end): also no LLM in the
  released code path, because the roles are deterministic functions given the frozen seed and inputs.

**No model is required to reproduce the reported numerical results from the frozen release artefacts.**

## 2. What the "agents" actually are in the released code

- The five roles are **functions**: `PAID/stage03_discovery/agents/roles.py`
  (`discovery_propose`, `experiment_dev`, falsification, physics-audit) and, for validation,
  `PAID/stage02_platform/agents/independent_validator.py`.
- The discovery search is a **deterministic greedy forward search with a local hill-climbing pass**
  over the operator set `{var, const, add, sub, mul, div, neg, inv, log, exp}`, maximum expression
  complexity 15, seeded `20260924` (`PAID/stage03_discovery/scripts/s03_02_symreg_search.py`).
- The role "personalities" are **frozen text prompts**
  (`PAID/stage02_platform/prompts/system_prompts.{md,json}`). In the released path these prompts act
  as **policy specifications** enforced by the deterministic search — they forbid direction-preset
  reasoning (no assumption that NDVI monotonically cools, that SVF warms or cools, that building
  height/volume carries a given thermal sign, that any single spatial scale, functional form,
  threshold or interaction is correct, or that past literature / correlation matrices may guide
  discovery). They are not sent to a model at run time.

## 3. The corrected AI-usage disclosure

The submission manuscript's AI-usage declaration now reads (identical text in
`declarations_en.md`, `manuscript_full_en.md` and `manuscript_npj_en.md`):

> The scientific discovery and validation pipeline reported in this study was executed as deterministic
> Python software. Large-language-model tools were used during workflow development and manuscript
> authoring, but no language-model service was called by the archived scientific execution pipeline at
> run time. Candidate evaluation, model fitting, spatial validation, permutation tests, bootstrap
> inference and all reported numerical results are reproducible from the released code, frozen data and
> random seeds without language-model or network access.

This agrees with the released artefact on both points that a reviewer can check: (i) the pipeline that
produced the results is deterministic software with no run-time model call (±a model used for authoring
support, which does not touch the results); and (ii) the numerical results are reproducible without a
model. The former "driven by a large language model" wording has been removed. What changed, and why,
is itemised in `LLM_MANUSCRIPT_CORRECTION.md`.

### 3b. The "Independent Validator" is a software role, not an external auditor

The phrase "independent validator" can be misread as an external human or third-party audit. It is not.
`PAID/stage02_platform/agents/independent_validator.py` is a **separate software process** outside the
discovery sandbox that holds the withheld targets and recomputes the pass conditions in-process.
"Independent" denotes **process separation from the discovery side** (a software boundary), not
institutional independence. (The same point holds for the Stage-04 "second, independently written
implementation" — it is a second piece of software, not a second person. The placebo is proved by
**specification identity**, not by two independent refits; see `NUMERICAL_TOLERANCE_POLICY.md` §2.)

## 4. The audit cases — and their resolution

| Case | Definition | Resolution in v1.2.1 |
|---|---|---|
| **L1** | No LLM in the result path **and** the manuscript wording is accurate about the artefact | **Now applies** — the wording has been corrected to CASE B |
| **L2** | No LLM in the released result path, **but the manuscript overstates / misdescribes AI use** | **Resolved** — the "driven by a large language model" sentence was corrected; the mismatch no longer exists |
| **L3** | An LLM **is** in the released result path | Does not apply — the released path has no model call |
| **L4** | Provenance of **offline** (authoring-time) model use cannot be settled from the artefact | **Answered by the author** — CASE B: authoring/writing support only; no model in protocol design or result generation |

## 5. What the released artefact guarantees, and what it does not

**Guarantees (checkable in this package):**
- The published numbers do not depend on any model being reachable at run time.
- The role boundaries (what each role may read, which region, what it may assume) were frozen before
  the search and are recorded in the hash-chained access log.
- No task-specific directional conclusion was injected into the prompts (the prompts forbid it, and
  the search screens candidate claims against a direction-preset / overreach blacklist).

**Does not guarantee:**
- That no model ever encountered urban-climate literature during pretraining. The operational claim is
  **"no task-specific conclusions were injected and the process is auditable"**, not "no prior
  knowledge". This is unaffected by CASE B.
- That the authors' own authoring tools had no prior exposure. CASE B concerns where the model was used
  (authoring), not what the model may have seen in pretraining.

## 6. Provenance of this file

This audit is derived from a static scan of the shipped tree, reproducible with:

```bash
grep -rniE "openai|anthropic|langchain|api[_-]?key|gpt-|claude-|completion\(" --include=*.py PAID/ release_tools/
# → 0 lines
```

`MODEL_AND_AGENT_DISCLOSURE.md` §2 records the same facts, now reconciled with the corrected
manuscript wording; this audit is the formal record and it sets the release-level flag.

---

**FLAG: `LLM_PROVENANCE: RESOLVED (CASE B)`** — the run-time provenance is settled (no model in the
released path) and the author has declared the authoring-time position; the manuscript wording has been
corrected to match. The `MANUSCRIPT_METHODS_CONSISTENCY_REQUIRED` flag from v1.2 is cleared: the
corrected declaration and the Methods description of the agent roles both describe deterministic
software roles and neither claims a run-time model dependency.
