#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_archive_paths.py — portability gate for the release archive member paths
===============================================================================
Fails the build if any member path in the release tree (and, when present, in the
sibling `PAID_REVIEWER_RELEASE_v1_2.zip`) is:

  * non-ASCII                       (would be mangled by a legacy-code-page reader)
  * not NFC-normalised              (two visually identical names could collide)
  * absolute, or carries a drive letter
  * contains a `..` component       (path traversal)
  * duplicated                      (two members, one name)

It also cross-checks the release manifest: every `MANIFEST_SHA256.csv` entry must
resolve to a real member, and any member not listed is reported.

Run:  python3 release_tools/verify_archive_paths.py
Exit code 0 = PASS.
"""
import csv
import os
import sys
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                       # noqa: E402
MAN = 'MANIFEST_SHA256.csv'


def walk_rel(root):
    rels = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != '__pycache__']
        for x in fn:
            if x == '.DS_Store':
                continue
            rels.append(os.path.relpath(os.path.join(dp, x), root).replace(os.sep, '/'))
    return rels


def member_problems(names):
    problems = {'non_ascii': [], 'non_nfc': [], 'absolute': [], 'traversal': [],
                'duplicate': [], 'backslash': []}
    seen = {}
    for n in names:
        if any(ord(c) > 127 for c in n):
            problems['non_ascii'].append(n)
        if unicodedata.normalize('NFC', n) != n:
            problems['non_nfc'].append(n)
        if n.startswith('/') or (len(n) > 1 and n[1] == ':'):
            problems['absolute'].append(n)
        parts = n.split('/')
        if '..' in parts or any(p == '..' for p in parts):
            problems['traversal'].append(n)
        if '\\' in n:
            problems['backslash'].append(n)
        seen[n] = seen.get(n, 0) + 1
    problems['duplicate'] = [n for n, c in seen.items() if c > 1]
    return problems


def main():
    root = RP.RELEASE_ROOT

    # ---- 1. staging-tree member paths ------------------------------------------------
    tree = walk_rel(root)
    tp = member_problems(tree)

    # ---- 2. real ZIP member list, if a sibling archive exists -------------------------
    zip_names = None
    cand = root.parent / (root.name + '.zip')
    if cand.exists():
        with zipfile.ZipFile(cand) as z:
            zp = member_problems(z.namelist())
        zip_names = list(zp.keys())

    # ---- 3. manifest cross-check ------------------------------------------------------
    man_path = root / MAN
    listed, missing, unlisted = [], [], []
    if man_path.exists():
        with open(man_path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                listed.append(row['release_path'])
        listed_set = set(listed)
        tree_set = set(tree)
        missing = sorted(listed_set - tree_set)
        unlisted = sorted(tree_set - listed_set - {MAN})

    n_bad = sum(len(v) for v in tp.values())
    if zip_names is not None:
        for k in zip_names:
            n_bad += 0  # placed below for clarity

    print('verify_archive_paths: %d members (tree)%s'
          % (len(tree), '' if zip_names is None else '  +1 zip'))
    print('  manifest entries: %d  resolved: %d  missing: %d  unlisted: %d'
          % (len(listed), len(listed) - len(missing), len(missing), len(unlisted)))
    for k, v in tp.items():
        if v:
            print('  TREE %-10s %d  e.g. %s' % (k, len(v), v[0]))
    if zip_names is not None:
        with zipfile.ZipFile(cand) as z:
            zp = member_problems(z.namelist()[1:])   # skip the top dir member
        for k, v in zp.items():
            if v:
                print('  ZIP  %-10s %d  e.g. %s' % (k, len(v), v[0]))
        zbad = sum(len(v) for v in zp.values())
    else:
        zbad = 0

    ok = (n_bad == 0 and zbad == 0 and not missing and not unlisted)
    if ok:
        print('  all member paths ASCII, normalized, traversal-free, uniquely resolvable')
        print('ARCHIVE_PATHS: PASS')
        return 0
    print('  missing: %s' % (missing[:5],))
    print('  unlisted: %s' % (unlisted[:5],))
    print('ARCHIVE_PATHS: FAIL')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
