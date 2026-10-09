# Author action required (public copy)

Items that **only the author** can close before this repository is published as final. The release
tooling deliberately does **not** convert any of these to PASS. This is a cleaned public copy: it keeps
the licence- and metadata-pending items and drops any author-private working detail.

Status vocabulary for these items is exactly: **AUTHOR ACTION REQUIRED** (never PASS).

---

## A-1 — AI-usage / LLM provenance

The author has declared that large-language-model tools were used during the **development and writing**
of this work, but that **no language model forms part of the released scientific pipeline**. The
manuscript AI-usage declaration states, correctly, that *no model is required to reproduce the reported
numerical results from the frozen release artefacts*. This item is **resolved** for the released code;
see `MODEL_AND_AGENT_DISCLOSURE.md` and `LLM_PROVENANCE_AUDIT_v1_2_1.md`.

## A-2 — Changchun redistribution licence

The Changchun 2021 slim analysis-ready table is **reviewer-only**: its redistribution licence is **not
confirmed** (no licence/README accompanied the source layers). Either confirm the licence and
attribution, or keep the table out of any public deposit and publish a derivation recipe instead. The
table is therefore **excluded from this public repository**. See `THIRD_PARTY_DATA_REVIEW.md`.

## A-3 — Code and data licence

**Code: resolved.** The authors have adopted the **MIT License** for author-owned source code only, at
`LICENSES/MIT-CODE.txt` (there is deliberately **no root `LICENSE`** file). **Data: still open.** No
blanket data licence is granted; data and non-code materials are governed by file-specific rights
notices and upstream terms (`docs/LICENSING.md`, `data/shenzhen/RIGHTS_NOTICE.md`,
`figures_source/RIGHTS_NOTICE.md`). The earlier proposed "CC-BY-4.0 for data" was **not** adopted and
must not be claimed. **Author-owned source code is licensed under the MIT License. See
`LICENSES/MIT-CODE.txt`.** The MIT licence does **not** apply automatically to data, figures,
manuscript text, or third-party-derived materials. Remaining author action is the **data** side
(upstream terms / redistribution) and confirmation of the final presentation; **do not claim a final
data licence here until it is confirmed.**

## A-4 — Author metadata

Authors, affiliations, ORCIDs, CRediT roles and funding are not entered. The draft citation template
`docs/CITATION_TEMPLATE.cff` carries `[author …]` placeholders. Fill them before publication.

## A-5 — Repository URL / DOI / commit SHA

No deposit has been performed and no identifier is asserted. No root `CITATION.cff` exists, so no
identifier token is carried in a live citation file; the draft template
(`docs/CITATION_TEMPLATE.cff`) intentionally leaves the optional identifier fields out. The
availability placeholders under `FINAL_*_AVAILABILITY_PLACEHOLDER_v1_2_1.txt` carry `{{token}}`
placeholders (`{{CODE_REPOSITORY_URL}}`, `{{CODE_ARCHIVE_DOI}}`, `{{RELEASE_TAG}}`). After a real,
verified upload, replace them — and re-verify the downloaded archive against `MANIFEST_SHA256.csv`
**before** writing any URL/DOI into the manuscript or into a final root `CITATION.cff`.

---

| item | status |
|---|---|
| A-1 LLM provenance + AI-usage correction | RESOLVED (author case B) |
| A-2 Changchun redistribution licence | AUTHOR ACTION REQUIRED |
| A-3 Code / data licence | AUTHOR ACTION REQUIRED |
| A-4 Author metadata | AUTHOR ACTION REQUIRED |
| A-5 Repository URL / DOI / commit | AUTHOR ACTION REQUIRED |
