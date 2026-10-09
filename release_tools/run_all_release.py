#!/usr/bin/env python3
"""
run_all_release.py — run the whole portable verification layer and report readiness
===================================================================================
Executes every reviewer-portable verifier in the archive, in order, as isolated
subprocesses. No AES key, no network, no author tree.

It prints two blocks:

  1. the per-verifier summary table, ending with
        RELEASE VERIFICATION: ALL PASS          (or FAILURES PRESENT)
  2. three INDEPENDENT readiness domains and the combined gate:

        TECHNICAL_REPRODUCIBILITY_READY   every technical verifier passes
        MANUSCRIPT_CONSISTENCY_READY      submission wording patches pass AND title matches
                                          AND the AI/LLM method wording is resolved (v1.2.1: True)
        DISTRIBUTION_READY                licences resolved AND no secrets AND the Changchun
                                          sharing status permits the actual archive contents
        JOURNAL_REVIEW_PACKAGE_READY      all three True

Unresolved AUTHOR items are never turned into PASS. See AUTHOR_ACTION_REQUIRED_v1_2_1.md.

Exit code 0 only if every verifier passes.

Environment:
  * S05_RF=1          also recompute the numpy RF/GBM Baseline-B numbers (~21 s)
  * CC_SKIP_GREEDY=1  skip the Changchun greedy re-discovery (~8 s)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402

# (domain label, script, where: 'tools' = release_tools/, 'verification' = ../verification/)
TOOLS = [
    ('ARCHIVE_PATHS',       'verify_archive_paths.py',       'tools'),
    ('MANIFEST',            'verify_manifest.py',            'verification'),
    ('STAGE01',             'verify_stage01_release.py',     'tools'),
    ('STAGE03',             'verify_stage03_release.py',     'tools'),
    ('STAGE04',             'verify_stage04_release.py',     'tools'),
    ('STAGE05',             'verify_stage05_release.py',     'tools'),
    ('CHANGCHUN_NUMERICS',  'verify_changchun_release.py',   'tools'),
    ('FIGURES',             'verify_figures_release.py',     'tools'),
    ('MANUSCRIPT_SUBMISSION', 'verify_manuscript_submission.py', 'tools'),
    ('INTERNAL_REFERENCES', 'verify_internal_references.py',  'tools'),
    ('AVAILABILITY',        'verify_availability_statements.py', 'tools'),
    ('SECRETS',             'scan_secrets.py',               'tools'),
    ('ABSOLUTE_PATHS',      'scan_absolute_paths.py',        'tools'),
]

# ---- AUTHOR-ACTION state (kept False until the AUTHOR resolves the item) -------------
LLM_PROVENANCE_RESOLVED   = True    # author case B recorded; manuscript AI-usage declaration corrected
CHANGCHUN_RIGHTS_RESOLVED = False   # redistribution licence not confirmed
LICENCE_RESOLVED          = False   # code/data licence not confirmed
AUTHOR_METADATA_RESOLVED  = False   # authors / ORCID / CRediT / funding not entered


def _script_path(script, where):
    base = os.path.dirname(os.path.abspath(__file__))
    if where == 'tools':
        return os.path.join(base, script)
    return os.path.join(base, '..', 'verification', script)


def main():
    print('=' * 74)
    print('PAID reviewer release v1.2.1 — portable verification')
    print('=' * 74)

    results = []
    for label, script, where in TOOLS:
        path = _script_path(script, where)
        print('\n>>> %-22s (%s)' % (label, script))
        proc = subprocess.run([sys.executable, path], cwd=str(RP.RELEASE_ROOT))
        results.append((label, script, proc.returncode == 0))
    by_label = {l: ok for l, _, ok in results}

    print('\n' + '=' * 74)
    print('%-30s %-26s %s' % ('verifier', 'script', 'result'))
    print('-' * 74)
    for label, script, _ in results:
        ok = by_label[label]
        extra = ''
        if label == 'CHANGCHUN_NUMERICS' and ok:
            extra = '  (data: RESTRICTED)'
        print('%-30s %-26s %s%s' % (label, script, 'PASS' if ok else 'FAIL', extra))
    n_fail = sum(1 for _, _, ok in results if not ok)
    print('-' * 74)
    print('%d/%d verifiers passed' % (len(results) - n_fail, len(results)))
    print('RELEASE VERIFICATION: %s' % ('ALL PASS' if n_fail == 0 else 'FAILURES PRESENT'))

    # ---- readiness domains ----------------------------------------------------------
    tech_ok = all(ok for _, _, ok in results)
    MANUSCRIPT_CONSISTENCY = by_label.get('MANUSCRIPT_SUBMISSION', False) and LLM_PROVENANCE_RESOLVED
    DISTRIBUTION = (by_label.get('SECRETS', False) and CHANGCHUN_RIGHTS_RESOLVED
                    and LICENCE_RESOLVED)
    TECHNICAL = tech_ok
    JOURNAL = TECHNICAL and MANUSCRIPT_CONSISTENCY and DISTRIBUTION

    print('=' * 74)
    print('readiness (independent flags)')
    print('-' * 74)
    print('%-36s %s' % ('TECHNICAL_REPRODUCIBILITY_READY:', TECHNICAL))
    print('%-36s %s' % ('MANUSCRIPT_CONSISTENCY_READY:', MANUSCRIPT_CONSISTENCY))
    print('%-36s %s' % ('DISTRIBUTION_READY:', DISTRIBUTION))
    print('%-36s %s' % ('JOURNAL_REVIEW_PACKAGE_READY:', JOURNAL))
    print('-' * 36)
    print('%-36s %s' % ('LLM_PROVENANCE:',
                        'RESOLVED' if LLM_PROVENANCE_RESOLVED else 'AUTHOR ACTION REQUIRED'))
    print('%-36s %s' % ('CHANGCHUN_DATA_RIGHTS:',
                        'RESOLVED' if CHANGCHUN_RIGHTS_RESOLVED else 'AUTHOR ACTION REQUIRED'))
    print('%-36s %s' % ('LICENCE:',
                        'RESOLVED' if LICENCE_RESOLVED else 'AUTHOR ACTION REQUIRED'))
    print('%-36s %s' % ('AUTHOR_METADATA:',
                        'RESOLVED' if AUTHOR_METADATA_RESOLVED else 'AUTHOR ACTION REQUIRED'))
    print('=' * 74)
    if not JOURNAL:
        print('UNRESOLVED AUTHOR ACTION REQUIRED items (never converted to PASS):')
        if not CHANGCHUN_RIGHTS_RESOLVED:
            print('  - Changchun redistribution licence: confirm before any public deposit.')
        if not LICENCE_RESOLVED:
            print('  - code/data licence not finalised.')
        if not AUTHOR_METADATA_RESOLVED:
            print('  - authors / affiliations / ORCID / CRediT / funding not entered.')
    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
