#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_internal_references.py — every release-document cross-reference resolves
===============================================================================
The reviewer layer is a set of documents that reference one another (README →
RELEASE_QA → CLEANROOM_TEST_REPORT → FINAL_*_PLACEHOLDER, and so on). After a
version rename it is easy to leave a dangling reference to a file that no longer
exists (e.g. a leftover `*_v1.1` report). This scanner builds an index of every
file actually shipped and then walks the reviewer-facing text files, extracting
every file-like cross-reference, and fails on any reference whose target is not
present in the archive.

Scope: the reviewer layer only. The historical `PAID/` tree is a frozen record and
keeps its own internal references, so it is excluded from the scan (but its files
still populate the index, so a reviewer-layer link into `PAID/` resolves).

References are matched as tokens ending in a document extension
(`.md`, `.txt`, `.cff`); a reference with a path separator is resolved against the
release root, otherwise the basename is matched against the shipped basenames.
A small allowlist covers references that are deliberately external to the archive
(e.g. a template the author will fill in at upload time).

Exit 0 = BROKEN_INTERNAL_REFERENCES=0.

Run:  python3 release_tools/verify_internal_references.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                       # noqa: E402

# file-like tokens we treat as cross-references (documents shipped in the release)
REF_RX = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_.\-/]*\.(?:md|txt|cff)')

SCAN_EXT = {'.md', '.txt', '.cff'}
# files whose *purpose* is to quote or enumerate references are skipped as sources
SKIP_SOURCES = {'verify_internal_references.py'}

# References that are intentionally external to this archive (author fills them in,
# or they name a future upload artefact). Match on basename.
EXTERNAL_ALLOW = {
    'README.md',                 # generic; where a repository will host one
    'LICENSE',                   # licence text may name a file the host adds
}


def build_index():
    """Return (set of release-relative POSIX paths, set of basenames)."""
    paths, names = set(), set()
    for dirpath, dirnames, filenames in os.walk(RP.RELEASE_ROOT):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for fn in filenames:
            if fn.endswith('.zip'):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, RP.RELEASE_ROOT).replace(os.sep, '/')
            paths.add(rel)
            names.add(fn)
    return paths, names


def scan_sources():
    """Yield (relative POSIX path, line number, line) for reviewer-layer text files."""
    excluded = os.path.abspath(os.path.join(RP.RELEASE_ROOT, 'PAID'))
    root = os.path.abspath(str(RP.RELEASE_ROOT))
    for dirpath, dirnames, filenames in os.walk(RP.RELEASE_ROOT):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        ad = os.path.abspath(dirpath)
        if ad == excluded or ad.startswith(excluded + os.sep):
            dirnames[:] = []
            continue
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in SCAN_EXT:
                continue
            if fn in SKIP_SOURCES:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, '/')
            if rel.startswith('PAID/'):
                continue
            try:
                with open(full, encoding='utf-8', errors='replace') as fh:
                    for i, line in enumerate(fh, 1):
                        yield rel, i, line
            except OSError:
                continue


def main():
    paths, names = build_index()
    basenames = {os.path.basename(p) for p in paths}
    broken = []
    n_refs = 0
    seen = set()
    files_seen = set()
    for rel, lineno, line in scan_sources():
        files_seen.add(rel)
        for tok in REF_RX.findall(line):
            tok = tok.strip()
            if not tok:
                continue
            n_refs += 1
            base = os.path.basename(tok)
            if base in EXTERNAL_ALLOW:
                continue
            if '/' in tok:
                norm = tok.lstrip('./').replace(os.sep, '/')
                if norm in paths or base in basenames:
                    continue
            else:
                if base in basenames:
                    continue
            key = (rel, tok)
            if key in seen:
                continue
            seen.add(key)
            broken.append((rel, lineno, tok))

    print('verify_internal_references: indexed %d shipped files' % len(paths))
    print('  scanned %d reviewer-layer documents, %d cross-reference tokens'
          % (len(files_seen), n_refs))
    print('  BROKEN_INTERNAL_REFERENCES=%d' % len(broken))
    if broken:
        print('  broken references:')
        for rel, lineno, tok in broken[:60]:
            print('    %s:%d -> %s' % (rel, lineno, tok))
        return 1
    print('  every referenced document/placeholder is present in the archive')
    print('INTERNAL_REFERENCES: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
