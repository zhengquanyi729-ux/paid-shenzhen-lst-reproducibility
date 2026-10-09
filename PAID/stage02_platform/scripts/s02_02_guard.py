"""
S02.2 沙箱工作树与访问守卫
==========================
构建发现侧**唯一**可读写的工作树 `sandbox_root/`，其中只放 A/B 开放数据与中性资料；
地理上不含 C 目标值、不含全域原始数据。随后做一次守卫冒烟测试。

输出：
  sandbox_root/inputs/{zone_A_open.csv, zone_B_devval.csv, hard_constraints.json,
                       DATA_DICTIONARY.md, no_direction_preset.md}
  sandbox_root/README.md
  reports/s02_02_guard.json / .md
"""
import sys, os, json, shutil, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import paths02 as P
import pandas as pd

CREATED = '2026-09-24'
VERSION = 'stage02-guard-v1'
os.makedirs(P.SANDBOX_INPUTS, exist_ok=True)
os.makedirs(P.SANDBOX_WORK, exist_ok=True)
os.makedirs(P.S02_REPORTS, exist_ok=True)

# ---------------------------------------------------------------- 1) 填充沙箱输入
COPIES = [
    (os.path.join(P.S01, 'split', 'zone_A_open.csv'), 'zone_A_open.csv'),
    (os.path.join(P.S01, 'split', 'zone_B_devval.csv'), 'zone_B_devval.csv'),
    (os.path.join(P.S01, 'constraints', 'hard_constraints.json'), 'hard_constraints.json'),
    (os.path.join(P.S01, 'constraints', 'DATA_DICTIONARY.md'), 'DATA_DICTIONARY.md'),
    (os.path.join(P.S01, 'constraints', 'no_direction_preset.md'), 'no_direction_preset.md'),
]
copied = []
for src, dst in COPIES:
    shutil.copy2(src, os.path.join(P.SANDBOX_INPUTS, dst))
    copied.append(dst)
# 空间掩膜（仅位置与角色，无任何目标值）：供 Falsification Agent 做空间块置换
_m = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))
_m = _m[_m['role'].isin(['discovery', 'dev_validation'])][['Grid_ID', 'row', 'col', 'role']]
_m.to_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'), index=False)
copied.append('spatial_mask.csv（Grid_ID,row,col,role；无目标值）')
# 清空上一次的工作目录（沙箱内产物不参与冻结）
for fn in os.listdir(P.SANDBOX_WORK):
    p = os.path.join(P.SANDBOX_WORK, fn)
    (shutil.rmtree(p) if os.path.isdir(p) else os.remove(p))

with open(os.path.join(P.SANDBOX_ROOT, 'README.md'), 'w', encoding='utf-8') as f:
    f.write('# 发现侧沙箱工作树（sandbox_root）\n\n'
            '这是 Discovery / Experiment / Falsification / Physics Auditor 四类 Agent 的**唯一**\n'
            '可读写区。目录内不存在 C 锁定区目标值，也不存在全域原始数据。\n\n'
            '- `inputs/`：A 发现区、B 开发验证区的开放数据，以及硬约束、数据字典、无方向预设。\n'
            '- `work/`：Agent 运行时产物（不参与冻结）。\n\n'
            '越界访问（保险库、`data/` 全域数据、`stage01_protocol/locked/`、平台报告）由\n'
            '`sandbox/access_guard.py` 在运行时拒绝，并写入 append-only 日志。\n')

# ---------------------------------------------------------------- 2) 守卫冒烟测试
PROBE = r'''
import sys, os
sys.path.insert(0, r"{lib}")
sys.path.insert(0, r"{sbx}")
import paths02 as P
import access_guard as G
G.activate(actor="probe", limits=dict(max_open_calls=10000, max_seconds=60, max_fits=50))
import pandas as pd
res = {{"allowed": [], "denied": [], "unexpected": []}}

def try_open(label, fn, expect_denied):
    try:
        fn()
        (res["unexpected"] if expect_denied else res["allowed"]).append(label)
    except G.AccessDenied as e:
        (res["denied"] if expect_denied else res["unexpected"]).append(label)
    except G.BudgetExceeded as e:
        res["unexpected"].append(label + " (budget)")

# 允许：读取沙箱内 A 区
try_open("read zone_A", lambda: pd.read_csv(os.path.join(P.SANDBOX_INPUTS,"zone_A_open.csv"), nrows=5), False)
# 允许：写入沙箱工作树
try_open("write work", lambda: open(os.path.join(P.SANDBOX_WORK,"probe.txt"),"w").write("ok"), False)
# 拒绝：保险库密文
try_open("read vault enc", lambda: open(P.VAULT_ENC,"rb").read(), True)
# 拒绝：保险库密钥
try_open("read vault key", lambda: open(P.VAULT_KEY,"rb").read(), True)
# 拒绝：Stage 01 明文 C 目标
try_open("read locked C", lambda: open(os.path.join(P.S01,"locked","zone_C_targets.csv")).read(), True)
# 拒绝：全域原始 CSV（含全城 LST）
try_open("read full CSV", lambda: pd.read_csv(os.path.join(P.DATA,"data_原始.csv"), nrows=5), True)
# 拒绝：全域 LST 栅格
try_open("read LST tif", lambda: open(os.path.join(P.DATA,"LST_30m_Final new.tif"),"rb").read(64), True)
# 拒绝：写 Stage 01 冻结产物
try_open("write stage01", lambda: open(os.path.join(P.S01,"PREREGISTRATION.md"),"a").write("x"), True)
# 拒绝：能力（子进程）
try_open("subprocess", lambda: __import__("subprocess").run(["ls"]), True)

st = G.shutdown("probe_done")
print("__RESULT__" + __import__("json").dumps({{"res":res,"status":st}}, ensure_ascii=False))
'''

probe_path = os.path.join(P.SANDBOX_WORK, '_guard_probe.py')
with open(probe_path, 'w', encoding='utf-8') as f:
    f.write(PROBE.format(lib=P.S02_LIB, sbx=P.S02_SANDBOX))

env = dict(os.environ, PYTHONPATH=P.S02_LIB + os.pathsep + P.S02_SANDBOX)
cp = subprocess.run([sys.executable, probe_path], capture_output=True, text=True, env=env)
out = cp.stdout
marker = '__RESULT__'
res = json.loads(out.split(marker, 1)[1].strip()) if marker in out else None

ok = bool(res) and not res['res']['unexpected'] and len(res['res']['denied']) == 7 and len(res['res']['allowed']) == 2

R = dict(version=VERSION, created=CREATED, status='OK' if ok else 'FAIL',
         sandbox_root=os.path.relpath(P.SANDBOX_ROOT, P.PROJ),
         inputs=copied,
         guard_probe=res,
         expect=dict(allowed=2, denied=7, unexpected=0),
         stderr_tail=cp.stderr[-500:] if cp.stderr else '')
with open(os.path.join(P.S02_REPORTS, 's02_02_guard.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.2 沙箱工作树与访问守卫\n', '版本 %s。状态 **%s**。\n' % (VERSION, R['status']),
     '沙箱工作树：`%s`（发现侧唯一可读写区）。\n' % R['sandbox_root'],
     '## 守卫冒烟测试\n', '| 用例 | 期望 | 实际 |', '|---|---|---|']
if res:
    for x in res['res']['allowed']:
        L.append('| %s | 允许 | ✓ 允许 |' % x)
    for x in res['res']['denied']:
        L.append('| %s | 拒绝 | ✓ 拒绝 |' % x)
    for x in res['res']['unexpected']:
        L.append('| %s | — | ✗ 意外 |' % x)
    L.append('\n拒绝次数 %d，沙箱内 open 计数 %d。' % (res['status']['denials'], res['status']['opens']))
with open(os.path.join(P.S02_REPORTS, 's02_02_guard.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(dict(status=R['status'], allowed=res and res['res']['allowed'],
                      denied=res and res['res']['denied'],
                      unexpected=res and res['res']['unexpected']),
                 ensure_ascii=False, indent=2))
if not ok:
    print('STDERR:', cp.stderr[-1500:])
    sys.exit(1)
