"""
bmlib.py — 零依赖 Baseline-B 机器学习库（纯 numpy）
====================================================
Stage 05 的 Baseline B 需要 RandomForest / GradientBoosting，但验证环境
无 sklearn / xgboost / scipy 且无网络。为可复现性，这里用 numpy 自行实现
CART 回归树、随机森林、平方损失梯度提升。功能等价于常见实现的核心，
而非逐行复刻某个库。

设计要点：
  * 树用扁平数组表示（feat/thr/left/right/val），预测时逐层向量化。
  * 分裂准则 = 平方误差（SSE）下降；importance = 各节点 SSE 下降之和。
  * 全部随机源来自 numpy 的 default_rng(seed)，保证确定性。
"""
import numpy as np

LEAF = -1


# ----------------------------------------------------------------- 回归树
def _build(X, y, idx, depth, max_depth, min_leaf, rng, mtry, feat, thr, left, right, val, imp):
    """递归建树；节点写入预分配的扁平数组。返回该子树的预测值节点号。"""
    node = len(feat)
    feat.append(LEAF); thr.append(0.0); left.append(-1); right.append(-1)
    val.append(float(y[idx].mean())); imp.append(0.0)
    n = len(idx)
    if depth >= max_depth or n < 2 * min_leaf:
        return node
    p = X.shape[1]
    nf = min(mtry, p)
    feats = rng.choice(p, size=nf, replace=False)
    best_sse = np.inf; best = None
    parent_sse = float(np.sum((y[idx] - y[idx].mean()) ** 2))
    for f in feats:
        xv = X[idx, f]
        order = np.argsort(xv, kind='mergesort')
        xs = xv[order]; ys = y[idx][order]
        csum = np.cumsum(ys); csq = np.cumsum(ys * ys)
        lo = min_leaf - 1; hi = n - min_leaf - 1
        if hi < lo:
            continue
        ln = np.arange(lo, hi + 1) + 1
        ls = csum[lo:hi + 1]; lq = csq[lo:hi + 1]
        rn = n - ln
        rs = csum[-1] - ls; rq = csq[-1] - lq
        sse = (lq - ls * ls / ln) + (rq - rs * rs / rn)
        valid = xs[lo:hi + 1] < xs[lo + 1:hi + 2]     # 阈值须真正切分
        sse = np.where(valid, sse, np.inf)
        j = int(np.argmin(sse))
        if sse[j] < best_sse:
            best_sse = float(sse[j])
            best = (f, 0.5 * (xs[lo + j] + xs[lo + j + 1]))
    if best is None or best_sse >= parent_sse:
        return node                                    # 无有效增益 → 叶
    f, t = best
    mask = X[idx, f] <= t
    li = idx[mask]; ri = idx[~mask]
    if len(li) == 0 or len(ri) == 0:
        return node
    feat[node] = f; thr[node] = float(t)
    ln_id = _build(X, y, li, depth + 1, max_depth, min_leaf, rng, mtry,
                   feat, thr, left, right, val, imp)
    rn_id = _build(X, y, ri, depth + 1, max_depth, min_leaf, rng, mtry,
                   feat, thr, left, right, val, imp)
    left[node] = ln_id; right[node] = rn_id
    imp[node] = parent_sse - best_sse
    return node


def _fit_tree(X, y, max_depth, min_leaf, mtry, rng, sample_idx=None):
    if sample_idx is None:
        idx = np.arange(len(y))
    else:
        idx = sample_idx
    feat, thr, left, right, val, imp = [], [], [], [], [], []
    _build(X, y, np.asarray(idx), 0, max_depth, min_leaf, rng, mtry,
           feat, thr, left, right, val, imp)
    return dict(feat=np.asarray(feat, np.int64), thr=np.asarray(thr, float),
                left=np.asarray(left, np.int64), right=np.asarray(right, np.int64),
                val=np.asarray(val, float), imp=np.asarray(imp, float), n=len(idx))


def _predict_tree(t, X):
    feat, thr, left, right, val = t['feat'], t['thr'], t['left'], t['right'], t['val']
    m = len(X)
    node = np.zeros(m, np.int64)
    row = np.arange(m)
    for _ in range(t['feat'].size):
        f = feat[node]
        internal = f >= 0
        if not internal.any():
            break
        go_left = X[row, f] <= thr[node]
        nxt = np.where(go_left, left[node], right[node])
        node = np.where(internal, nxt, node)
    return val[node]


# ----------------------------------------------------------------- 随机森林
def fit_rf(X, y, n_estimators=300, max_depth=12, min_leaf=10, mtry=None,
           seed=20260924, sample_frac=1.0, bootstrap=True):
    n, p = X.shape
    if mtry is None:
        mtry = max(1, int(round(p / 3)))
    rng = np.random.default_rng(seed)
    trees = []
    imp = np.zeros(p)
    for _ in range(n_estimators):
        if bootstrap:
            sub = rng.integers(0, n, size=n)
        else:
            sub = rng.choice(n, size=max(1, int(sample_frac * n)), replace=False)
        t = _fit_tree(X, y, max_depth, min_leaf, mtry, rng, sub)
        # importance 按叶子样本数加权（节点 imp 已含父节点规模）
        imp += np.bincount(t['feat'][t['feat'] >= 0], weights=t['imp'][t['feat'] >= 0],
                           minlength=p)
        trees.append(t)
    total = imp.sum()
    imp = imp / total if total > 0 else imp
    return dict(kind='rf', trees=trees, importance=imp, mtry=mtry,
                params=dict(n_estimators=n_estimators, max_depth=max_depth,
                            min_leaf=min_leaf, mtry=mtry, seed=seed))


def predict_rf(mdl, X):
    P = np.zeros(len(X))
    for t in mdl['trees']:
        P += _predict_tree(t, X)
    return P / len(mdl['trees'])


# ----------------------------------------------------------------- 梯度提升
def fit_gbm(X, y, n_estimators=300, learning_rate=0.05, max_depth=4,
            min_leaf=20, subsample=1.0, mtry=None, seed=20260924):
    n, p = X.shape
    if mtry is None:
        mtry = p
    rng = np.random.default_rng(seed)
    base = float(y.mean())
    P = np.full(n, base)
    trees = []
    imp = np.zeros(p)
    for _ in range(n_estimators):
        r = y - P
        if subsample < 1.0:
            sub = rng.choice(n, size=max(1, int(subsample * n)), replace=False)
        else:
            sub = None
        t = _fit_tree(X, r, max_depth, min_leaf, mtry, rng, sub)
        imp += np.bincount(t['feat'][t['feat'] >= 0], weights=t['imp'][t['feat'] >= 0],
                           minlength=p)
        P = P + learning_rate * _predict_tree(t, X)
        trees.append(t)
    total = imp.sum()
    imp = imp / total if total > 0 else imp
    return dict(kind='gbm', base=base, trees=trees, lr=learning_rate, importance=imp,
                params=dict(n_estimators=n_estimators, learning_rate=learning_rate,
                            max_depth=max_depth, min_leaf=min_leaf,
                            subsample=subsample, seed=seed))


def predict_gbm(mdl, X):
    P = np.full(len(X), mdl['base'])
    for t in mdl['trees']:
        P += mdl['lr'] * _predict_tree(t, X)
    return P


# ----------------------------------------------------------------- 通用
def fit(kind, X, y, **kw):
    return fit_rf(X, y, **kw) if kind == 'rf' else fit_gbm(X, y, **kw)


def predict(mdl, X):
    return predict_rf(mdl, X) if mdl['kind'] == 'rf' else predict_gbm(mdl, X)


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2)))


def partial_dependence(mdl, X, j, grid):
    """单变量 PDP：把第 j 列整体替换为 grid 值，取预测均值。"""
    out = []
    XX = X.copy()
    for g in grid:
        XX[:, j] = g
        out.append(float(predict(mdl, XX).mean()))
    return out
