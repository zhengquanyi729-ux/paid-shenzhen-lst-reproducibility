"""
release_model.py — pure evaluation math, copied from the frozen implementation
==============================================================================
This module is the *only* place the review layer needs evaluation arithmetic. Every
function below is a faithful copy of a function in the frozen Stage 00–05 tree:

  * `fit_linear`, `fit_expr`, `predict`, `expr_design`, `_design`, `_zmap`,
    `_eval_term`, `expr_vars`, `rmse`, `complexity`, `expr_complexity`
        — copied from `PAID/stage02_platform/agents/model.py`
  * `canon_hash`               — copied from `PAID/stage02_platform/agents/independent_validator.py`
  * `delta_rmse`, `block_perm_p`, `block_bootstrap_ci`
        — transcribed from `Independent Validator.validate()` (same estimator, same
          seed, same block size, same N_PERM / N_BOOT), so the reviewer recomputes the
          published statistics without the AES key and without importing `paths02`.

**No scientific formula was changed.** Numerical guards (`exp` clip to [-30, 30]; `log`
floor 1e-6; division by |d|<1e-6) are reproduced verbatim from the platform model. The
constants N_PERM=199, N_BOOT=1000, block size 5, seed 20260924, and the estimator
p = (1 + #{null ≥ obs}) / (1 + N_PERM) are the frozen protocol values.

The frozen Baseline-A specification is the 7 pre-specified morphological covariates used
by the platform (`model.BASELINE_A_TERMS`), fitted by OLS on Region A only.
"""
import hashlib
import io
import json

import numpy as np
import pandas as pd

COVARIATES = ['NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens',
              'X_BD', 'X_BH', 'X_VolDens']
BASELINE_A_TERMS = list(COVARIATES)
Y = 'LST_mean'
MAX_COMPLEXITY = 15
_EPS = 1e-6

# frozen protocol constants (validation_protocol.json / independent_validator.py)
N_PERM = 199
N_BOOT = 1000
BLOCK = 5
SEED = 20260924


# ------------------------------------------------------------------ core algebra
def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.asarray(y_true, float) - np.asarray(y_pred, float)) ** 2)))


def _design(df, terms, mu, sd):
    X = np.column_stack([(df[t].to_numpy(float) - mu[t]) / sd[t] for t in terms])
    return np.column_stack([np.ones(len(df)), X])


def _zmap(df, mu, sd):
    return {v: ((df[v].to_numpy(float) - mu[v]) / sd[v]) for v in mu}


def _eval_term(term, Z):
    op = term['op']
    if op == 'var':
        return Z[term['name']]
    if op == 'const':
        return np.full_like(next(iter(Z.values())), float(term['value']))
    if op == 'add':
        return _eval_term(term['args'][0], Z) + _eval_term(term['args'][1], Z)
    if op == 'sub':
        return _eval_term(term['args'][0], Z) - _eval_term(term['args'][1], Z)
    if op == 'mul':
        return _eval_term(term['args'][0], Z) * _eval_term(term['args'][1], Z)
    if op == 'div':
        a = _eval_term(term['args'][0], Z); b = _eval_term(term['args'][1], Z)
        b = np.where(np.abs(b) < _EPS, np.where(b < 0, -_EPS, _EPS), b)
        return a / b
    if op == 'neg':
        return -_eval_term(term['arg'], Z)
    if op == 'inv':
        a = _eval_term(term['arg'], Z)
        a = np.where(np.abs(a) < _EPS, np.where(a < 0, -_EPS, _EPS), a)
        return 1.0 / a
    if op == 'exp':
        return np.exp(np.clip(_eval_term(term['arg'], Z), -30.0, 30.0))
    if op == 'log':
        return np.log(np.maximum(_eval_term(term['arg'], Z), _EPS))
    raise ValueError('illegal operator: %r' % op)


def expr_vars(term):
    if term.get('op') == 'var':
        return {term['name']}
    if term.get('op') == 'const':
        return set()
    if term.get('op') in ('add', 'sub', 'mul', 'div'):
        return expr_vars(term['args'][0]) | expr_vars(term['args'][1])
    return expr_vars(term['arg'])


def expr_design(df, terms, mu, sd):
    Z = _zmap(df, mu, sd)
    return np.column_stack([np.ones(len(df))] + [_eval_term(t, Z) for t in terms])


def fit_linear(df, terms, mu=None, sd=None):
    mu = mu or {t: float(df[t].mean()) for t in terms}
    sd = sd or {t: float(df[t].std(ddof=0)) or 1.0 for t in terms}
    X = _design(df, terms, mu, sd)
    beta = np.linalg.lstsq(X, df[Y].to_numpy(float), rcond=None)[0]
    return dict(form='linear', terms=list(terms), mu=mu, sd=sd,
                beta=beta.tolist(), intercept=True, n_fit=int(len(df)))


def fit_expr(df, terms, mu=None, sd=None, var_names=None):
    var_names = var_names or sorted(set().union(*[expr_vars(t) for t in terms]))
    mu = mu or {v: float(df[v].mean()) for v in var_names}
    sd = sd or {v: float(df[v].std(ddof=0)) or 1.0 for v in var_names}
    X = expr_design(df, terms, mu, sd)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    beta = np.linalg.lstsq(X, df[Y].to_numpy(float), rcond=None)[0]
    return dict(form='expr', terms=terms, standardize=True, intercept=True,
                mu=mu, sd=sd, beta=beta.tolist(), n_fit=int(len(df)))


def predict(model, df):
    if model['form'] == 'linear':
        X = _design(df, model['terms'], model['mu'], model['sd'])
        return X @ np.array(model['beta'], float)
    if model['form'] == 'expr':
        X = expr_design(df, model['terms'], model['mu'], model['sd'])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return X @ np.array(model['beta'], float)
    raise ValueError('unknown model form: %r' % model['form'])


def canon_hash(cand):
    core = {k: cand.get(k) for k in ('id', 'claim', 'expression', 'model')}
    return hashlib.sha256(json.dumps(core, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def delta_rmse(df, mdl_c, mdl_b):
    rc = rmse(df[Y], predict(mdl_c, df))
    rb = rmse(df[Y], predict(mdl_b, df))
    return rb - rc, rb, rc


# ------------------------------------------------------------------ estimators
def block_perm_p(df, mdl_c, mdl_b, d_obs, n_perm=N_PERM, seed=SEED, bs=BLOCK):
    """Spatial block permutation p-value.

    Transcribed from `Independent Validator.validate()`: permute the *values* of block
    means, add back within-block residuals, recompute the RMSE difference; the frozen
    estimator is p = (1 + #{null >= obs}) / (1 + N_PERM). Varying this seed or RNG call
    order changes individual null draws, so the p reported here is the frozen one only
    when the seed and call order match the validator (they do). See KNOWN_LIMITATIONS.
    """
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    bmean = df[Y].groupby(blk).transform('mean')
    resid = df[Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc_b = predict(mdl_b, df); pc_c = predict(mdl_c, df)
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yperm = blk.map(sh).to_numpy(float) + resid
        rc_n = np.sqrt(np.mean((yperm - pc_c) ** 2))
        rb_n = np.sqrt(np.mean((yperm - pc_b) ** 2))
        null[i] = rb_n - rc_n
    p = float((1 + np.sum(null >= d_obs)) / (1 + n_perm))
    # permutation-validity sanity (the historical guard; corr < 0.9 required)
    sh_chk = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yperm_chk = blk.map(sh_chk).to_numpy(float) + resid
    perm_corr = float(np.corrcoef(df[Y].to_numpy(float), yperm_chk)[0, 1])
    return p, perm_corr


def block_bootstrap_ci(df, mdl_c, mdl_b, n_boot=N_BOOT, seed=SEED, bs=BLOCK):
    """Spatial block bootstrap 95% CI of ΔRMSE, transcribed from the validator.

    NOTE: this standalone form starts a *fresh* RNG stream. The frozen Stage-04 published
    CI comes from `validate()`, which shares ONE stream across the 199 permutation draws,
    the sanity draw and the 1000 bootstrap draws, so its bootstrap is advanced past those
    draws. To reproduce the published CI exactly use `primary_endpoint()`; this function is
    kept for the R=25 sensitivity path (which only reports Δ and p).
    """
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    groups = {b: g.index.to_numpy() for b, g in df.groupby(blk)}
    blocks = list(groups)
    boot = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        d, _, _ = delta_rmse(df.iloc[sel], mdl_c, mdl_b)
        boot[i] = d
    return [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]


def primary_endpoint(df, mdl_c, mdl_b, n_perm=N_PERM, n_boot=N_BOOT, seed=SEED, bs=BLOCK):
    """Recompute the frozen Stage-04 primary endpoint exactly as `validate()` does.

    The validator draws, from a SINGLE `default_rng(20260924)`: the 199 block-mean
    permutations, then one permutation-validity sanity draw, then the 1000 block-bootstrap
    resamples. Sharing one stream is what makes the published CI reproducible; a fresh
    stream per stage (see `block_bootstrap_ci`) yields the *Stage-05 re-draw* CI instead.
    Returns dict(rmse_baselineA, rmse_candidate, delta_rmse, perm_p, ci95, perm_corr).
    """
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    groups = {b: g.index.to_numpy() for b, g in df.groupby(blk)}
    blocks = list(groups)
    bmean = df[Y].groupby(blk).transform('mean')
    resid = df[Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc_b = predict(mdl_b, df); pc_c = predict(mdl_c, df)
    yv = df[Y].to_numpy(float)
    rb = float(np.sqrt(np.mean((yv - pc_b) ** 2)))
    rc = float(np.sqrt(np.mean((yv - pc_c) ** 2)))
    d_obs = rb - rc
    null = np.empty(n_perm)
    for i in range(n_perm):
        sh = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
        yperm = blk.map(sh).to_numpy(float) + resid
        null[i] = (np.sqrt(np.mean((yperm - pc_b) ** 2)) - np.sqrt(np.mean((yperm - pc_c) ** 2)))
    p_perm = float((1 + np.sum(null >= d_obs)) / (1 + n_perm))
    sh_chk = pd.Series(rng.permutation(ymean.to_numpy(float)), index=ymean.index)
    yperm_chk = blk.map(sh_chk).to_numpy(float) + resid
    perm_corr = float(np.corrcoef(yv, yperm_chk)[0, 1])
    boot = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.choice(len(blocks), size=len(blocks), replace=True)
        sel = np.concatenate([groups[blocks[j]] for j in pick])
        d, _, _ = delta_rmse(df.iloc[sel], mdl_c, mdl_b)
        boot[i] = d
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
    return dict(rmse_baselineA=rb, rmse_candidate=rc, delta_rmse=d_obs,
                perm_p=p_perm, ci95=ci, perm_corr=perm_corr)


# ------------------------------------------------------------------ helpers
def load_candidate(cand_dir, cid):
    with open(cand_dir / (cid + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def attach_rows(df, mask_csv, id_col='Grid_ID', subset=('row', 'col')):
    """Merge (row, col) onto a zone table by Grid_ID, as the validator does."""
    m = pd.read_csv(mask_csv)
    cols = [id_col] + [c for c in subset if c in m.columns]
    return df.merge(m[cols], on=id_col, how='left')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ AST builders
# copied from PAID/stage03_discovery/agents/core.py (formatters and constructors)
def var(n):        return {'op': 'var', 'name': n}
def const(v):      return {'op': 'const', 'value': float(v)}
def add(a, b):     return {'op': 'add', 'args': [a, b]}
def sub(a, b):     return {'op': 'sub', 'args': [a, b]}
def mul(a, b):     return {'op': 'mul', 'args': [a, b]}
def div(a, b):     return {'op': 'div', 'args': [a, b]}
def neg(a):        return {'op': 'neg', 'arg': a}
def inv(a):        return {'op': 'inv', 'arg': a}
def log(a):        return {'op': 'log', 'arg': a}
def exp(a):        return {'op': 'exp', 'arg': a}
def sq(n):         return mul(var(n), var(n))


def expr_complexity(term):
    if not isinstance(term, dict):
        raise ValueError('term must be a dict')
    op = term.get('op')
    if op in ('var', 'const'):
        return 1
    if op in ('add', 'sub', 'mul', 'div'):
        return 1 + expr_complexity(term['args'][0]) + expr_complexity(term['args'][1])
    if op in ('exp', 'log', 'neg', 'inv'):
        return 1 + expr_complexity(term['arg'])
    raise ValueError('illegal operator: %r' % op)


def complexity(terms):
    return int(sum(expr_complexity(t) for t in terms) + len(terms))


def _fmt(t):
    o = t['op']
    if o == 'var':
        return t['name'].replace('_mean', '')
    if o == 'const':
        return '%.3g' % t['value']
    if o in ('add', 'sub', 'mul', 'div'):
        sym = {'add': '+', 'sub': '-', 'mul': '*', 'div': '/'}[o]
        return '(%s %s %s)' % (_fmt(t['args'][0]), sym, _fmt(t['args'][1]))
    if o == 'neg':
        return '(-%s)' % _fmt(t['arg'])
    if o == 'inv':
        return '(1/%s)' % _fmt(t['arg'])
    return '%s(%s)' % (o, _fmt(t['arg']))


def fmt_terms(terms):
    return ' + '.join(_fmt(t) for t in terms)


# ------------------------------------------------------------------ spatial CV
def kmeans(pts, k, seed, it=80, restarts=10):
    """Copied from PAID/stage03_discovery/agents/core.py (deterministic given seed)."""
    rng = np.random.default_rng(seed)
    best, best_in = None, np.inf
    for _ in range(restarts):
        c = pts[rng.choice(len(pts), k, replace=False)].astype(float)
        for _ in range(it):
            d = ((pts[:, None, :] - c[None, :, :]) ** 2).sum(-1)
            lab = d.argmin(1)
            nc = np.array([pts[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
            if np.allclose(nc, c):
                c = nc
                break
            c = nc
        inertia = float(((pts - c[lab]) ** 2).sum())
        if inertia < best_in:
            best_in, best = inertia, lab
    return best, best_in


def spatial_folds(df, k=5, seed=SEED, rowcol=('row', 'col')):
    pts = df[list(rowcol)].to_numpy(float)
    lab, _ = kmeans(pts, k, seed)
    return lab


def pooled_cv_rmse(df, terms, folds):
    """Copied from PAID/stage03_discovery/agents/core.py: standardise per training fold."""
    truths, preds, per = [], [], []
    for f in np.unique(folds):
        tr, te = folds != f, folds == f
        dtr = df[tr]
        vs = sorted(set().union(*[expr_vars(t) for t in terms]))
        mu = {v: float(dtr[v].mean()) for v in vs}
        sd = {v: float(dtr[v].std(ddof=0)) or 1.0 for v in vs}
        mdl = fit_expr(dtr, terms, mu=mu, sd=sd)
        p = predict(mdl, df[te])
        truths.append(df.loc[te, Y].to_numpy(float))
        preds.append(p)
        per.append(rmse(df.loc[te, Y], p))
    t = np.concatenate(truths)
    p = np.concatenate(preds)
    return float(np.sqrt(np.mean((t - p) ** 2))), [float(x) for x in per]


def greedy_terms(df, folds, K, pool, prescreen=24, max_complexity=MAX_COMPLEXITY):
    """Greedy forward selection — copied from PAID/stage03_discovery/agents/core.py.

    Same prescreen (|corr| of the standardised term column vs standardised LST), same
    stop rule (`step >= best - 1e-6`), same complexity cap.  `pool` is supplied by the
    caller (the frozen Shenzhen pool or the Changchun-adapted pool), so the search is
    identical to the historical one apart from the variables it is allowed to use.
    Returns (terms_list, trace).
    """
    yz = (df[Y] - df[Y].mean()) / (df[Y].std(ddof=0) or 1.0)
    scored = []
    for label, t in pool:
        vs = sorted(expr_vars(t))
        mu = {v: float(df[v].mean()) for v in vs}
        sd = {v: float(df[v].std(ddof=0)) or 1.0 for v in vs}
        col = expr_design(df, [t], mu, sd)[:, 1]
        if not np.all(np.isfinite(col)) or np.std(col) == 0:
            continue
        scored.append((abs(float(np.corrcoef(col, yz)[0, 1])), label, t))
    scored.sort(reverse=True, key=lambda z: z[0])
    cand = [(l, t) for _, l, t in scored[:prescreen]]

    chosen, trace, best = [], [], None
    while len(chosen) < K:
        step = None
        for label, t in cand:
            trials = [tt for _, tt in chosen] + [t]
            if complexity(trials) > max_complexity:
                continue
            r, _ = pooled_cv_rmse(df, trials, folds)
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
