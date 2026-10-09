"""
Stage 03 核心：符号表达式空间、空间分块 CV、诊断量
====================================================
本模块是发现侧的**工具层**（§3.2 允许的计算工具，须预注册）：
  - 表达式算子集 = 冻结 Baseline C 规格：+ - * / exp log（另有 neg/inv 两个等价一元形式）；
  - 最大复杂度 = 15（AST 节点数 + 项数）；
  - 搜索空间上限 10^4：本模块给出的候选族远小于该上限。
本模块**不包含任何方向性预设**：不规定 NDVI 必降温、SVF 必升温等；方向只在结果中如实报告。

只使用沙箱内可见的 A/B 数据（sandbox_root/inputs），不触碰 data/ 或 C 区。
"""
import os
import numpy as np
import pandas as pd

VARS = ['NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens']
Y = 'LST_mean'

# 数值条件门限（PA7）：输入均已标准化为 O(1)，故任何可解释的代数项在域内也应保持同一量级。
# 若某项在 A 区上的 max|取值| > 1000（即跨 3 个数量级），单一线性系数失去物理可解释性，
# 且折内重标准化会把它放大成极端外推（实证：exp(X_BD) 在留出折上使 CV RMSE 爆炸至 23）。
TERM_SCALE_LIMIT = 1000.0

# ------------------------------------------------------------------ AST 构造
def var(n):            return {'op': 'var', 'name': n}
def const(v):          return {'op': 'const', 'value': float(v)}
def add(a, b):         return {'op': 'add', 'args': [a, b]}
def sub(a, b):         return {'op': 'sub', 'args': [a, b]}
def mul(a, b):         return {'op': 'mul', 'args': [a, b]}
def div(a, b):         return {'op': 'div', 'args': [a, b]}
def neg(a):            return {'op': 'neg', 'arg': a}
def inv(a):            return {'op': 'inv', 'arg': a}
def log(a):            return {'op': 'log', 'arg': a}
def exp(a):            return {'op': 'exp', 'arg': a}
def sq(n):             return mul(var(n), var(n))


def _fmt(t):
    o = t['op']
    if o == 'var':   return t['name'].replace('_mean', '')
    if o == 'const': return '%.3g' % t['value']
    if o in ('add', 'sub', 'mul', 'div'):
        sym = {'add': '+', 'sub': '-', 'mul': '*', 'div': '/'}[o]
        return '(%s %s %s)' % (_fmt(t['args'][0]), sym, _fmt(t['args'][1]))
    if o == 'neg':   return '(-%s)' % _fmt(t['arg'])
    if o == 'inv':   return '(1/%s)' % _fmt(t['arg'])
    return '%s(%s)' % (o, _fmt(t['arg']))


def fmt_terms(terms):
    return ' + '.join(_fmt(t) for t in terms)


# ------------------------------------------------------------------ 空间分块
def kmeans(pts, k, seed, it=80, restarts=10):
    rng = np.random.default_rng(seed)
    best, best_in = None, np.inf
    for _ in range(restarts):
        c = pts[rng.choice(len(pts), k, replace=False)].astype(float)
        for _ in range(it):
            d = ((pts[:, None, :] - c[None, :, :]) ** 2).sum(-1)
            lab = d.argmin(1)
            nc = np.array([pts[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
            if np.allclose(nc, c):
                c = nc; break
            c = nc
        inertia = float(((pts - c[lab]) ** 2).sum())
        if inertia < best_in:
            best_in, best = inertia, lab
    return best, best_in


def spatial_folds(A, k=5, seed=20260924):
    """A 区空间分块 CV 折：对格中心 (row,col) 做 k-means → k 个连通簇（冻结规格：分块=连通簇，块数≥5）。"""
    pts = A[['row', 'col']].to_numpy(float)
    lab, _ = kmeans(pts, k, seed)
    return lab


def pooled_cv_rmse(A, terms, folds):
    import model as M
    truths, preds = [], []
    per = []
    for f in np.unique(folds):
        tr, te = folds != f, folds == f
        dtr = A[tr]
        vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
        mu = {v: float(dtr[v].mean()) for v in vs}
        sd = {v: float(dtr[v].std(ddof=0)) or 1.0 for v in vs}
        mdl = M.fit_expr(dtr, terms, mu=mu, sd=sd)
        p = M.predict(mdl, A[te])
        truths.append(A.loc[te, Y].to_numpy(float)); preds.append(p)
        per.append(M.rmse(A.loc[te, Y], p))
    t = np.concatenate(truths); p = np.concatenate(preds)
    try:                                        # 计入 fit 预算（每折一次拟合）
        import access_guard as G
        G.count_fit(int(len(np.unique(folds))))
    except Exception:
        pass
    return float(np.sqrt(np.mean((t - p) ** 2))), [float(x) for x in per]


# ------------------------------------------------------------------ 数值条件诊断（PA7）
def term_scale(A, terms):
    """逐项给出在 A 区上的 max|取值|（输入已标准化）；以及整体最大值。用于 PA7 数值条件审计。"""
    import model as M
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
    mu = {v: float(A[v].mean()) for v in vs}
    sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
    scale = {}
    for i, t in enumerate(terms):
        col = M.expr_design(A, [t], mu, sd)[:, 1]
        col = np.nan_to_num(col, nan=0.0, posinf=0.0, neginf=0.0)
        scale['term%d:%s' % (i, _fmt(t))] = float(np.max(np.abs(col))) if len(col) else 0.0
    return scale, (max(scale.values()) if scale else 0.0)


def _prescreen(A, pool, n):
    """按「项与 A 区 LST 的标准化相关系数绝对值」取前 n 项（仅用于降低搜索成本，不改判定）。"""
    import model as M
    yz = (A[Y] - A[Y].mean()) / (A[Y].std(ddof=0) or 1.0)
    scored = []
    for label, t in pool:
        vs = sorted(M.expr_vars(t))
        mu = {v: float(A[v].mean()) for v in vs}
        sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
        col = M.expr_design(A, [t], mu, sd)[:, 1]
        if not np.all(np.isfinite(col)) or np.std(col) == 0:
            continue
        scored.append((abs(float(np.corrcoef(col, yz)[0, 1])), label, t))
    scored.sort(reverse=True, key=lambda z: z[0])
    return [(l, t) for _, l, t in scored[:n]]


# ------------------------------------------------------------------ 局部修订搜索（第 3 轮）
def local_refine(A, folds, seed_terms, pool=None, prescreen=24, max_evals=80):
    """以 seed_terms 为起点做「加/换」爬山：每次尝试一个单步改动，接受使 CV RMSE 下降最多者。

    返回 (terms, trace)。每次尝试均调用 pooled_cv_rmse（计入 fit 预算）。
    """
    import model as M
    pool = pool or term_pool()
    cand = _prescreen(A, pool, prescreen)
    cur = list(seed_terms)
    best, _ = pooled_cv_rmse(A, cur, folds)
    budget = {'evals': 0}
    trace = []

    def try_trial(trial, desc):
        """尝试一个单步改动；复杂度越界或预算耗尽则返回 None（不计数、不求值）。"""
        if not trial or M.complexity(trial) > M.MAX_COMPLEXITY or budget['evals'] >= max_evals:
            return None
        r, _ = pooled_cv_rmse(A, trial, folds)
        budget['evals'] += 1
        return (r, trial, desc)

    def better(res, inc):
        return res is not None and res[0] < best - 1e-9 and (inc is None or res[0] < inc[0])

    improved = True
    while improved and budget['evals'] < max_evals:
        improved = False
        inc = None
        for label, t in cand:
            # (a) 加项（复杂度越界则自动跳过，但不影响下面的换项/删项）
            res = try_trial(cur + [t], dict(action='add', term=label))
            if better(res, inc):
                inc = res
            # (b) 换项（对每个已有项尝试替换——这是突破复杂度上限的主要手段）
            for i in range(len(cur)):
                res = try_trial(cur[:i] + [t] + cur[i + 1:],
                                dict(action='replace', at=i, term=label))
                if better(res, inc):
                    inc = res
        # (c) 删项（释放复杂度，为后续加项腾出空间）
        for i in range(len(cur)):
            res = try_trial(cur[:i] + cur[i + 1:], dict(action='drop', at=i))
            if better(res, inc):
                inc = res
        if inc is not None:
            best, cur = inc[0], inc[1]
            desc = inc[2]
            desc['cv_rmse'] = best; desc['n_terms'] = len(cur); desc['expr'] = fmt_terms(cur)
            trace.append(desc)
            improved = True
        else:
            trace.append(dict(action='no_improve', cv_rmse=best, n_evals=budget['evals']))
    return cur, trace


# ------------------------------------------------------------------ 诊断量
def block_bootstrap_ci(A, model, n_boot=1000, block=5, seed=20260924):
    """空间块自助 95% CI（块=block×block 格）：重采样块，对**固定模型**重算 RMSE。"""
    import model as M
    rng = np.random.default_rng(seed)
    y = A[Y].to_numpy(float)
    p = M.predict(model, A)
    key = (A['row'].to_numpy() // block) * 100000 + (A['col'].to_numpy() // block)
    order = np.argsort(key, kind='stable')
    ks = key[order]
    bounds = np.searchsorted(ks, np.unique(ks), side='left')
    bounds = np.append(bounds, len(ks))
    groups = [order[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    ng = len(groups)
    out = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, ng, ng)
        idx = np.concatenate([groups[j] for j in pick])
        out[i] = np.sqrt(np.mean((y[idx] - p[idx]) ** 2))
    return [float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))]


def moran_I(A, values):
    """A 区残差的 queen 邻接 Moran's I（如实报告空间自相关，Table 13 开发指标必报项）。"""
    idx = {(int(r), int(c)): i for i, (r, c) in
           enumerate(zip(A['row'].to_numpy(), A['col'].to_numpy()))}
    x = np.asarray(values, float)
    xm = x - x.mean()
    num = 0.0; wsum = 0
    for (r, c), i in idx.items():
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                j = idx.get((r + dr, c + dc))
                if j is not None:
                    num += xm[i] * xm[j]; wsum += 1
    den = float((xm ** 2).sum())
    n = len(x)
    return float((n / wsum) * (num / den)) if wsum and den else float('nan')


# ------------------------------------------------------------------ 候选族（发现侧的假设议程）
def term_pool():
    """预注册的项池（供贪心选择）：单项、平方、两两乘积、比值、log 平方、exp、倒数。

    规模 ≈ 98 项，远小于冻结的搜索空间上限 10^4。
    """
    pool = []
    for v in VARS:
        pool.append((v, var(v)))
        pool.append((v + '^2', sq(v)))
        pool.append(('log(%s^2)' % v, log(sq(v))))
        pool.append(('exp(%s)' % v, exp(var(v))))
        pool.append(('1/%s' % v, inv(var(v))))
    for i, a in enumerate(VARS):
        for b in VARS[i + 1:]:
            pool.append(('%s*%s' % (a, b), mul(var(a), var(b))))
            pool.append(('%s/%s' % (a, b), div(var(a), var(b))))
            pool.append(('%s/%s' % (b, a), div(var(b), var(a))))
    return pool


def greedy_terms(A, folds, K, pool=None, prescreen=24):
    """贪心前向选择（符号回归的搜索部分）：从项池按 A 区空间分块 CV 逐步加项，直到 K 项。

    预筛：先按「项与 A 区 LST 的相关绝对值」取前 prescreen 项，降低搜索成本。
    返回 (terms_list, trace)，trace 记录每一步加入的项与 CV RMSE（供完整实验轨迹）。
    """
    import model as M
    pool = pool or term_pool()
    yz = (A[Y] - A[Y].mean()) / (A[Y].std(ddof=0) or 1.0)
    scored = []
    for label, t in pool:
        vs = sorted(M.expr_vars(t))
        mu = {v: float(A[v].mean()) for v in vs}
        sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
        col = M.expr_design(A, [t], mu, sd)[:, 1]
        if not np.all(np.isfinite(col)) or np.std(col) == 0:
            continue
        scored.append((abs(float(np.corrcoef(col, yz)[0, 1])), label, t))
    scored.sort(reverse=True, key=lambda z: z[0])
    cand = [(l, t) for _, l, t in scored[:prescreen]]

    chosen, trace, best = [], [], None
    while len(chosen) < K:
        step = None
        counts = 0
        for label, t in cand:
            trials = [tt for _, tt in chosen] + [t]
            if M.complexity(trials) > M.MAX_COMPLEXITY:
                continue
            r, _ = pooled_cv_rmse(A, trials, folds)
            counts += 1
            # 预算计数由调用方通过 log_tool/count_fit 处理；此处返回尝试次数
            if step is None or r < step[0]:
                step = (r, label, t)
        if step is None:
            break
        if best is not None and step[0] >= best - 1e-6:
            trace.append(dict(action='stop_no_improve', cv_rmse=step[0], n_terms=len(chosen)))
            break
        best = step[0]
        chosen.append((step[1], step[2]))
        trace.append(dict(action='add', term=step[1], term_ast=step[2],
                          cv_rmse=step[0], n_terms=len(chosen)))
    return [t for _, t in chosen], trace


def hypotheses():
    """首轮假设议程（复杂度升序）。每项给出候选的项集合与其"科学主张"（中性、无方向预设）。"""
    H = []

    def h(hid, name, terms, claim):
        H.append(dict(hid=hid, name=name, terms=terms, claim=claim))

    h('H01-LIN7', '全部 7 个预指定变量的一次项（参照）',
      [var(v) for v in VARS],
      'LST 可由 7 个预指定形态变量的线性组合描述（作为后续候选的参照模型）。')

    # 唯一 ID 标签（避免 X_BD / X_VolDens 都被简写为 X 而撞 ID）
    _TAG = {'NDVI_mean': 'NDVI', 'X_BD': 'XBD', 'X_VolDens': 'XVOL', 'SVF_mean': 'SVF'}
    for v in ('NDVI_mean', 'X_BD', 'X_VolDens', 'SVF_mean'):
        h('H02-QUAD-%s' % _TAG[v], '%s 的二次响应' % v,
          [var(v), sq(v)],
          'LST 与 %s 之间为可测的二次（非线性）关系。' % v)

    h('H03-BUILD3', '建筑覆盖 / 高度 / 体量三项',
      [var('X_BD'), var('X_BH'), var('X_VolDens')],
      'LST 与建筑覆盖、平均高度、体量密度三项联合相关。')

    h('H04-VEG-BUILD', '植被—建筑交互',
      [var('NDVI_mean'), var('X_BD'), mul(var('NDVI_mean'), var('X_BD'))],
      'NDVI 与建筑覆盖的联合项对 LST 的解释优于各自单独的线性项。')

    h('H05-SVF-BUILD', '天空可视度—建筑交互',
      [var('SVF_mean'), var('X_BD'), mul(var('SVF_mean'), var('X_BD'))],
      'SVF 与建筑覆盖的联合项对 LST 的解释优于各自单独的线性项。')

    h('H06-ROAD-VEG', '道路密度—植被交互',
      [var('Road_Dens'), var('NDVI_mean'), mul(var('Road_Dens'), var('NDVI_mean'))],
      '道路密度与 NDVI 的联合项对 LST 的解释优于各自单独的线性项。')

    h('H07-VEGBLD-RATIO', '植被/建筑 比值项',
      [div(var('NDVI_mean'), var('X_BD')), var('X_BD')],
      '植被与建筑覆盖之比构成的组合项与 LST 相关。')

    h('H08-VOLDENS-LOG', '体量密度的对数（log 平方）',
      [log(sq('X_VolDens'))],
      'LST 与体量密度的对数尺度的单调相关。')

    h('H09-EXP-BUILD', '建筑覆盖的指数项（受物理审计检验）',
      [exp(var('X_BD')), var('SVF_mean')],
      'LST 对建筑覆盖呈指数式响应。')

    return H
