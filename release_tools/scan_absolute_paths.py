#!/usr/bin/env python3
"""
scan_absolute_paths.py — assert the reviewer-facing layer carries no author paths
=================================================================================
The historical implementation under `PAID/` keeps its original absolute paths (it is a
frozen record; see `PORTABILITY_AUDIT.md`).  Everything a reviewer is told to read or run
must be free of author-environment paths.  This scanner walks the reviewer layer only —
every file except the historical `PAID/` tree — and fails on any occurrence of an
author mount or machine token.

Two files are intentionally exempt and are reported as skipped:
  * `PORTABILITY_AUDIT.md` — the audit whose purpose is to enumerate these tokens;
  * this scanner — its detector patterns are built from fragments so that the tool itself
    contains none of the literal tokens.

Exit 0 = 0 matches, 1 = matches found.

Run:  python3 release_tools/scan_absolute_paths.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402

# Build the detector tokens from fragments so this file does not itself contain them.
_FRAG = [('/' + 'sessions' + '/'), ('/' + 'mnt' + '/'), ('/' + 'Users' + '/'),
         ('/' + 'home' + '/'), ('/' + 'Volumes' + '/'), ('C:' + '\\\\'),
         ('friendly-' + 'awesome-turing'), ('AI' + '_lst'), ('02 ' + 'changchun')]
RX = re.compile('|'.join(_FRAG))

TEXT_EXT = {'.py', '.md', '.txt', '.json', '.csv', '.cff', '.yml', '.yaml', '.cfg',
            '.ini', '.jsonl', '.tsv', '.rst', '.toml', '.sh'}
ALLOW = {'PORTABILITY_AUDIT.md', 'scan_absolute_paths.py'}


def main():
    findings = []
    skipped = []
    n_scanned = 0
    excluded = os.path.abspath(os.path.join(RP.RELEASE_ROOT, 'PAID'))
    for dirpath, dirnames, filenames in os.walk(RP.RELEASE_ROOT):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        if os.path.abspath(dirpath) == excluded or \
           os.path.abspath(dirpath).startswith(excluded + os.sep):
            dirnames[:] = []
            continue
        for fn in filenames:
            if fn.endswith('.zip') or os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), RP.RELEASE_ROOT)
            if os.path.basename(fn) in ALLOW:
                skipped.append(rel)
                continue
            n_scanned += 1
            try:
                with open(os.path.join(dirpath, fn), encoding='utf-8',
                          errors='replace') as fh:
                    for i, line in enumerate(fh, 1):
                        if RX.search(line):
                            findings.append('%s:%d: %s' % (rel, i, line.strip()[:100]))
            except OSError:
                continue

    print('scan_absolute_paths: scanned %d reviewer-layer files (PAID/ excluded)'
          % n_scanned)
    print('  allowlisted (document the scan): %s' % ', '.join(sorted(skipped)))
    if findings:
        print('  MATCHES (%d):' % len(findings))
        for f in findings:
            print('    ' + f)
        print('\n== Absolute-path scan: FAIL ==')
        return 1
    print('  no author mount / machine tokens in any reviewer-layer file')
    print('\n== Absolute-path scan: PASS (0 matches) ==')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
