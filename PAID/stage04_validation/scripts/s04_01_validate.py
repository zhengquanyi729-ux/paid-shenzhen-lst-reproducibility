"""
S04.1 Stage 04 独立验证：**单次解封 + 完整验证协议**（沙箱之外）
================================================================
框架依据：Table 12 验证协议；§5.3 解封原则；Table 13 七类检验；
          `stage01_protocol/protocol/validation_protocol.json`。

本脚本一次性完成协议要求的**全部**分析（因为每个候选只有一次解封机会，
二次解封会被拒绝，故 strata / 测量误差 / 替代判据必须在同一轮内算完）：

  1) 主终点（逐候选）——直接调用 Stage 02 的 Independent Validator 的 `validate()`，
     取冻结规格的 RMSE(C)、ΔRMSE(vs Baseline A)、199 次空间块置换 p、95% 空间块自助 CI，
     以及**独立复算**的物理审计与负对照（不采信发现侧自报值）。
  2) 多重比较——Holm–Bonferroni（family = 冻结候选集），同时报告未校正 p。
  3) 地表分层——按 NDVI 三分位（全局阈值）分低/中/高植被分层报告 ΔRMSE 与 95% CI；
     并显式报告 C 区分层构成（偏斜）。
  4) 测量误差敏感性——对 C 区目标叠加 ±0.5 / ±1.0 K 高斯扰动重算主检验。
  5) 替代判据稳健性——用更保守的 R=25 格重划 C（C_alt ⊆ C_main，来自同一冻结分区），重算主检验。
  6) 负对照——空间块置换 / 随机目标（由 validate 的独立复算给出）+ **打乱行序的伪候选**（本脚本）。
  7) 缺失/排除登记——C 区格数、缓冲剔除、替代分区剔除，逐一登记。

安全属性：本脚本在沙箱之外运行；只接受 `registry/approved_unseal.json` 中已批准的候选；
         仍然强制冻结哈希一致与 validation_runs<1；结果完整发布（含失败）。

用法：python3 stage04_validation/scripts/s04_01_validate.py [--dry-run]
"""
import os, sys, json, datetime, argparse
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
S04 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S04)
S02 = os.path.join(PROJ, 'stage02_platform')
S03 = os.path.join(PROJ, 'stage03_discovery')
for _p in (os.path.join(S02, 'agents'), os.path.join(S02, 'lib'),
           os.path.join(S02, 'sandbox'), os.path.join(S03, 'lib'),
           os.path.join(PROJ, 'lib')):
    sys.path.insert(0, _p)

import paths02 as P
import paths03 as P3
import log_tool
import model as M
import independent_validator as IV
from independent_validator import (ValidationRefused, canon_hash, decrypt_vault,
                                   delta_rmse, validate)

APPROVED = os.path.join(S04, 'registry', 'approved_unseal.json')
S04_REPORTS = os.path.join(S04, 'reports')
RESULTS = os.path.join(S04_REPORTS, 's04_validation_results.json')
LOG = P3.EXPERIMENT_LOG
SEED = 20260924
N_PERM = IV.N_PERM          # 199
N_BOOT = IV.N_BOOT          # 1000
OFF = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# ------------------------------------------------------------------ 通用统计
def block_perm_pvalue(df, mdl_c, mdl_b, n_perm=N_PERM, seed=SEED, bs=5):
    """空间块置换检验：重排块均值的**取值**并贴回原块标签（保留块内残差）。

    与独立验证服务同一判据、同一实现思路；含"置换须真正改变目标"的显式断言。
    """
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    bmean = df[M.Y].groupby(blk).transform('mean')
    resid = df[M.Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc_b = M.predict(mdl_b, df); pc_c = M.predict(mdl_c, df)
    yv = df[M.Y].to_numpy(float)
    d_obs = float(np.sqrt(np.mean((yv - pc_b) ** 2)) - np.sqrt(np.mean((yv - pc_c) ** 2)))
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yperm = blk.map(sh).to_numpy(float) + resid
        null[i] = (np.sqrt(np.mean((yperm - pc_b) ** 2)) - np.sqrt(np.mean((yperm - pc_c) ** 2)))
    p = float((1 + np.sum(null >= d_obs)) / (1 + n_perm))
    sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yp = blk.map(sh).to_numpy(float) + resid
    corr = float(np.corrcoef(yv, yp)[0, 1])
    if not (corr < 0.9):
        raise ValidationRefused('空间块置换退化为恒等（corr=%.3f）' % corr)
    return p, d_obs, corr


def block_bootstrap_delta(df, mdl_c, mdl_b, n_boot=N_BOOT, seed=SEED, bs=5):
    df = df.reset_index(drop=True)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    groups = {b: g.index.to_numpy() for b, g in df.groupby(blk)}
    blocks = list(groups)
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        d, _, _ = delta_rmse(df.iloc[sel], mdl_c, mdl_b)
        boot[i] = d
    return [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]


# ------------------------------------------------------------------ 分层 / 误差 / 替代判据
def global_terciles():
    """全局 NDVI 三分位阈值（在 Stage 01 主样本上计算，与 S01.2 同规则）。"""
    ids = [int(x) for x in open(os.path.join(P.S00, 'mask', 'valid_ids_main.txt')).read().split()]
    df = pd.read_csv(os.path.join(P.DATA, 'data_原始.csv'))
    df.columns = [c.strip() for c in df.columns]
    df = df.set_index('My_ID')
    ndvi = np.array([float(df.loc[g, 'NDVI_mean']) for g in ids])
    q1, q2 = np.quantile(ndvi, [1 / 3, 2 / 3])
    return float(q1), float(q2)


def strata_report(C, mdl_c, mdl_b, q1, q2):
    tt = np.where(C['NDVI_mean'].to_numpy(float) <= q1, 0,
                  np.where(C['NDVI_mean'].to_numpy(float) <= q2, 1, 2))
    out = {}
    for lab, name in ((0, 'low_veg'), (1, 'mid_veg'), (2, 'high_veg')):
        sub = C[tt == lab].reset_index(drop=True)
        if len(sub) < 20:
            out[name] = dict(n=int(len(sub)), note='格数过少，不单独推断')
            continue
        rb = M.rmse(sub[M.Y], M.predict(mdl_b, sub))
        rc = M.rmse(sub[M.Y], M.predict(mdl_c, sub))
        ci = block_bootstrap_delta(sub, mdl_c, mdl_b, n_boot=500)
        out[name] = dict(n=int(len(sub)), rmse_baselineA=rb, rmse_candidate=rc,
                         delta_rmse=rb - rc, ci95_delta=ci,
                         ci_excludes_zero=bool(ci[0] > 0 or ci[1] < 0))
    return out


def measurement_error(C, mdl_c, mdl_b, sds=(0.5, 1.0), n_draws=20):
    out = {}
    for sd in sds:
        rng = np.random.default_rng(SEED + int(round(sd * 10)))
        ps, ds = [], []
        for _ in range(n_draws):
            Cn = C.copy()
            Cn[M.Y] = Cn[M.Y].to_numpy(float) + rng.normal(0.0, sd, len(Cn))
            p, d, _ = block_perm_pvalue(Cn, mdl_c, mdl_b, n_perm=99)
            ps.append(p); ds.append(d)
        ds = np.asarray(ds, float); ps = np.asarray(ps, float)
        out['sd_%.1fK' % sd] = dict(
            n_draws=n_draws, delta_mean=float(ds.mean()), delta_min=float(ds.min()),
            delta_max=float(ds.max()), delta_interval_width=float(ds.max() - ds.min()),
            p_median=float(np.median(ps)), frac_p_lt_0p05=float((ps < 0.05).mean()),
            frac_delta_pos=float((ds > 0).mean()))
    return out


# ------------------------------------------------------------------ 替代判据分区（R=25）
def _dilate(mask, k, NR, NCc):
    o = mask.copy()
    for _ in range(k):
        n = o.copy()
        for dr, dc in OFF:
            a = np.zeros_like(o)
            a[max(0, dr):NR + min(0, dr), max(0, dc):NCc + min(0, dc)] = \
                o[max(0, -dr):NR + min(0, -dr), max(0, -dc):NCc + min(0, -dc)]
            n |= a
        o = n
    return o


def alt_R_ids():
    """用更保守判据 R=25 格重划锁定区（C_alt ⊆ C_main），复刻 S01.2 的缓冲逻辑。"""
    sp = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))
    NR = int(sp['row'].max()) + 1
    NCc = int(sp['col'].max()) + 1
    zone = np.zeros((NR, NCc), np.int8)
    inmain = np.zeros((NR, NCc), bool)
    zone[sp['row'].to_numpy(), sp['col'].to_numpy()] = sp['zone'].to_numpy()
    inmain[sp['row'].to_numpy(), sp['col'].to_numpy()] = sp['in_main'].to_numpy().astype(bool)
    AB = (zone == 1) | (zone == 2)
    nearAB = _dilate(AB, 1, NR, NCc)
    # 自检：R=15 时缓冲格应等于冻结清单的 3407
    tc15 = _dilate(nearAB, 14, NR, NCc) & (zone == 3) & inmain
    tc25 = _dilate(nearAB, 24, NR, NCc) & (zone == 3) & inmain
    ids15 = set(sp['Grid_ID'].to_numpy()[tc15[sp['row'].to_numpy(), sp['col'].to_numpy()]])
    ids25 = set(sp['Grid_ID'].to_numpy()[tc25[sp['row'].to_numpy(), sp['col'].to_numpy()]])
    main_c = set(sp['Grid_ID'].to_numpy()[(sp['zone'] == 3).to_numpy() &
                                          (sp['in_main'].to_numpy().astype(bool))])
    c_alt = main_c - ids25
    return dict(n_buffer_R15=len(ids15), n_buffer_R25=len(ids25),
                n_C_main=len(main_c), n_C_alt=len(c_alt), c_alt_ids=c_alt)


# ------------------------------------------------------------------ 伪候选（打乱行序）
def pseudo_shuffled_candidate(cand, A):
    """在 A 区用**打乱的 LST**拟合候选表达式——零技巧伪候选，应该在 C 上无增益。"""
    terms = IV._as_ast(cand['expression']['terms'])
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
    mu = {v: float(A[v].mean()) for v in vs}
    sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
    rng = np.random.default_rng(SEED)
    As = A.copy(); As[M.Y] = rng.permutation(As[M.Y].to_numpy())
    return M.fit_expr(As, terms, mu=mu, sd=sd)


# ------------------------------------------------------------------ 主流程
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)

    os.makedirs(S04_REPORTS, exist_ok=True)
    appr = json.load(open(APPROVED, encoding='utf-8'))
    registry = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    reg = {c['id']: c for c in registry['frozen']}
    approved_ids = [c['id'] for c in appr['approved_candidates']]

    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    mask = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))[['Grid_ID', 'row', 'col']]
    A = A.merge(mask, on='Grid_ID', how='left')
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv')).merge(
        mask, on='Grid_ID', how='left')
    mdl_b = M.fit_linear(A, M.BASELINE_A_TERMS)

    C, vault_sha = decrypt_vault()
    sp = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))[['Grid_ID', 'row', 'col']]
    C = C.merge(sp, on='Grid_ID', how='left')

    q1, q2 = global_terciles()
    alt = alt_R_ids()
    C_alt = C[C['Grid_ID'].isin(alt['c_alt_ids'])].reset_index(drop=True)

    out = dict(version='stage04-validation-v1',
               created=datetime.datetime.now().isoformat(timespec='seconds'),
               approved=appr['approved_candidates'],
               n_C_main=int(len(C)), n_C_alt=int(alt['n_C_alt']),
               buffer=dict(R15=alt['n_buffer_R15'], R25=alt['n_buffer_R25']),
               vault_plaintext_sha256=vault_sha,
               ndvi_tercile_thresholds=[q1, q2],
               note='单次解封；完整协议分析在同一轮内完成；失败同样完整发布。',
               candidates={})

    for cid in approved_ids:
        # 冻结校验
        if cid not in reg:
            raise ValidationRefused('候选 %s 未在冻结登记中' % cid)
        cand = json.load(open(os.path.join(P3.S03_CAND, cid + '.json'), encoding='utf-8'))
        if canon_hash(cand) != reg[cid]['canon_hash']:
            raise ValidationRefused('候选 %s 哈希与冻结登记不一致' % cid)
        if not a.dry_run and reg[cid].get('validation_runs', 0) >= 1:
            raise ValidationRefused('候选 %s 已解封过（validation_runs=1）' % cid)

        mdl_c = cand['model']
        rec = {}

        # ---- 1) 主终点（冻结规格的验证服务）
        res, _ = validate(cand, registry, dry_run=True)   # 直接取函数结果，不做注册表自增
        rec['primary_endpoint'] = res['primary_endpoint']
        rec['conditions'] = res['conditions']
        rec['passed'] = res['passed']
        rec['independent_audit'] = res['independent_audit']
        rec['independent_controls'] = res['independent_controls']
        rec['self_reported'] = res['self_reported']

        # 交叉核对：本脚本独立实现的主终点应与验证服务一致
        p2, d2, corr2 = block_perm_pvalue(C, mdl_c, mdl_b)
        rec['cross_check'] = dict(
            delta_rmse_self=float(d2), delta_rmse_validator=float(res['primary_endpoint']['delta_rmse']),
            perm_p_self=p2, perm_p_validator=float(res['primary_endpoint']['perm_p']),
            agree_delta=bool(abs(d2 - res['primary_endpoint']['delta_rmse']) < 1e-9))

        # ---- 3) NDVI 分层
        rec['strata_ndvi'] = strata_report(C, mdl_c, mdl_b, q1, q2)

        # ---- 4) 测量误差
        rec['measurement_error'] = measurement_error(C, mdl_c, mdl_b)

        # ---- 5) 替代判据 R=25
        pa, da, _ = block_perm_pvalue(C_alt, mdl_c, mdl_b)
        rec['criterion_sensitivity_R25'] = dict(
            n_C=int(len(C_alt)), delta_rmse=float(da), perm_p=pa,
            sign_consistent_with_R15=bool((da > 0) == (res['primary_endpoint']['delta_rmse'] > 0)))

        # ---- 6) 伪候选（打乱行序）
        if cand.get('expression', {}).get('form') == 'expr':
            try:
                mdl_ps = pseudo_shuffled_candidate(cand, A)
                rps = float(M.rmse(C[M.Y], M.predict(mdl_ps, C)))
                rbs = float(M.rmse(C[M.Y], M.predict(mdl_b, C)))
                rcs = float(M.rmse(C[M.Y], M.predict(mdl_c, C)))
                # 常数地板：以 A 区 LST 均值作为常数预测在 C 区的 RMSE。
                # 打乱 A 区目标后重拟合通常得到 ≈0 系数，预测退化为常数；
                # 若该"伪候选"仍胜过 Baseline A，说明 Baseline A 在 C 区迁移性弱
                # （比较器脆弱），此时更有意义的是"真候选是否胜过伪候选"。
                const = float(np.sqrt(np.mean((C[M.Y].to_numpy(float) - A[M.Y].mean()) ** 2)))
                rec['pseudo_row_shuffled'] = dict(
                    rmse=float(rps), rmse_baselineA=float(rbs), rmse_candidate=float(rcs),
                    rmse_constant_floor=const,
                    delta_rmse_pseudo_vs_baseline=float(rbs - rps),
                    pseudo_beats_baseline=bool(rps < rbs),
                    candidate_beats_pseudo=bool(rcs < rps),
                    note='打乱 A 区目标行序后重拟合得到的伪候选（预测≈常数）。'
                         'pseudo_beats_baseline=True 只说明 Baseline A 在 C 区迁移性弱，'
                         '不构成对候选的支持；关键判据是 candidate_beats_pseudo。')
            except Exception as e:
                rec['pseudo_row_shuffled'] = dict(error=repr(e))
        else:
            rec['pseudo_row_shuffled'] = dict(skipped='线性形式候选，不构造伪候选')

        out['candidates'][cid] = rec
        log_tool.append(cid, 'unsealed_validated', logpath=LOG,
                        delta_rmse=rec['primary_endpoint']['delta_rmse'],
                        perm_p=rec['primary_endpoint']['perm_p'],
                        passed=rec['passed'], dry_run=a.dry_run)

    # ---- 2) Holm–Bonferroni（family = 冻结候选集）
    m = len(registry['frozen'])
    tested = sorted(approved_ids,
                    key=lambda k: out['candidates'][k]['primary_endpoint']['perm_p'])
    holm = []
    for i, cid in enumerate(tested):
        p = out['candidates'][cid]['primary_endpoint']['perm_p']
        thr = 0.05 / (m - i)          # Holm 逐步下调阈值，rank 从 1 起
        holm.append(dict(id=cid, p_uncorrected=p, holm_threshold=thr,
                         reject=bool(p < thr)))
    out['multiplicity'] = dict(
        family_size=m, family='冻结候选集（3 发现候选 + 1 安慰剂）',
        note='Holm–Bonferroni。本轮仅解封 2 个（保守方案），其余保留解封预算；'
             'family_size 按预注册的冻结集取 %d（更保守）。' % m,
        stepdown=holm)

    if not a.dry_run:
        with open(RESULTS, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        for c in registry['frozen']:
            if c['id'] in approved_ids:
                c['validation_runs'] = c.get('validation_runs', 0) + 1
                c['last_result'] = dict(passed=out['candidates'][c['id']]['passed'],
                                        delta_rmse=out['candidates'][c['id']]['primary_endpoint']['delta_rmse'])
        with open(P3.FROZEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
        print('[s04] wrote', RESULTS)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
