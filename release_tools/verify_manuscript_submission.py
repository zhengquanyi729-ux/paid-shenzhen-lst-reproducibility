#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_manuscript_submission.py — wording gate for the submission manuscript copy
=================================================================================
Checks the shipped submission copy only (`manuscript_submission/`): the rendered
`PAID_Shenzhen_LST_manuscript_npj_FINAL.docx` and its markdown sources under
`manuscript_source/`. The historical Stage-05 manuscript inside `PAID/` is a record and
is deliberately NOT checked.

Rules (case-sensitive substring counts):

  * every BANNED phrase  == 0  in the docx AND in the concatenated sources
  * every REQUIRED phrase >= 1 in the docx AND in the concatenated sources
  * the submission TITLE is present in the docx paragraphs

In v1.2.1 the AI-usage declaration is no longer held open: the author recorded case B and the
declaration was corrected, so its wording is part of the ordinary prose rules. See
MANUSCRIPT_PATCH_VERIFICATION.md and LLM_PROVENANCE_AUDIT_v1_2_1.md.

Run:  python3 release_tools/verify_manuscript_submission.py
Exit code 0 = PASS.
"""
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                       # noqa: E402

SUB = RP.RELEASE_ROOT / 'manuscript_submission'
DOCX = SUB / 'PAID_Shenzhen_LST_manuscript_npj_FINAL.docx'
SRC_DIR = SUB / 'manuscript_source'

BANNED = [
    'same qualitative skeleton',
    'real, transferable signal',
    'real but selection-region-specific',
    'locked-region result is real but fragile',
    'L2 level (a spatially robust relationship)',
    'differ in climate and time of year',
    'Verification note',
    'Retrieval method: web search only',
    'validated negative result',
    'reproducible directional pattern',
    'independent audit',
    'prospectively selected candidate',
    'prospectively-selected candidate',
    'no journal-specific format fixed yet',
]
REQUIRED = [
    'locked-region evaluation under a documented protocol deviation',
    'partial conceptual overlap',
    'post-hoc implementation audit',
    'No portable urban thermal law was established',
]
TITLE = ('Auditable autonomous symbolic discovery of urban thermal relationships with '
         'admissibility constraints and separated validation')


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    return re.sub(r'<[^>]+>', '', xml)


def main():
    missing = [p for p in (DOCX,) if not p.exists()]
    if not SRC_DIR.is_dir():
        missing.append(SRC_DIR)
    if missing:
        print('MANUSCRIPT_SUBMISSION: FAIL — missing %s' % (missing,))
        return 1

    docx = docx_text(DOCX)
    srcs = []
    for name in sorted(os.listdir(SRC_DIR)):
        if name.endswith('.md'):
            with open(SRC_DIR / name, encoding='utf-8') as f:
                srcs.append(f.read())
    src = '\n'.join(srcs)

    bad_docx = [(p, docx.count(p)) for p in BANNED if docx.count(p) != 0]
    bad_src = [(p, src.count(p)) for p in BANNED if src.count(p) != 0]
    req_docx = [(p, docx.count(p)) for p in REQUIRED if docx.count(p) < 1]
    req_src = [(p, src.count(p)) for p in REQUIRED if src.count(p) < 1]
    have_title = TITLE in docx

    for p in BANNED:
        print('  BAN  %-46s docx=%d src=%d' % (p, docx.count(p), src.count(p)))
    for p in REQUIRED:
        print('  REQ  %-46s docx=%d src=%d' % (p, docx.count(p), src.count(p)))
    print('  TITLE present in docx: %s' % have_title)

    problems = bad_docx + bad_src + req_docx + req_src
    if problems or not have_title:
        print('  problems: %s' % (problems,))
        print('MANUSCRIPT_SUBMISSION: FAIL')
        return 1
    print('  0 banned phrases; required phrases present; title match')
    print('MANUSCRIPT_SUBMISSION: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
