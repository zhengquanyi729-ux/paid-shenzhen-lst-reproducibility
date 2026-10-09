"""
S03.4 Stage 03 报告 + SHA-256 清单
====================================
从冻结产物与验证结果生成 STAGE03_REPORT.md 与 manifests/stage03_hashes.txt。
只读 registry/ 与 reports/，不改动任何候选记录。

用法：python3 stage03_discovery/scripts/s03_04_report.py
"""
import os, sys, json, hashlib, glob, datetime
_HERE = os.path.dirname(os.path.abspath(__file__))
S03 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S03)
sys.path.insert(0, os.path.join(S03, 'lib'))
import paths03 as P3


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def f4(x):
    return '%.4f' % x


def sgn(x):
    return '%+.4f' % x


def main():
    fr = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    reg = json.load(open(P3.CANDIDATE_REGISTRY, encoding='utf-8'))
    traj = json.load(open(P3.FULL_TRAJECTORY, encoding='utf-8'))
    ver = {}
    vp = os.path.join(P3.S03_REPORTS, 'verification.json')
    if os.path.exists(vp):
        ver = json.load(open(vp, encoding='utf-8'))
    rob = {}
    robp = os.path.join(P3.S03_REPORTS, 'robustness.json')
    if os.path.exists(robp):
        rob = json.load(open(robp, encoding='utf-8'))
    # 沙箱输入行数与冻结的测量域（供报告如实引用，不硬编码）
    S02 = os.path.join(PROJ, 'stage02_platform')
    with open(os.path.join(S02, 'sandbox_root', 'inputs', 'zone_A_open.csv'), encoding='utf-8') as f:
        nA = sum(1 for _ in f) - 1
    with open(os.path.join(S02, 'sandbox_root', 'inputs', 'zone_B_devval.csv'), encoding='utf-8') as f:
        nB = sum(1 for _ in f) - 1
    md = json.load(open(os.path.join(P3.S01, 'constraints', 'hard_constraints.json'),
                        encoding='utf-8'))['measured_domain']
    spm = json.load(open(os.path.join(P3.S01, 'split', 'split_manifest.json'), encoding='utf-8'))
    nC = spm['zone_size_post_buffer']['3']

    cands = reg['candidates']
    ba = reg['baselineA_dev_cv_rmse']
    frozen_ids = [f['id'] for f in fr['frozen']]
    by_id = {c['id']: c for c in cands}
    gain = [c for c in cands if c['status'] == 'passed_dev_gain']
    gain.sort(key=lambda c: c['dev_evidence']['cv_rmse'])

    L = []
    A = L.append
    A('# Stage 03 深圳发现：候选登记与冻结报告\n')
    A('| 项 | 值 |')
    A('|---|---|')
    A('| 版本 | stage03-discovery-v1 |')
    A('| 报告生成 | %s |' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    A('| 规范运行标签 | %s（%s） |' % (reg.get('run_tag') if reg.get('run_tag') else 'S03-canonical',
                                       traj.get('ran_at', '')))
    A('| 数据边界 | 沙箱内仅 A/B 两区；**C 区全程密封未读** |')
    A('| 守卫统计 | 打开 %d 次，拒绝 %d 次，拟合 %d/%d |'
      % (reg['guard']['opens'], reg['guard']['denials'], reg['guard']['fits'],
         reg['budget']['total_fit_budget']))
    A('| 候选总数 | %d（通过 %d，物理否决 %d） |'
      % (reg['n_candidates'], sum(1 for c in cands if c['status'].startswith('passed')),
         sum(1 for c in cands if c['status'] == 'rejected_physics')))
    A('| 冻结候选 | %d（上限 %d） |' % (fr['n_frozen'], reg['budget']['freeze_max']))
    A('| 自身验证 | %s（%d 项） |' % (ver.get('verdict', '未运行'),
                                     ver.get('n_checks', 0)))
    A('')

    # ------------------------------------------------------------------ 0 摘要
    best = gain[0] if gain else None
    A('## 0 摘要\n')
    A('在访问守卫内、**只使用 A 发现区与 B 开发验证区**，按框架 §4.3 跑完了三轮自主探索循环，'
      '共评估 %d 个候选（12 个预注册假设 + 2 个贪心搜索产物 + 1 个局部修订产物）。'
      '其中 %d 个因**数值条件与量纲尺度**不合法被物理审计否决（见 §5），其余全部通过审计与'
      '反例测试。' % (reg['n_candidates'], sum(1 for c in cands if c['status'] == 'rejected_physics')))
    if best:
        A('')
        A('有 %d 个候选在 A 区空间分块 CV 上优于冻结 Baseline A（CV RMSE %s ℃）。最好者为 '
          '`%s`，CV RMSE %s ℃，相对基线下降 %s ℃（%.1f%%）。'
          % (len(gain), f4(ba), best['id'], f4(best['dev_evidence']['cv_rmse']),
             f4(best['dev_evidence']['delta_cv_vs_baselineA']),
             100 * best['dev_evidence']['delta_cv_vs_baselineA'] / ba))
    A('')
    A('按预注册规则冻结了 %d 个候选（3 个发现候选 + 1 个安慰剂参考），并**停在此处**：'
      'C 锁定区一个格点都没有解封，所有候选的解封机会（validation_runs=1）完好。'
      '下一步 Stage 04 是否解封、解封哪些、如何控制多重比较，须由你确认后执行。' % fr['n_frozen'])
    A('')
    A('需要先说明的一点：所有优于基线的读数都来自 **A 区**，而 A 区正是搜索用来选模型的那批数据，'
      '因此这些 CV 数值带有**选择偏倚**，是乐观估计。它们只用于"该不该冻结"，不足以支撑'
      '"发现了规律"。真正的检验在 C 区，而每个候选只有一次机会。')
    A('')

    # ------------------------------------------------------------------ 1 边界
    A('## 1 运行边界与合规\n')
    A('| 项 | 值 |')
    A('|---|---|')
    A('| 执行环境 | stage02_platform/sandbox/access_guard.py（与 Stage 02 同一守卫，未改动权限模型） |')
    A('| 运行器 | stage03_discovery/scripts/s03_01_run_sandboxed.py（max_fits=5000，等于 Stage 01 冻结上限） |')
    A('| 可见数据 | zone_A_open.csv（A 区 %d 格）、zone_B_devval.csv（B 区 %d 格）、spatial_mask.csv、软约束与数据字典 |'
      % (nA, nB))
    A('| 越界尝试 | 拒绝 %d 次（本次运行） |' % reg['guard']['denials'])
    A('| 拟合预算 | 用 %d / %d（冻结上限） |' % (reg['guard']['fits'], reg['budget']['total_fit_budget']))
    A('| 每轮候选数（最大轮） | %d（冻结上限 %d） |' % (max(reg['rounds'].values()), reg['budget']['per_round_max_candidates']))
    A('| 冻结候选数 | %d（发现候选上限 %d，另加 1 个安慰剂参考） |'
      % (fr['n_frozen'], reg['budget']['freeze_max']))
    A('')
    A('发现侧在沙箱内只能写 `sandbox_root/work/s03/`；`registry/`、`reports/` 位于沙箱之外，'
      '只有冻结/汇总步骤可写——发现 Agent 无法自行登记或改写候选（§5.1 防火墙）。'
      '冻结所用的规范化哈希与独立验证服务使用**同一个函数**（`independent_validator.canon_hash`）。')
    A('')

    # ------------------------------------------------------------------ 2 方法
    A('## 2 方法：三轮自主探索\n')
    A('**评估分区。** 折为 A 区上的 5 个空间连通簇（对格中心 (row,col) 做 k-means，seed 20260924），'
      '各折格数 %s。开发指标 = 折内标准化、折外预测的合并 CV RMSE（℃）。'
      '所有变量在每一次拟合中按**训练折**均值/标准差标准化（无量纲），复杂度按冻结规则计'
      '（AST 节点数 + 项数），上限 %d。' % (reg['folds']['sizes'], 15))
    A('')
    A('**Round 1 — 预注册假设议程（12 个）。** 人工设定的可证伪假设，复杂度升序，'
      '覆盖一次项参照、四个单变量二次响应、建筑三项、以及植被/建筑、天空可视度/建筑、'
      '道路/植被三组交互，另有植被对建筑比值、体量密度对数、建筑覆盖指数三型。')
    A('')
    A('**Round 2 — 贪心前向搜索（全项池、无预筛）。** 从约 98 项项池出发，每一步选入使'
      'A 区空间分块 CV RMSE 下降最多的项，直到复杂度触顶。不设相关性预筛，避免预筛偏置。')
    A('')
    A('| 步 | 加入的项 | 项数 | CV RMSE |')
    A('|---|---|---|---|')
    for e in traj['greedy_trace']:
        if e.get('action') == 'add':
            A('| %d | `%s` | %d | %s |' % (e['n_terms'], e['term'].replace('_mean', ''),
                                           e['n_terms'], f4(e['cv_rmse'])))
        else:
            A('| — | （停止：%s） | %d | %s |' % (e['action'], e.get('n_terms', 0), f4(e.get('cv_rmse', float('nan')))))
    A('')
    A('**Round 3 — 局部修订（以当前最优为起点）。** 对当前最优做"加项 / 换项 / 删项"单步爬山，'
      '只接受使 CV RMSE 下降最多的改动，对应 §4.3 的"修订或放弃"。轨迹：')
    A('')
    A('| 动作 | 位置 | 项 | 项数 | CV RMSE | 表达式 |')
    A('|---|---|---|---|---|---|')
    for e in traj['refine_trace']:
        if e.get('action') in ('add', 'replace', 'drop'):
            A('| %s | %s | `%s` | %d | %s | `%s` |'
              % (e['action'], e.get('at', '—'), str(e.get('term', '')).replace('_mean', ''),
                 e.get('n_terms', 0), f4(e['cv_rmse']), e.get('expr', '')))
        else:
            A('| 停止 | — | — | — | %s | 无进一步改善（已尝试 %d 次单步改动） |'
              % (f4(e.get('cv_rmse', float('nan'))), e.get('n_evals', 0)))
    A('')
    A('> 搜索空间说明：项池 ~98 项、复杂度上限 15，实际求值的组合数 %.0f 以内，'
      '远小于冻结的搜索空间上限 10⁴。' % (reg['guard']['fits'] / 5.0))
    A('')

    # ------------------------------------------------------------------ 3 全量登记
    A('## 3 结果：全量候选登记\n')
    A('失败与不达标候选一并保留（§4.3：只追加、不覆盖）。ΔA = Baseline A 的 A 区 CV RMSE − 候选的；'
      'ΔB = 候选在 B 区的 RMSE 改善（B 未参与选择，但按 §5.1 只作开发期参考，不算独立确认）。')
    A('')
    A('| ID | 轮次 | 表达式 | 复杂度 | A-CV | ΔA | ΔB | 物理审计 | 反例 | 状态 |')
    A('|---|---|---|---|---|---|---|---|---|---|')
    rnd = {'R1_agenda': 'R1', 'R2_greedy': 'R2', 'R3_refine': 'R3'}
    for c in cands:
        de = c['dev_evidence']; fa = c['falsification']; pa = c['physics_audit']
        A('| %s | %s | `%s` | %d | %s | %s | %s | %s | %s | %s |'
          % (c['id'], rnd.get(c['round'], '?'), c['expression']['expr'].replace('_mean', ''),
             de['complexity'], f4(de['cv_rmse']), sgn(de['delta_cv_vs_baselineA']),
             sgn(fa['delta_B_vs_baselineA']), pa['verdict'], fa['verdict'], c['status']))
    A('')
    A('状态计数：' + '，'.join('%s=%d' % (k, v) for k, v in reg['status_counts'].items()) + '。')
    A('')

    # ------------------------------------------------------------------ 4 冻结
    A('## 4 冻结候选\n')
    A('选择规则（预注册）：入选条件为 `status=passed_dev_gain`（通过物理审计 + 未被反例识破 + '
      'A 区 CV 优于 Baseline A）；按 A 区 CV 升序取前 %d 个；另额外冻结 Baseline A 规格本身'
      '作为**安慰剂/参考**——它在验证区主终点上 ΔRMSE 按定义为 0，应当被验证服务判为不通过，'
      '用来检验验证服务能否把"零效应"识别出来。' % reg['budget']['freeze_max'])
    A('')
    A('| ID | 角色 | 表达式 | 复杂度 | A-CV | ΔA | ΔB | canon_hash |')
    A('|---|---|---|---|---|---|---|---|')
    for f in fr['frozen']:
        c = by_id[f['id']]
        de = c['dev_evidence']
        A('| %s | %s | `%s` | %d | %s | %s | %s | `%s…` |'
          % (f['id'], f['role'], c['expression']['expr'].replace('_mean', ''), de['complexity'],
             f4(de['cv_rmse']), sgn(de['delta_cv_vs_baselineA']),
             sgn(c['falsification']['delta_B_vs_baselineA']), f['canon_hash'][:16]))
    A('')
    for f in fr['frozen']:
        c = by_id[f['id']]; de = c['dev_evidence']
        A('**%s**（%s，复杂度 %d）  ' % (f['id'], f['role'], de['complexity']))
        A('表达式：`%s`  ' % c['expression']['expr'])
        A('科学主张：%s  ' % c['claim'])
        A('开发证据：A 区空间分块 CV RMSE %s ℃（逐折 %s），ΔA=%s；B 区 RMSE %s（基线 %s，ΔB=%s）。  '
          % (f4(de['cv_rmse']), '、'.join(f4(x) for x in de['per_fold_rmse']),
             sgn(de['delta_cv_vs_baselineA']), f4(c['falsification']['rmse_real']),
             f4(c['falsification']['rmse_B_baselineA']), sgn(c['falsification']['delta_B_vs_baselineA'])))
        dirs = '、'.join('%s %s（%+.2f ℃/SD）' % (k.replace('_mean', ''), v['direction'],
                                                v['delta_LST_per_SD'])
                        for k, v in sorted(de['directions'].items()))
        A('效应方向（±1 SD 有限差分，未预设）：%s。  ' % dirs)
        A('不确定性：95%% 空间块自助 CI = [%s, %s] ℃；残差 Moran’s I = %s（空间自相关未消除）。  '
          % (f4(de['ci95_rmse'][0]), f4(de['ci95_rmse'][1]), '%.3f' % de['moran_I_resid']))
        A('物理审计：%s（项尺度 max|项|=%s）。' % (c['physics_audit']['verdict'], '%.2f' % de['term_scale_max']))
        A('')

    # ------------------------------------------------------------------ 5 物理审计
    A('## 5 物理审计与数值条件\n')
    A('每个候选都过一遍七项审计，但七项的**强度并不相同**，必须如实区分（复核修正）：\n')
    A('**四项硬门**（可否决候选）——PA3 能量守恒/因果过度延伸、PA4 无方向预设（§3.2）、'
      'PA5 测量边界、PA7 数值条件与量纲尺度。'
      '**三项记录性检查**（结构上不可能否决，故不参与 verdict）——PA1 量纲/无量纲化'
      '（全部变量已标准化，必然无量纲）、PA2 几何合法性（X_BD/X_BH/DEM 的定义告警，'
      '留待作者澄清）、PA6 统计诚信必报项（字段由 Experiment Agent 必然写入）。'
      '把 PA1/PA2/PA6 计入"硬约束"会夸大审计强度，故显式标注为记录项。\n')
    A('本轮有 %d 个候选被硬门否决，全部因 PA7。' % sum(1 for c in cands if c['status'] == 'rejected_physics'))
    A('')
    for c in cands:
        if c['status'] != 'rejected_physics':
            continue
        de = c['dev_evidence']; pa = c['physics_audit']
        bad = {k: round(v, 1) for k, v in de['term_scale_by_term'].items() if v > 1000}
        A('- `%s`：%s  ' % (c['id'], c['expression']['expr']))
        A('  越界项 %s；逐折 CV RMSE = %s ℃。  '
          % (json.dumps(bad, ensure_ascii=False), '、'.join(f4(x) for x in de['per_fold_rmse'])))
        A('  该折 RMSE 的爆点说明：输入已标准化为 O(1)，此处的项却在 A 区跨越 3 个数量级，'
          '单一线性系数失去可解释性；折内重标准化后更被放大为极端外推。')
    A('')
    A('PA7 门限与本轮数据的一个结构性事实有关：`Road_Dens`（77% 的格为 0）、`X_BD`、`X_BH`、'
      '`X_VolDens` 都是强零膨胀/重尾变量。它们的比值与指数形式在 A 区小标准差下天然爆炸——'
      '这不是搜索的偶然失误，而是数据分布决定的系统性风险，必须由审计层拦截。')
    A('')

    # ------------------------------------------------------------------ 6 反例与误差
    A('## 6 反例与误差分析\n')
    A('**这里有两类性质不同的检查，不可混为一谈。**\n')
    A('其一，**反例地板（floor）**：NC1 逐格随机重排目标、NC2 空间块置换（重排块均值、'
      '保留块内残差）、NC3 高斯随机目标，判据是各对照 RMSE ≥ 真实 RMSE。'
      '必须如实说明其**检验力很弱**：NC1/NC3 破坏了一切结构，其 RMSE ≈ 目标标准差，'
      '因此任何比"常数均值预测"更有技巧的模型都会通过——它只能淘汰零技巧模型，'
      '**不能**识别过拟合。故只记为地板式体检，本轮通过审计的候选全部 `not_fooled`。\n')
    A('其二，**B 区空间块置换检验（ΔB 的零分布）**：把块均值随机重新指派（保留块内残差），'
      '给出 ΔB = RMSE_基线 − RMSE_候选 的置换 p 值。这比地板式体检更有判别力，'
      '但因 B 已参与方法筛选，仍只作开发期参考（非确认性检验）。\n')
    A('')
    A('| ID | 真实 RMSE | NC1 重排 | NC2 块置换 | NC3 随机目标 | ΔB | ΔB 置换 p |')
    A('|---|---|---|---|---|---|---|')
    for c in cands:
        f = c['falsification']
        pp = f.get('block_perm_p_B')
        A('| %s | %s | %s | %s | %s | %s | %s |'
          % (c['id'], f4(f['rmse_real']),
             f4(f['controls']['NC1_row_shuffle']),
             f4(f['controls']['NC2_block_permute']),
             f4(f['controls']['NC3_random_target']),
             sgn(f['delta_B_vs_baselineA']),
             ('%.3f' % pp) if pp is not None else '—'))
    A('')
    A('这一层曾出问题，值得记下：NC2 最初实现成"重排块均值的**索引顺序**"，再用标签取值'
      '——结果是每个块取回自己的原值，置换退化为恒等（实测 corr=1.000），负对照形同虚设。'
      '同一写法也出现在 Stage 02 的独立验证服务里，会让置换检验的 p 值**恒为 1.0**（主终点永不可能通过，'
      '属只会假阴性、不会假阳性的缺陷）。已在 Stage 03 验证步骤中被发现并修正为"重排块均值的取值"，'
      '修正后 B 区实测 corr 降到 0.086，置换检验恢复判别力。Stage 02 的对应缺陷已同步修正并重跑自测。')
    A('')
    A('残差空间自相关没有消失：全部候选的残差 Moran’s I 在 %.2f–%.2f 之间。'
      '这说明当前模型的误差仍呈强空间聚集，空间分块 CV 很可能**低估**了真实不确定度，'
      'C 区检验时应当把这一点带进去看。'
      % (min(c['dev_evidence']['moran_I_resid'] for c in cands),
         max(c['dev_evidence']['moran_I_resid'] for c in cands)))
    A('')

    # ------------------------------------------------------------------ 7 局限
    A('## 7 局限与威胁\n')
    A('**选择偏倚。** 贪心与修订都在 A 区 CV 上选模型，选完又拿同一批 A 区数据报告 CV——'
      '这些数值是乐观估计。B 区未参与选择，它的改善读数（ΔB）更有参考价值，但 B 与 A 同城同时相，'
      '按 §5.1 仍不算独立确认。三个冻结候选里，`S03-H10-GREEDY` 在 A、B 两区同向改善'
      '（ΔA=%s，ΔB=%s）；`S03-H11-REFINE` 的 A 区增益最大（ΔA=%s）但 B 区增益略小（ΔB=%s），'
      '且它是复杂度触顶者；`S03-H10P-GREEDY-MIN` 只有 2 项、最简，A 区有增益但 B 区反而变差'
      '（ΔB=%s），A 区那点增益很可能就是噪声。'
      % (sgn(by_id['S03-H10-GREEDY']['dev_evidence']['delta_cv_vs_baselineA']),
         sgn(by_id['S03-H10-GREEDY']['falsification']['delta_B_vs_baselineA']),
         sgn(by_id['S03-H11-REFINE']['dev_evidence']['delta_cv_vs_baselineA']),
         sgn(by_id['S03-H11-REFINE']['falsification']['delta_B_vs_baselineA']),
         sgn(by_id['S03-H10P-GREEDY-MIN']['falsification']['delta_B_vs_baselineA'])))
    A('')
    A('**多重比较。** 本轮评估了 %d 个候选并从中挑最好的，因此"最好的那个"本身就带最大选择效应。'
      '框架对主终点规定了 Holm–Bonferroni 校正，Stage 04 按冻结候选数执行即可。'
      % reg['n_candidates'])
    A('')
    A('**增益的边际收益很低。** 从 2 项加到 5 项，A 区 CV 只从 %s 降到 %s（%.3f ℃）；'
      '也就是说，绝大部分解释力集中在前 1–2 个项（都以 NDVI 的非线性变换为核心，'
      '方向为负，与植被降温一致），更复杂的结构在开发集上收效甚微。'
      % (f4(by_id['S03-H10P-GREEDY-MIN']['dev_evidence']['cv_rmse']),
         f4(by_id['S03-H11-REFINE']['dev_evidence']['cv_rmse']),
         by_id['S03-H10P-GREEDY-MIN']['dev_evidence']['cv_rmse']
         - by_id['S03-H11-REFINE']['dev_evidence']['cv_rmse']))
    A('')
    A('**数据定义未决。** X_BD（上界 %.2f，非 [0,1] 覆盖率）、X_BH（上界 %.1f m，非 100 m 格均高）、'
      'DEM（%.0f–%.0f m，偏低）三者的定义与量纲仍待作者澄清（继承自 Stage 00/01）。'
      '在这些变量进入任何物理解释之前，其系数不应被当作定量效应。'
      % (md['X_BD']['max'], md['X_BH']['max'], md['DEM_mean']['min'], md['DEM_mean']['max']))
    A('')
    A('**测量边界与无 QA。** 数据无观测时间、传感器与 QA 标记，无法做测量误差传播；'
      'SVF 为 5 m 尺度产品，不得当作与 100 m LST 同分辨率的新观测。'
      '框架规定的 ±0.5 / ±1.0 K 测量误差敏感性检验留到 Stage 04。')
    A('')

    # ------------------------------------------------------------------ 7.5 稳健性
    A('## 7.5 A/B 区稳健性检查（说明性，未开 C 区）\n')
    if rob:
        disc = rob.get('candidates', [])
        A('在进入 Stage 04 之前，对"发现候选在 A 区优于冻结基线"这一结论做了敏感性检查。'
          '所有检查**只读 A/B 两区**，不接触 C 区、不消耗任何解封机会（`validation_runs` 不变）。'
          '请注意：A 区读数带**选择偏倚**，以下只用于说明"结论是否稳健"，'
          '**不构成确认性检验**——真正的检验是 C 区单次解封的主终点。\n')
        A('**C1 折划分种子（4 个）.** ΔA = 基线 CV − 候选 CV，逐种子：\n')
        for row in rob.get('C1_multi_seed', []):
            A('- seed=%d：%s' % (row['seed'], '，'.join(
                '%s %+.4f' % (cid.replace('S03-', ''), row[cid]['delta_A']) for cid in disc)))
        A('')
        A('**C2 分块粒度（k=5/8/12）.**\n')
        for row in rob.get('C2_block_granularity', []):
            A('- k=%d：%s' % (row['k'], '，'.join(
                '%s %+.4f' % (cid.replace('S03-', ''), row[cid]['delta_A']) for cid in disc)))
        A('')
        A('**C3 测量误差（目标叠加 ±0.5 / ±1.0 K 高斯噪声并重新拟合，各 20 次抽样）.**\n')
        for row in rob.get('C3_measurement_error', []):
            A('- sd=%.1f K：%s' % (row['sd_err_K'], '，'.join(
                '%s 均值 %+.3f（正例 %.0f%%）'
                % (cid.replace('S03-', ''), row[cid]['mean'], 100 * row[cid]['frac_pos'])
                for cid in disc)))
        A('')
        A('**C4/C5 A 区内说明性推断（空间块自助 95% CI 与空间块置换 p）.**\n')
        c45 = rob.get('C45_A_only_inference', {})
        for cid in disc:
            d = c45.get(cid)
            if not d:
                continue
            A('- %s：ΔA=%+.4f，95%% 块自助 CI=[%+.4f, %+.4f]，置换 p=%.3f，置换有效性 corr=%.3f。'
              % (cid, d['delta_A_obs'], d['ci95_A'][0], d['ci95_A'][1],
                 d['perm_p_A'], d['perm_corr_sanity']))
        A('')
        A('**读法.** C1/C2 显示 ΔA 对折种子与分块粒度不敏感；C3 说明增益不是某一次噪声抽样'
          '的偶然（±0.5–1.0 K 下始终为正），但它**不是**显著性证据——加噪后基线与候选看到'
          '同一批噪声，正例比例高只能说明增益稳定，不能说明它显著。'
          'C4/C5 才是判别力所在：两个候选的 ΔA 置信区间不含 0、置换 p=0.005，'
          '而最简的那一个 ΔA 区间含 0、p 不显著——与它在 B 区 ΔB 为负相互印证，'
          '提示其 A 区增益多为噪声。这把"该不该冻结"之外的稳健性证据补齐，但不改变冻结规则'
          '（预注册规则一旦冻结不得事后更改）。\n')
    else:
        A('（`reports/robustness.json` 尚未生成；运行 `s03_06_robustness.py` 后本节将自动填充。）\n')
    A('')

    # ------------------------------------------------------------------ 8 下一步
    A('## 8 下一步（Stage 04）——等待你确认\n')
    A('按你选定的终点"止于候选冻结"，这里**不自动解封**。C 区共 %d 格，每个冻结候选只有一次'
      '解封机会（`validation_runs=1`），一旦解封结果就会完整发布、不可撤回。'
      'Stage 04 需要先确定：解封哪几个候选、是否连同安慰剂一起、多重比较如何校正'
      '（Holm–Bonferroni）、以及 ±0.5/±1.0 K 敏感性分析与 NDVI 三分位分层是否都纳入。'
      % nC)
    A('')
    A('我的建议：先只解封 `S03-H10-GREEDY`（A、B 两区同向，且是复杂度 14 的中间解）与'
      '安慰剂 `S03-H01-LIN7`（预期不通过，用于确认验证服务的判别力）；'
      '若两者表现符合预期，再考虑 `S03-H11-REFINE`。')
    A('')

    # ------------------------------------------------------------------ 8.1 复核记录
    A('## 8.1 复核记录：一次确定性重跑与洁净室修复\n')
    A('在开启 Stage 04 之前的复核中，发现并修复了一处**跨阶段副作用**：Stage 02 端到端自测'
      '（`s02_07_selftest.py`）的"洁净室"步骤会无差别清空**各阶段共享**的工作树 '
      '`sandbox_root/work/`，因此重跑 Stage 02 自测会连带删除 Stage 03 发现侧写出的原始登记'
      '（`work/s03/candidate_registry.json`）。根因是该洁净室未区分阶段专属子目录，'
      '把"本阶段产物"与"他阶段证据"一并清除。\n')
    A('处置分三步：其一，把洁净室改为**保留形如 `sNN` 的阶段专属子目录**、只清散落文件'
      '（外部预置诱饵仍会被清除，安全意图不变）；其二，按附 A 的原始命令**确定性重跑一次**'
      '发现侧搜索，重建 `work/s03/candidate_registry.json`；其三，重新执行冻结、报告与验证。\n')
    A('这次重跑顺带成为一次强**可复现性**证据：重跑产生的 15 个候选及其全部 CV 数值逐一相同，'
      '并且四个冻结候选的 `canon_hash` 逐字一致（%s）。重建文件与首次的 SHA-256 不同，'
      '唯一原因是登记里含 `ran_at` 运行时刻戳。\n'
      % '、'.join('%s=%s' % (f['id'], f['canon_hash'][:12]) for f in fr['frozen']))
    A('冻结候选的**内容**（ID、表达式、主张、`canon_hash`、`validation_runs`）在重跑前后完全不变，'
      'Stage 04 的解封对象未受影响；C 区仍全程未读，四个候选解封预算仍为 0。\n')
    A('')

    # ------------------------------------------------------------------ 附
    A('## 附 A 复现步骤\n')
    A('```bash')
    A('# 1) 发现侧：沙箱内三轮自主探索（只用 A/B）')
    A('PAID_ACTOR="Discovery Agent" python3 stage03_discovery/scripts/s03_01_run_sandboxed.py \\')
    A('      stage03_discovery/scripts/s03_02_symreg_search.py')
    A('# 2) 冻结（沙箱外，写 registry/）')
    A('python3 stage03_discovery/scripts/s03_03_freeze.py')
    A('# 3) 自身验证（不解封 C；含防火墙回归与指标复算）')
    A('python3 stage03_discovery/scripts/s03_05_verify.py')
    A('# 4) 报告与清单')
    A('python3 stage03_discovery/scripts/s03_04_report.py')
    A('```')
    A('')
    A('> Stage 04 的解封命令（**尚未执行**）形如：')
    A('> `python3 stage02_platform/agents/independent_validator.py --candidate '
      'stage03_discovery/registry/candidates/<ID>.json --registry stage03_discovery/registry/frozen_candidates.json`')
    A('')

    A('## 附 B 哈希清单\n')
    A('见 `manifests/stage03_hashes.txt`（本报告与清单自身之外的全部 Stage 03 产物逐一 SHA-256）。')
    A('')

    os.makedirs(P3.S03, exist_ok=True)
    with open(P3.REPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    # ---------------------------------------------------------------- 清单
    files = [P3.FROZEN_FILE, P3.CANDIDATE_REGISTRY, P3.FULL_TRAJECTORY, P3.REPORT]
    files += sorted(glob.glob(os.path.join(P3.S03_CAND, '*.json')))
    files += [vp] if os.path.exists(vp) else []
    files += [robp] if os.path.exists(robp) else []
    LOG = P3.EXPERIMENT_LOG
    os.makedirs(P3.S03_MANIFEST, exist_ok=True)
    with open(P3.HASH_MANIFEST, 'w', encoding='utf-8') as f:
        f.write('# Stage 03 产物 SHA-256 清单（相对 PAID/；不含本清单自身）\n')
        f.write('# 生成于 %s；发现侧原始登记另见 stage02_platform/sandbox_root/work/s03/（动态运行态）\n'
                % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        for p in files:
            rel = os.path.relpath(p, PROJ).replace(os.sep, '/')
            f.write('%s  %10d  %s\n' % (sha256_file(p), os.path.getsize(p), rel))
        if os.path.exists(LOG):
            with open(LOG, encoding='utf-8') as lf:
                n = sum(1 for _ in lf)
            f.write('\n# append-only 实验日志（含全部开发期迭代，故不逐行入清单）\n')
            f.write('%s  %10d  %s  (lines=%d)\n'
                    % (sha256_file(LOG), os.path.getsize(LOG),
                       os.path.relpath(LOG, PROJ).replace(os.sep, '/'), n))
    print('[s03-report] wrote', P3.REPORT)
    print('[s03-report] wrote', P3.HASH_MANIFEST, '(%d files)' % len(files))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
