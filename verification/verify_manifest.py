#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_manifest.py — release-integrity checker for the PAID Reviewer Reproducibility Package.

Recomputes SHA-256 for every file listed in MANIFEST_SHA256.csv (relative to the
release root) and reports any mismatch, missing file, or unlisted file.

Usage:
    python3 verification/verify_manifest.py            # from the release root
    python3 verification/verify_manifest.py <root>     # explicit release root

Exit code 0 = all OK ; 1 = at least one problem.
"""
import os, sys, csv, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
MAN = os.path.join(ROOT, 'MANIFEST_SHA256.csv')
SELF = 'MANIFEST_SHA256.csv'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    if not os.path.isfile(MAN):
        print('FAIL: manifest not found at', MAN); return 1
    listed = {}
    with open(MAN, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            listed[r['release_path']] = r['sha256']
    bad = []
    for rel, want in listed.items():
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            bad.append((rel, 'MISSING'))
        else:
            got = sha256(p)
            if got != want:
                bad.append((rel, 'HASH %s != %s' % (got, want)))
    # unlisted files (informational; MANIFEST_SHA256.csv is intentionally excluded)
    present = set()
    for dp, dn, fn in os.walk(ROOT):
        for x in fn:
            r = os.path.relpath(os.path.join(dp, x), ROOT)
            if r != SELF:
                present.add(r)
    unlisted = sorted(present - set(listed))
    print('manifest entries : %d' % len(listed))
    print('files present    : %d' % len(present))
    print('unlisted files   : %d' % len(unlisted))
    for u in unlisted:
        print('   unlisted:', u)
    if bad:
        print('MISMATCHES       : %d' % len(bad))
        for rel, why in bad[:50]:
            print('   ', rel, '->', why)
        print('RESULT: FAIL')
        return 1
    print('RESULT: PASS (all listed hashes verified)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
