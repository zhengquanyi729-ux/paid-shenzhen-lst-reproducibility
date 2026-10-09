# Code licensing audit — paid-shenzhen-lst-reproducibility

**Scope.** Whether the *code* in this repository can be released under a permissive licence
(a proposed MIT), independently of the data-rights question. This is a release-engineering audit, not
legal advice.

**Conclusion: `MIT_CANDIDATE_SUPPORTED`** for the source code as an author work, subject to the open
items in §5. This says nothing about the data, whose rights are assessed separately in
`SHENZHEN_LICENSING_REVIEW.md` and `UPSTREAM_DATA_RIGHTS_MATRIX.csv`.

---

## 1. What "code" covers

Two layers, both author-written:

| Layer | Files | Notes |
|---|---|---|
| **Portable verifier layer** | `release_tools/*.py` (18), `release_tools/__init__.py` | The layer a reviewer actually runs. Depends only on the Python standard library plus `numpy` and `pandas`. |
| **Historical implementation** | `PAID/**/*.py` (~61 scripts, agents, libs, renderers) | Frozen Stage 00–05 record. Kept verbatim; imports absolute author paths and is not meant to be executed by a third party. |
| **Integrity checker** | `verification/verify_manifest.py` | Standard library only. |

## 2. Third-party source-code contamination scan

Searched for `copied from`, `adapted from`, `derived from`, `vendor`, `Copyright (c)`, `SPDX-License`,
`GPL`, plus the `License`/`Copyright` markers across all `.py` files.

- **No vendored third-party source.** Every "copied from" / "derived from" marker points at the
  authors' **own** PAID code — e.g. `release_tools/release_model.py` ("copied from
  `PAID/stage03_discovery/agents/core.py`"), `release_tools/release_bmlib.py` ("Derived from the
  historical `PAID/stage05_paper/scripts/bmlib.py`"). These are internal refactors, not imports of
  external code.
- **No copyleft marker.** Zero occurrences of `GNU General Public License`, `GPL`, `LGPL`, `AGPL`,
  `copyleft` or `Affero` anywhere in the `.py` files.
- No generated/snippet code from an external project is embedded.

## 3. Runtime dependencies and their licences

Imports actually present in the tree:

| Dependency | Where used | Upstream licence family | Copyleft? |
|---|---|---|---|
| Python standard library | everywhere | PSF | no |
| `numpy` | portable layer, historical | BSD-3-Clause | no |
| `pandas` | portable layer, historical | BSD-3-Clause | no |
| `matplotlib` | historical (figures) | matplotlib (BSD-compatible) | no |
| `Pillow` (PIL) | historical | HPND / MIT-like | no |
| `python-docx` (`docx`) | historical (paper renderer) | MIT | no |
| `cryptography` | historical (vault) | Apache-2.0 / BSD-3-Clause | no |
| `imageio` | historical | BSD-2-Clause | no |

The certified environment (`requirements-lock.txt`) pins only `numpy`, `pandas`, `matplotlib`,
`Pillow` and their transitive dependencies (all permissive: `python-dateutil` BSD, `pytz` MIT, `six`
MIT, `contourpy` BSD, `cycler` BSD, `fonttools` MIT, `kiwisolver` BSD, `packaging` BSD/Apache-2.0,
`pyparsing` MIT, `scipy-openblas64` BSD-3-Clause).

Because the code links these only as libraries (via imports) and ships no derivative of their source,
the author's own code may be licensed independently. No dependency imposes a copyleft obligation on
this repository.

## 4. Why MIT is a supportable candidate for the code

- All code is author-written; nothing is vendored.
- All runtime dependencies are permissive; none is copyleft.
- The repository ships no third-party source-code derivative.
- MIT imposes no share-alike obligation and is compatible with the repository also distributing data
  under a *different*, upstream-respecting arrangement (the data licence is a separate question).

## 5. Open items (do not convert to PASS)

1. **The final licence is the author's decision.** This audit supports MIT *as a candidate*; it does
   not assign a licence. [Dated note, 2026-10-09: the Option-C implementation has since been applied —
   the authors have adopted MIT for author-owned **code only**, at `LICENSES/MIT-CODE.txt`, with **no
   root `LICENSE`** file and **no blanket data licence**. This audit still grants no rights of its own;
   see `LICENSING_IMPLEMENTATION_RECORD.md` and `LICENSING.md`. The original finding below is retained
   as the pre-implementation record.] There was deliberately **no `LICENSE` file** in the repository
   at the time of this audit; the status is stated in `LICENSE_STATUS.md` and this audit grants no
   rights.
2. **Historical `PAID/` path-strings.** The frozen scripts contain absolute author-machine paths. That
   is a *portability/provenance* matter (documented in `ARCHIVE_PORTABILITY_REPORT.md`), not a licence
   defect, but it should be acknowledged if the historical tree is published.
3. **Code-vs-data coupling.** MIT on the code does **not** relicense the shipped data tables. A reader
   must be told explicitly that the code licence applies to the code only, and that the data carry
   their own (currently unresolved) rights. See `PUBLIC_RELEASE_LICENSING_GATE.md`.
4. **No fabricated licence.** Nothing in this repository asserts a licence that does not exist.

---

*Companion artefacts: `SHENZHEN_LICENSING_MATRIX.csv`, `SHENZHEN_LICENSING_REVIEW.md`,
`AUTHOR_CREATED_MATERIALS_MATRIX.csv`, `UPSTREAM_DATA_RIGHTS_MATRIX.csv`,
`PUBLIC_RELEASE_LICENSING_GATE.md`.*
