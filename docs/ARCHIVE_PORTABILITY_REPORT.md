# ARCHIVE PORTABILITY REPORT — v1.2.1

**Scope.** Two portability questions that broke or threatened v1.1: (1) does the ZIP contain member
paths a UTF-8-hostile extraction toolchain would mangle or refuse, and (2) do two independent tools
see the **same** member set? This report records the fix (carried from v1.2) and how the two-tool check was run for v1.2.1. The
governing principle: **no science changes** — only member names, and only where a name was non-ASCII.

**Why the check is list-only, not a second extraction.** The v1.1 build attempted two *full* extractions of the
~45 MB archive into `/tmp`; that filled the sandbox filesystem and aborted the build. v1.2 therefore
compares the two tools' **member lists** (`namelist()` vs `unzip -Z1`) — which is exactly the surface
the portability question is about — and performs **one** real extraction (the clean-room test in
`CLEANROOM_TEST_REPORT_v1_2_1.md`). The archive is opened and read, never written out twice.

---

## 1. The v1.1 defect

v1.1 shipped exactly **one** non-ASCII release path:

```
PAID/stage00_data_audit/reports/evidence/过程__image1.png
```

Every other member was ASCII. The single non-ASCII name is enough to break extraction on toolchains
whose ZIP reader assumes a legacy code page: the member is either refused, or written under a mangled
name that then fails the manifest hash check. This is a *packaging* defect, not a data defect — the
bytes are fine.

## 2. The fix (carried from v1.2)

1. **ASCII alias, byte-identical.** The same bytes now ship under the ASCII alias
   `process_image1.png`. The two names share one SHA-256, so the object is provably unchanged:

   | Release path (v1.2.1) | Source path (v1.1) | SHA-256 | bytes_identical |
   |---|---|---|---|
   | `PAID/…/evidence/process_image1.png` | `PAID/…/evidence/过程__image1.png` | `ef7ccd98658889a2775d94cbe206f692b6dac2e1ce154866e354e4c0d7590a6f` | TRUE |

   The mapping is recorded in `FILENAME_MAP.csv`; `RELEASE_FILE_INVENTORY.csv` carries the
   `source_path` column.

2. **A build-time gate.** `release_tools/verify_archive_paths.py` fails the build on any member that
   is **non-ASCII**, **non-normalized (NFC)**, **contains `..`**, **is absolute or has a drive
   letter**, or **appears twice**. It also checks that every `MANIFEST_SHA256.csv` entry resolves to a
   real member and reports any unlisted member, and — when a sibling `PAID_REVIEWER_RELEASE_v1_2_1.zip`
   is present — checks the **real ZIP member list**, not just the staging tree.

3. **ASCII-only as a stated policy.** The README and `RELEASE_NOTES_v1_2_1.md` state the rule so
   future additions do not reintroduce a non-ASCII name.

## 3. The two-tool member-list check (list-only)

The final ZIP's member list was read with **two independent toolchains** — no extraction, no writes:

```bash
# Method 1 — Python standard library
python3 -c "import zipfile;print('\n'.join(zipfile.ZipFile('PAID_REVIEWER_RELEASE_v1_2_1.zip').namelist()))" > names_py.lst

# Method 2 — Info-ZIP
unzip -Z1 PAID_REVIEWER_RELEASE_v1_2_1.zip > names_unz.lst
```

The two lists were then normalised (trailing `/` on directory entries kept) and compared:

```
members (Python zipfile namelist) : 394  (328 files + 66 directory entries)
members (system unzip -Z1)        : 394
diff of the two sorted lists      : empty  (identical)
non-ASCII member paths            : 0
duplicate member names            : 0
```

Because both tools report the identical member set and neither mangles or drops the ASCII-only names,
the portability defect is closed. The **byte-level** confirmation is the single clean-room extraction
(one `unzip`, one verification) recorded in `CLEANROOM_TEST_REPORT_v1_2_1.md`:

```
$ python3 verification/verify_manifest.py
RESULT: PASS (all listed hashes verified)

$ python3 release_tools/run_all_release.py
13/13 verifiers passed
RELEASE VERIFICATION: ALL PASS
```

## 4. What this establishes

- The two tools see the **same** member list, and no member path is non-ASCII, non-normalized,
  traversal-bearing, absolute, or duplicated.
- The single extraction that *was* performed verifies completely (manifest PASS, 13/13 verifiers).
- The fix is **naming-only**: the underlying object keeps its SHA-256, so nothing in the frozen
  record changed.

## 5. Residual notes

- The alias affects only the **release layer**. The historical `PAID/` tree in the manuscript and the
  v1.1 archive keep the original name; `FILENAME_MAP.csv` is the bridge.
- Member **ordering** is deterministic (sorted), timestamps are fixed at `2026-10-09 00:00:00`, and
  entries are written with Unix file modes so the ZIP is reproducible modulo the (excluded) build
  noise.
- Directory entries (the 66 members ending in `/`) are emitted explicitly so the archive unpacks to a
  complete tree even on tools that do not infer intermediate directories.
