"""
S03.6 复核：A/B 区稳健性检查（**不开 C 区**）
=============================================
目的：在进入 Stage 04 之前，检验"三个发现候选在 A 区优于冻结基线"这一结论
对若干分析选择的敏感程度。所有检验**只读 A/B 两区与冻结登记**——不接触 C 区、
不消耗任何候选的解封机会（validation_runs 保持不变）。

检验项：
  C1 折划分种子    —— 换 4 个种子重算 A 区空间分块 CV（k=5）；
  C2 分块粒度      —— k=5/8/12 三档（同一 k-means 连通簇规则）；
  C3 测量误差      —— 目标叠加 ±0.5 / ±1.0 K 高斯噪声并**重新拟合**（各 20 次抽样）；
  C4 分块自助 CI   —— A 区内 ΔA 的 95% 自助区间（说明性，不替代 C 区主终点）；
  C5 空间块置换 p  —— A 区内 ΔA 的置换显著性（说明性）。

判读纪律：A 区读数带**选择偏倚**（搜索就在 A 区选模型），因此 C4/C5 只用于说明
"结论是否稳健"，**不能**当作确认性检验——真正的检验是 C 区单次解封的主终点。

用法：python3 stage03_discovery/scripts/s03_06_robustness.py
输出：stage03_discovery/reports/robustness.json
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S03)
S02 = os.path.join(PROJ, 'stage02_platform')
for p in (os.path.join(S03, 'lib'), os.path.join(S03, 'agents'),
          os.path.join(S02, 'agents'), os.path.join(S02, 'lib')):
    sys.path.insert(0, p)
import paths02 as P
import paths03 as P3
import model as M
import core as CORE

Y = M.Y
SEED0 = 20260924
N_BOOT = 1000
N_PERM = 199
BA_TERMS = [CORE.var(v) for v in M.BASELINE_A_TERMS]


def load():
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    m = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))[['Grid_ID', 'row', 'col']]
    A = A.merge(m, on='Grid_ID', how='left')
    B = B.merge(m, on='Grid_ID', how='left')
    return A, B


def cv(df, terms, folds):
    r, _ = CORE.pooled_cv_rmse(df, terms, folds)
    return float(r)


def fit_on(df, terms):
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
    mu = {v: float(df[v].mean()) for v in vs}
    sd = {v: float(df[v].std(ddof=0)) or 1.0 for v in vs}
    return M.fit_expr(df, terms, mu=mu, sd=sd)


def rmse_of(df, mdl):
    return M.rmse(df[Y], M.predict(mdl, df))


def main():
    A, B = load()
    reg = json.load(open(P3.CANDIDATE_REGISTRY, encoding='utf-8'))
    fr = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    by_id = {c['id']: c for c in reg['candidates']}
    disc = [f['id'] for f in fr['frozen'] if f['role'] == 'discovery_candidate']
    terms = {cid: by_id[cid]['expression']['terms'] for cid in disc}

    out = dict(version='stage03-robustness-v1',
               created=datetime.datetime.now().isoformat(timespec='seconds'),
               note='只读 A/B；不开 C 区；不消耗解封机会。A 区读数含选择偏倚，属说明性检验。',
               n_A=int(len(A)), n_B=int(len(B)), candidates=disc,
               baselineA_terms=M.BASELINE_A_TERMS)

    # ---------------------------------------------------------------- C1 多种子
    c1 = []
    for seed in (SEED0, 7, 101, 2026):
        folds = CORE.spatial_folds(A, 5, seed)
        base = cv(A, BA_TERMS, folds)
        row = dict(seed=int(seed), baselineA_cv=base)
        for cid in disc:
            r = cv(A, terms[cid], folds)
            row[cid] = dict(cv=r, delta_A=base - r)
        c1.append(row)
    out['C1_multi_seed'] = c1

    # ---------------------------------------------------------------- C2 多粒度
    c2 = []
    for k in (5, 8, 12):
        folds = CORE.spatial_folds(A, k, SEED0)
        base = cv(A, BA_TERMS, folds)
        row = dict(k=int(k), baselineA_cv=base)
        for cid in disc:
            r = cv(A, terms[cid], folds)
            row[cid] = dict(cv=r, delta_A=base - r)
        c2.append(row)
    out['C2_block_granularity'] = c2

    # ---------------------------------------------------------------- C3 测量误差（重拟合）
    folds0 = CORE.spatial_folds(A, 5, SEED0)
    rng = np.random.default_rng(SEED0)
    c3 = []
    for sd_err in (0.5, 1.0):
        acc = {cid: [] for cid in disc}
        for _ in range(20):
            An = A.copy()
            An[Y] = An[Y].to_numpy(float) + rng.normal(0.0, sd_err, len(An))
            base = cv(An, BA_TERMS, folds0)
            for cid in disc:
                acc[cid].append(base - cv(An, terms[cid], folds0))
        row = dict(sd_err_K=sd_err, n_draws=20)
        for cid in disc:
            a = np.asarray(acc[cid], float)
            row[cid] = dict(mean=float(a.mean()), min=float(a.min()), max=float(a.max()),
                            frac_pos=float((a > 0).mean()))
        c3.append(row)
    out['C3_measurement_error'] = c3

    # ---------------------------------------------------------------- C4/C5（A 区内，块=5×5）
    C = A.reset_index(drop=True)
    blk = pd.Series(list(zip(C['row'] // 5, C['col'] // 5)), index=C.index)
    groups = {b: g.index.to_numpy() for b, g in C.groupby(blk)}
    blocks = list(groups)
    rng2 = np.random.default_rng(SEED0)
    mdl_base = fit_on(C, BA_TERMS)
    c45 = {}
    for cid in disc:
        mdl_c = fit_on(C, terms[cid])
        rb = rmse_of(C, mdl_base); rc = rmse_of(C, mdl_c)
        d_obs = rb - rc
        # C4 自助 CI
        boot = np.empty(N_BOOT)
        for i in range(N_BOOT):
            pick = rng2.choice(len(blocks), size=len(blocks), replace=True)
            sel = np.concatenate([groups[blocks[j]] for j in pick])
            sub = C.iloc[sel]
            boot[i] = rmse_of(sub, mdl_base) - rmse_of(sub, mdl_c)
        ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
        # C5 空间块置换（重排块均值的**取值**，保留块内残差）
        bmean = C[Y].groupby(blk).transform('mean')
        resid = C[Y].to_numpy(float) - bmean.to_numpy(float)
        ymean = bmean.groupby(blk).first()
        pc_b = M.predict(mdl_base, C); pc_c = M.predict(mdl_c, C)
        null = np.empty(N_PERM)
        for i in range(N_PERM):
            sh = pd.Series(rng2.permutation(ymean.to_numpy(float)), index=ymean.index)
            yperm = blk.map(sh).to_numpy(float) + resid
            null[i] = (np.sqrt(np.mean((yperm - pc_b) ** 2))
                       - np.sqrt(np.mean((yperm - pc_c) ** 2)))
        p = float((1 + np.sum(null >= d_obs)) / (1 + N_PERM))
        # 置换是否确实发生了（防"恒等"缺陷的显式断言）
        corr_y = float(np.corrcoef(C[Y].to_numpy(float), (blk.map(
            pd.Series(rng2.permutation(ymean.to_numpy(float)), index=ymean.index)
        ).to_numpy(float) + resid))[0, 1])
        c45[cid] = dict(delta_A_obs=float(d_obs), ci95_A=ci,
                        ci_excludes_zero=bool(ci[0] > 0 or ci[1] < 0),
                        perm_p_A=p, n_perm=N_PERM,
                        perm_corr_sanity=corr_y)
    out['C45_A_only_inference'] = c45

    os.makedirs(P3.S03_REPORTS, exist_ok=True)
    outp = os.path.join(P3.S03_REPORTS, 'robustness.json')
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # ---------------------------------------------------------------- 摘要
    print('== C1 多种子 A 区空间分块 CV（ΔA = 基线 - 候选）==')
    for row in c1:
        print('  seed=%-9d base=%.4f | %s' % (
            row['seed'], row['baselineA_cv'],
            ' '.join('%s=%+.4f' % (cid.split('-')[1], row[cid]['delta_A']) for cid in disc)))
    print('== C2 分块粒度 ==')
    for row in c2:
        print('  k=%-3d base=%.4f | %s' % (
            row['k'], row['baselineA_cv'],
            ' '.join('%s=%+.4f' % (cid.split('-')[1], row[cid]['delta_A']) for cid in disc)))
    print('== C3 测量误差（重拟合，20 次抽样）==')
    for row in c3:
        print('  sd=%.1fK | %s' % (
            row['sd_err_K'],
            ' '.join('%s: mean%+.3f [%+.3f,%+.3f] pos=%.0f%%'
                     % (cid.split('-')[1], row[cid]['mean'], row[cid]['min'],
                        row[cid]['max'], 100 * row[cid]['frac_pos']) for cid in disc)))
    print('== C4/C5 A 区内说明性推断 ==')
    for cid, d in c45.items():
        print('  %-22s dA=%+.4f CI=[%+.4f,%+.4f] excl0=%s perm_p=%.3f corr_sanity=%.3f'
              % (cid, d['delta_A_obs'], d['ci95_A'][0], d['ci95_A'][1],
                 d['ci_excludes_zero'], d['perm_p_A'], d['perm_corr_sanity']))
    print('[s03-robustness] wrote', outp)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
