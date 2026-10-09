"""
S03.2 沙箱内自主探索循环（Stage 03 核心）
==========================================
在访问守卫内运行，只用 A/B 数据；按 §4.3 循环：
  观察数据 → 生成可证伪假设 → 设计开发实验 → 反例与误差分析 → 修订或放弃 → 冻结少量候选。
每步以对应角色名写入 append-only 哈希链日志；失败候选保留，不覆盖。

多轮结构（本轮首过；每轮都在同一预算与同一访问守卫下）：
  Round 1  预注册假设议程 H01–H09（人工设定的可证伪假设，复杂度升序）
  Round 2  贪心前向搜索（从 ~98 项项池按 A 区空间分块 CV 逐步选入，直到不再改善或触复杂度上限）
  Round 3  局部修订（以当前最优为起点，做「加项 / 换项」爬山——对应 §4.3 的"修订或放弃"）

本脚本**不访问 C 区或全域数据**（由 sandbox/access_guard.py 强制）。
输出写入 sandbox_root/work/s03/（发现侧唯一可写区），供沙箱外的冻结/汇总步骤读取。

用法：
  PAID_ACTOR="Discovery Agent" python3 stage03_discovery/scripts/s03_01_run_sandboxed.py \
        stage03_discovery/scripts/s03_02_symreg_search.py
"""
import os, sys, json, time
_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
S02 = os.path.join(os.path.dirname(S03), 'stage02_platform')
for p in (os.path.join(S03, 'agents'), os.path.join(S02, 'agents'),
          os.path.join(S02, 'lib'), os.path.join(S02, 'sandbox')):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd
import paths02 as P
import log_tool
import access_guard as G
import model as M
import core as CORE
import roles as R

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')
WORK = os.path.join(P.SANDBOX_WORK, 's03')
os.makedirs(WORK, exist_ok=True)

# 规范运行标签：append-only 日志会保留全部开发期迭代，用该标签标出**最终规范运行**的起点。
RUN_TAG = os.environ.get('S03_RUN_TAG', 'S03-canonical')

# 预算（**严于**冻结上限）：冻结上限为 每轮≤50 候选 / 总 fit 5000 / 冻结≤8
BUDGET = dict(per_round_max_candidates=50, total_fit_budget=5000, freeze_max=8,
              greedy_prescreen='全部项池（无预筛）', refine_prescreen=12, refine_max_evals=120,
              note='遵守 Stage 01 冻结预算；Rounds 1–3 全部在守卫下运行。')


def load_inputs():
    A = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_A_open.csv'))
    B = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'zone_B_devval.csv'))
    m = pd.read_csv(os.path.join(P.SANDBOX_INPUTS, 'spatial_mask.csv'))
    A = A.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    B = B.merge(m[['Grid_ID', 'row', 'col']], on='Grid_ID', how='left')
    hc = json.load(open(os.path.join(P.S01, 'constraints', 'hard_constraints.json'), encoding='utf-8'))
    return A, B, hc.get('measured_domain', {})


def evaluate_candidate(cand, A, B, folds, measured, ba_cv, mdl_ba, round_name):
    """把候选依次交给四个发现侧角色：Discovery → Experiment → Falsification → Physics Auditor。"""
    cand = R.experiment_dev(cand, A, folds)
    cand['dev_evidence']['delta_cv_vs_baselineA'] = ba_cv - cand['dev_evidence']['cv_rmse']
    cand['dev_evidence']['beats_baselineA'] = bool(cand['dev_evidence']['delta_cv_vs_baselineA'] > 0)
    cand = R.falsify(cand, B, baseline_model=mdl_ba)
    cand = R.audit(cand, measured)

    if cand['physics_audit']['verdict'] != 'pass':
        cand['status'] = 'rejected_physics'
    elif cand['falsification']['verdict'] != 'not_fooled':
        cand['status'] = 'rejected_controls'
    elif cand['dev_evidence']['beats_baselineA']:
        cand['status'] = 'passed_dev_gain'
    else:
        cand['status'] = 'passed_dev_nogain'
    cand['round'] = round_name
    log_tool.append(cand['id'], 'candidate_verdict', logpath=LOG,
                    agent='Experiment Agent', round=round_name, status=cand['status'],
                    cv_rmse=cand['dev_evidence']['cv_rmse'],
                    delta_vs_baselineA=cand['dev_evidence']['delta_cv_vs_baselineA'],
                    delta_B_vs_baselineA=cand['falsification']['delta_B_vs_baselineA'],
                    term_scale_max=cand['dev_evidence']['term_scale_max'],
                    physics=cand['physics_audit']['verdict'],
                    controls=cand['falsification']['verdict'])
    print('[s03] %-20s %-18s cv=%.4f dA=%+.4f dB=%s pa=%s' % (
        cand['id'], cand['status'], cand['dev_evidence']['cv_rmse'],
        cand['dev_evidence']['delta_cv_vs_baselineA'],
        ('%+.4f' % cand['falsification']['delta_B_vs_baselineA'])
        if cand['falsification']['delta_B_vs_baselineA'] is not None else 'NA',
        cand['physics_audit']['verdict']))
    return cand


def main():
    A, B, measured = load_inputs()
    log_tool.append('Platform', 'run_start', logpath=LOG, run_tag=RUN_TAG,
                    note='Stage 03 沙箱内自主探索循环（append-only；开发期迭代亦保留在链上）')
    log_tool.append('Platform', 'budget_declared', logpath=LOG, **BUDGET)
    log_tool.append('Platform', 'observe_data', logpath=LOG,
                    n_A=int(len(A)), n_B=int(len(B)), n_vars=len(CORE.VARS),
                    vars=CORE.VARS)

    # 空间分块 CV 折（冻结规格：分块=连通簇，块数≥5）
    folds = CORE.spatial_folds(A, k=5, seed=20260924)
    fold_sizes = [int((folds == f).sum()) for f in np.unique(folds)]
    log_tool.append('Experiment Agent', 'spatial_folds', logpath=LOG,
                    k=int(len(np.unique(folds))), sizes=fold_sizes,
                    rule='连通簇（k-means on row/col, seed 20260924）')
    print('[s03] folds:', fold_sizes)

    # 参照：冻结 Baseline A（在 A 区拟合 + A 区空间分块 CV）
    ba_terms = [CORE.var(v) for v in M.BASELINE_A_TERMS]
    ba_cv, ba_per = CORE.pooled_cv_rmse(A, ba_terms, folds)
    G.count_fit(1)
    mdl_ba = M.fit_linear(A, M.BASELINE_A_TERMS)
    rmse_B_ba = M.rmse(B[M.Y], M.predict(mdl_ba, B))
    log_tool.append('Experiment Agent', 'baselineA_ref', logpath=LOG,
                    cv_rmse=ba_cv, per_fold=ba_per, rmse_B=rmse_B_ba,
                    terms=M.BASELINE_A_TERMS)
    print('[s03] Baseline A: dev CV RMSE=%.4f | B RMSE=%.4f' % (ba_cv, rmse_B_ba))

    registry = []

    # ------------------------------------------------------------ Round 1：预注册假设议程
    log_tool.append('Platform', 'round_start', logpath=LOG, round='R1_agenda',
                    n=len(CORE.hypotheses()))
    for spec in CORE.hypotheses():
        cand = R.discovery_propose(spec['hid'], spec['name'], spec['terms'], spec['claim'])
        cand = evaluate_candidate(cand, A, B, folds, measured, ba_cv, mdl_ba, 'R1_agenda')
        registry.append(cand)
        if len(registry) >= BUDGET['per_round_max_candidates']:
            break

    # ------------------------------------------------------------ Round 2：贪心前向搜索（全项池，无预筛）
    n_pool = len(CORE.term_pool())
    log_tool.append('Platform', 'round_start', logpath=LOG, round='R2_greedy',
                    prescreen=n_pool, note='全项池前向选择，无相关性预筛（避免预筛偏置）')
    g_terms, g_trace = CORE.greedy_terms(A, folds, K=99, prescreen=n_pool)
    adds = [e for e in g_trace if e.get('action') == 'add']
    log_tool.append('Experiment Agent', 'greedy_search', logpath=LOG, round='R2_greedy',
                    n_terms=len(g_terms), trace=g_trace, expr=CORE.fmt_terms(g_terms))
    print('[s03] greedy -> %d terms, %s' % (len(g_terms), [(e['n_terms'], round(e['cv_rmse'], 4)) for e in adds]))
    if g_terms:
        spec = dict(hid='H10-GREEDY', name='贪心前向搜索（%d 项，全池）' % len(g_terms), terms=g_terms,
                    claim='由项池按 A 区空间分块 CV 逐步选出的 %d 项组合，对 LST 的描述优于更简模型。'
                          % len(g_terms))
        cand = R.discovery_propose(spec['hid'], spec['name'], spec['terms'], spec['claim'])
        cand['search_trace'] = g_trace
        cand = evaluate_candidate(cand, A, B, folds, measured, ba_cv, mdl_ba, 'R2_greedy')
        registry.append(cand)

    # Round 2b：最简前缀（parsimony）——贪心路径上**最早优于基线**的前缀。
    # 科学动机：若增益主要来自前几项，则更简模型在解释力/稳定性上更可取（奥卡姆）。
    prefix_terms = None
    for e in adds:
        if e['cv_rmse'] < ba_cv:
            n = e['n_terms']
            prefix_terms = [x['term_ast'] for x in adds[:n]]
            break
    if prefix_terms and len(prefix_terms) < len(g_terms):
        spec = dict(hid='H10P-GREEDY-MIN', name='贪心最简前缀（%d 项）' % len(prefix_terms),
                    terms=prefix_terms,
                    claim='贪心路径上最早优于冻结基线的 %d 项组合（同增益下的最简模型）。' % len(prefix_terms))
        cand = R.discovery_propose(spec['hid'], spec['name'], spec['terms'], spec['claim'])
        cand['search_trace'] = [x for x in adds[:len(prefix_terms)]]
        cand['parsimony_note'] = '由 H10-GREEDY 贪心轨迹截取最简前缀（CV 首次 < Baseline A）'
        cand = evaluate_candidate(cand, A, B, folds, measured, ba_cv, mdl_ba, 'R2_greedy')
        registry.append(cand)
        print('[s03] parsimonious prefix -> %d terms' % len(prefix_terms))

    # ------------------------------------------------------------ Round 3：局部修订（以当前最优为起点）
    pool = [c for c in registry if c['status'] == 'passed_dev_gain']
    seed = min(pool, key=lambda c: c['dev_evidence']['cv_rmse']) if pool else registry[0]
    log_tool.append('Platform', 'round_start', logpath=LOG, round='R3_refine',
                    seed=seed['id'], seed_expr=seed['expression']['expr'],
                    max_evals=BUDGET['refine_max_evals'])
    print('[s03] refine seed %s (%s)' % (seed['id'], seed['expression']['expr']))
    r_terms, r_trace = CORE.local_refine(A, folds, seed['expression']['terms'],
                                         prescreen=BUDGET['refine_prescreen'],
                                         max_evals=BUDGET['refine_max_evals'])
    log_tool.append('Experiment Agent', 'local_refine', logpath=LOG, round='R3_refine',
                    n_terms=len(r_terms), trace=r_trace, expr=CORE.fmt_terms(r_terms))
    print('[s03] refine -> %d terms, cv=%.4f' % (len(r_terms), r_trace[-1].get('cv_rmse', float('nan'))))
    if CORE.fmt_terms(r_terms) != seed['expression']['expr']:
        spec = dict(hid='H11-REFINE', name='局部修订（%d 项）' % len(r_terms), terms=r_terms,
                    claim='在贪心候选基础上做加/换项修订所得的组合，对 LST 的描述优于其起点。')
        cand = R.discovery_propose(spec['hid'], spec['name'], spec['terms'], spec['claim'])
        cand['search_trace'] = r_trace
        cand = evaluate_candidate(cand, A, B, folds, measured, ba_cv, mdl_ba, 'R3_refine')
        registry.append(cand)

    # ------------------------------------------------------------ 汇总
    log_tool.append('Platform', 'round_end', logpath=LOG, round='ALL',
                    n_candidates=len(registry),
                    n_passed_gain=sum(1 for c in registry if c['status'] == 'passed_dev_gain'))
    st = G.shutdown('symreg_search_done')
    log_tool.append('Platform', 'run_end', logpath=LOG, run_tag=RUN_TAG,
                    n_candidates=len(registry), guard=st)
    out = dict(run_tag=RUN_TAG, ran_at=time.strftime('%Y-%m-%dT%H:%M:%S'),
               budget=BUDGET, baselineA_dev_cv_rmse=ba_cv, baselineA_per_fold=ba_per,
               baselineA_rmse_B=rmse_B_ba,
               folds=dict(k=int(len(np.unique(folds))), sizes=fold_sizes),
               rounds=dict(R1_agenda=len([c for c in registry if c['round'] == 'R1_agenda']),
                           R2_greedy=len([c for c in registry if c['round'] == 'R2_greedy']),
                           R3_refine=len([c for c in registry if c['round'] == 'R3_refine'])),
               greedy_trace=g_trace, refine_trace=r_trace, refine_seed=seed['id'],
               n_candidates=len(registry), candidates=registry, guard=st)
    with open(os.path.join(WORK, 'candidate_registry.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('[s03] wrote', os.path.join(WORK, 'candidate_registry.json'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
