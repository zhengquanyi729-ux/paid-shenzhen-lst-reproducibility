#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_availability_statements.py — data/code availability must be correct and consistent
==========================================================================================
The data- and code-availability statements exist in several places (the manuscript
declarations, the submission copy, the manuscript-ready placeholders and the two
redirect stubs). This verifier asserts that each carries the corrected wording and
that none carries a stale or over-claiming phrase.

Rules checked:

  * the manuscript Data-availability paragraph states the *complete 32,748-cell*
    split and marks Region C as *scientifically spent under Protocol V1*;
  * the same paragraph never claims the raw source archive is redistributed and
    never claims a pristine confirmatory holdout;
  * the Code-availability paragraph states that reproducing the numbers needs
    *no LLM or network*, and the placeholder carries the exact sentence
    "No model is required to reproduce the reported numerical results from the
    frozen release artefacts.";
  * the placeholders keep the {{TOKEN}} markers (nothing is fabricated) and the
    data placeholder gives the Region-C n = 2,987;
  * both redirect stubs point at their `*_v1_2_1` placeholder and carry no stale
    "v1.1 supersedes this file" text;
  * the shipped submission DOCX contains the corrected Data-availability wording.

This is a prose/consistency gate only; it touches no frozen number.

Run:  python3 release_tools/verify_availability_statements.py
Exit code 0 = PASS.
"""
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                       # noqa: E402

ROOT = RP.RELEASE_ROOT

DECL_TREE = 'PAID/stage05_paper/manuscript/declarations_en.md'
DECL_SUB = 'manuscript_submission/manuscript_source/declarations_en.md'
DATA_PH = 'FINAL_DATA_AVAILABILITY_PLACEHOLDER_v1_2_1.txt'
CODE_PH = 'FINAL_CODE_AVAILABILITY_PLACEHOLDER_v1_2_1.txt'
DATA_STUB = 'FINAL_DATA_AVAILABILITY.txt'
CODE_STUB = 'FINAL_CODE_AVAILABILITY.txt'
DOCX = 'manuscript_submission/PAID_Shenzhen_LST_manuscript_npj_FINAL.docx'

# banned anywhere in the availability documents — stale or over-claiming wording
GLOBAL_BANNED = [
    'no model was required to produce',
    'for all 32,748 cells',
    'v1.1 supersedes this file',
    'supersedes this file',
    'prospectively selected candidate',
    'prospectively-selected candidate',
    'driven by a large language model',
]

# (relative path, [required substrings], [forbidden substrings])
CHECKS = [
    (DECL_TREE,
     ['complete 32,748-cell Shenzhen spatial split',
      'Regions A, B and C',
      'scientifically spent under Protocol V1',
      'no LLM or network access'],
     ['is included in the core release',
      'pristine confirmatory holdout that remains']),
    (DECL_SUB,
     ['complete 32,748-cell Shenzhen spatial split',
      'Regions A, B and C',
      'scientifically spent under Protocol V1',
      'no LLM or network access'],
     ['is included in the core release',
      'pristine confirmatory holdout that remains']),
    (DATA_PH,
     ['complete 32,748-cell Shenzhen spatial split',
      '233 x 362 analysis grid',
      'scientifically spent under Protocol V1',
      'n = 2,987',
      '{{DATA_ARCHIVE_DOI}}',
      '{{DATA_REVIEWER_LINK}}'],
     []),
    (CODE_PH,
     ['{{CODE_REPOSITORY_URL}}',
      '{{CODE_ARCHIVE_DOI}}',
      '{{CODE_COMMIT_SHA}}',
      '{{RELEASE_TAG}}',
      'No model is required to reproduce the reported numerical results '
      'from the frozen'],
     []),
    (DATA_STUB,
     [DATA_PH],
     []),
    (CODE_STUB,
     [CODE_PH],
     []),
]


def read(path):
    with open(os.path.join(str(ROOT), path), encoding='utf-8', errors='replace') as fh:
        return fh.read()


def docx_text(path):
    with zipfile.ZipFile(os.path.join(str(ROOT), path)) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    return re.sub(r'<[^>]+>', '', xml)


def main():
    problems = []
    for rel, need, forbid in CHECKS:
        full = os.path.join(str(ROOT), rel)
        if not os.path.isfile(full):
            problems.append('MISSING FILE: %s' % rel)
            print('  %-52s MISSING' % rel)
            continue
        text = read(rel)
        miss = [s for s in need if s not in text]
        bad = [s for s in forbid if s in text]
        for s in GLOBAL_BANNED:
            if s in text and s not in forbid:
                bad.append(s)
        if miss:
            problems.append('%s: missing required %s' % (rel, miss))
        if bad:
            problems.append('%s: forbidden present %s' % (rel, bad))
        status = 'ok' if (not miss and not bad) else 'FAIL'
        print('  %-52s %s' % (rel, status))
        for s in miss:
            print('      - missing: %r' % s)
        for s in bad:
            print('      - forbidden: %r' % s)

    # DOCX must carry the corrected data-availability wording.
    dfull = os.path.join(str(ROOT), DOCX)
    if not os.path.isfile(dfull):
        problems.append('MISSING FILE: %s' % DOCX)
        print('  %-52s MISSING' % DOCX)
    else:
        dtext = docx_text(DOCX)
        dmiss = [s for s in ('32,748-cell', 'scientifically spent under Protocol V1')
                 if s not in dtext]
        if dmiss:
            problems.append('%s: docx missing %s' % (DOCX, dmiss))
        print('  %-52s %s' % (DOCX + ' (docx)', 'ok' if not dmiss else 'FAIL'))
        for s in dmiss:
            print('      - docx missing: %r' % s)

    if problems:
        print('\nAVAILABILITY_STATEMENTS: FAIL (%d problems)' % len(problems))
        return 1
    print('\nAVAILABILITY_STATEMENTS: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
