"""
S03.5 独立验证（对 Stage 03 交付物自身，不是对候选的科学验证）
================================================================
本脚本**不解封 C 区、不消耗任何候选的解封机会**（除非打补丁的哈希校验在解密之前失败，
它会在解密前就抛错）。它检查：

  V1 原始登记完整性   —— 沙箱产出的 candidate_registry.json 的 SHA-256 与冻结记录一致；
  V2 冻结↔解封握手     —— 每个冻结候选的 canon_hash 由同一函数重算后与冻结登记逐字一致；
  V3 拒绝逻辑（负对照）—— 篡改任一字段 → 哈希不再一致 → 独立验证服务**在解密前**拒绝；
  V4 解封预算完好      —— 所有冻结候选 validation_runs == 0（单次解封机会未被消耗）；
  V5 预算合规          —— 守卫拟合次数 ≤ 5000、每轮候选 ≤ 50、冻结数 ≤ 8；
  V6 开发指标可复现    —— 用同一折与同一标准化规则重算各冻结候选的 A 区空间分块 CV RMSE；
  V7 必报项完整        —— 方向 / 95% 自助 CI / 残差 Moran's I / 物理审计结论齐备；
  V8 防火墙回归        —— 重跑 Stage 02 十类泄漏测试，确认共享守卫仍然 10/10 PASS。

用法：python3 stage03_discovery/scripts/s03_05_verify.py
"""
import os, sys, json, hashlib, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S03)
S02 = os.path.join(PROJ, 'stage02_platform')
for p in (os.path.join(S03, 'lib'), os.path.join(S03, 'agents'),
          os.path.join(S02, 'agents'), os.path.join(S02, 'lib'), os.path.join(S02, 'sandbox')):
    sys.path.insert(0, p)
import paths03 as P3
import numpy as np
import pandas as pd
import model as M
import core as CORE
from independent_validator import canon_hash, validate, ValidationRefused

CHECKS = []


def chk(cid, desc, ok, detail=''):
    CHECKS.append(dict(id=cid, desc=desc, ok=bool(ok), detail=detail))
    print('  %-3s %-28s %s  %s' % (cid, desc, '✓' if ok else '✗', detail))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    freeze = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    reg = json.load(open(P3.CANDIDATE_REGISTRY, encoding='utf-8'))
    raw = json.load(open(P3.RAW_REGISTRY, encoding='utf-8'))

    # ---- V1
    hs = sha256_file(P3.RAW_REGISTRY)
    chk('V1', '原始登记 SHA-256', hs == freeze['source']['raw_registry_sha256'],
        'sha256=%s…' % hs[:16])

    # ---- V2
    ok2, det2 = True, []
    for fr in freeze['frozen']:
        p = os.path.join(P3.S03_CAND, fr['id'] + '.json')
        h = canon_hash(json.load(open(p, encoding='utf-8')))
        good = (h == fr['canon_hash'])
        ok2 &= good
        det2.append('%s:%s' % (fr['id'], 'ok' if good else 'MISMATCH'))
    chk('V2', '冻结↔解封哈希握手', ok2, '; '.join(det2))

    # ---- V3 负对照：篡改后必须在解密前被拒
    fr0 = freeze['frozen'][0]
    tampered = json.load(open(os.path.join(P3.S03_CAND, fr0['id'] + '.json'), encoding='utf-8'))
    tampered = json.loads(json.dumps(tampered))
    tampered['claim'] = tampered['claim'] + '（篡改）'
    refused_tamper = False
    det3e = ''
    try:
        validate(tampered, freeze, dry_run=True)      # 哈希不符 → 应在解密前 raise
    except ValidationRefused:
        refused_tamper = True
    except Exception as e:                            # 其他异常视为"未按预期拒绝"，并记录原因
        refused_tamper = False
        det3e = 'unexpected=%r' % e
    unknown = dict(id='S03-DOES-NOT-EXIST', claim='x', expression={}, model={})
    refused_unknown = False
    try:
        validate(unknown, freeze, dry_run=True)
    except ValidationRefused:
        refused_unknown = True
    chk('V3', '拒绝逻辑（篡改/未登记）', refused_tamper and refused_unknown,
        'tamper=%s unknown=%s%s' % (refused_tamper, refused_unknown,
                                    (' ' + det3e) if det3e else ''))

    # ---- V4
    runs = {fr['id']: fr.get('validation_runs', 0) for fr in freeze['frozen']}
    chk('V4', '解封预算完好（runs=0）', all(v == 0 for v in runs.values()), json.dumps(runs, ensure_ascii=False))

    # ---- V5
    g = raw.get('guard', {})
    fits = g.get('fits', 10 ** 9)
    per_round_ok = all(n <= raw['budget']['per_round_max_candidates'] for n in raw['rounds'].values())
    chk('V5', '预算合规', fits <= raw['budget']['total_fit_budget'] and per_round_ok
        and freeze['n_frozen'] <= raw['budget']['freeze_max'],
        'fits=%d/%d rounds=%s n_frozen=%d/%d' % (fits, raw['budget']['total_fit_budget'],
                                                 raw['rounds'], freeze['n_frozen'],
                                                 raw['budget']['freeze_max']))

    # ---- V6 开发指标可复现（重算 A 区空间分块 CV）
    A = pd.read_csv(os.path.join(S02, 'sandbox_root', 'inputs', 'zone_A_open.csv'))
    m = pd.read_csv(os.path.join(S02, 'sandbox_root', 'inputs', 'spatial_mask.csv'))
    A = A.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    folds = CORE.spatial_folds(A, k=5, seed=20260924)
    ok6, det6 = True, []
    for fr in freeze['frozen']:
        c = json.load(open(os.path.join(P3.S03_CAND, fr['id'] + '.json'), encoding='utf-8'))
        terms = c['expression']['terms']
        cv, _ = CORE.pooled_cv_rmse(A, terms, folds)
        rec = c['dev_evidence']['cv_rmse']
        good = abs(cv - rec) < 1e-6
        ok6 &= good
        det6.append('%s:%.6f/%s' % (fr['id'], cv, 'ok' if good else 'MISMATCH(rec=%.6f)' % rec))
    ba_cv, _ = CORE.pooled_cv_rmse(A, [CORE.var(v) for v in M.BASELINE_A_TERMS], folds)
    ok6 &= abs(ba_cv - raw['baselineA_dev_cv_rmse']) < 1e-6
    chk('V6', '开发指标可复现', ok6, 'BaselineA=%.6f; ' % ba_cv + '; '.join(det6))

    # ---- V7
    ok7, det7 = True, []
    for fr in freeze['frozen']:
        c = json.load(open(os.path.join(P3.S03_CAND, fr['id'] + '.json'), encoding='utf-8'))
        de = c['dev_evidence']
        good = all(k in de for k in ('directions', 'ci95_rmse', 'moran_I_resid')) \
            and (c.get('physics_audit') or {}).get('verdict') in ('pass', 'fail')
        ok7 &= good
        det7.append('%s:%s' % (fr['id'], 'ok' if good else 'MISSING'))
    chk('V7', '必报项完整', ok7, '; '.join(det7))

    # ---- V8 共享守卫回归（Stage 02 十类泄漏测试）
    leak = subprocess.run([sys.executable, os.path.join(S02, 'scripts', 's02_06_leakage_test.py')],
                          capture_output=True, text=True, cwd=S02)
    lk = {}
    try:                    # 读取其写出的报告（比解析 stdout 稳健）
        lk = json.load(open(os.path.join(S02, 'reports', 's02_06_leakage_test.json'), encoding='utf-8'))
    except Exception:
        pass
    chk('V8', '防火墙回归（Stage 02 泄漏）', leak.returncode == 0 and lk.get('verdict') == 'PASS',
        'verdict=%s n_checks=%s rc=%d' % (lk.get('verdict'), lk.get('n_checks'), leak.returncode))

    FAIL = [c['id'] for c in CHECKS if not c['ok']]
    verdict = 'PASS' if not FAIL else 'FAIL:' + ','.join(FAIL)
    out = dict(version='stage03-verify-v1', verdict=verdict, n_checks=len(CHECKS),
               checks=CHECKS)
    os.makedirs(P3.S03_REPORTS, exist_ok=True)
    with open(os.path.join(P3.S03_REPORTS, 'verification.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('\n[verify] %s (%d/%d)' % (verdict, sum(c['ok'] for c in CHECKS), len(CHECKS)))
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
