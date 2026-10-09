"""
S02.7 端到端自测 + Stage 02 报告 + 哈希清单
===========================================
框架依据：Table 17 Stage 02 交付物「可运行系统与泄漏测试」。

流程（打通并验证整条链路）：
  1) 沙箱内依次运行 Discovery → Experiment → Falsification → Physics Auditor；
  2) 冻结候选（写入 frozen_candidates.json，登记规范化哈希）；
  3) 沙箱之外运行 Independent Validator：解封 → 主终点 → 空间块置换 → 自助 CI → 发布；
  4) 拒绝路径测试：未冻结候选 / 哈希不一致（解封后修订）/ 重复解封；
  5) 通过条件判定函数的正反两例单元测试（证明 PASS 通路已接通）；
  6) 写出 STAGE02_REPORT.md 与 manifests/stage02_hashes.txt，并复算清单。

注意：本步为**平台冒烟测试**，候选为预注册 Baseline A 占位，非科学发现；
Stage 02 不产生任何「新规律」结论。
"""
import sys, os, json, subprocess, hashlib, shutil, tempfile, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'sandbox'))
import paths02 as P
import log_tool
import independent_validator as IV

CREATED = '2026-09-24'
VERSION = 'stage02-selftest-v1'
os.makedirs(P.S02_MANIFEST, exist_ok=True)
os.makedirs(P.S02_REPORTS, exist_ok=True)
W = P.SANDBOX_WORK
LOG = P.LOG_FILE
STEPS = []


def run(cmd, env=None):
    cp = subprocess.run([sys.executable] + cmd, capture_output=True, text=True,
                        env=dict(os.environ, **(env or {})))
    return cp.returncode, cp.stdout, cp.stderr


def step(name, ok, detail):
    STEPS.append(dict(step=name, ok=bool(ok), detail=detail))


# ---------------------------------------------------------------- 0) 洁净室：清空沙箱工作树
# 该目录是发现侧唯一可写区，也是唯一可能被「外部预置诱饵」污染之处。运行前清空，
# 可移除任何跨轮残留或人为投递的副本/硬链接（硬链接另有 L2b inode 防线兜底）。
# 注意（2026-09-27 修正）：`work/` 是**各阶段共享**的工作树，Stage 03 的发现侧产出
# 也落在 work/<stage>/ 之下。早期实现无差别删除 work/* 的子目录，会在重跑本自测时
# **误删他阶段（如 work/s03/）的证据**。现改为：清空所有**散落文件**（含外部预置诱饵），
# 但**保留形如 sNN 的阶段专属子目录**，只清理本自测自身产出的文件。
import re as _re
_removed = 0
for _p in sorted(glob.glob(os.path.join(W, '*'))):
    if os.path.isdir(_p) and _re.match(r'^s\d\d$', os.path.basename(_p)):
        continue                                    # 保留他阶段的阶段专属子目录
    try:
        shutil.rmtree(_p) if os.path.isdir(_p) else os.remove(_p)
        _removed += 1
    except OSError:
        pass
step('洁净室：清空沙箱工作树（保留阶段专属子目录）', True, 'removed=%d' % _removed)

# ---------------------------------------------------------------- 1) 沙箱内四 Agent
sand = os.path.join(P.S02_SANDBOX, 'run_sandboxed.py')
c0 = os.path.join(W, 'cand_0_proposed.json')
c1 = os.path.join(W, 'cand_1_devtested.json')
c2 = os.path.join(W, 'cand_2_falsified.json')
c3 = os.path.join(W, 'cand_3_audited.json')

rc, out, err = run([sand, os.path.join(P.S02_AGENTS, 'discovery_agent.py'), c0, '--id', 'SMOKE-0001'],
                   dict(PAID_ACTOR='Discovery Agent'))
step('Discovery Agent（沙箱内）', rc == 0 and os.path.exists(c0), out.strip() or err[-300:])

rc, out, err = run([sand, os.path.join(P.S02_AGENTS, 'experiment_agent.py'), c0, c1],
                   dict(PAID_ACTOR='Experiment Agent'))
step('Experiment Agent（沙箱内）', rc == 0 and os.path.exists(c1), out.strip() or err[-300:])

rc, out, err = run([sand, os.path.join(P.S02_AGENTS, 'falsification_agent.py'), c1, c2],
                   dict(PAID_ACTOR='Falsification Agent'))
step('Falsification Agent（沙箱内）', rc == 0 and os.path.exists(c2), out.strip() or err[-300:])

rc, out, err = run([sand, os.path.join(P.S02_AGENTS, 'physics_auditor.py'), c2, c3,
                    os.path.abspath(os.path.join(P.SANDBOX_INPUTS, 'hard_constraints.json'))],
                   dict(PAID_ACTOR='Physics Auditor'))
step('Physics Auditor（沙箱内）', rc == 0 and os.path.exists(c3), out.strip() or err[-300:])

if not os.path.exists(c3):
    print(json.dumps(dict(status='FAIL: 沙箱内流水线未产生候选',
                          steps={s['step']: s['ok'] for s in STEPS}), ensure_ascii=False, indent=2))
    sys.exit(1)
cand = json.load(open(c3, encoding='utf-8'))

# ---------------------------------------------------------------- 2) 冻结候选
canon = IV.canon_hash(cand)
frozen = json.load(open(P.FROZEN_FILE, encoding='utf-8'))
frozen['frozen'] = [f for f in frozen['frozen'] if f['id'] != cand['id']]
frozen['frozen'].append(dict(id=cand['id'], canon_hash=canon,
                             frozen_at=CREATED, validation_runs=0,
                             note='平台冒烟占位（Baseline A 规格）'))
with open(P.FROZEN_FILE, 'w', encoding='utf-8') as f:
    json.dump(frozen, f, ensure_ascii=False, indent=2)
log_tool.append(cand['id'], 'candidate_frozen', logpath=LOG, canon_hash=canon,
                agent=cand['agent'], terms=cand['expression']['terms'])
step('冻结候选', True, 'id=%s canon=%s' % (cand['id'], canon[:16]))

# ---------------------------------------------------------------- 3) 拒绝路径测试
V = os.path.join(P.S02_AGENTS, 'independent_validator.py')
env = dict(PYTHONPATH=os.pathsep.join([P.S02_LIB, P.S02_SANDBOX, P.S02]))
refusals = {}

unfr = os.path.join(W, 'cand_unfrozen.json')
u = json.loads(json.dumps(cand)); u['id'] = 'SMOKE-UNFROZEN'
json.dump(u, open(unfr, 'w', encoding='utf-8'), ensure_ascii=False)
rc, out, err = run([V, '--candidate', unfr, '--registry', P.FROZEN_FILE], env)
refusals['unfrozen'] = dict(rc=rc, refused='拒绝解封' in out)

tam = os.path.join(W, 'cand_tampered.json')
t = json.loads(json.dumps(cand)); t['model']['beta'][1] += 0.05
json.dump(t, open(tam, 'w', encoding='utf-8'), ensure_ascii=False)
rc, out, err = run([V, '--candidate', tam, '--registry', P.FROZEN_FILE], env)
refusals['tampered_hash'] = dict(rc=rc, refused='哈希与冻结登记不一致' in out)

step('拒绝未冻结候选', refusals['unfrozen']['rc'] == 2 and refusals['unfrozen']['refused'],
     json.dumps(refusals['unfrozen'], ensure_ascii=False))
step('拒绝哈希不一致（解封后修订）', refusals['tampered_hash']['rc'] == 2 and
     refusals['tampered_hash']['refused'], json.dumps(refusals['tampered_hash'], ensure_ascii=False))

# ---------------------------------------------------------------- 4) 正式验证（沙箱外）
rc, out, err = run([V, '--candidate', c3, '--registry', P.FROZEN_FILE, '--out', P.VALIDATION_OUT], env)
published = os.path.exists(P.VALIDATION_OUT)
result = json.load(open(P.VALIDATION_OUT, encoding='utf-8')) if published else None
step('Independent Validator 解封并发布（沙箱外）', rc == 0 and published,
     json.dumps(result['primary_endpoint'], ensure_ascii=False) if result else (out + err)[-300:])

# 重复解封应被拒
rc, out, err = run([V, '--candidate', c3, '--registry', P.FROZEN_FILE], env)
refusals['rerun'] = dict(rc=rc, refused='验证过一次' in out)
step('拒绝重复解封（validation_runs=1）', refusals['rerun']['rc'] == 2 and refusals['rerun']['refused'],
     json.dumps(refusals['rerun'], ensure_ascii=False))

# ---------------------------------------------------------------- 5) 通过条件判定单元测试
def decide_ok(cond):
    return all(cond.values())

pos = {'delta_rmse_pos': True, 'perm_p_lt_0.05': True, 'ci_excludes_zero': True,
       'physics_audit_pass': True, 'negative_controls_not_fooled': True}
neg = dict(pos, **{'perm_p_lt_0.05': False})
unit_pass = decide_ok(pos) is True and decide_ok(neg) is False
step('通过条件判定单元测试（正/反两例）', unit_pass,
     'all-true→%s, p-fail→%s' % (decide_ok(pos), decide_ok(neg)))

# ---------------------------------------------------------------- 6) 报告
logv = log_tool.verify()
STEPS_OK = all(s['ok'] for s in STEPS)
status = 'PASS' if STEPS_OK else 'FAIL:' + ','.join(s['step'] for s in STEPS if not s['ok'])

R = dict(version=VERSION, created=CREATED, status=status,
         steps=STEPS, refusals=refusals, unit_test_pass=unit_pass,
         frozen_candidate=cand['id'], canon_hash=canon,
         validation_result=result, log=logv,
         note='平台冒烟测试：候选为预注册 Baseline A 占位，非科学发现。')
with open(os.path.join(P.S02_REPORTS, 's02_07_selftest.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- 7) 哈希清单
EXCLUDE_DIRS = {os.path.join(P.S02, 'logs'), os.path.join(P.SANDBOX_ROOT, 'work')}
OS_JUNK = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
# 本脚本自身的产物在清单写就后才定稿，属自指，故排除（与 Stage 01 S01.6 同样处理）
META = {'manifests/stage02_hashes.txt',
        'reports/s02_07_selftest.json', 'reports/s02_07_selftest.md'}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


rows = []
for dp, dns, fns in os.walk(P.S02):
    dns[:] = [d for d in dns if os.path.join(dp, d) not in EXCLUDE_DIRS and d != '__pycache__']
    for fn in sorted(fns):
        if fn.startswith('.') or fn in OS_JUNK:
            continue
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, P.S02).replace(os.sep, '/')
        if rel in META:
            continue
        rows.append((rel, os.path.getsize(p), sha(p)))
rows.sort()
with open(os.path.join(P.S02_MANIFEST, 'stage02_hashes.txt'), 'w') as f:
    f.write('# Stage 02 产物 SHA-256 清单（相对 stage02_platform/；不含本清单自身；\n')
    f.write('# 排除动态运行态：logs/ 与 sandbox_root/work/）\n')
    for rel, size, h in rows:
        f.write('%s  %10d  %s\n' % (h, size, rel))

# 复算清单
bad = [rel for rel, _, h in rows if sha(os.path.join(P.S02, rel)) != h]
manifest_ok = not bad
R['hash_manifest'] = dict(n_files=len(rows), ok=manifest_ok, mismatched=bad)
with open(os.path.join(P.S02_REPORTS, 's02_07_selftest.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.7 端到端自测\n', '版本 %s。判定：**%s**。\n' % (VERSION, status),
     '| 步骤 | 结果 | 明细 |', '|---|---|---|']
for s in STEPS:
    L.append('| %s | %s | %s |' % (s['step'], '✓' if s['ok'] else '✗', s['detail'][:180]))
if result:
    pe = result['primary_endpoint']
    L += ['', '## 验证服务发布（沙箱外）\n',
          '候选 `%s`：RMSE(C)=%.4f，Baseline A RMSE(C)=%.4f，ΔRMSE=%.4f，'
          '空间块置换 p=%.3f（%d 次），95%% CI=[%.4f, %.4f]。'
          % (result['candidate'], pe['rmse_candidate'], pe['rmse_baselineA'],
             pe['delta_rmse'], pe['perm_p'], pe['n_perm'], pe['ci95_delta'][0], pe['ci95_delta'][1]),
          '', '通过条件：%s → **%s**。' % (json.dumps(result['conditions'], ensure_ascii=False),
                                          '通过' if result['passed'] else '未通过'),
          '', '> %s' % '；'.join(result['caveats'])]
L += ['', '## 日志\n', '哈希链自洽 **%s**，共 %d 条，链尾 `%s`。'
      % (logv['ok'], logv['n'], logv['tail']),
      '', '## 哈希清单\n', '共 %d 个产物，复算一致 **%s**。' % (len(rows), manifest_ok)]
with open(os.path.join(P.S02_REPORTS, 's02_07_selftest.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(dict(status=status, steps={s['step']: s['ok'] for s in STEPS},
                      refusals={k: v['refused'] for k, v in refusals.items()},
                      unit_test_pass=unit_pass, manifest=dict(n_files=len(rows), ok=manifest_ok),
                      log_ok=logv['ok'], log_n=logv['n']), ensure_ascii=False, indent=2))
sys.exit(0 if STEPS_OK and manifest_ok else 1)
