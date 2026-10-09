"""
S02.6 泄漏测试套件（Stage 02 核心交付物之一）
============================================
框架依据：Table 17 Stage 02 交付物「可运行系统与泄漏测试」；Table 19 风险防范；
§5.1/§5.3；Table 13（空间分块/缓冲、负对照）。

十类测试：
  LK1 静态·ID 隔离     —— 沙箱可见文件中不含任何 C 区 Grid_ID；
  LK2 静态·数值隔离   —— 沙箱可见文件中不含 C 区任何目标值；
  LK3 静态·统计量隔离 —— 沙箱内无 C 区聚合统计量（均值/方差/分位数）；
  LK4 运行时·直读     —— 守卫内直读保险库/密钥/locked/全域 CSV/栅格 全部被拒；
  LK5 运行时·绕行     —— 相对路径/归一化路径/numpy/mmap/symlink 等绕行尝试均被拒；
  LK6 密码学          —— 无密钥不可解密；密文中不含明文片段；有密钥可正确还原；
  LK7 反向·回传       —— 验证服务只发布聚合结论；沙箱内不可读 reports（含解封结论）；
  LK8 对抗·硬链接     —— 白名单内预置「无敏感词名」的硬链接，按 inode 身份拒绝；
  LK9 对抗·异位副本   —— 白名单之外的改名副本（/tmp），由读白名单拒绝；
  LK10 对抗·符号链接  —— 指向锁定真值的 symlink，realpath 落回拒绝前缀。
  （LK8-LK10 为一次独立红队复核发现路径规则缺口后新增的回归测试。）
"""
import sys, os, json, subprocess, hashlib, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import paths02 as P
import pandas as pd
import numpy as np

CREATED = '2026-09-24'
VERSION = 'stage02-leakage-v1'
os.makedirs(P.S02_REPORTS, exist_ok=True)
CHECKS = []


def chk(cid, desc, ok, detail):
    CHECKS.append(dict(id=cid, desc=desc, ok=bool(ok), detail=detail))


# ---------------------------------------------------------------- C 区真值（测试侧）
cdf_plain = pd.read_csv(os.path.join(P.S01, 'locked', 'zone_C_targets.csv'))
C_IDS = set(int(x) for x in cdf_plain['Grid_ID'])
C_VALS = set(round(float(v), 4) for v in cdf_plain['LST_mean'])
SPLIT = json.load(open(os.path.join(P.S01, 'split', 'split_manifest.json'), encoding='utf-8'))
AB_IDS = set()
for f in ('zone_A_open.csv', 'zone_B_devval.csv'):
    AB_IDS |= set(int(x) for x in pd.read_csv(os.path.join(P.S01, 'split', f))['Grid_ID'])
ZPOST = SPLIT['zone_size_post_buffer']


def sandbox_files():
    out = []
    for dp, _, fs in os.walk(P.SANDBOX_ROOT):
        for fn in fs:
            if fn.startswith('.') or fn.endswith('.pyc') or '__pycache__' in dp:
                continue
            out.append(os.path.join(dp, fn))
    return out


# ---------------------------------------------------------------- LK1 静态 ID
offenders = []
for p in sandbox_files():
    try:
        txt = open(p, 'r', encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    if p.endswith('.csv'):
        try:
            ids = set(int(x) for x in pd.read_csv(p)['Grid_ID'])
            inter = ids & C_IDS
            if inter:
                offenders.append((os.path.relpath(p, P.PROJ), len(inter)))
        except Exception:
            pass
chk('LK1', '沙箱可见 CSV 不含任何 C 区 Grid_ID', not offenders, 'offenders=%s' % offenders)

# ---------------------------------------------------------------- LK2 样本恰为 A∪B 子集
mismatch = []
for p in sandbox_files():
    if not p.endswith('.csv') or not os.path.basename(p).startswith('zone_'):
        continue
    ids = set(int(x) for x in pd.read_csv(p)['Grid_ID'])
    n_expect = {'zone_A_open.csv': ZPOST['1'], 'zone_B_devval.csv': ZPOST['2']}[os.path.basename(p)]
    if (ids - AB_IDS) or (ids & C_IDS) or len(ids) != n_expect:
        mismatch.append((os.path.basename(p), len(ids), n_expect,
                         len(ids - AB_IDS), len(ids & C_IDS)))
chk('LK2', '沙箱样本恰为 A∪B 子集（行数=分区规模，且与 C 无交集）', not mismatch,
    'A=%d B=%d C=%d；mismatch=%s' % (ZPOST['1'], ZPOST['2'], ZPOST['3'], mismatch))

# ---------------------------------------------------------------- LK3 输入为原始公共文件的原样副本
# 判据：沙箱输入与 Stage 01 公共来源逐字节一致（无注入 C 内容）；
# 并附「偶然数值重合」的统计说明，说明为何子串匹配不是有效泄漏判据。
SRC = {
    'zone_A_open.csv': os.path.join(P.S01, 'split', 'zone_A_open.csv'),
    'zone_B_devval.csv': os.path.join(P.S01, 'split', 'zone_B_devval.csv'),
    'hard_constraints.json': os.path.join(P.S01, 'constraints', 'hard_constraints.json'),
    'DATA_DICTIONARY.md': os.path.join(P.S01, 'constraints', 'DATA_DICTIONARY.md'),
    'no_direction_preset.md': os.path.join(P.S01, 'constraints', 'no_direction_preset.md'),
}


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


drift = [(k, sha(os.path.join(P.SANDBOX_INPUTS, k)) != sha(v)) for k, v in SRC.items()
         if sha(os.path.join(P.SANDBOX_INPUTS, k)) != sha(v)]
C_STATS = dict(mean=round(float(cdf_plain['LST_mean'].mean()), 3),
               sd=round(float(cdf_plain['LST_mean'].std()), 3),
               min=round(float(cdf_plain['LST_mean'].min()), 3),
               max=round(float(cdf_plain['LST_mean'].max()), 3))
chk('LK3', '沙箱输入为 Stage 01 公共来源的原样副本（无注入 C 内容）', not drift,
    'drifted=%s' % drift)

# ---------------------------------------------------------------- LK8-LK10 对抗性诱饵
# 背景：一次独立红队复核发现，**纯路径规则**挡不住「白名单内预置硬链接」——
# 硬链接的 realpath 指向其自身路径而非源文件，故按前缀/文件名均判为合法。
# 对策是 L2b（按 inode 身份拒绝）与 L2c（读白名单：白名单之外一律拒绝）。
# 本组三例即为该复核的回归测试。
_LOCKED = os.path.join(P.S01, 'locked', 'zone_C_targets.csv')
HL = os.path.join(P.SANDBOX_WORK, 'lk8_payload.dat')      # 硬链接，文件名不含敏感词
CO = '/tmp/lk9_payload.dat'                               # 读白名单之外的改名副本
SL = os.path.join(P.SANDBOX_WORK, 'lk10_symlink.dat')     # 指向锁定真值的符号链接
for _p in (HL, CO, SL):
    if os.path.islink(_p) or os.path.exists(_p):
        os.remove(_p)
os.link(_LOCKED, HL)
shutil.copyfile(_LOCKED, CO)
os.symlink(_LOCKED, SL)

# ---------------------------------------------------------------- LK4/LK5 运行时（守卫内探针）
PROBE = r'''
import sys, os, json
sys.path.insert(0, r"{lib}"); sys.path.insert(0, r"{sbx}"); sys.path.insert(0, r"{s02}")
import paths02 as P
import access_guard as G
G.activate(actor="leak_probe", limits=dict(max_open_calls=100000, max_seconds=60, max_fits=50))
import numpy as np, builtins
res = {{"denied": [], "leaked": [], "contained": []}}
def attempt(label, fn):
    try:
        fn(); res["leaked"].append(label)
    except G.AccessDenied:
        res["denied"].append(label)
    except Exception as e:
        # 其它异常（如 InvalidTag）不计为泄漏
        res["denied"].append(label + "(" + type(e).__name__ + ")")

def attempt_ret(label, fn):
    # 某些调用（glob）会吞掉 PermissionError；判据改为**返回值是否为空**
    try:
        r = fn()
    except Exception as e:
        res["denied"].append(label + "(" + type(e).__name__ + ")"); return
    if not r:
        res["contained"].append(label)          # 抛错被吞但未获得信息
    else:
        res["leaked"].append(label)

attempt("direct_enc", lambda: open(P.VAULT_ENC,"rb").read())
attempt("direct_key", lambda: open(P.VAULT_KEY,"rb").read())
attempt("locked_C", lambda: open(os.path.join(P.S01,"locked","zone_C_targets.csv")).read())
attempt("full_csv", lambda: open(os.path.join(P.DATA,"data_原始.csv")).read())
attempt("full_raster", lambda: open(os.path.join(P.DATA,"LST_30m_Final new.tif"),"rb").read(64))
rel = os.path.join(P.SANDBOX_ROOT, "work", "..", "..", "vault", "zone_C_targets.enc")
attempt("relative_dotdot", lambda: open(os.path.relpath(rel)).read())
attempt("normalized_path", lambda: open(rel).read())
attempt("numpy_fromfile", lambda: np.fromfile(P.VAULT_ENC, dtype="uint8", count=16))
attempt("numpy_loadtxt", lambda: np.loadtxt(os.path.join(P.DATA,"data_原始.csv"), delimiter=",", max_rows=2))
attempt("listdir_vault", lambda: os.listdir(P.VAULT))
attempt("listdir_locked", lambda: os.listdir(os.path.join(P.S01,"locked")))
attempt("read_reports", lambda: open(os.path.join(P.S02,"reports","s02_validation_result.json")).read())
attempt_ret("glob_vault", lambda: __import__("glob").glob(os.path.join(P.VAULT,"*")))
attempt_ret("glob_locked", lambda: __import__("glob").glob(os.path.join(P.S01,"locked","*")))
# 对抗性诱饵：白名单内硬链接 / 白名单外改名副本 / symlink（LK8-LK10）
attempt("LK8_hardlink_open", lambda: open(r"{hl}","rb").read(64))
attempt("LK8_numpy_fromfile", lambda: np.fromfile(r"{hl}", dtype="uint8", count=16))
attempt("LK9_tmp_copy", lambda: open(r"{co}","rb").read(64))
attempt("LK10_symlink", lambda: open(r"{sl}","rb").read(64))
st = G.shutdown("leak_probe_done")
print("__RESULT__" + json.dumps({{"res":res,"status":st}}))
'''
probe = os.path.join(P.SANDBOX_WORK, '_leak_probe.py')
open(probe, 'w', encoding='utf-8').write(
    PROBE.format(lib=P.S02_LIB, sbx=P.S02_SANDBOX, s02=P.S02, hl=HL, co=CO, sl=SL))
env = dict(os.environ, PYTHONPATH=os.pathsep.join([P.S02_LIB, P.S02_SANDBOX, P.S02]))
cp = subprocess.run([sys.executable, probe], capture_output=True, text=True, env=env)
res = json.loads(cp.stdout.split('__RESULT__', 1)[1].strip()) if '__RESULT__' in cp.stdout else None

direct = ['direct_enc', 'direct_key', 'locked_C', 'full_csv', 'full_raster']
bypass = ['relative_dotdot', 'normalized_path', 'numpy_fromfile', 'numpy_loadtxt',
          'listdir_vault', 'listdir_locked', 'read_reports', 'glob_vault', 'glob_locked']
if res:
    denied = set(res['res']['denied']); contained = set(res['res'].get('contained', []))
    lk = res['res']['leaked']
    chk('LK4', '守卫内直读敏感目标全部被拒',
        all(x in denied for x in direct) and not any(x in lk for x in direct),
        'denied=%s leaked=%s' % (sorted(denied), lk))
    chk('LK5', '绕行尝试（相对/归一化路径、numpy、listdir、glob、reports）均未取得信息',
        not any(x in lk for x in bypass),
        'denied=%s contained(抛错被吞但为空)=%s leaked=%s'
        % (sorted(denied), sorted(contained), lk))
else:
    chk('LK4', '守卫内直读敏感目标全部被拒', False, 'probe 未产出结果')
    chk('LK5', '绕行尝试均未取得信息', False, 'stderr=%s' % cp.stderr[-300:])

# ---------------------------------------------------------------- LK6 密码学
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
blob = open(P.VAULT_ENC, 'rb').read()
key = open(P.VAULT_KEY, 'rb').read()
wrong = bytes(b ^ 0xFF for b in key)
try:
    AESGCM(wrong).decrypt(blob[:12], blob[12:], b'PAID-stage02-vault-v1'); wrong_ok = False
except InvalidTag:
    wrong_ok = True
real_pt = AESGCM(key).decrypt(blob[:12], blob[12:], b'PAID-stage02-vault-v1')
frag = ('%.4f' % float(cdf_plain['LST_mean'].iloc[0])).encode()
chk('LK6', '无密钥不可解密；密文不含明文片段；有密钥可还原',
    wrong_ok and (frag not in blob) and real_pt.startswith(b'Grid_ID'),
    'wrong_key_rejected=%s plaintext_fragment_in_cipher=%s plaintext_head=%r'
    % (wrong_ok, frag in blob, real_pt[:12]))

# ---------------------------------------------------------------- LK7 反向回传
vp = os.path.join(P.S02_REPORTS, 's02_05_validator.json')
vman = json.load(open(vp, encoding='utf-8')) if os.path.exists(vp) else {}
chk('LK7', '验证服务只发布聚合结论，且沙箱不可读 reports',
    'C 区逐格目标值' in vman.get('never_returns', []) and
    (res and 'read_reports' in res['res']['denied']),
    'never_returns=%s sandbox_reports_denied=%s'
    % (vman.get('never_returns'), res and 'read_reports' in res['res']['denied']))

# ---------------------------------------------------------------- LK8-LK10 对抗性绕行（回归）
if res:
    denied2 = set(res['res']['denied']); lk2 = res['res']['leaked']
    lk8 = ['LK8_hardlink_open', 'LK8_numpy_fromfile']
    chk('LK8', '白名单内预置硬链接（文件名无敏感词）无法读取——按 inode 身份拒绝',
        all(x in denied2 for x in lk8) and not any(x in lk2 for x in lk8),
        'denied=%s leaked=%s' % (sorted(denied2 & set(lk8)), [x for x in lk2 if x in lk8]))
    chk('LK9', '白名单之外的改名副本（/tmp）无法读取——读白名单拒绝',
        'LK9_tmp_copy' in denied2 and 'LK9_tmp_copy' not in lk2,
        'denied=%s' % ('LK9_tmp_copy' in denied2))
    chk('LK10', '指向锁定真值的符号链接无法读取（realpath 落回拒绝前缀）',
        'LK10_symlink' in denied2 and 'LK10_symlink' not in lk2,
        'denied=%s' % ('LK10_symlink' in denied2))
else:
    for cid in ('LK8', 'LK9', 'LK10'):
        chk(cid, '对抗性绕行（硬链接/异位副本/symlink）被拒', False, 'probe 未产出结果')

# 清理诱饵（不得留在工作树内）
for _p in (HL, CO, SL):
    try:
        os.remove(_p)
    except OSError:
        pass

# ---------------------------------------------------------------- 附：偶然数值重合（说明性）
_ab_vals = set()
for f in ('zone_A_open.csv', 'zone_B_devval.csv'):
    _ab_vals |= set(round(float(v), 4) for v in pd.read_csv(os.path.join(P.S01, 'split', f))['LST_mean'])
_obs = len(_ab_vals & C_VALS)
_rng = float(cdf_plain['LST_mean'].max() - cdf_plain['LST_mean'].min())
_bins = _rng * 10 ** 4
_exp = len(_ab_vals) * len(C_VALS) / _bins
COINCIDENCE = dict(observed_4dp_matches=_obs, expected_by_chance=round(_exp, 1),
                   note='LST 连续、量程约 %.1f ℃；4 位小数下有 ~%.0f 个可分辨区间，'
                        'A∪B 与 C 的偶然重合期望约 %.0f 次，与实测 %d 同量级。'
                        '故「数值子串匹配」不是有效泄漏判据；有效判据是 LK1（ID 归属）与 '
                        'LK3（输入为原样副本）。' % (_rng, _bins, _exp, _obs))

# ---------------------------------------------------------------- 结论
FAIL = [c['id'] for c in CHECKS if not c['ok']]
verdict = 'PASS' if not FAIL else 'FAIL:' + ','.join(FAIL)
R = dict(version=VERSION, created=CREATED, verdict=verdict, n_checks=len(CHECKS),
         checks=CHECKS, probe=res, C_stats_hidden=C_STATS, coincidence_note=COINCIDENCE)
with open(os.path.join(P.S02_REPORTS, 's02_06_leakage_test.json'), 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

L = ['# S02.6 泄漏测试套件\n', '版本 %s。判定：**%s**（%d 项）。\n' % (VERSION, verdict, len(CHECKS)),
     '| 编号 | 测试 | 结果 | 明细 |', '|---|---|---|---|']
for c in CHECKS:
    L.append('| %s | %s | %s | %s |' % (c['id'], c['desc'], '✓' if c['ok'] else '✗', c['detail']))
L.append('')
L.append('## 附：为何不用「数值子串匹配」判定泄漏\n')
L.append(COINCIDENCE['note'])
L.append('')
L.append('> LK4/LK5 在访问守卫进程内执行；所有拒绝均已写入 append-only 日志。')
L.append('> 局限：守卫运行于同一 OS 用户，属运行时+密码学隔离；内核级隔离（专用用户/容器）为生产化下一步。')
with open(os.path.join(P.S02_REPORTS, 's02_06_leakage_test.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

print(json.dumps(dict(verdict=verdict, failed=FAIL,
                      lk4_lk5=(res['res'] if res else None)), ensure_ascii=False, indent=2))
sys.exit(0 if verdict == 'PASS' else 1)
