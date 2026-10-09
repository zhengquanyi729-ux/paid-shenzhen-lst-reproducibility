"""
S04.4 H10 表达式复盘：DEM 依赖审查（只读，不改 Stage 04 冻结记录）
==================================================================
背景：`S03-H10-GREEDY` 的 5 项中有 3 项涉及 `DEM_mean`
（`exp(DEM_mean)`、`exp(NDVI)×?` 及 `NDVI_mean×DEM_mean`），
而 Stage 01 已认定 DEM 值域仅 3–17 m、明显不可信。本脚本回答：

  Q1 冻结 H10 的预测有多少由 DEM 项撑起？（项解剖：每项对预测方差的贡献占比）
  Q2 把 DEM 项整体/部分删掉后，A-CV、B 区、C 区的增益还剩多少？
  Q3 DEM 本身可不可信、是否只是"位置"的代理？（值域、共线性、对坐标的 R²）
  Q4 若用平滑空间坐标替代 DEM 项，能否复现同样的增益？（空间代理检验）

A/B 区读数无争议；C 区**已在本轮解封**，下列 C 区读数属**post-hoc 探索性**，
不是新增的确认性检验，报告中据实标注。

用法：python3 stage04_validation/expr_review/s04_04_expr_review.py
输出：stage04_validation/expr_review/{expr_review.json, EXPR_REVIEW.md}
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
S04 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S04)
S02 = os.path.join(PROJ, 'stage02_platform')
S03 = os.path.join(PROJ, 'stage03_discovery')
for _p in (os.path.join(S02, 'agents'), os.path.join(S02, 'lib'),
           os.path.join(S02, 'sandbox'), os.path.join(S03, 'lib'),
           os.path.join(S03, 'agents')):
    sys.path.insert(0, _p)

import paths02 as P
import paths03 as P3
import model as M
import core as CORE
from independent_validator import decrypt_vault

Y = M.Y
SEED0 = 20260924
N_PERM = 199
N_BOOT = 1000
BA = [CORE.var(v) for v in M.BASELINE_A_TERMS]


# ---------------------------------------------------------------- 载入
def load():
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    m = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))[['Grid_ID', 'row', 'col']]
    A = A.merge(m, on='Grid_ID', how='left')
    B = B.merge(m, on='Grid_ID', how='left')
    C, sha = decrypt_vault()
    sp = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))[['Grid_ID', 'row', 'col']]
    C = C.merge(sp, on='Grid_ID', how='left')
    return A, B, C, sha


def fit_on(df, terms):
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms])) if terms else []
    mu = {v: float(df[v].mean()) for v in vs}
    sd = {v: float(df[v].std(ddof=0)) or 1.0 for v in vs}
    return M.fit_expr(df, terms, mu=mu, sd=sd)


def d_rmse(df, mdl_c, mdl_b):
    rb = M.rmse(df[Y], M.predict(mdl_b, df))
    rc = M.rmse(df[Y], M.predict(mdl_c, df))
    return rb - rc, rb, rc


# ---------------------------------------------------------------- 推断（块=5×5）
def block_perm(df, mdl_c, mdl_b, n_perm=N_PERM, seed=SEED0, bs=5):
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    bmean = df[Y].groupby(blk).transform('mean')
    resid = df[Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc_b = M.predict(mdl_b, df); pc_c = M.predict(mdl_c, df)
    yv = df[Y].to_numpy(float)
    d = float(np.sqrt(np.mean((yv - pc_b) ** 2)) - np.sqrt(np.mean((yv - pc_c) ** 2)))
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yp = blk.map(sh).to_numpy(float) + resid
        null[i] = np.sqrt(np.mean((yp - pc_b) ** 2)) - np.sqrt(np.mean((yp - pc_c) ** 2))
    p = float((1 + np.sum(null >= d)) / (1 + n_perm))
    sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yp = blk.map(sh).to_numpy(float) + resid
    corr = float(np.corrcoef(yv, yp)[0, 1])
    return p, d, corr


def block_boot(df, mdl_c, mdl_b, n_boot=N_BOOT, seed=SEED0, bs=5):
    df = df.reset_index(drop=True)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    groups = {b: g.index.to_numpy() for b, g in df.groupby(blk)}
    blocks = list(groups)
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        sub = df.iloc[sel]
        boot[i] = M.rmse(sub[Y], M.predict(mdl_b, sub)) - M.rmse(sub[Y], M.predict(mdl_c, sub))
    return [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]


# ---------------------------------------------------------------- 主流程
def main():
    A, B, C, sha = load()
    cand = json.load(open(os.path.join(P3.S03_CAND, 'S03-H10-GREEDY.json'), encoding='utf-8'))
    T = cand['expression']['terms']
    mdl_b = M.fit_linear(A, M.BASELINE_A_TERMS)
    folds = CORE.spatial_folds(A, 5, SEED0)
    base_cv, _ = CORE.pooled_cv_rmse(A, BA, folds)
    dat = dict(version='stage04-expr-review-v1',
               created=datetime.datetime.now().isoformat(timespec='seconds'),
               vault_plaintext_sha256=sha,
               n_A=int(len(A)), n_B=int(len(B)), n_C=int(len(C)),
               baselineA_cv=float(base_cv),
               note='C 区已解封；下列 C 区读数为 post-hoc 探索性，非新增确认性检验。')

    # ============================================================== Q1 项解剖
    mu = cand['model']['mu']; sd = cand['model']['sd']; beta = np.asarray(cand['model']['beta'], float)
    X = np.nan_to_num(M.expr_design(C, T, mu, sd), nan=0.0, posinf=0.0, neginf=0.0)
    contrib = [beta[1 + i] * X[:, 1 + i] for i in range(len(T))]
    pred = beta[0] + np.sum(contrib, axis=0)
    var_all = float(np.var(pred))
    labels = [CORE._fmt(t) for t in T]          # 逐项格式化（fmt_terms 返回整串，不能用）
    anatomy = []
    for i, t in enumerate(T):
        dvars = sorted(M.expr_vars(t))
        var_minus = float(np.var(pred - contrib[i]))
        share = (var_all - var_minus) / var_all if var_all > 0 else float('nan')
        anatomy.append(dict(term=labels[i], vars=dvars, beta=float(beta[1 + i]),
                            dem=bool('DEM_mean' in dvars),
                            contrib_sd=float(np.std(contrib[i])),
                            pred_var_share=float(share)))
    dat['Q1_anatomy'] = dict(intercept_beta=float(beta[0]), pred_var_C=var_all,
                             terms=anatomy,
                             dem_terms_share=float(sum(a['pred_var_share'] for a in anatomy if a['dem'])))

    # ============================================================== Q2 DEM 消融
    def has_dem(t):
        return 'DEM_mean' in M.expr_vars(t)
    variants = {
        'full(冻结H10)': T,
        'no_dem': [t for t in T if not has_dem(t)],
        'drop_expDEM': [t for t in T if not (t.get('op') == 'exp' and has_dem(t))],
        'drop_NDVIxDEM': [t for t in T if t.get('op') != 'mul'],
        'dem_only': [t for t in T if has_dem(t)],
        'no_dem+coords': [t for t in T if not has_dem(t)] + [CORE.var('row'), CORE.var('col')],
    }
    # 逐项单删（重拟合）——精确定位哪一项在起作用
    for i, t in enumerate(T):
        variants['drop[%d]%s' % (i + 1, labels[i])] = [x for j, x in enumerate(T) if j != i]
    dem_ab = {}
    for name, terms in variants.items():
        mdl = fit_on(A, terms)
        cv, _ = CORE.pooled_cv_rmse(A, terms, folds)
        dA = float(base_cv - cv)
        dB, rb_b, _ = d_rmse(B, mdl, mdl_b)
        dC, rb_c, rc_c = d_rmse(C, mdl, mdl_b)
        pC, dC2, corrC = block_perm(C, mdl, mdl_b)
        ciC = block_boot(C, mdl, mdl_b)
        dem_ab[name] = dict(n_terms=len(terms), complexity=int(M.complexity(terms)),
                            terms=CORE.fmt_terms(terms),
                            A_cv=float(cv), delta_A_cv=dA,
                            B_rmse=float(M.rmse(B[Y], M.predict(mdl, B))), delta_B=float(dB),
                            C_rmse=float(rc_c), delta_C=float(dC),
                            C_perm_p=pC, C_ci95=ciC,
                            C_ci_excludes_zero=bool(ciC[0] > 0 or ciC[1] < 0),
                            perm_corr_sanity=corrC)
    dat['Q2_dem_ablation'] = dem_ab
    dat['Q2_constant_floor_C_rmse'] = float(np.sqrt(np.mean(
        (C[Y].to_numpy(float) - A[Y].mean()) ** 2)))

    # ============================================================== Q3 DEM 可信性
    def dem_stats(df):
        v = df['DEM_mean'].to_numpy(float)
        return dict(n=int(len(v)), min=float(v.min()), max=float(v.max()),
                    mean=float(v.mean()), sd=float(v.std(ddof=0)))
    corr = {}
    for v in ['NDVI_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens',
              'row', 'col']:
        a = A['DEM_mean'].to_numpy(float); b = A[v].to_numpy(float)
        corr[v] = float(np.corrcoef(a, b)[0, 1])
    # DEM ~ [row,col,row^2,col^2] 的 OLS R²（A 区）：衡量 DEM 是否只是平滑空间场
    rc = A[['row', 'col']].to_numpy(float)
    rc = (rc - rc.mean(0)) / (rc.std(0) + 1e-12)
    Xd = np.column_stack([np.ones(len(A)), rc, rc[:, 0] ** 2, rc[:, 1] ** 2])
    yv = A['DEM_mean'].to_numpy(float)
    bb = np.linalg.lstsq(Xd, yv, rcond=None)[0]
    r2 = 1 - np.sum((yv - Xd @ bb) ** 2) / np.sum((yv - yv.mean()) ** 2)
    dat['Q3_dem'] = dict(A=dem_stats(A), B=dem_stats(B), C=dem_stats(C),
                         corr_on_A=corr, dem_on_coords_r2_A=float(r2))

    # ============================================================== Q4 空间代理检验
    # 若"去 DEM + 平滑空间坐标"能复现 full 的 C 区增益，则 DEM 项实质是位置代理。
    full = dem_ab['full(冻结H10)']; nodem = dem_ab['no_dem']; coord = dem_ab['no_dem+coords']
    dat['Q4_spatial_proxy'] = dict(
        full_delta_C=full['delta_C'], no_dem_delta_C=nodem['delta_C'],
        coord_delta_C=coord['delta_C'],
        coord_recovers_frac=float(coord['delta_C'] / full['delta_C']) if full['delta_C'] else None,
        coord_gain_over_no_dem=float(coord['delta_C'] - nodem['delta_C']),
        note='no_dem 已单独达到该增益，再加平滑坐标的增量接近 0，'
             '说明增益**不在**"DEM/位置代理"这条通道上，'
             '而在非 DEM 的植被项里（见 Q2 单删 exp(NDVI) 的结果）。')

    # ============================================================== 输出
    with open(os.path.join(_HERE, 'expr_review.json'), 'w', encoding='utf-8') as f:
        json.dump(dat, f, ensure_ascii=False, indent=2)
    _write_report(dat)
    print('[s04-expr-review] wrote', os.path.join(_HERE, 'expr_review.json'))
    print('[s04-expr-review] wrote', os.path.join(_HERE, 'EXPR_REVIEW.md'))
    # ---- 控制台摘要
    print('\nQ1 项解剖（DEM 项预测方差占比合计 %.3f）:' % dat['Q1_anatomy']['dem_terms_share'])
    for a in anatomy:
        print('   %-26s beta=%+.3f dem=%-5s share=%.3f' % (a['term'], a['beta'], a['dem'], a['pred_var_share']))
    print('\nQ2 消融（Δ vs Baseline A）:')
    print('   %-16s %-6s %8s %9s %9s %8s' % ('variant', 'cplx', 'A_CV', 'dA_CV', 'dB(B)', 'dC(C)'))
    for name, r in dem_ab.items():
        print('   %-16s %-6d %8.4f %+9.4f %+9.4f %+8.4f' %
              (name, r['complexity'], r['A_cv'], r['delta_A_cv'], r['delta_B'], r['delta_C']))
    print('\nQ3 DEM: A range [%.2f, %.2f]; corr(row)=%.3f corr(col)=%.3f; R2(DEM~coords)=%.3f'
          % (dat['Q3_dem']['A']['min'], dat['Q3_dem']['A']['max'],
             corr['row'], corr['col'], r2))
    print('Q4 空间代理: full dC=%+.4f  no_dem dC=%+.4f  +coords dC=%+.4f  (recovers %.2f)'
          % (full['delta_C'], nodem['delta_C'], coord['delta_C'],
             dat['Q4_spatial_proxy']['coord_recovers_frac'] or float('nan')))
    return 0


def _write_report(d):
    L = []
    A_ = L.append
    A_('# H10 表达式复盘：DEM 依赖审查（Stage 04 后续）')
    A_('')
    A_('| 项 | 值 |')
    A_('|---|---|')
    A_('| 版本 | stage04-expr-review-v1 |')
    A_('| 生成 | %s |' % d['created'])
    A_('| 对象 | `S03-H10-GREEDY` 的冻结表达式 |')
    A_('| 数据 | A %d / B %d / C %d（C 已解封，C 区读数属 post-hoc 探索） |'
      % (d['n_A'], d['n_B'], d['n_C']))
    A_('| 不改动 | Stage 04 冻结结果与清单均未改写 |')
    A_('')
    A_('## Q1 项解剖：DEM 项撑起多少预测方差')
    A_('')
    A_('在 C 区、用冻结标准化常数与系数，逐项看它塑造预测的程度'
      '（`pred_var_share` = 去掉该项后预测方差的相对下降）。')
    A_('')
    A_('| 项 | 系数 β | 含 DEM | 贡献 sd | 预测方差占比 |')
    A_('|---|---|---|---|---|')
    for a in d['Q1_anatomy']['terms']:
        A_('| `%s` | %+.3f | %s | %.3f | %.3f |'
          % (a['term'], a['beta'], '✓' if a['dem'] else '', a['contrib_sd'], a['pred_var_share']))
    A_('')
    A_('**含 DEM 项合计占预测方差 %.3f**（截距 β=%.3f）。'
      % (d['Q1_anatomy']['dem_terms_share'], d['Q1_anatomy']['intercept_beta']))
    A_('')
    A_('## Q2 DEM 消融：删项后增益还剩多少')
    A_('')
    A_('各变体在 A 区重新拟合（同一冻结折划分），比较 A 区空间分块 CV、B 区、C 区'
      '相对 Baseline A 的 ΔRMSE。')
    A_('')
    A_('| 变体 | 复杂度 | A_CV | ΔA_CV | ΔB | ΔC(post-hoc) | C p | C CI 不含0 |')
    A_('|---|---|---|---|---|---|---|---|')
    for name, r in d['Q2_dem_ablation'].items():
        A_('| %s | %d | %.4f | %+.4f | %+.4f | **%+.4f** | %.3f | %s |'
          % (name, r['complexity'], r['A_cv'], r['delta_A_cv'], r['delta_B'], r['delta_C'],
             r['C_perm_p'], '是' if r['C_ci_excludes_zero'] else '否'))
    A_('')
    A_('C 区常数地板（A 区 LST 均值）RMSE = %.4f ℃。' % d['Q2_constant_floor_C_rmse'])
    A_('')
    A_('## Q3 DEM 本身可不可信')
    A_('')
    A_('| 区 | n | min | max | mean | sd |')
    A_('|---|---|---|---|---|---|')
    for k in ('A', 'B', 'C'):
        s = d['Q3_dem'][k]
        A_('| %s | %d | %.2f | %.2f | %.2f | %.2f |'
          % (k, s['n'], s['min'], s['max'], s['mean'], s['sd']))
    A_('')
    A_('A 区 DEM 与各变量的相关系数：' +
      '；'.join('`%s`=%.3f' % (k, v) for k, v in d['Q3_dem']['corr_on_A'].items()) + '。')
    A_('')
    A_('DEM 对 `[row, col, row², col²]` 的 OLS **R² = %.3f**（A 区）。'
      'R² 越高，DEM 越像一个平滑空间场，其"地形"含义越可疑。'
      % d['Q3_dem']['dem_on_coords_r2_A'])
    A_('')
    A_('## Q4 空间代理检验')
    A_('')
    A_('| 模型 | ΔC(post-hoc) |')
    A_('|---|---|')
    A_('| full(冻结H10) | %+.4f |' % d['Q4_spatial_proxy']['full_delta_C'])
    A_('| no_dem | %+.4f |' % d['Q4_spatial_proxy']['no_dem_delta_C'])
    A_('| no_dem + 平滑坐标 | %+.4f |' % d['Q4_spatial_proxy']['coord_delta_C'])
    A_('')
    A_('平滑坐标在 no_dem 之上只多出 ΔC %+.4f（几乎为零）。%s'
      % (d['Q4_spatial_proxy']['coord_gain_over_no_dem'],
         d['Q4_spatial_proxy']['note']))
    A_('')
    A_('## Q5 判读（对写作的建议）')
    A_('')
    full = d['Q2_dem_ablation']['full(冻结H10)']
    nodem = d['Q2_dem_ablation']['no_dem']
    dropn = d['Q2_dem_ablation']['drop[1]exp(NDVI)']
    A_('1. **C 区结论不依赖 DEM。** 删掉任一含 DEM 项后，C 区增益不降反升'
      '（full %+.4f → no_dem %+.4f / drop_expDEM %+.4f），且置换 p 仍为 0.005。'
      '因此"DEM 值域不可信"**不足以**推翻 Stage 04 的验证结果。'
      % (full['delta_C'], nodem['delta_C'], d['Q2_dem_ablation']['drop_expDEM']['delta_C']))
    A_('2. **真正的支点是 `exp(NDVI)`。** 单独删去该项，A/B/C 三区增益同时崩塌'
      '（ΔC %+.4f，p=%.3f，CI 含 0）；DEM 项净贡献仅约 %.0f%% 的预测方差，'
      '且交互项为抑制项（占比为负）。'
      % (dropn['delta_C'], dropn['C_perm_p'], 100 * d['Q1_anatomy']['dem_terms_share']))
    A_('3. **DEM 项是 A 区过拟合。** 它们在 A 区有帮助（full ΔA %+.4f，'
      '删 DEM 后 %+.4f），但不迁移到 C。叠加 Q3（DEM 对坐标 R²=%.3f、与 row 相关 %.3f）'
      '可知：DEM 项既不可解释、在验证区也无贡献，**不应作为机制写进论文**。'
      % (full['delta_A_cv'], nodem['delta_A_cv'], d['Q3_dem']['dem_on_coords_r2_A'],
         d['Q3_dem']['corr_on_A']['row']))
    A_('4. **建议的主结果表述：** 报告一个**去 DEM 的简化式**'
      '（`no_dem`：`exp(NDVI)` + `SVF` + `Road_Dens`，复杂度 7，在 C 区 ΔC %+.4f、p=%.3f）'
      '作为可解释的结论；把冻结 H10 的 DEM 项降级为"选择期产物、不迁移"的如实说明。'
      % (nodem['delta_C'], nodem['C_perm_p']))
    A_('5. **范围。** 上述 C 区读数为 post-hoc；若要把它当**正式**结论，'
      '应作为 Stage 05 的**新预注册**用新数据/新分区确认，而非直接替换 Stage 04 的冻结结果。')
    A_('')
    A_('> 说明：C 区在本轮已解封，以上 C 区读数为**事后探索**，用于判断结论是否依赖 DEM；'
      '不构成新的确认性检验，也不能改变 Stage 04 的正式结论。')
    A_('')
    with open(os.path.join(_HERE, 'EXPR_REVIEW.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


if __name__ == '__main__':
    raise SystemExit(main())
