# MODEL AND AGENT DISCLOSURE

This document tells a reviewer exactly what the "agents" in this package are, how the search was
bounded, and — critically — **whether an LLM must be available to reproduce the results**. It is
written to be checkable against the shipped code, not to be taken on trust.

---

## 1. What the "agents" are, in the shipped artefact

The PAID pipeline is described in the manuscript as a multi-agent discovery system. In the **code that
is shipped in this package**, the roles are implemented as **deterministic Python functions**, not as
calls to a language-model service:

| Role | Where it lives | What it does |
|---|---|---|
| Discovery Agent | `PAID/stage02_platform/agents/discovery_agent.py`, `PAID/stage03_discovery/agents/roles.py :: discovery_propose` | proposes candidate expressions inside the frozen operator space |
| Experiment Agent | `.../experiment_agent.py`, `roles.py :: experiment_dev` | fits/evaluates a candidate on Region A, records dev evidence |
| Falsification Agent | `.../falsification_agent.py`, `roles.py` | runs the negative controls and the permutation test |
| Physics Auditor | `.../physics_auditor.py` | checks dimensional/physical admissibility |
| Independent Validator | `.../independent_validator.py` | unseals Region C, recomputes the pass conditions in-process |

The **role personalities are frozen text prompts** (`PAID/stage02_platform/prompts/system_prompts.md`
and `.json`), but in the released code path those prompts define *policy constraints* (what a role may
and may not assume) that are enforced by the deterministic search, not by asking a model to generate an
answer at run time.

### The checkable claim: no network / LLM dependency in the released code

A reviewer can verify that **no external model or network service is called anywhere in `PAID/`**:

```bash
grep -rniE "openai|anthropic|import requests|import urllib|import httpx|import socket|api[_-]?key|gpt-|claude-" \
     --include=*.py PAID/
# → no matches (0 lines)
```

There are no API keys, no HTTP clients, and no model endpoints in the released code. The frozen search
is a **deterministic greedy forward search with a local-refinement pass** over the operator set
`+ − × ÷ exp log`, with maximum complexity 15
(`PAID/stage03_discovery/scripts/s03_02_symreg_search.py`), seeded with `20260924`.

**Consequence for reproducibility:** the two verification classes below hold.

- **Class 1 — frozen-result verification** (recompute every published number and hash from the shipped
  data): **no LLM needed**, runs in minutes (see `QUICKSTART.md`).
- **Class 2 — full agent replay** (re-run the discovery search and the validation end-to-end): also
  **no LLM needed** in the released code path — it is deterministic given the frozen seed and inputs,
  because the roles are functions, not model calls.

## 2. What the manuscript claims about AI use (and how it squares with the code)

The manuscript's AI-usage declaration has been corrected in this build (author case **B**): it now
states that the scientific pipeline was executed as deterministic Python software and that
large-language-model tools were used only for authoring/writing support, with no language-model service
called at run time. This agrees with the five roles that this package implements as deterministic Python
functions. The code is complete and self-contained (every published number reproduces from it, §1). The
reconciliation is:

- The **released artefact** contains the deterministic implementations and the frozen prompts that
  define the roles' behaviour. Whatever interactive tooling was used during development, **the results
  in this package do not depend on any model being reachable at run time**: the numbers reproduce from
  the shipped code, data and seed alone.
- The prompts explicitly **forbid injecting directional conclusions** — the roles may not assume that
  NDVI cools, that SVF warms/cools, that height/volume has a given thermal sign, or that any particular
  scale, functional form or interaction is correct (`system_prompts.md`, §3.2 "无方向预设禁令"). The
  released `roles.py` additionally screens candidate claims against a direction-preset / overreach
  blacklist (`_DIR_PRESET`, `_OVERREACH`).
- The system may have encountered relevant urban-climate literature during pretraining. The operational
  claim is therefore **not** "the system had no prior knowledge" but "**no task-specific conclusions
  were injected into the prompts**, all role boundaries are frozen before the search, and the whole
  process is auditable through the hash-chained log."

This is formally recorded as **author case B (resolved)** in `LLM_PROVENANCE_AUDIT_v1_2_1.md`; the exact
wording change is itemised in `LLM_MANUSCRIPT_CORRECTION.md` and the applied patch is recorded in
`MANUSCRIPT_PATCH_VERIFICATION.md`. The release sets `LLM_PROVENANCE_RESOLVED = True`; the earlier
`MANUSCRIPT_METHODS_CONSISTENCY_REQUIRED` flag is cleared because the corrected declaration and the Methods
description of the roles now agree (both describe deterministic software roles).

## 3. What the system did **not** set for itself

The following were **frozen by the authors before the search** and are not chosen by any agent:
the spatial partition (A/B/Buffer/C and R = 15 cells), the primary endpoint (Region-C ΔRMSE vs
Baseline A), the pass conditions, the fit/search budget, the admissibility (hard) constraints, and the
operator set. See `PAID/stage01_protocol/PREREGISTRATION.md`,
`PAID/stage01_protocol/protocol/validation_protocol.json`, and
`PAID/stage01_protocol/constraints/`.

## 4. Auditability

Every experiment is written **append-only** to
`PAID/stage02_platform/logs/experiment_log.jsonl`, a hash chain in which each record carries `seq`,
`hash` and `prev`; failed results are never overwritten. The log is frozen at **1,259 records**
(SHA-256 `b10cc702…5488`). The verification scripts in this package **never modify** this log.

The access history of the withheld region — including the protocol deviation — is disclosed separately
in `PROTOCOL_DEVIATION.md` and in `PAID/stage05_paper/manuscript/A6B_TIMELINE_AUDIT.md`.

## 5. Summary for a reviewer

- Agents = deterministic Python functions + frozen prompts; **no model API in the released code**.
- Reproducing every published number requires **no LLM**; it requires only `numpy`/`pandas`/`matplotlib`/`Pillow`.
- The roles could not inject directional conclusions (frozen prompts + claim screening).
- The search was bounded by author-frozen partition, endpoint, budget and constraints.
- AI/LLM usage is declared in the manuscript; the operational guarantee is **auditable process**, not
  absence of pretraining.
