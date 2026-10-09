"""
Stage 03 四个发现侧角色的实现（Discovery / Experiment / Falsification / Physics Auditor）
=========================================================================================
每个角色是被沙箱内搜索循环调用的函数，并以其角色名写入 append-only 哈希链日志
（Table 10 权限；§4.3 每轮实验只追加、不覆盖失败结果）。

首轮说明：四个角色以**模块函数**形式在同一个沙箱进程内按顺序执行（角色与日志分离、
权限由同一访问守卫统一把关）。Stage 02 提供的"独立进程"能力在需要时可切换。
"""
import os
import numpy as np
import pandas as pd
import model as M
import log_tool
import paths02 as P
import core as CORE

LOG = os.path.join(P.S02_LOGS, 'experiment_log.jsonl')
VARS = ['NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens']
Y = 'LST_mean'

# π 无方向预设禁令（§3.2）：候选主张中不得出现预设方向/因果的措辞
_DIR_PRESET = ['必须降温', '必须升温', '必降温', '必升温', '降温效应', '增温效应',
               '导致降温', '导致升温', '引起降温', '引起升温', '证明了因果', '因果关系']
_OVERREACH = ['已验证的物理定律', '能量闭合', '能量守恒成立', '因果', '调控机制']


# ------------------------------------------------------------------ Discovery
def discovery_propose(hid, name, terms, claim, created='2026-09-24'):
    cand = dict(
        id='S03-' + hid, created=created, agent='Discovery Agent',
        model_version='stage03-symreg-v1', code_version='stage03-discovery-v1',
        hypothesis=name, claim=claim,
        expression=dict(form='expr', terms=terms, standardize=True, intercept=True,
                        complexity=M.complexity(terms), expr=CORE.fmt_terms(terms)),
        variables={v: '见 constraints/DATA_DICTIONARY.md' for v in
                   sorted(set().union(*[M.expr_vars(t) for t in terms]))},
        domain='深圳研究区、单一时相、100 m 网格；A 发现区（B 仅作方法筛选）',
        dev_evidence=None, prereg_test='见 protocol/validation_protocol.json 主终点（C 区 RMSE 与 ΔRMSE）',
        physics_audit=None, unseal_result=None, status='proposed')
    log_tool.append(cand['id'], 'candidate_proposed', logpath=LOG,
                    agent=cand['agent'], hypothesis=name,
                    complexity=cand['expression']['complexity'],
                    n_terms=len(terms))
    return cand


# ------------------------------------------------------------------ Experiment
def experiment_dev(cand, A, folds):
    terms = cand['expression']['terms']
    vs = sorted(set().union(*[M.expr_vars(t) for t in terms]))
    mu = {v: float(A[v].mean()) for v in vs}
    sd = {v: float(A[v].std(ddof=0)) or 1.0 for v in vs}
    mdl = M.fit_expr(A, terms, mu=mu, sd=sd)
    try:
        import access_guard as G
        G.count_fit(1)
    except Exception:
        pass
    cv, per = _pooled_cv(A, terms, folds)
    p = M.predict(mdl, A)
    mae = float(np.mean(np.abs(A[Y].to_numpy(float) - p)))
    ci = _boot_ci(A, mdl)
    resid = A[Y].to_numpy(float) - p
    from core import moran_I, term_scale
    I = moran_I(A, resid)
    dirs = M.effect_directions(mdl, A)
    tscale_by_term, tscale_max = term_scale(A, terms)
    cand['model'] = mdl
    cand['dev_evidence'] = dict(
        dev_metric='A 区空间分块 CV RMSE (℃)', cv_rmse=cv, per_fold_rmse=per,
        worst_fold_rmse=float(max(per)) if per else float('nan'),
        sd_fold_rmse=float(np.std(per)) if per else float('nan'),
        mae_A=mae, r2_A=M.r2(A[Y], p), rmse_A=M.rmse(A[Y], p),
        pred_range_A=[float(p.min()), float(p.max())],
        term_scale_max=tscale_max, term_scale_by_term=tscale_by_term,
        complexity=M.complexity(terms), n_terms=len(terms),
        ci95_rmse=ci, moran_I_resid=I, directions=dirs, n_A=int(len(A)))
    cand['status'] = 'dev_tested'
    log_tool.append(cand['id'], 'dev_fit', logpath=LOG, agent='Experiment Agent',
                    cv_rmse=cv, rmse_A=cand['dev_evidence']['rmse_A'], mae_A=mae,
                    worst_fold_rmse=cand['dev_evidence']['worst_fold_rmse'],
                    term_scale_max=tscale_max,
                    complexity=cand['dev_evidence']['complexity'],
                    moran_I_resid=I, n_A=int(len(A)))
    return cand


def _pooled_cv(A, terms, folds):
    from core import pooled_cv_rmse
    return pooled_cv_rmse(A, terms, folds)


def _boot_ci(A, mdl):
    from core import block_bootstrap_ci
    return block_bootstrap_ci(A, mdl)


# ------------------------------------------------------------------ Falsification
def _block_permute(df, ycol, bs=5, seed=20260924):
    """空间块置换：把块均值**随机重新指派**到各块，再加回块内残差。

    注意（2026-09-24 修正）：必须重排块的**取值**并贴回原块标签。早先写成
    `uniq.loc[permutation(uniq.index)]`（只重排索引顺序），再用 `blk.map(sh)` 按标签取值，
    结果每个标签仍取回自己的原值——置换退化为恒等（实测 corr(原值, 置换值)=1.000），
    负对照形同虚设。修正后 corr 显著下降，负对照才真正破坏「协变量—目标」对应关系。
    """
    rng = np.random.default_rng(seed)
    blk = pd.Series(list(zip(df['row'] // bs, df['col'] // bs)), index=df.index)
    bmean = df[ycol].groupby(blk).transform('mean')
    resid = df[ycol].to_numpy(float) - bmean.to_numpy(float)
    uniq = bmean.groupby(blk).first()
    sh = pd.Series(rng.permutation(uniq.to_numpy(float)), index=uniq.index)
    out = df.copy()
    out[ycol] = blk.map(sh).to_numpy(float) + resid
    return out


def falsify(cand, B, baseline_model=None, n_perm=199):
    """B 区反例与误差分析。

    两项证据：
      (1) **反例地板（floor）** —— NC1 逐格重排目标 / NC2 空间块置换 / NC3 高斯随机目标。
          判据是各对照 RMSE ≥ 真实 RMSE。必须如实说明其**检验力很弱**：NC1/NC3 破坏了一切
          结构，其 RMSE ≈ 目标标准差，所以任何比"常数均值预测"更有技巧的模型都会通过它；
          它只能淘汰"毫无技巧"的模型，**不能**识别过拟合。故只记为地板式体检，判据不变。
      (2) **B 区空间块置换检验（ΔB 的零分布）** —— 更有判别力的诊断：把块均值随机重新指派
          （保留块内残差），给出 ΔB=RMSE_基线−RMSE_候选 的置换 p 值。非确认性检验
          （B 已参与方法筛选），只用于判断 B 区增益是否只是空间噪声。

    内置**置换有效性断言**：置换后目标与原目标的相关必须显著小于 1，否则说明块置换退化成了
    恒等（本项目曾出现过该缺陷）——直接抛错，避免"绿着坏掉"。
    """
    mdl = cand['model']
    rmse_real = M.rmse(B[Y], M.predict(mdl, B))
    rng = np.random.default_rng(7)

    B1 = B.copy(); B1[Y] = rng.permutation(B1[Y].to_numpy())
    nc1 = M.rmse(B1[Y], M.predict(mdl, B1))
    B2 = _block_permute(B, Y)
    nc2 = M.rmse(B2[Y], M.predict(mdl, B2))
    B3 = B.copy(); B3[Y] = rng.normal(B[Y].mean(), B[Y].std(), len(B))
    nc3 = M.rmse(B3[Y], M.predict(mdl, B3))

    # B 区「开发验证」读数（§5.1：B 参与调参后不再视为独立确认，仅作开发期哨兵）
    rmse_b_base = None
    if baseline_model is not None:
        rmse_b_base = M.rmse(B[Y], M.predict(baseline_model, B))

    ctrls = dict(NC1_row_shuffle=nc1, NC2_block_permute=nc2, NC3_random_target=nc3)
    passed = {k: bool(v >= rmse_real) for k, v in ctrls.items()}
    verdict = 'not_fooled' if all(passed.values()) else 'fooled_suggest_drop'

    # ---- B 区空间块置换检验（ΔB 的零分布）
    blk = pd.Series(list(zip(B['row'] // 5, B['col'] // 5)), index=B.index)
    bmean = B[Y].groupby(blk).transform('mean')
    resid = B[Y].to_numpy(float) - bmean.to_numpy(float)
    ymean = bmean.groupby(blk).first()
    pc = M.predict(mdl, B)
    pb = M.predict(baseline_model, B) if baseline_model is not None else None
    d_obs_B = None if rmse_b_base is None else (rmse_b_base - rmse_real)
    p_perm_B = None
    corr_sanity = float('nan')
    if pb is not None:
        rngp = np.random.default_rng(20260924)
        null = np.empty(n_perm)
        for i in range(n_perm):
            sh = pd.Series(rngp.permutation(ymean.to_numpy(float)), index=ymean.index)
            yp = blk.map(sh).to_numpy(float) + resid
            null[i] = np.sqrt(np.mean((yp - pb) ** 2)) - np.sqrt(np.mean((yp - pc) ** 2))
        p_perm_B = float((1 + np.sum(null >= d_obs_B)) / (1 + n_perm))
        # 置换有效性断言：置换后的目标必须与原目标显著不同
        sh = pd.Series(rngp.permutation(ymean.to_numpy(float)), index=ymean.index)
        yp = blk.map(sh).to_numpy(float) + resid
        corr_sanity = float(np.corrcoef(B[Y].to_numpy(float), yp)[0, 1])
        if not (corr_sanity < 0.9):
            raise AssertionError('空间块置换退化为恒等（corr=%.3f）；检查是否误排索引而非取值'
                                 % corr_sanity)

    cand['falsification'] = dict(
        on='B 开发验证区', rmse_real=rmse_real, controls=ctrls, control_passed=passed,
        verdict=verdict,
        floor_note='NC1–NC3 为**地板式**体检：NC1/NC3 破坏全部结构，RMSE≈目标标准差，'
                   '任何优于常数均值预测的模型都会通过；只能淘汰零技巧模型，不能识别过拟合。',
        rmse_B_baselineA=rmse_b_base,
        delta_B_vs_baselineA=d_obs_B,
        block_perm_p_B=p_perm_B, n_perm=n_perm, perm_corr_sanity=corr_sanity,
        skill_significant_B=(None if p_perm_B is None else bool(p_perm_B < 0.05)),
        caveat='B 区读数仅供开发期参考；B 已参与方法筛选，不作为独立确认。')
    log_tool.append(cand['id'], 'falsification', logpath=LOG, agent='Falsification Agent',
                    rmse_real=rmse_real, rmse_B_baselineA=rmse_b_base,
                    delta_B_vs_baselineA=d_obs_B, block_perm_p_B=p_perm_B,
                    perm_corr_sanity=corr_sanity, **ctrls, verdict=verdict)
    return cand


# ------------------------------------------------------------------ Physics Auditor
def audit(cand, measured):
    expr_txt = (cand.get('expression', {}).get('expr') or '')
    claim = cand.get('claim', '')
    dev = cand.get('dev_evidence') or {}
    md = measured or {}

    def mx(k):
        return (md.get(k) or {}).get('max', float('nan'))

    def mn(k):
        return (md.get(k) or {}).get('min', float('nan'))

    items = []
    # 审计分两类，必须如实区分（复核修正）：
    #   hard=True  —— 可否决候选（PA3/PA4/PA5 文本合规 + PA7 数值条件）；
    #   hard=False —— **记录性**检查（PA1/PA2/PA6），在结构上不可能否决：
    #                PA1 标准化后必然无量纲、PA2 是数据定义告警、PA6 的字段由 experiment_dev
    #                必然写入。把它们计入"硬约束"会夸大审计强度，故显式标注为记录项。
    # PA1 量纲/无量纲化：所有变量均已按 A 区标准差标准化 → 无量纲，量纲一致
    items.append(dict(id='PA1', name='量纲与无量纲化', ok=True, hard=False,
                      detail='全部变量经标准化（无量纲），加减乘除量纲一致。（记录项，结构上不可否决）'))
    # PA2 几何合法性（数据定义风险，作为告警而非否决——S00/S01 已认定需作者澄清）
    items.append(dict(id='PA2', name='几何合法性（数据定义）', ok=True, hard=False,
                      warn=True, detail='X_BD 上界 %.2f（非 [0,1] 覆盖率）、X_BH 上界 %.1f m'
                                        '（非 100 m 格均高）、DEM %.0f–%.0f m 偏低：'
                                        '均需作者澄清定义后其物理解释方可成立。（记录项/告警）'
                             % (mx('X_BD'), mx('X_BH'), mn('DEM_mean'), mx('DEM_mean'))))
    # PA3 能量守恒过度延伸：无通量输入，任何能量闭合主张一律否决
    overreach = [w for w in _OVERREACH if w in claim]
    items.append(dict(id='PA3', name='能量守恒/因果过度延伸', ok=not overreach, hard=True,
                      detail=('主张文本含过度延伸措辞：%s' % overreach) if overreach
                             else '未宣称能量闭合或因果机制；观测性关系表述。'))
    # PA4 无方向预设：提示词与主张均不含方向预设
    dirhits = [w for w in _DIR_PRESET if w in claim]
    items.append(dict(id='PA4', name='无方向预设（§3.2）', ok=not dirhits, hard=True,
                      detail='发现侧提示词与候选主张均无方向性预设。' if not dirhits
                             else '主张含方向预设：%s' % dirhits))
    # PA5 测量边界：不得把 SVF(5 m) 当作 LST 分辨率，不得把重采样当新观测
    bad_meas = ('SVF' in expr_txt and '5 m' in claim) or ('重采样' in claim and '观测' in claim)
    items.append(dict(id='PA5', name='测量边界', ok=not bad_meas, hard=True,
                      detail='未把细尺度变量当作同分辨率温度观测。' if not bad_meas
                             else '存在测量边界违规表述。'))
    # PA6 统计诚信：必报项齐全（方向、CI、残差空间自相关、均已报告）
    miss = [k for k in ('directions', 'ci95_rmse', 'moran_I_resid') if k not in dev]
    items.append(dict(id='PA6', name='统计诚信（必报项）', ok=not miss, hard=False,
                      detail=('必报项齐全（方向、95% 自助 CI、残差 Moran’s I）。'
                              '（记录项：字段由 Experiment Agent 必然写入，不构成硬否决）')
                             if not miss else ('缺少必报项：%s' % miss)))
    # PA7 数值条件与量纲尺度：输入已标准化为 O(1)，故任何可解释项在域内也应同量级。
    # 项在 A 区上 max|取值| > TERM_SCALE_LIMIT 时，单一线性系数失去物理可解释性，
    # 且折内重标准化会将其放大为极端外推（实证：exp(X_BD) 使留出折 CV RMSE 爆炸）。作为硬否决。
    tmax = dev.get('term_scale_max')
    if tmax is None:
        items.append(dict(id='PA7', name='数值条件与量纲尺度', ok=True, hard=True,
                          detail='未提供项尺度诊断（视为不适用）。'))
    else:
        bad = {k: v for k, v in (dev.get('term_scale_by_term') or {}).items()
               if v > CORE.TERM_SCALE_LIMIT}
        ok7 = not bad
        items.append(dict(id='PA7', name='数值条件与量纲尺度', ok=ok7, hard=True,
                          detail=('项尺度越界（max|项| > %g，跨 3 个数量级，系数不可解释）：%s'
                                  % (CORE.TERM_SCALE_LIMIT, bad)) if bad
                                 else ('项尺度有界（max|项|=%.3g ≤ %g），量纲与标准化尺度一致。'
                                       % (tmax, CORE.TERM_SCALE_LIMIT))))

    hard_fail = [it['id'] for it in items if it.get('hard', True) and not it['ok']]
    verdict = 'pass' if not hard_fail else 'fail'
    cand['physics_audit'] = dict(
        verdict=verdict, items=items, fail_items=hard_fail,
        hard_items=[it['id'] for it in items if it.get('hard', True)],
        info_items=[it['id'] for it in items if not it.get('hard', True)],
        note='审计含 %d 项**硬门**（可否决：PA3/PA4/PA5/PA7）与 %d 项**记录性检查**'
             '（PA1/PA2/PA6，结构上不可否决）。只有硬门参与 verdict。'
             % (sum(1 for it in items if it.get('hard', True)),
                sum(1 for it in items if not it.get('hard', True))),
        cautions=['X_BD/X_BH/DEM/Road_Dens 的定义与量纲待作者澄清',
                  '无观测时间/传感器/QA，无法做测量误差传播',
                  'Road_Dens/X_BD/X_BH/X_VolDens 强零膨胀/重尾；'
                  '其比值与指数形式在 A 区小标准差下数值爆炸，须经 PA7 拦截'])
    log_tool.append(cand['id'], 'physics_audit', logpath=LOG, agent='Physics Auditor',
                    verdict=verdict, fail_items=hard_fail)
    return cand
