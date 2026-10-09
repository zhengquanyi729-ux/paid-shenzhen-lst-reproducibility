"""
S05.1 Baseline B — 与冻结协议下的基线 A / 候选公平比较（RF 与梯度提升）
========================================================================
框架 Experiment 4 要求把"提出的方法"与 Baseline A（预指定线性模型）和
Baseline B（RF / XGBoost）在**统一数据、统一折划分、统一指标**下比较。

本环境无 sklearn / xgboost 且无网络，故 Baseline B 用 numpy 自实现
（见 bmlib.py：CART 回归树 + 随机森林 + 平方损失梯度提升）。这同时保证了
复现不依赖第三方 ML 库。

公平性口径（与 Stage 01 冻结一致）：
  * 训练集 = A 区；开发指标 = A 区**同一冻结空间分块 CV**（connected k-means,
    k=5, seed=20260924）；B 区作开发验证；C 区作锁定检验（**已解封，读数为
    事后比较，非新增确认性检验**）。
  * Baseline B 使用与 Baseline A **相同的 7 个原始协变量**（主口径）；
    另给一个"增广"口径：7 原始 + 候选 H10 用到的工程特征，作为上界对照。
  * 树模型对单调变量缩放不变，故未对输入标准化（与冻结 dev 指标等价）。

子命令（分开跑以避开单次 45s 上限，逐段写 cache/）：
  cv <k>   : 第 k 折 A 区 CV（RF+GBM）
  fit      : 全 A 拟合 RF/GBM(原始)，预测 A/B/C，存 importance
  fit_aug  : 全 A 拟合 RF(增广)，预测 A/B/C
  pdp      : 重拟合 RF(原始)，算 NDVI/DEM/SVF 的 1D PDP
  perm     : 加载预测，算 B/C 区置换 p 与自助 CI
  report   : 汇总 → reports/baselineB.json + reports/BASELINE_B.md

用法：python3 stage05_paper/scripts/s05_01_baselineB.py <子命令> [k]
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
S02 = os.path.join(PROJ, 'stage02_platform')
S03 = os.path.join(PROJ, 'stage03_discovery')
for _p in (os.path.join(S02, 'agents'), os.path.join(S02, 'lib'),
           os.path.join(S02, 'sandbox'), os.path.join(S03, 'lib'),
           os.path.join(S03, 'agents'), _HERE):
    sys.path.insert(0, _p)

import paths02 as P
import paths03 as P3
import model as M
import core as CORE
import bmlib as B
from independent_validator import decrypt_vault

Y = M.Y
COLS = list(M.BASELINE_A_TERMS)
SEED0 = 20260924
N_PERM = 199
N_BOOT = 1000
RF = dict(n_estimators=300, max_depth=12, min_leaf=10, seed=SEED0)
GBM = dict(n_estimators=300, learning_rate=0.05, max_depth=4, min_leaf=20, seed=SEED0)
CACHE = os.path.join(S05, 'cache')
REPORTS = os.path.join(S05, 'reports')


# ---------------------------------------------------------------- 载入
def load():
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    Bm = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    m = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))[['Grid_ID', 'row', 'col']]
    A = A.merge(m, on='Grid_ID', how='left')
    Bm = Bm.merge(m, on='Grid_ID', how='left')
    C, sha = decrypt_vault()
    sp = pd.read_csv(os.path.join(P.S01, 'split', 'analysis_split.csv'))[['Grid_ID', 'row', 'col']]
    C = C.merge(sp, on='Grid_ID', how='left')
    return A, Bm, C, sha


def origX(df):
    return df[COLS].to_numpy(float)


def augX(df):
    nv = df['NDVI_mean'].to_numpy(float)
    dv = df['DEM_mean'].to_numpy(float)
    return np.column_stack([origX(df), np.exp(nv), np.exp(dv), nv * dv])


AUG_NAMES = COLS + ['exp(NDVI_mean)', 'exp(DEM_mean)', 'NDVI_mean*DEM_mean']


def h10_terms():
    cand = json.load(open(os.path.join(P3.S03_CAND, 'S03-H10-GREEDY.json'), encoding='utf-8'))
    T = cand['expression']['terms']
    nodem = [t for t in T if 'DEM_mean' not in M.expr_vars(t)]
    return T, nodem


# ---------------------------------------------------------------- CV
def cmd_cv(k):
    A, Bm, C, sha = load()
    folds = CORE.spatial_folds(A, 5, SEED0)
    tr = folds != k; te = folds == k
    Xtr, ytr = origX(A[tr]), A.loc[tr, Y].to_numpy(float)
    Xte, yte = origX(A[te]), A.loc[te, Y].to_numpy(float)
    rf = B.fit('rf', Xtr, ytr, **RF)
    gb = B.fit('gbm', Xtr, ytr, **GBM)
    np.savez(os.path.join(CACHE, 'cv_fold%d.npz' % k),
             y=yte, rf=B.predict(rf, Xte), gbm=B.predict(gb, Xte))
    print('[cv fold %d] n_te=%d rf=%.4f gbm=%.4f' %
          (k, len(yte), B.rmse(yte, B.predict(rf, Xte)), B.rmse(yte, B.predict(gb, Xte))))
    return 0


# ---------------------------------------------------------------- 全量拟合
def cmd_fit():
    A, Bm, C, sha = load()
    Xa, ya = origX(A), A[Y].to_numpy(float)
    rf = B.fit('rf', Xa, ya, **RF)
    gb = B.fit('gbm', Xa, ya, **GBM)
    out = {}
    for nm, df in (('A', A), ('B', Bm), ('C', C)):
        out['y' + nm] = df[Y].to_numpy(float)
        out['rf' + nm] = B.predict(rf, origX(df))
        out['gbm' + nm] = B.predict(gb, origX(df))
    np.savez(os.path.join(CACHE, 'preds.npz'), **out)
    json.dump(dict(importance_rf=dict(zip(COLS, rf['importance'].tolist())),
                   importance_gbm=dict(zip(COLS, gb['importance'].tolist())),
                   params=dict(rf=RF, gbm=GBM)),
              open(os.path.join(CACHE, 'importance.json'), 'w'), indent=2)
    print('[fit] A/B/C preds saved; rf train RMSE %.4f gbm %.4f'
          % (B.rmse(ya, B.predict(rf, Xa)), B.rmse(ya, B.predict(gb, Xa))))
    print('[fit] rf imp', dict(zip(COLS, np.round(rf['importance'], 3))))
    return 0


def cmd_fit_aug():
    A, Bm, C, sha = load()
    rf = B.fit('rf', augX(A), A[Y].to_numpy(float), **RF)
    out = {}
    for nm, df in (('A', A), ('B', Bm), ('C', C)):
        out['rf_aug' + nm] = B.predict(rf, augX(df))
    np.savez(os.path.join(CACHE, 'preds_aug.npz'), **out)
    json.dump(dict(importance_rf_aug=dict(zip(AUG_NAMES, rf['importance'].tolist())),
                   augmented_features=AUG_NAMES),
              open(os.path.join(CACHE, 'importance_aug.json'), 'w'), indent=2)
    print('[fit_aug] saved; imp', dict(zip(AUG_NAMES, np.round(rf['importance'], 3))))
    return 0


# ---------------------------------------------------------------- PDP
def cmd_pdp(nm='NDVI_mean'):
    A, Bm, C, sha = load()
    rf = B.fit('rf', origX(A), A[Y].to_numpy(float), **RF)
    Xa = origX(A)
    j = COLS.index(nm)
    g = np.quantile(A[nm].to_numpy(float), np.linspace(0.02, 0.98, 21)).tolist()
    fn = os.path.join(CACHE, 'pdp.json')
    pdp = json.load(open(fn)) if os.path.exists(fn) else {}
    pdp[nm] = dict(grid=[float(x) for x in g],
                   rf=[float(x) for x in B.partial_dependence(rf, Xa, j, g)])
    json.dump(pdp, open(fn, 'w'), indent=2)
    print('[pdp] saved for', nm)
    return 0


# ---------------------------------------------------------------- 推断
def block_perm(y, pb, pc, rows, cols, n_perm=N_PERM, seed=SEED0, bs=5):
    blk = pd.Series(list(zip(rows // bs, cols // bs)))
    bmean = pd.Series(y).groupby(blk).transform('mean').to_numpy(float)
    resid = y - bmean
    ymean = pd.Series(bmean).groupby(blk).first()
    d = B.rmse(y, pb) - B.rmse(y, pc)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yp = blk.map(sh).to_numpy(float) + resid
        null[i] = B.rmse(yp, pb) - B.rmse(yp, pc)
    p = float((1 + np.sum(null >= d)) / (1 + n_perm))
    sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yp = blk.map(sh).to_numpy(float) + resid
    corr = float(np.corrcoef(y, yp)[0, 1])
    return p, float(d), corr


def block_boot(y, pb, pc, rows, cols, n_boot=N_BOOT, seed=SEED0, bs=5):
    blk = pd.Series(list(zip(rows // bs, cols // bs)))
    groups = {b: g.index.to_numpy() for b, g in pd.Series(y).groupby(blk)}
    blocks = list(groups); rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        boot[i] = B.rmse(y[sel], pb[sel]) - B.rmse(y[sel], pc[sel])
    return [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]


def cmd_perm():
    A, Bm, C, sha = load()
    pr = np.load(os.path.join(CACHE, 'preds.npz'))
    pa = np.load(os.path.join(CACHE, 'preds_aug.npz'))
    inf = json.load(open(os.path.join(CACHE, 'importance.json')))
    # Baseline A 与候选（在 A 上重新拟合后预测）
    mdl_b = M.fit_linear(A, M.BASELINE_A_TERMS)
    T, nodem = h10_terms()
    mdl_h10 = M.fit_expr(A, T)
    mdl_nd = M.fit_expr(A, nodem)
    res = {k: {} for k in ('A', 'B', 'C')}
    for nm, df in (('A', A), ('B', Bm), ('C', C)):
        y = df[Y].to_numpy(float)
        pb = M.predict(mdl_b, df)
        models = dict(baselineA=pb,
                      rf=pr['rf' + nm], gbm=pr['gbm' + nm], rf_aug=pa['rf_aug' + nm],
                      h10=M.predict(mdl_h10, df), no_dem=M.predict(mdl_nd, df),
                      constant=np.full(len(df), A[Y].mean()))
        rows = df['row'].to_numpy(); cols = df['col'].to_numpy()
        for mk, pc in models.items():
            d = float(B.rmse(y, pb) - B.rmse(y, pc))
            r = dict(rmse=B.rmse(y, pc), delta_vs_baselineA=d)
            if nm in ('B', 'C') and mk != 'baselineA':
                p, dd, corr = block_perm(y, pb, pc, rows, cols)
                r['perm_p'] = p; r['ci95'] = block_boot(y, pb, pc, rows, cols)
                r['ci_excludes_zero'] = bool(r['ci95'][0] > 0 or r['ci95'][1] < 0)
                r['perm_corr_sanity'] = corr
            res[nm][mk] = r
    json.dump(res, open(os.path.join(CACHE, 'infer.json'), 'w'), indent=2)
    print('[perm] C ΔRMSE:', {k: round(v['delta_vs_baselineA'], 4) for k, v in res['C'].items()})
    return 0


# ---------------------------------------------------------------- 负对照
def cmd_control():
    """打乱 A 区目标行序后训练 RF/GBM（破坏 A 内信号），预测 B/C。
    若其 RMSE 只与常数地板相当、远差于真基线 B，则 Baseline B 的优势是真实信号。"""
    A, Bm, C, sha = load()
    rng = np.random.default_rng(SEED0)
    ysh = rng.permutation(A[Y].to_numpy(float))
    Xa = origX(A)
    res = {}
    for kind, kw in (('rf', RF), ('gbm', GBM)):
        mdl = B.fit(kind, Xa, ysh, **kw)
        rec = {}
        for nm, df in (('A', A), ('B', Bm), ('C', C)):
            rec[nm] = B.rmse(df[Y].to_numpy(float), B.predict(mdl, origX(df)))
        res[kind] = rec
    json.dump(res, open(os.path.join(CACHE, 'control.json'), 'w'), indent=2)
    print('[control] shuffled-target RF/GBM:', json.dumps(res, indent=0))
    return 0


# ---------------------------------------------------------------- 汇总
def cmd_report():
    A, Bm, C, sha = load()
    folds = CORE.spatial_folds(A, 5, SEED0)
    base_cv, _ = CORE.pooled_cv_rmse(A, [CORE.var(v) for v in M.BASELINE_A_TERMS], folds)
    T, nodem = h10_terms()
    h10_cv, _ = CORE.pooled_cv_rmse(A, T, folds)
    nd_cv, _ = CORE.pooled_cv_rmse(A, nodem, folds)
    # RF/GBM 的 A 区 CV（合并各折）
    ys, prf, pgb = [], [], []
    for k in range(5):
        z = np.load(os.path.join(CACHE, 'cv_fold%d.npz' % k))
        ys.append(z['y']); prf.append(z['rf']); pgb.append(z['gbm'])
    y = np.concatenate(ys)
    rf_cv = B.rmse(y, np.concatenate(prf)); gb_cv = B.rmse(y, np.concatenate(pgb))

    inf = json.load(open(os.path.join(CACHE, 'infer.json')))
    imp = json.load(open(os.path.join(CACHE, 'importance.json')))
    impa = json.load(open(os.path.join(CACHE, 'importance_aug.json')))
    pdp = json.load(open(os.path.join(CACHE, 'pdp.json')))
    ctl = json.load(open(os.path.join(CACHE, 'control.json')))

    dat = dict(version='stage05-baselineB-v1',
               created=datetime.datetime.now().isoformat(timespec='seconds'),
               vault_plaintext_sha256=sha,
               setup=dict(n_A=int(len(A)), n_B=int(len(Bm)), n_C=int(len(C)),
                          covariates=COLS, augmented=AUG_NAMES,
                          fold_spec='connected k-means k=5 seed=20260924',
                          rf=RF, gbm=GBM, n_perm=N_PERM, n_boot=N_BOOT,
                          note='Baseline B = numpy 自实现 CART 森林 / 平方损失提升树（无 sklearn/xgboost）。'
                               'C 区已解封，C 读数为事后公平比较。'),
               A_cv=dict(baselineA=float(base_cv), rf=rf_cv, gbm=gb_cv,
                         h10=float(h10_cv), no_dem=float(nd_cv)),
               regions=inf,
               importance=imp, importance_aug=impa, pdp=pdp,
               negative_control_shuffled_target=ctl)
    os.makedirs(REPORTS, exist_ok=True)
    json.dump(dat, open(os.path.join(REPORTS, 'baselineB.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)
    _write_md(dat)
    print('[report] wrote baselineB.json / BASELINE_B.md')
    print('A-CV:', {k: round(v, 4) for k, v in dat['A_cv'].items()})
    return 0


def _write_md(d):
    L = []; A_ = L.append
    A_('# Baseline B 公平比较（RF / 梯度提升）')
    A_('')
    A_('| 项 | 值 |')
    A_('|---|---|')
    A_('| 版本 | %s |' % d['version'])
    A_('| 生成 | %s |' % d['created'])
    A_('| 数据 | A %d / B %d / C %d（C 已解封，C 区读数为事后比较） |'
      % (d['setup']['n_A'], d['setup']['n_B'], d['setup']['n_C']))
    A_('| Baseline B | numpy 自实现 CART 随机森林 + 平方损失梯度提升（无 sklearn/xgboost） |')
    A_('')
    A_('## A 区开发指标（同一冻结空间分块 CV，RMSE ℃ 越低越好）')
    A_('')
    A_('| 模型 | A-CV RMSE |')
    A_('|---|---|')
    for k in ('baselineA', 'rf', 'gbm', 'h10', 'no_dem'):
        A_('| %s | %.4f |' % (k, d['A_cv'][k]))
    A_('')
    for reg, lab in (('B', 'B 区（开发验证）'), ('C', 'C 区（锁定，事后）')):
        A_('## %s' % lab)
        A_('')
        A_('| 模型 | RMSE | ΔRMSE vs Baseline A | 置换 p | 95% CI | CI 不含0 |')
        A_('|---|---|---|---|---|---|')
        for k, r in d['regions'][reg].items():
            A_('| %s | %.4f | %+.4f | %s | %s | %s |'
              % (k, r['rmse'], r['delta_vs_baselineA'],
                 ('%.3f' % r['perm_p']) if 'perm_p' in r else '—',
                 ('[%.4f, %.4f]' % tuple(r['ci95'])) if 'ci95' in r else '—',
                 ('是' if r.get('ci_excludes_zero') else '否') if 'ci95' in r else '—'))
        A_('')
    A_('## 特征重要度（RF，原始 7 变量）')
    A_('')
    A_('| 变量 | 重要度 |')
    A_('|---|---|')
    for k, v in d['importance']['importance_rf'].items():
        A_('| %s | %.3f |' % (k, v))
    A_('')
    A_('## 特征重要度（RF，增广=原始+候选工程特征）')
    A_('')
    A_('| 变量 | 重要度 |')
    A_('|---|---|')
    for k, v in d['importance_aug']['importance_rf_aug'].items():
        A_('| %s | %.3f |' % (k, v))
    A_('')
    A_('## 负对照：打乱 A 区目标后训练（破坏信号）')
    A_('')
    A_('| 模型 | A | B | C |')
    A_('|---|---|---|---|')
    for k, v in d['negative_control_shuffled_target'].items():
        A_('| %s | %.4f | %.4f | %.4f |' % (k, v['A'], v['B'], v['C']))
    A_('')
    rc = d['regions']['C']['rf']['rmse']; cc = d['negative_control_shuffled_target']['rf']['C']
    A_('打乱目标后 RF 在 C 的 RMSE 为 %.4f（≈ 常数地板），而真 RF 为 %.4f；'
      '差异说明真 RF 的优势来自真实信号，而非目标泄漏或位置伪影。' % (cc, rc))
    A_('')
    A_('> C 区已解封：以上 C 区读数为事后公平比较，不构成新的确认性检验。')
    A_('')
    with open(os.path.join(REPORTS, 'BASELINE_B.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


CMD = dict(cv=cmd_cv, fit=cmd_fit, fit_aug=cmd_fit_aug, pdp=cmd_pdp,
           perm=cmd_perm, report=cmd_report, control=cmd_control)

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in CMD:
        print('usage: s05_01_baselineB.py {%s} [k]' % '|'.join(CMD)); raise SystemExit(2)
    if sys.argv[1] == 'cv':
        raise SystemExit(CMD['cv'](int(sys.argv[2])))
    if sys.argv[1] == 'pdp':
        raise SystemExit(CMD['pdp'](sys.argv[2] if len(sys.argv) > 2 else 'NDVI_mean'))
    raise SystemExit(CMD[sys.argv[1]]())
