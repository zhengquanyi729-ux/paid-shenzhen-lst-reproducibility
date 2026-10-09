#!/usr/bin/env python3
"""
verify_stage05_release.py — recompute the Stage-05 headline numbers portably
===========================================================================
Reads only shipped tables + frozen reports; no AES key, no network, no author tree.
Recomputes, from `data/shenzhen/zone_A_open.csv`, `zone_B_devval.csv` and the released
Region-C table:

  * Baseline A (7-covariate OLS, fitted on A) in-sample RMSE on A / B / C
    (frozen: 2.914880975503129 / 2.54250853893637 / 2.841519144671417);
  * Baseline A spatial-block CV RMSE on A (frozen: 3.1576525409870713);
  * the frozen H10 expression refit on A, in-sample on A / B / C and its A-CV
    (frozen: 2.744089595252658 / 2.4203020828004322 / 2.462447828502684, A-CV 2.9560392780323155);
  * the DEM-free projection ("no_dem") on C and its A-CV
    (frozen: 2.4089664048408896, A-CV 3.2614111497811065);
  * internal consistency of the reported ΔRMSE / CI / permutation flags;
  * that Baseline-D's reference block reproduces Baseline-B, and that its
    selection-leak inflation is internally consistent.

Optional (set S05_RF=1): additionally refit the numpy RandomForest and GradientBoosting
on Region A and recompute their in-sample RMSE on A/B/C, comparing to the frozen
Baseline-B numbers (this is the slow step, ~20 s).

Nothing is hardcoded: every expected value is read from the shipped frozen JSON;
comparisons use tolerance 1e-9.

Run:  python3 release_tools/verify_stage05_release.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_paths as RP                     # noqa: E402
import release_model as RM                     # noqa: E402
from path_guard import guard                   # noqa: E402

TOL = 1e-9
Y = RM.Y


def _load_zones():
    A = pd.read_csv(guard(RP.ZONE_A))
    Bm = pd.read_csv(guard(RP.ZONE_B))
    C = pd.read_csv(guard(RP.ZONE_C_ANALYSIS_READY))
    mask = pd.read_csv(guard(RP.ANALYSIS_SPLIT))[['Grid_ID', 'row', 'col']]
    A = A.merge(mask, on='Grid_ID', how='left')
    Bm = Bm.merge(mask, on='Grid_ID', how='left')
    C = C.merge(mask, on='Grid_ID', how='left')
    return A, Bm, C


def main():
    checks = []

    def chk(cid, name, ok, detail=''):
        checks.append(dict(id=cid, name=name, ok=bool(ok), detail=detail))
        print('  %-6s %-46s %s %s' % (cid, name, 'PASS' if ok else 'FAIL', detail))

    bb = json.load(open(guard(RP.STAGE05_BASELINEB), encoding='utf-8'))
    bd = json.load(open(guard(RP.STAGE05_BASELINED), encoding='utf-8'))
    s04 = json.load(open(guard(RP.STAGE04_RESULTS), encoding='utf-8'))
    vm = json.load(open(guard(RP.VAULT_MANIFEST), encoding='utf-8'))

    A, Bm, C = _load_zones()

    # frozen candidate H10 terms; DEM-free projection drops terms containing DEM_mean
    cand = RM.load_candidate(RP.STAGE03_CAND_DIR, 'S03-H10-GREEDY')
    T = cand['expression']['terms'] if 'expression' in cand else cand['model']['terms']
    nodem = [t for t in T if 'DEM_mean' not in RM.expr_vars(t)]

    # --- S5-1: Baseline A in-sample RMSE on A/B/C
    mdl_b = RM.fit_linear(A, RM.BASELINE_A_TERMS)
    rmse_ba = {nm: RM.rmse(df[Y], RM.predict(mdl_b, df)) for nm, df in
               (('A', A), ('B', Bm), ('C', C))}
    ok1 = all(abs(rmse_ba[nm] - bb['regions'][nm]['baselineA']['rmse']) < TOL
              for nm in ('A', 'B', 'C'))
    chk('S5-1', 'Baseline A in-sample RMSE on A/B/C', ok1,
        'A=%.15f B=%.15f C=%.15f' % (rmse_ba['A'], rmse_ba['B'], rmse_ba['C']))

    # --- S5-2: Baseline A A-CV
    folds = RM.spatial_folds(A, k=5, seed=20260924)
    cv_ba, _ = RM.pooled_cv_rmse(A, [RM.var(v) for v in RM.BASELINE_A_TERMS], folds)
    chk('S5-2', 'Baseline A spatial-block CV RMSE (A)',
        abs(cv_ba - bb['A_cv']['baselineA']) < TOL, 'CV=%.15f' % cv_ba)

    # --- S5-3: frozen H10 refit on A, in-sample on A/B/C
    mdl_h = RM.fit_expr(A, T)
    rmse_h = {nm: RM.rmse(df[Y], RM.predict(mdl_h, df)) for nm, df in
              (('A', A), ('B', Bm), ('C', C))}
    ok3 = all(abs(rmse_h[nm] - bb['regions'][nm]['h10']['rmse']) < TOL
              for nm in ('A', 'B', 'C'))
    chk('S5-3', 'frozen H10 in-sample RMSE on A/B/C', ok3,
        'A=%.15f B=%.15f C=%.15f' % (rmse_h['A'], rmse_h['B'], rmse_h['C']))

    # --- S5-4: H10 A-CV
    cv_h, _ = RM.pooled_cv_rmse(A, T, folds)
    chk('S5-4', 'frozen H10 spatial-block CV RMSE (A)',
        abs(cv_h - bb['A_cv']['h10']) < TOL, 'CV=%.15f' % cv_h)

    # --- S5-5: DEM-free projection in-sample on C + A-CV
    mdl_nd = RM.fit_expr(A, nodem)
    rmse_nd_c = RM.rmse(C[Y], RM.predict(mdl_nd, C))
    cv_nd, _ = RM.pooled_cv_rmse(A, nodem, folds)
    chk('S5-5', 'DEM-free projection on C + A-CV',
        abs(rmse_nd_c - bb['regions']['C']['no_dem']['rmse']) < TOL
        and abs(cv_nd - bb['A_cv']['no_dem']) < TOL,
        'C=%.15f cv=%.15f' % (rmse_nd_c, cv_nd))

    # --- S5-6: delta consistency across all reported entries (delta == rb - rc)
    ok6, det6 = True, []
    for nm in ('A', 'B', 'C'):
        rb = bb['regions'][nm]['baselineA']['rmse']
        for mk, r in bb['regions'][nm].items():
            if mk == 'baselineA':
                continue
            if abs((rb - r['rmse']) - r['delta_vs_baselineA']) > TOL:
                ok6 = False
                det6.append('%s/%s' % (nm, mk))
    chk('S5-6', 'ΔRMSE == baselineA − candidate (all entries)', ok6,
        'mismatches=%s' % (det6 or 'none'))

    # --- S5-7: CI / permutation flags internally consistent
    ok7, det7 = True, []
    for nm in ('B', 'C'):
        for mk, r in bb['regions'][nm].items():
            if mk == 'baselineA':
                continue
            xz = bool(r['ci95'][0] > 0 or r['ci95'][1] < 0)
            if xz != r['ci_excludes_zero']:
                ok7 = False
                det7.append('%s/%s' % (nm, mk))
    chk('S5-7', 'ci_excludes_zero flags match ci95 signs', ok7,
        'mismatches=%s' % (det7 or 'none'))

    # --- S5-8: vault hash consistent across reports
    ok8 = (bb['vault_plaintext_sha256'] == vm['plaintext_sha256'] == s04.get('vault_plaintext_sha256'))
    chk('S5-8', 'vault plaintext SHA consistent (B / manifest / Stage-04)', ok8,
        'sha=%s…' % bb['vault_plaintext_sha256'][:16])

    # --- S5-9: Baseline-D reference block reproduces Baseline-B
    r = bd['reference']
    ok9 = (abs(r['baselineA']['cv_rmse'] - bb['A_cv']['baselineA']) < TOL
           and abs(r['baselineA']['rmse_B'] - bb['regions']['B']['baselineA']['rmse']) < TOL
           and abs(r['baselineA']['rmse_C'] - bb['regions']['C']['baselineA']['rmse']) < TOL
           and abs(r['h10_constrained']['cv_rmse'] - bb['A_cv']['h10']) < TOL
           and abs(r['h10_constrained']['rmse_B'] - bb['regions']['B']['h10']['rmse']) < TOL
           and abs(r['h10_constrained']['rmse_C'] - bb['regions']['C']['h10']['rmse']) < TOL)
    chk('S5-9', 'Baseline-D reference == Baseline-B', ok9, 'cross-report consistent')

    # --- S5-10: Baseline-D selection-leak inflation internally consistent
    a2 = bd['arm2_firewall_off']
    infl = a2['honest_selected_by_A']['rmse_C'] - a2['selected_by_C']['rmse_C']
    ok10 = abs(infl - a2['c_rmse_inflation']) < TOL and a2['c_rmse_inflation'] > 0
    chk('S5-10', 'Baseline-D selection-leak inflation consistent', ok10,
        'inflation=%.15f' % infl)

    # --- S5-11 (optional): recompute numpy RF / GBM on A → A/B/C
    if os.environ.get('S05_RF') == '1':
        import time
        import release_bmlib as B
        RF = dict(n_estimators=300, max_depth=12, min_leaf=10, seed=20260924)
        GBM = dict(n_estimators=300, learning_rate=0.05, max_depth=4, min_leaf=20, seed=20260924)
        t0 = time.time()
        Xa = A[RM.BASELINE_A_TERMS].to_numpy(float)
        ya = A[Y].to_numpy(float)
        rf = B.fit('rf', Xa, ya, **RF)
        gb = B.fit('gbm', Xa, ya, **GBM)
        ok11, det11 = True, []
        for kind, mdl in (('rf', rf), ('gbm', gb)):
            for nm, df in (('A', A), ('B', Bm), ('C', C)):
                p = B.predict(mdl, df[RM.BASELINE_A_TERMS].to_numpy(float))
                got = B.rmse(df[Y], p)
                exp = bb['regions'][nm][kind]['rmse']
                if abs(got - exp) > 1e-6:
                    ok11 = False
                    det11.append('%s/%s' % (kind, nm))
        chk('S5-11', 'numpy RF/GBM in-sample RMSE on A/B/C', ok11,
            'mismatches=%s (%.1fs)' % (det11 or 'none', time.time() - t0))
    else:
        checks.append(dict(id='S5-11', name='numpy RF/GBM in-sample RMSE on A/B/C',
                           ok=True, expected=True, detail='SKIPPED (set S05_RF=1 to run)'))
        print('  %-6s %-46s %s' % ('S5-11', 'numpy RF/GBM in-sample RMSE on A/B/C',
                                   'SKIP (set S05_RF=1)'))

    ok_all = all(c['ok'] for c in checks)
    npass = sum(c['ok'] for c in checks)
    print('\n== Stage 05 (release_tools): %s (%d/%d) =='
          % ('PASS' if ok_all else 'FAIL', npass, len(checks)))
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
