#!/usr/bin/env python3
"""
verify_stage03_release.py — verify the frozen discovery registry
===============================================================
Recomputes from shipped files only:

  * the raw sandbox registry SHA-256 recorded at freeze time;
  * the canonical hash of all four frozen candidates (discovery + placebo);
  * that every frozen candidate still carries its mandatory reported fields;
  * budget compliance (fits ≤ total, per-round ≤ cap, n_frozen ≤ cap);
  * the unsealing budget state (V4).  After the authorised Stage-04 unsealing, the two
    approved candidates legitimately hold validation_runs = 1, so V4 is an EXPECTED
    tripwire — it is reported as EXPECTED, not as a failure.

Run:  python3 release_tools/verify_stage03_release.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402
import release_model as RM                     # noqa: E402
from path_guard import guard                   # noqa: E402


def main():
    checks = []

    def chk(cid, name, ok, detail='', expected=False):
        checks.append(dict(id=cid, name=name, ok=bool(ok), expected=expected, detail=detail))
        tag = 'EXPECTED' if (expected and not ok) else ('PASS' if ok else 'FAIL')
        print('  %-4s %-44s %s %s' % (cid, name, tag, detail))

    frozen = json.load(open(guard(RP.STAGE03_FROZEN), encoding='utf-8'))
    raw = json.load(open(guard(RP.PAID_ROOT / 'stage02_platform' / 'sandbox_root' / 'work' / 's03' / 'candidate_registry.json'), encoding='utf-8'))

    # --- V1 raw registry hash
    raw_sha = RM.sha256_file(guard(RP.PAID_ROOT / 'stage02_platform' / 'sandbox_root' / 'work' / 's03' / 'candidate_registry.json'))
    chk('V1', 'raw sandbox registry SHA-256', raw_sha == frozen['source']['raw_registry_sha256'],
        'sha256=%s…' % raw_sha[:16])

    # --- V2 canonical hashes reproduce
    ok2, det2 = True, []
    for fr in frozen['frozen']:
        cand = RM.load_candidate(RP.STAGE03_CAND_DIR, fr['id'])
        good = RM.canon_hash(cand) == fr['canon_hash']
        ok2 &= good
        det2.append('%s:%s' % (fr['id'], 'ok' if good else 'MISMATCH'))
    chk('V2', 'frozen candidates: canon hash reproduce', ok2, '; '.join(det2))

    # --- V3 mandatory fields present
    ok3, det3 = True, []
    for fr in frozen['frozen']:
        c = RM.load_candidate(RP.STAGE03_CAND_DIR, fr['id'])
        de = c.get('dev_evidence', {})
        good = all(k in de for k in ('directions', 'ci95_rmse', 'moran_I_resid')) \
            and (c.get('physics_audit') or {}).get('verdict') in ('pass', 'fail')
        ok3 &= good
        det3.append('%s:%s' % (fr['id'], 'ok' if good else 'MISSING'))
    chk('V3', 'mandatory reported fields present', ok3, '; '.join(det3))

    # --- V4 budget compliance
    g = raw.get('guard', {})
    fits = g.get('fits', 10 ** 9)
    per_round_ok = all(n <= raw['budget']['per_round_max_candidates'] for n in raw['rounds'].values())
    chk('V4', 'budget compliance', fits <= raw['budget']['total_fit_budget'] and per_round_ok
        and frozen['n_frozen'] <= raw['budget']['freeze_max'],
        'fits=%d/%d n_frozen=%d/%d' % (fits, raw['budget']['total_fit_budget'],
                                       frozen['n_frozen'], raw['budget']['freeze_max']))

    # --- V5 unsealing budget state (EXPECTED tripwire after Stage-04 unsealing)
    runs = {fr['id']: fr.get('validation_runs', 0) for fr in frozen['frozen']}
    two_unsealed = sorted(k for k, v in runs.items() if v == 1)
    others_zero = all(v == 0 for k, v in runs.items() if v != 1)
    ok5 = (two_unsealed == ['S03-H01-LIN7', 'S03-H10-GREEDY'] and others_zero
           and len(two_unsealed) == 2)
    chk('V5', 'unsealing state = expected post-Stage-04',
        ok5, 'runs=%s' % json.dumps(runs, ensure_ascii=False), expected=True)

    fails = [c for c in checks if not c['ok'] and not c['expected']]
    ok_all = not fails
    npass = sum(c['ok'] for c in checks)
    print('\n== Stage 03 (release_tools): %s (%d/%d; V5 expected tripwire) =='
          % ('PASS' if ok_all else 'FAIL', npass, len(checks)))
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
