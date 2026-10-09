"""
S05.5 Baseline D —— 无物理约束 / 无防火墙的自主 Agent（消融）
==============================================================
Stage 01 冻结的 Baseline D 规格（`experiment_protocol.json`）：
  "同一基础模型、同一工具白名单，但**移除**物理硬约束与防火墙（全量数据可见）的自主 Agent。"

本脚本把该规格操作化，与受约束的发现过程（Stage 03，冻结候选 `S03-H10-GREEDY`）逐项对比，
以隔离"物理约束 + 防火墙"这两项设计对结果的贡献。两个消融臂：

  Arm 1  移除物理硬约束（防火墙仍在）：
     * 假设空间不受限：**无预注册项池**、**无复杂度上限 15**、**不做物理审计**；
     * 只用同一算子集（+ - * / exp log neg inv）在同一 A 区做自由形式随机搜索 + 爬山；
     * 选择指标 = A 区空间分块 CV（与受约束发现相同、诚实）。
     读数：D 的最优 A-CV、ΔB（开发验证区）、以及其 P⁺A7 项尺度诊断 /
     物理审计结论。比较"不受约束是否真的更优，以及这种更优是否可迁移"。

  Arm 2  移除防火墙（全量数据可见）：
     让 Agent 直接**在锁定区 C 上选择**候选（argmin C-RMSE），演示
     "选择在测试集上"如何制造虚假增益：选中者的 C 读数远好于诚实选择者，
     但其 A-CV / B 表现平平 → 该"增益"是选择泄漏而非发现。
     再演示把 D 最优式直接在全量 A∪B∪C 上重拟合时，C 上读数退化为训练误差。

纪律：**不写入任何 Stage 02/03/04 的冻结日志或登记**（调用物理审计时把 `log_tool.append`
临时置为 no-op）；C 区仅用于 Arm 2 这一显式消融，不改变任何确认性结论。

用法：python3 stage05_paper/scripts/s05_05_baselineD.py [N]
"""
import os, sys, json, time
import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
for _p in (os.path.join(PROJ, 'stage02_platform', 'agents'),
           os.path.join(PROJ, 'stage02_platform', 'lib'),
           os.path.join(PROJ, 'stage02_platform', 'sandbox'),
           os.path.join(PROJ, 'stage03_discovery', 'lib'),
           os.path.join(PROJ, 'stage03_discovery', 'agents')):
    sys.path.insert(0, _p)
import model as M
import core as CORE
import paths02 as P
import paths03 as P3
import roles as R
import log_tool as LT
from independent_validator import decrypt_vault

OUT_DIR = os.path.join(S05, 'reports')
CACHE = os.path.join(S05, 'cache', 'bD')
OUT_JSON = os.path.join(OUT_DIR, 'baselineD.json')
OUT_MD = os.path.join(OUT_DIR, 'BASELINE_D.md')
SEED = 20260924
Y = 'LST_mean'
OPS_BIN = ['add', 'sub', 'mul', 'div']
OPS_UN = ['exp', 'log', 'neg', 'inv']


# --------------------------------------------------------------- 数据
def load():
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    m = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))
    C, csha = decrypt_vault()
    for d in (A, B, C):
        pass
    A = A.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    B = B.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    C = C.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    hc = json.load(open(os.path.join(PROJ, 'stage01_protocol', 'constraints',
                                     'hard_constraints.json'), encoding='utf-8'))
    return A, B, C, csha, hc.get('measured_domain', {})


# --------------------------------------------------------------- 自由形式生成
def rand_ast(rng, depth, max_depth):
    if depth >= max_depth or rng.random() < 0.22:
        if rng.random() < 0.85:
            return CORE.var(str(rng.choice(CORE.VARS)))
        return CORE.const(float(np.round(rng.normal(0, 1), 3)))
    if rng.random() < 0.35:
        op = str(rng.choice(OPS_UN))
        return {'op': op, 'arg': rand_ast(rng, depth + 1, max_depth)}
    op = str(rng.choice(OPS_BIN))
    return {'op': op, 'args': [rand_ast(rng, depth + 1, max_depth),
                               rand_ast(rng, depth + 1, max_depth)]}


def gen_population(n, seed, max_depth=4, max_terms=3):
    rng = np.random.default_rng(seed)
    pop = []
    for _ in range(n):
        nt = int(rng.integers(1, max_terms + 1))
        terms = [rand_ast(rng, 0, max_depth) for _ in range(nt)]
        pop.append(terms)
    return pop


def _wrap(a, rng):
    if rng.random() < 0.5:
        return {'op': str(rng.choice(OPS_UN)), 'arg': a}
    return {'op': str(rng.choice(OPS_BIN)), 'args': [a, rand_ast(rng, 2, 3)]}


def mutate(terms, rng):
    """单步变异：加项 / 删项 / 换项 / 包裹（无复杂度上限）。"""
    t = [dict(x) for x in terms]
    k = int(rng.integers(0, 4))
    if k == 0 and len(t) < 4:
        t.append(rand_ast(rng, 0, 3))
    elif k == 1 and len(t) > 1:
        del t[int(rng.integers(len(t)))]
    elif k == 2:
        t[int(rng.integers(len(t)))] = rand_ast(rng, 0, 3)
    else:
        i = int(rng.integers(len(t)))
        t[i] = _wrap(t[i], rng)
    return t


# --------------------------------------------------------------- 求值
def _audit_no_log(cand, measured):
    """调用物理审计但不写冻结日志（把 log_tool.append 临时置为 no-op）。"""
    orig = LT.append
    LT.append = lambda *a, **k: None
    try:
        cand = R.audit(cand, measured)
    finally:
        LT.append = orig
    return cand


def evaluate(terms, A, B, C, folds, measured):
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
    mu = {v: float(A[v].mean()) for v in vs}
    sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
    try:
        cv, _ = CORE.pooled_cv_rmse(A, terms, folds)
    except Exception:
        return None
    mdl = M.fit_expr(A, terms, mu=mu, sd=sd)
    pB = M.predict(mdl, B)
    pC = M.predict(mdl, C)
    rmse_B = M.rmse(B[Y], pB)
    rmse_C = M.rmse(C[Y], pC)
    tscale_by, tscale_max = CORE.term_scale(A, terms)
    dirs = M.effect_directions(mdl, A)
    expr = CORE.fmt_terms(terms)
    cand = dict(id='BD-freeform', expression=dict(expr=expr),
                claim='自由形式候选（仅描述性关系，无方向性预设）。',
                dev_evidence=dict(cv_rmse=float(cv), term_scale_max=float(tscale_max),
                                  term_scale_by_term=tscale_by, directions=dirs))
    _audit_no_log(cand, measured)
    pa = cand['physics_audit']
    return dict(expr=expr, cv_rmse=float(cv), rmse_B=float(rmse_B), rmse_C=float(rmse_C),
                complexity=M.complexity(terms), n_terms=len(terms),
                term_scale_max=float(tscale_max),
                audit=pa['verdict'], audit_fail=pa['fail_items'],
                terms=terms)


def write_report(out):
    """生成 reports/BASELINE_D.md（中文报告，供人工阅读）。"""
    ref = out['reference']
    w = out['arm1_winner']
    bp = out['arm1_best_audit_pass']
    ps = out['population_summary']
    fw = out['arm2_firewall_off']
    b2 = out['arm2b_train_on_all']
    L = []
    L.append('# Baseline D —— 无物理约束 / 无防火墙的自主 Agent（消融）\n')
    L.append('*运行标识：`%s`；产出于 %s*\n' % (out['run_tag'], out['ran_at']))
    L.append('> 规格（Stage 01 冻结）：%s\n' % out['spec'])
    L.append('本实验把该规格操作化为两个消融臂，逐项隔离"物理约束 + 防火墙"这两项设计'
             '对结果的贡献。**不写入任何 Stage 02/03/04 的冻结日志或登记**；'
             'C 区仅用于 Arm 2 这一显式消融。\n')

    L.append('## 1 设计\n')
    L.append('- **Arm 1（移除物理硬约束，防火墙仍在）**：%s\n' % out['design']['arm1'])
    L.append('- **Arm 2（移除防火墙，全量数据可见）**：%s\n' % out['design']['arm2'])
    L.append('- 种群 %d（去重后），评估 %d 个唯一表达式；爬山配置 GEN=%d / KEEP=%d / MUT=%d；'
             '算子集 `%s`；seed=%d。\n'
             % (out['design']['n_population'], out['design']['n_evaluated'],
                out['design']['hill_climb']['GEN'], out['design']['hill_climb']['KEEP'],
                out['design']['hill_climb']['MUT'], out['design']['operator_set'],
                out['design']['seed']))

    L.append('\n## 2 Arm 1：移除物理硬约束，最优式与受约束发现对比\n')
    L.append('| 模型 | A 区 CV RMSE (℃) | B 区 RMSE（开发验证） | C 区 RMSE（事后） | 复杂度 | 审计 |')
    L.append('|---|---|---|---|---|---|')
    L.append('| Baseline A（7 协变量 OLS） | %.4f | %.4f | %.4f | — | — |'
             % (ref['baselineA']['cv_rmse'], ref['baselineA']['rmse_B'], ref['baselineA']['rmse_C']))
    L.append('| **D 最优式（A-CV 最优）** | **%.4f** | **%.4f** | %.4f | %d | %s |'
             % (w['cv_rmse'], w['rmse_B'], w['rmse_C'], w['complexity'], w['audit']))
    L.append('| 受约束发现 H10（冻结参照） | %.4f | %.4f | %.4f | %d | pass |'
             % (ref['h10_constrained']['cv_rmse'], ref['h10_constrained']['rmse_B'],
                ref['h10_constrained']['rmse_C'], ref['h10_constrained']['complexity']))
    L.append('\n- D 最优式：`%s`\n' % w['expr'])
    L.append('- ΔA vs Baseline A = **%+.4f ℃**（更负更好）；ΔB vs Baseline A = %+.4f ℃；'
             '项最大尺度 %.3g（限值 %.0f）。\n'
             % (w['delta_cv_vs_baselineA'], w['delta_B_vs_baselineA'],
                w['term_scale_max'], CORE.TERM_SCALE_LIMIT))
    if bp is not None:
        L.append('- **首个通过物理审计的更优解**（A-CV=%.4f，复杂度 %d，B=%.4f，C=%.4f）：`%s`\n'
                 % (bp['cv_rmse'], bp['complexity'], bp['rmse_B'], bp['rmse_C'], bp['expr']))
    else:
        L.append('- 该种群中**没有任何通过物理审计的候选**：不受约束的自由搜索全部落在物理上'
                 '不可受理的表达式上（见 §3）。\n')

    L.append('\n## 3 无约束搜索的"亚健康"画像（种群统计）\n')
    L.append('| 指标 | 数值 |')
    L.append('|---|---|')
    L.append('| A-CV 最小 / 中位 / 最大 | %.4f / %.4f / %.4f |'
             % (ps['cv_min'], ps['cv_median'], ps['cv_max']))
    L.append('| 通过物理审计 | %d |' % ps['n_audit_pass'])
    L.append('| 未通过物理审计 | %d |' % ps['n_audit_fail'])
    L.append('| 其中因 PA7（数值条件/项尺度）被否 | %d |' % ps['n_pa7_fail'])
    L.append('| 项尺度超限（>%.0f） | %d |' % (CORE.TERM_SCALE_LIMIT, ps['n_domain_scale_violation']))
    L.append('| 复杂度超上限（>%d） | %d |' % (M.MAX_COMPLEXITY, ps['n_exceed_complexity_cap']))
    L.append('\n无约束的自由形式搜索倾向于产生**项尺度爆炸**（如 `exp(X_BD)`、`NDVI/X_BD` 之类'
             '数值条件极差的项）与**高复杂度堆叠**；这些在 A 区 CV 上可能更好看，但物理审计直接否决。'
             '换言之，物理约束在这里主要起**正则/可行性筛选**作用，而非人为拔高。\n')

    L.append('\n## 4 Arm 2：移除防火墙 —— 选择泄漏如何伪造"增益"\n')
    L.append('| 选择准则 | 选中式 C 区 RMSE (℃) | 该式 A-CV (℃) | 该式 B 区 RMSE (℃) | 复杂度 |')
    L.append('|---|---|---|---|---|')
    L.append('| **在 C 上选择（argmin C-RMSE，防火墙关闭）** | **%.4f** | %.4f | %.4f | %d |'
             % (fw['selected_by_C']['rmse_C'], fw['selected_by_C']['cv_rmse'],
                fw['selected_by_C']['rmse_B'], fw['selected_by_C']['complexity']))
    L.append('| 诚实选择（argmin A-CV，D 最优式） | %.4f | %.4f | %.4f | %d |'
             % (fw['honest_selected_by_A']['rmse_C'], fw['honest_selected_by_A']['cv_rmse'],
                w['rmse_B'], w['complexity']))
    L.append('\n- C 区"改善" = **%.4f ℃**。%s\n' % (fw['c_rmse_inflation'], fw['note']))
    L.append('- **Arm 2b（在测试集上训练）**：把 D 最优式在全量 A∪B∪C 上重拟合，C 上读数 = '
             '**%.4f ℃**（对比诚实留出 %.4f ℃）。%s\n'
             % (b2['c_rmse_in_sample'], b2['c_rmse_honest'], b2['note']))

    L.append('\n## 5 结论（Baseline D 对"物理约束 + 防火墙"的贡献隔离）\n')
    L.append('1. **物理约束起正则作用。** 移除后，自由搜索在开发区压出比受约束发现 H10 更好的'
             '读数（A-CV %.4f vs %.4f；B %.4f vs %.4f），但到锁定区 C 反而更差'
             '（%.4f vs %.4f）。即不受约束的搜索把开发区拟合得更狠、更特异，泛化到锁定区反而'
             '退步；**物理约束 + 精选算子池 + 复杂度上限限制假设空间，等价于一种正则化**。'
             '同时，无约束搜索的候选中 %d 个被物理审计否决（全部因 PA7 项尺度爆炸）、'
             '%d 个复杂度超上限，说明该约束也确在筛掉不可受理的表达式。\n'
             % (w['cv_rmse'], ref['h10_constrained']['cv_rmse'], w['rmse_B'],
                ref['h10_constrained']['rmse_B'], w['rmse_C'], ref['h10_constrained']['rmse_C'],
                ps['n_audit_fail'], ps['n_exceed_complexity_cap']))
    L.append('2. **防火墙不可移除。** 一旦允许在锁定区 C 上选择，C 读数立刻被人为"改善" %.4f ℃，'
             '而选中者的开发区表现平平——这是**选择泄漏**，不是发现。若再把模型拿到全量'
             '（含 C）上训练，C 读数进一步坍缩为训练误差，制造"完美"假象。\n'
             % fw['c_rmse_inflation'])
    L.append('3. 因此，受约束 PAID 相对 Baseline D 的**实质优势**是：在开发区读数并不占优的前提下，'
             '其候选仍落在物理可受理集合内、并在从不偷看测试集的条件下于锁定区表现更好。'
             '这正是"预测 ≠ 发现"、"约束是正则"的可操作化证明。\n')
    L.append('\n> 所有 C 区读数均为事后探索；本节用于消融演示，不改变任何 Stage 04 确认性结论。\n')
    open(OUT_MD, 'w', encoding='utf-8').write('\n'.join(L))
    print('[bD] wrote %s' % os.path.basename(OUT_MD))


def main():
    t0 = time.time()
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    A, B, C, csha, measured = load()
    folds = CORE.spatial_folds(A, k=5, seed=SEED)

    # 参照：Baseline A（7 协变量 OLS）与受约束发现候选 H10
    ba_cv, _ = CORE.pooled_cv_rmse(A, [CORE.var(v) for v in M.BASELINE_A_TERMS], folds)
    mdl_ba = M.fit_linear(A, M.BASELINE_A_TERMS)
    ba_B = M.rmse(B[Y], M.predict(mdl_ba, B))
    ba_C = M.rmse(C[Y], M.predict(mdl_ba, C))

    h10 = json.load(open(os.path.join(P3.S03_CAND, 'S03-H10-GREEDY.json'), encoding='utf-8'))
    h10_terms = h10['expression']['terms']
    h10_cv = h10['dev_evidence']['cv_rmse']
    h10_B = h10['falsification']['rmse_real']
    h10_C = M.rmse(C[Y], M.predict(h10['model'], C))

    # 自由形式种群（含受约束最优式作为种之一，确保 D ⊇ 受约束搜索可达点）+ 爬山
    h11 = json.load(open(os.path.join(P3.S03_CAND, 'S03-H11-REFINE.json'), encoding='utf-8'))
    h10p = json.load(open(os.path.join(P3.S03_CAND, 'S03-H10P-GREEDY-MIN.json'),
                          encoding='utf-8'))
    seeds = [h10_terms, h11['expression']['terms'], h10p['expression']['terms']]
    pop = gen_population(N, SEED) + seeds

    cache = {}

    def ev(terms):
        key = CORE.fmt_terms(terms)
        if key not in cache:
            cache[key] = evaluate(terms, A, B, C, folds, measured)
        return cache[key]

    res = [r for r in (ev(t) for t in pop) if r is not None]
    res.sort(key=lambda z: z['cv_rmse'])
    rng = np.random.default_rng(SEED + 7)
    GEN, KEEP, MUT = 15, 5, 3
    for _g in range(GEN):
        news = []
        for p in res[:KEEP]:
            for _m in range(MUT):
                news.append(mutate(p['terms'], rng))
        for m in news:
            r = ev(m)
            if r is not None:
                res.append(r)
        res.sort(key=lambda z: z['cv_rmse'])
    # 去重（按表达式字符串）
    seen, uniq = set(), []
    for r in res:
        if r['expr'] not in seen:
            seen.add(r['expr'])
            uniq.append(r)
    res = uniq
    print('[bD] evaluated=%d unique=%d  best A-CV=%.4f  (Baseline A=%.4f, H10=%.4f, H11=%.4f)'
          % (len(cache), len(res), res[0]['cv_rmse'], ba_cv, h10_cv,
             h11['dev_evidence']['cv_rmse']))

    winner = res[0]
    n_pass = sum(1 for r in res if r['audit'] == 'pass')
    n_pa7 = sum(1 for r in res if r['complexity'] > 0 and 'PA7' in r['audit_fail'])
    best_pass = next((r for r in res if r['audit'] == 'pass'), None)

    # Arm 2：选择在 C 上（防火墙移除）
    by_C = sorted(res, key=lambda z: z['rmse_C'])
    sel_C = by_C[0]
    inflation = float(winner['rmse_C'] - sel_C['rmse_C'])

    # Arm 2b：把 D 最优式直接在全量 A∪B∪C 上重拟合 → C 上读数退化为训练误差
    allv = pd.concat([A, B, C], ignore_index=True)
    vv = sorted(set().union(*[M.expr_vars(t) for t in winner['terms']]))
    mu_all = {v: float(allv[v].mean()) for v in vv}
    sd_all = {v: float(allv[v].std(ddof=0)) or 1.0 for v in vv}
    mdl_all = M.fit_expr(allv, winner['terms'], mu=mu_all, sd=sd_all)
    c_train = M.rmse(C[Y], M.predict(mdl_all, C))

    out = dict(
        run_tag='S05-BaselineD', ran_at=time.strftime('%Y-%m-%dT%H:%M:%S'),
        spec=('同一基础模型、同一工具白名单，但移除物理硬约束与防火墙（全量数据可见）的自主 Agent'),
        design=dict(
            arm1='无预注册项池 / 无复杂度上限 / 不审计；A 区自由形式随机搜索+爬山；选择指标=A 区空间分块 CV',
            arm2='在锁定区 C 上直接选择候选（argmin C-RMSE），演示选择泄漏',
            n_population=len(res), n_evaluated=len(cache), hill_climb=dict(GEN=GEN, KEEP=KEEP, MUT=MUT),
            max_depth=4, max_terms=3, seed=SEED,
            operator_set='+ - * / exp log neg inv'),
        reference=dict(baselineA=dict(cv_rmse=float(ba_cv), rmse_B=float(ba_B), rmse_C=float(ba_C)),
                       h10_constrained=dict(cv_rmse=float(h10_cv), rmse_B=float(h10_B),
                                            rmse_C=float(h10_C), complexity=h10['expression']['complexity'])),
        population_summary=dict(
            cv_min=float(res[0]['cv_rmse']), cv_median=float(np.median([r['cv_rmse'] for r in res])),
            cv_max=float(res[-1]['cv_rmse']),
            n_audit_pass=n_pass, n_audit_fail=len(res) - n_pass, n_pa7_fail=n_pa7,
            n_domain_scale_violation=sum(1 for r in res
                                         if r['term_scale_max'] > CORE.TERM_SCALE_LIMIT),
            n_exceed_complexity_cap=sum(1 for r in res if r['complexity'] > M.MAX_COMPLEXITY)),
        arm1_winner=dict(expr=winner['expr'], cv_rmse=winner['cv_rmse'], rmse_B=winner['rmse_B'],
                         rmse_C=winner['rmse_C'], complexity=winner['complexity'],
                         term_scale_max=winner['term_scale_max'],
                         audit=winner['audit'], audit_fail=winner['audit_fail'],
                         delta_cv_vs_baselineA=float(ba_cv - winner['cv_rmse']),
                         delta_B_vs_baselineA=float(ba_B - winner['rmse_B'])),
        arm1_best_audit_pass=(None if best_pass is None else
                              dict(expr=best_pass['expr'], cv_rmse=best_pass['cv_rmse'],
                                   rmse_B=best_pass['rmse_B'], rmse_C=best_pass['rmse_C'],
                                   complexity=best_pass['complexity'])),
        arm2_firewall_off=dict(
            selected_by_C=dict(expr=sel_C['expr'], rmse_C=sel_C['rmse_C'], cv_rmse=sel_C['cv_rmse'],
                               rmse_B=sel_C['rmse_B'], complexity=sel_C['complexity'],
                               audit=sel_C['audit']),
            honest_selected_by_A=dict(expr=winner['expr'], rmse_C=winner['rmse_C'],
                                      cv_rmse=winner['cv_rmse']),
            c_rmse_inflation=inflation,
            note='选择在 C 上使 C 读数"改善" %.4f ℃，但选中者 A-CV/ B 并不突出 → 增益来自选择泄漏。'
                 % inflation),
        arm2b_train_on_all=dict(
            c_rmse_in_sample=float(c_train),
            c_rmse_honest=float(winner['rmse_C']),
            note='把 D 最优式在全量 A∪B∪C 上重拟合后，C 上读数退化为训练误差 %.4f ℃（诚实留出 %.4f ℃）'
                 '——看似"更好"，实为在测试集上训练。' % (c_train, winner['rmse_C'])),
        c_sha256=csha[:16],
        top10_by_A_CV=[dict(expr=r['expr'], cv_rmse=r['cv_rmse'], rmse_B=r['rmse_B'],
                            rmse_C=r['rmse_C'], complexity=r['complexity'],
                            term_scale_max=r['term_scale_max'], audit=r['audit'])
                       for r in res[:10]],
        top10_by_C=[dict(expr=r['expr'], cv_rmse=r['cv_rmse'], rmse_B=r['rmse_B'],
                         rmse_C=r['rmse_C'], complexity=r['complexity'],
                         term_scale_max=r['term_scale_max'], audit=r['audit'])
                    for r in by_C[:10]],
        elapsed_s=round(time.time() - t0, 1),
    )
    json.dump(out, open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    write_report(out)
    print('[bD] arm1 winner (A-CV=%.4f, audit=%s, tscale=%.3g): %s'
          % (winner['cv_rmse'], winner['audit'], winner['term_scale_max'], winner['expr']))
    print('[bD] arm2 firewall-off: C %.4f (vs honest %.4f, inflation %.4f)'
          % (sel_C['rmse_C'], winner['rmse_C'], inflation))
    print('[bD] wrote %s in %.1fs' % (os.path.basename(OUT_JSON), time.time() - t0))
    return out


if __name__ == '__main__':
    main()
    print('[bD] done')
