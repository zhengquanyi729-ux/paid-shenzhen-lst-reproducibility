#!/usr/bin/env python3
"""
verify_stage01_release.py — verify the frozen spatial split and the R = 15 buffer
================================================================================
Recomputes, from the shipped split tables only:

  * the four frozen split-file SHA-256 hashes recorded in `split_manifest.json`;
  * the post-buffer zone sizes (A = 19,184 · B = 6,182 · C = 2,987 · buffer = 3,407);
  * that the locked region C is connected (1 component) after the C-only buffer;
  * the minimum 8-neighbour (chessboard) distance from C to A∪B, which must be ≥ R = 15.

Run:  python3 release_tools/verify_stage01_release.py
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

OFF = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _dilate(mask, k, NR, NC):
    o = mask.copy()
    for _ in range(k):
        n = o.copy()
        for dr, dc in OFF:
            a = np.zeros_like(o)
            a[max(0, dr):NR + min(0, dr), max(0, dc):NC + min(0, dc)] = \
                o[max(0, -dr):NR + min(0, -dr), max(0, -dc):NC + min(0, -dc)]
            n |= a
        o = n
    return o


def _components(cells):
    idx = {p: i for i, p in enumerate(cells)}
    par = list(range(len(cells)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i, (r, c) in enumerate(cells):
        for dr, dc in OFF:
            j = idx.get((r + dr, c + dc))
            if j is not None:
                a, b = find(i), find(j)
                if a != b:
                    par[a] = b
    return len({find(i) for i in range(len(cells))})


def main():
    checks = []

    def chk(cid, name, ok, detail=''):
        checks.append(dict(id=cid, name=name, ok=bool(ok), detail=detail))
        print('  %-4s %-44s %s %s' % (cid, name, 'PASS' if ok else 'FAIL', detail))

    stage01 = RP.PAID_ROOT / 'stage01_protocol'
    man = json.load(open(guard(stage01 / 'split' / 'split_manifest.json'), encoding='utf-8'))
    autocorr = json.load(open(guard(stage01 / 'reports' / 's01_01_spatial_autocorr.json'),
                             encoding='utf-8'))
    RCELL = int(man['R_cells'])

    # --- P1: R derivation is internally consistent
    chk('P1', 'R-cells derivation consistent', RCELL == int(autocorr['recommendation']['R_cells']) == 15,
        'R=%d cells (%.1f km)' % (RCELL, RCELL * 0.1))

    # --- P2: frozen split-file hashes reproduce
    ok_h, det = True, []
    for rel, h in man['files'].items():
        p = stage01 / rel
        good = p.exists() and RM.sha256_file(p) == h
        ok_h &= good
        det.append('%s:%s' % (os.path.basename(rel), 'ok' if good else 'MISMATCH'))
    chk('P2', 'frozen split-file SHA-256 reproduce', ok_h, '; '.join(det))

    # --- load the shipped split and rebuild the grid
    sp = pd.read_csv(guard(RP.ANALYSIS_SPLIT))
    rows, cols = sp['row'].to_numpy(), sp['col'].to_numpy()
    NR = int(rows.max()) + 1
    NC = int(cols.max()) + 1
    role = np.full((NR, NC), '', dtype=object)
    inmain = np.zeros((NR, NC), bool)
    role[rows, cols] = sp['role'].to_numpy()
    inmain[rows, cols] = sp['in_main'].to_numpy().astype(bool)

    n = {k: int((sp['role'] == k).sum()) for k in ('discovery', 'dev_validation', 'locked', 'buffer')}
    # --- P3: post-buffer zone sizes
    ok3 = (n['discovery'] == man['zone_size_post_buffer']['1'] == 19184
           and n['dev_validation'] == man['zone_size_post_buffer']['2'] == 6182
           and n['locked'] == man['zone_size_post_buffer']['3'] == 2987
           and n['buffer'] == man['buffer_cells'] == 3407)
    chk('P3', 'post-buffer zone sizes reproduce', ok3,
        'A=%d B=%d C=%d buffer=%d' % (n['discovery'], n['dev_validation'],
                                      n['locked'], n['buffer']))

    # --- P4: C connectivity after buffer
    crc = list(zip(*np.where(role == 'locked')))
    ncomp = _components(crc)
    chk('P4', 'locked region C connected after buffer', ncomp == man['connectivity']['C_components_after_buffer'] == 1,
        'components=%d' % ncomp)

    # --- P5: min distance C -> A∪B >= R (chessboard)
    ab = (role == 'discovery') | (role == 'dev_validation')
    cur = ab.copy()
    d = None
    for k in range(1, 90):
        cur = _dilate(cur, 1, NR, NC)
        if cur[role == 'locked'].any():
            d = k
            break
    chk('P5', 'min distance C→A∪B ≥ R cells', d is not None and d >= RCELL,
        'd_C_AB=%s R=%d' % (d, RCELL))

    ok_all = all(c['ok'] for c in checks)
    print('\n== Stage 01 (release_tools): %s (%d/%d) =='
          % ('PASS' if ok_all else 'FAIL', sum(c['ok'] for c in checks), len(checks)))
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
