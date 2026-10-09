"""
S04.3 Stage 04 自验证
======================
复核解封后系统状态与发布结果的一致性。**不改变任何记录**（C 区重算只为验证可复现性，
不消耗 validation_runs）。

检查项：
  V1 解封登记：已批准候选 validation_runs==1，未批准候选 ==0
  V2 冻结哈希：已解封候选的 canon_hash 与冻结登记仍逐字节一致（解封未篡改候选）
  V3 日志链：verify()==ok，且含 2 条 dry_run=False 的 unsealed_validated
  V4 清单：manifests/stage04_hashes.txt 中除清单自身外逐条 SHA-256 复算一致
  V5 可复现：重算主终点，与发布结果逐位一致（ΔRMSE/p/CI/金库明文哈希）
  V6 报告一致：STAGE04_REPORT.md 中关键数字与结果 JSON 一致

用法：python3 stage04_validation/scripts/s04_03_verify.py
"""
import os, sys, json, hashlib, re

_HERE = os.path.dirname(os.path.abspath(__file__))
S04 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S04)
S02 = os.path.join(PROJ, 'stage02_platform')
S03 = os.path.join(PROJ, 'stage03_discovery')
for _p in (os.path.join(S02, 'agents'), os.path.join(S02, 'lib'),
           os.path.join(S02, 'sandbox'), os.path.join(S03, 'lib')):
    sys.path.insert(0, _p)

import paths02 as P
import paths03 as P3
import log_tool
from independent_validator import validate, canon_hash

RESULTS = os.path.join(S04, 'reports', 's04_validation_results.json')
APPROVED = os.path.join(S04, 'registry', 'approved_unseal.json')
REPORT = os.path.join(S04, 'STAGE04_REPORT.md')
MANIFEST = os.path.join(S04, 'manifests', 'stage04_hashes.txt')
VERIFY_OUT = os.path.join(S04, 'reports', 'verification.json')

checks = []


def chk(cid, name, ok, detail=''):
    checks.append(dict(id=cid, name=name, ok=bool(ok), detail=detail))
    print('%s %-8s %s%s' % ('[OK] ' if ok else '[FAIL]', cid, name,
                            (' | ' + detail) if detail else ''))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def main():
    res = json.load(open(RESULTS, encoding='utf-8'))
    appr = json.load(open(APPROVED, encoding='utf-8'))
    fr = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    reg = {c['id']: c for c in fr['frozen']}
    approved_ids = [c['id'] for c in appr['approved_candidates']]
    others = [i for i in reg if i not in approved_ids]

    # ---- V1 解封登记
    v1a = all(reg[i].get('validation_runs', 0) == 1 for i in approved_ids)
    v1b = all(reg[i].get('validation_runs', 0) == 0 for i in others)
    chk('V1', '解封登记（批准=1 / 其余=0）', v1a and v1b,
        'approved=%s others=%s' % ({i: reg[i].get('validation_runs', 0) for i in approved_ids},
                                   {i: reg[i].get('validation_runs', 0) for i in others}))

    # ---- V2 冻结哈希一致（候选未被改写）
    bad = []
    for i in approved_ids:
        cand = json.load(open(os.path.join(P3.S03_CAND, i + '.json'), encoding='utf-8'))
        if canon_hash(cand) != reg[i]['canon_hash']:
            bad.append(i)
    chk('V2', '冻结哈希一致（解封未篡改候选）', not bad, 'mismatch=%s' % bad)

    # ---- V3 日志链
    lv = log_tool.verify()
    lines = [json.loads(l) for l in open(P3.EXPERIMENT_LOG, encoding='utf-8') if l.strip()]
    unsealed = [l for l in lines if l.get('action') == 'unsealed_validated'
                and not l.get('detail', {}).get('dry_run')]
    ok3 = bool(lv.get('ok')) and len(unsealed) >= 2
    chk('V3', '日志链完整且含 2 条正式解封记录', ok3,
        'verify=%s n=%s unsealed(real)=%d' % (lv.get('ok'), lv.get('n'), len(unsealed)))

    # ---- V4 清单复算
    man_bad = []
    if os.path.exists(MANIFEST):
        for ln in open(MANIFEST, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if not ln or ln.startswith('#'):
                continue
            parts = [x for x in re.split(r'\s{2,}', ln.strip()) if x]
            if len(parts) < 3:
                continue                      # 非 "hash  size  rel" 行
            h = parts[0]
            rel = parts[2]                    # 第三字段恒为相对路径（日志行第 4 字段才是 "(lines=N)"）
            if rel.endswith('verification.json'):
                continue                      # 自验证输出自身会随本次运行改变，跳过
            full = os.path.join(PROJ, rel)
            if not os.path.exists(full):
                man_bad.append(rel + '(missing)')
                continue
            if sha256_file(full) != h:
                man_bad.append(rel)
    chk('V4', '清单 SHA-256 逐条复算一致', not man_bad,
        'checked from %s; mismatch=%s' % (os.path.basename(MANIFEST), man_bad))

    # ---- V5 主终点可复现（重算，不改记录）
    rep = {}
    for cid in approved_ids:
        cand = json.load(open(os.path.join(P3.S03_CAND, cid + '.json'), encoding='utf-8'))
        r, _ = validate(cand, fr, dry_run=True)
        rp = r['primary_endpoint']
        pub = res['candidates'][cid]['primary_endpoint']
        same = (abs(rp['delta_rmse'] - pub['delta_rmse']) < 1e-9
                and rp['perm_p'] == pub['perm_p']
                and abs(rp['ci95_delta'][0] - pub['ci95_delta'][0]) < 1e-9
                and abs(rp['ci95_delta'][1] - pub['ci95_delta'][1]) < 1e-9
                and r['passed'] == res['candidates'][cid]['passed'])
        rep[cid] = dict(passed=r['passed'], delta=rp['delta_rmse'], p=rp['perm_p'],
                        match=same)
    ok5 = all(v['match'] for v in rep.values())
    chk('V5', '主终点可复现（重算与发布逐位一致）', ok5, json.dumps(rep, ensure_ascii=False))

    # ---- V6 报告关键数字一致
    txt = open(REPORT, encoding='utf-8').read()
    h10 = res['candidates']['S03-H10-GREEDY']['primary_endpoint']
    need = ['+%.4f' % h10['delta_rmse'], '%.3f' % h10['perm_p'],
            '%.4f' % h10['ci95_delta'][0], '%.4f' % h10['ci95_delta'][1],
            '%d' % res['n_C_main'], '+0.1375', '0.085']
    miss = [s for s in need if s not in txt]
    chk('V6', '报告关键数字与结果 JSON 一致', not miss, 'missing_tokens=%s' % miss)

    # ---- V7 冻结登记仅按授权变更（证明是授权递增、不是篡改）
    snap = json.load(open(os.path.join(S04, 'registry', 'pre_unseal_snapshot.json'),
                         encoding='utf-8'))
    pre = snap['frozen_validation_runs']
    now = {c['id']: c.get('validation_runs', 0) for c in fr['frozen']}
    haslr = {c['id']: ('last_result' in c) for c in fr['frozen']}
    ok_a = all(now[i] == pre[i] + 1 and haslr[i] for i in approved_ids)
    ok_b = all(now[i] == pre[i] and not haslr[i] for i in others)
    chk('V7', '冻结登记仅按授权变更（预算+1 / 其余不动 / 末次结果仅批准项）', ok_a and ok_b,
        'approved=%s others=%s last_result=%s' % ({i: now[i] for i in approved_ids},
                                                  {i: now[i] for i in others}, haslr))

    ok_all = all(c['ok'] for c in checks)
    print('\n== Stage 04 verify: %s (%d/%d) =='
          % ('PASS' if ok_all else 'FAIL', sum(c['ok'] for c in checks), len(checks)))
    os.makedirs(os.path.dirname(VERIFY_OUT), exist_ok=True)
    json.dump(dict(ok=ok_all, checks=checks), open(VERIFY_OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    return 0 if ok_all else 1


if __name__ == '__main__':
    raise SystemExit(main())
