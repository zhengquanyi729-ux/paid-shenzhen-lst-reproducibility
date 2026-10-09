"""
候选表达式的**最小可执行模型**（平台层，非发现层）
==================================================
本模块是「模型评估」的唯一实现，被发现侧（沙箱内）与独立验证服务共同使用，
以保证**同一份表达式在开发区与锁定区被逐字相同地求值**。

两种允许的表达式形式（平台冻结的通信 schema）：

1) 线性（Baseline A 与 Stage 02 冒烟候选使用）
   {form:'linear', terms:[covariate,...], standardize:true, intercept:true}
   所有协变量在拟合前按 A 区均值/标准差标准化（无量纲化，符合 §3 量纲约束）。

2) 符号表达式（Stage 03 自主发现使用，对应冻结的 Baseline C 规格：
   算子集 + - * / exp log，最大复杂度 15）
   {form:'expr', terms:[<term_ast>,...], standardize:true, intercept:true,
    mu:{var:...}, sd:{var:...}, beta:[b0,b1,...], complexity:<int>}
   term_ast := {"op":"var","name":VAR}
             | {"op":"const","value":v}
             | {"op":"add"|"sub"|"mul"|"div","args":[a,b]}
             | {"op":"exp"|"log"|"neg"|"inv","arg":a}
   变量一律先按 A 区 mu/sd 标准化；模型预测 = b0 + Σ b_i · term_i。

数值安全（实现层护栏，不改变算子集）：exp 的输入截断到 [-30,30]；log 的输入下界
取 1e-6；除法分母以 |d|<1e-6 视作 ±1e-6。这样任何合法 AST 都不会产生 inf/nan，
而「表达式是否因此变得无物理意义」由 Physics Auditor 判定，不在此处掩盖。
"""
import json
import numpy as np

COVARIATES = ['NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens',
              'X_BD', 'X_BH', 'X_VolDens']
# 冻结的 Baseline A 规格：预指定协变量的一次项 OLS（不含交互、无惩罚）。
# 说明：Stage 01 experiment_protocol.json 的 frozen_specs.A 文本把目标 LST_mean 也列进了
# 「8 个预指定变量」，与 9 列 CSV 构成（7 协变量 + 目标 + My_ID）不符；实际以代码形式冻结
# 并使用的 Baseline A 为下面这 7 个协变量（Stage 02 冒烟即用此定义）。
BASELINE_A_TERMS = list(COVARIATES)
Y = 'LST_mean'
MAX_COMPLEXITY = 15

_EPS = 1e-6


# ------------------------------------------------------------------ 通用
def _design(df, terms, mu, sd):
    X = np.column_stack([(df[t].to_numpy(float) - mu[t]) / sd[t] for t in terms])
    return np.column_stack([np.ones(len(df)), X])          # 截距列


def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.asarray(y_true, float) - np.asarray(y_pred, float)) ** 2)))


def r2(y_true, y_pred):
    y = np.asarray(y_true, float)
    return float(1 - np.sum((y - y_pred) ** 2) / np.sum((y - y.mean()) ** 2))


def serialize(model):
    return json.dumps(model, ensure_ascii=False, sort_keys=True)


def evaluate(model, df):
    p = predict(model, df)
    return dict(n=int(len(df)), rmse=rmse(df[Y], p), r2=r2(df[Y], p))


# ------------------------------------------------------------------ 线性
def fit_linear(df, terms, mu=None, sd=None):
    """在 df 上拟合 y = b0 + Σ b_j * z_j，z_j 为 A 区标准化后的协变量。"""
    mu = mu or {t: float(df[t].mean()) for t in terms}
    sd = sd or {t: float(df[t].std(ddof=0)) or 1.0 for t in terms}
    X = _design(df, terms, mu, sd)
    beta = np.linalg.lstsq(X, df[Y].to_numpy(float), rcond=None)[0]
    return dict(form='linear', terms=list(terms), mu=mu, sd=sd,
                beta=beta.tolist(), intercept=True, n_fit=int(len(df)))


# ------------------------------------------------------------------ 符号表达式
def expr_complexity(term):
    """AST 节点数（叶子与内部节点均计 1）——冻结的复杂度计数规则。"""
    if not isinstance(term, dict):
        raise ValueError('term 必须是 dict')
    op = term.get('op')
    if op in ('var', 'const'):
        return 1
    if op in ('add', 'sub', 'mul', 'div'):
        return 1 + expr_complexity(term['args'][0]) + expr_complexity(term['args'][1])
    if op in ('exp', 'log', 'neg', 'inv'):
        return 1 + expr_complexity(term['arg'])
    raise ValueError('非法算子: %r' % op)


def expr_vars(term):
    if term.get('op') == 'var':
        return {term['name']}
    if term.get('op') == 'const':
        return set()
    if term.get('op') in ('add', 'sub', 'mul', 'div'):
        return expr_vars(term['args'][0]) | expr_vars(term['args'][1])
    return expr_vars(term['arg'])


def complexity(terms):
    """冻结规则的复杂度：所有项 AST 节点数之和 + 项数（每个系数记 1）。"""
    return int(sum(expr_complexity(t) for t in terms) + len(terms))


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
    raise ValueError('非法算子: %r' % op)


def _zmap(df, mu, sd):
    return {v: ((df[v].to_numpy(float) - mu[v]) / sd[v]) for v in mu}


def expr_design(df, terms, mu, sd):
    Z = _zmap(df, mu, sd)
    return np.column_stack([np.ones(len(df))] + [_eval_term(t, Z) for t in terms])


def fit_expr(df, terms, mu=None, sd=None, var_names=None):
    """在 df（应为 A 发现区）上拟合 y = b0 + Σ b_i·term_i，冻结标准化常数与系数。"""
    var_names = var_names or sorted(set().union(*[expr_vars(t) for t in terms]))
    mu = mu or {v: float(df[v].mean()) for v in var_names}
    sd = sd or {v: float(df[v].std(ddof=0)) or 1.0 for v in var_names}
    X = expr_design(df, terms, mu, sd)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    beta = np.linalg.lstsq(X, df[Y].to_numpy(float), rcond=None)[0]
    return dict(form='expr', terms=terms, standardize=True, intercept=True,
                mu=mu, sd=sd, beta=beta.tolist(), n_fit=int(len(df)),
                complexity=complexity(terms))


# ------------------------------------------------------------------ 统一预测
def predict(model, df):
    if model['form'] == 'linear':
        X = _design(df, model['terms'], model['mu'], model['sd'])
        return X @ np.array(model['beta'], float)
    if model['form'] == 'expr':
        X = expr_design(df, model['terms'], model['mu'], model['sd'])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        return X @ np.array(model['beta'], float)
    raise ValueError('未知模型形式: %r' % model['form'])


def effect_directions(model, df):
    """对每个用到的原始变量做「±1 个 A 区标准差」的有限差分，如实报告 LST 方向。

    仅用于报告方向（**不预设方向**）；对线性模型等价于系数符号。
    """
    out = {}
    for v in model['mu']:
        lo, hi = df.copy(), df.copy()
        lo[v] = model['mu'][v] - model['sd'][v]
        hi[v] = model['mu'][v] + model['sd'][v]
        d = float(np.mean(predict(model, hi) - predict(model, lo)))
        out[v] = dict(delta_LST_per_SD=d,
                      direction=('+' if d > 1e-9 else '-' if d < -1e-9 else '0'))
    return out
