# Pre-release archive status

**Date:** 2026-10-09. This note records the status of the public release ZIP that was built **before**
the Git EOL / byte-preservation fix described in `docs/EOL_BYTE_IDENTITY_AUDIT.csv` and
`docs/EOL_MANIFEST_STABILITY_CHECK.csv`. It changes no scientific value and performs no git mutation.

## The archive

| Item | Value |
|---|---|
| Archive | `PAID_PUBLIC_RELEASE_v1_2_1.zip` |
| SHA-256 | `fbe821bbd7a737d60eaa9d4a8e0ed82caf12a070a3f0c0dfdb20e649ccadcbe1` |
| Size | 38,361,006 bytes |
| Built from | tracked working-tree content at Git HEAD `876768cd2ab1ea97c201a11e40966d2cf50045d4` |
| Status | **PROVISIONAL_PRE_EOL_FIX_ARCHIVE** |

The archive is **not deleted**. It is a valid, self-consistent package: running
`verification/verify_manifest.py` on the extracted tree reports **PASS** (325 listed files, 0
unlisted), and both the secret scan and the absolute-path scan report **PASS**.

## Why it cannot be the final v1.2.1 release archive

At the time it was created, the repository's `.gitattributes` carried `* text=auto`. Under that rule,
Git normalises line endings on checkout, so for **18 CSV files** the Git HEAD *blob* is **LF** while the
frozen, manifest-certified working-tree bytes are **CRLF**. `git archive` (and therefore GitHub's
automatically generated **"Source code" zip/tar.gz** for a tag) emits the **LF** blob form, which does
**not** match the bytes certified by `MANIFEST_SHA256.csv`. This is a **Git byte-provenance /
archive-equivalence** problem only.

- It is **not** a scientific-content error. No value, table, registry, result or Region-C datum is
  wrong in this archive.
- The archive's own internal manifest **does** verify, because it was built from the working-tree
  (CRLF) bytes and therefore shipped the same bytes the manifest certifies.
- The mismatch appears only between that archive and the *canonical Git object* form of those 18 files.

## What the fix does, and what the final archive must be

A byte-preservation policy (**18 precise `-text` rules**, one per affected path) has been **prepared in
the working tree** of `.gitattributes` so Git stores the frozen CRLF bytes as the canonical blob,
making a fresh clone / `git archive` / GitHub Source-code download **byte-identical** to the manifest
(see `docs/EOL_BYTE_IDENTITY_AUDIT.csv` and `docs/EOL_MANIFEST_STABILITY_CHECK.csv`). The prepared
change is **not yet committed** (this round performs no git mutation). `.gitattributes` moves from
`1a1dbe176bc233b499d35a57db7513f2941c99ab9759f177830c9149be99005b` to
`ecf02661cec82cd5e6e15fa13523bff7851d354d140f8ad4f5f285d939a6cb8a`; that is the only manifest-listed
hash that changes by design — all 18 preserved files keep their existing canonical manifest hashes.

**The final v1.2.1 archive must be rebuilt from the exact Git commit that carries this EOL-preservation
fix**, not from this provisional archive. This provisional archive is retained only as the pre-fix
record. Do not use it as the v1.2.1 GitHub/Zenodo deposit artefact.

## Reviewer package

The confidential reviewer package (`PAID_REVIEWER_RELEASE_v1_2_1.zip`, SHA-256
`146722cac3f7fe163bdc65e9940cb924ff27f8a3b2052c7dc6998697e41efe76`) is unaffected and must never be
attached to a public GitHub Release (it contains the restricted Changchun row-level table).

*This note is a factual release-engineering record; it is not legal advice.*
