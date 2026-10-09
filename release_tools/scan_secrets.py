#!/usr/bin/env python3
"""
scan_secrets.py — secret / credential scan over the release archive
===================================================================
Walks every file inside the archive (through the containment guard) and looks for
material that must never ship to a reviewer:

  * key-material filenames (`*.key`, `*.pem`, `*.p12`, `*.pfx`, `id_rsa*`, `*.keystore`,
    `validator_key.bin`, `*.secret`);
  * private-key / cloud-token / API-key patterns in text files
    (PEM blocks, AWS `AKIA…`, OpenAI `sk-…`, GitHub `ghp_…`, Slack `xox…`, JWTs);
  * the frozen vault key file, by name, anywhere in the tree.

The AES vault key is deliberately **not** redistributed, so the expected result is
0 findings.  `{{…}}` placeholder tokens used by the availability statements are not
secrets and are ignored.

Exit code 0 = clean, 1 = findings.

Run:  python3 release_tools/scan_secrets.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402

KEY_NAME_PATTERNS = [
    re.compile(r'\.key$', re.I), re.compile(r'\.pem$', re.I), re.compile(r'\.p12$', re.I),
    re.compile(r'\.pfx$', re.I), re.compile(r'^id_rsa', re.I), re.compile(r'\.keystore$', re.I),
    re.compile(r'validator_key', re.I), re.compile(r'\.secret$', re.I),
]

CONTENT_PATTERNS = [
    (re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----'), 'PEM private key'),
    (re.compile(rb'AKIA[0-9A-Z]{16}'), 'AWS access key id'),
    (re.compile(rb'ghp_[A-Za-z0-9]{36}'), 'GitHub personal access token'),
    (re.compile(rb'xox[baprs]-[A-Za-z0-9-]{10,}'), 'Slack token'),
    (re.compile(rb'sk-[A-Za-z0-9]{20,}'), 'OpenAI-style API key'),
    (re.compile(rb'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), 'JWT'),
]

TEXT_EXT = {'.py', '.md', '.txt', '.json', '.csv', '.cff', '.yml', '.yaml', '.cfg',
            '.ini', '.jsonl', '.tsv', '.rst', '.toml'}


def main():
    findings = []
    n_scanned = 0
    for dirpath, dirnames, filenames in os.walk(RP.RELEASE_ROOT):
        # do not scan the zip itself or __pycache__
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for fn in filenames:
            if fn.endswith('.zip'):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, RP.RELEASE_ROOT)
            if any(p.search(fn) for p in KEY_NAME_PATTERNS):
                findings.append((rel, 'key-material filename'))
            ext = os.path.splitext(fn)[1].lower()
            if ext in TEXT_EXT:
                n_scanned += 1
                try:
                    with open(path, 'rb') as fh:
                        blob = fh.read()
                except OSError:
                    continue
                for pat, label in CONTENT_PATTERNS:
                    if pat.search(blob):
                        findings.append((rel, label))

    print('scan_secrets: scanned %d text files under %s'
          % (n_scanned, RP.RELEASE_ROOT.name))
    if findings:
        print('  FINDINGS (%d):' % len(findings))
        for rel, label in findings:
            print('    %-60s %s' % (rel, label))
        print('\n== Secrets scan: FAIL ==')
        return 1
    print('  no key-material filenames, no private-key / cloud-token / API-key patterns')
    print('\n== Secrets scan: PASS (0 findings) ==')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
