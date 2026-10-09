"""
S01.4 四份预注册清单（Table 12 余下四项）
==========================================
目的：在开放正式发现环境之前，冻结 Agent 权限、实验协议、验证协议与代码清单，
使「发现—验证防火墙」在制度上可审计、在计算上可复算。

框架依据：
  Table 12 六清单——本脚本产出其中四项：
    Agent manifest      ：模型版本、系统提示词、工具白名单、权限与实验预算。
    Experiment protocol ：候选上限、开发指标、停止条件、失败记录策略。
    Validation protocol ：主终点、空间统计推断、多重比较、缺失处理与通过条件。
    Code manifest       ：依赖环境、数据变换脚本、候选模型代码及哈希。
  Table 10 五 Agent 分工与权限；Table 11 数据层权限；§5.3 解封原则；
  Table 13 七类检验；Table 14 对照组；§3.2 无方向预设（system prompt 约束）。

输出：
  agent/agent_manifest.json
  protocol/experiment_protocol.json
  protocol/validation_protocol.json
  manifest/code_manifest.json
  reports/s01_04_protocols.json / .md
"""
import sys, os, json, hashlib, glob, platform
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import config as C

VERSION = 'stage01-protocols-v1'
CREATED = '2026-09-24'
os.makedirs(os.path.join(C.S01, 'agent'), exist_ok=True)
os.makedirs(os.path.join(C.S01, 'protocol'), exist_ok=True)
os.makedirs(C.S01_MANIFEST, exist_ok=True)

hc = json.load(open(os.path.join(C.S01_CONSTRAINTS, 'hard_constraints.json'), encoding='utf-8'))
sm = json.load(open(os.path.join(C.S01, 'split', 'split_manifest.json'), encoding='utf-8'))
sa = json.load(open(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.json'), encoding='utf-8'))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ================================================================ 1) Agent manifest
AGENTS = [
    dict(agent='Discovery Agent', page='open_discovery',
         purpose='自主选择特征、尺度、假设与数学表达式，提出可证伪候选。',
         data_access=['A 发现区'],
         forbidden_access=['B 开发验证区（调参用，不下发目标）', 'C 锁定区目标值', '旧论文结论/相关矩阵'],
         tools=['numpy', 'pandas', '自写统计/特征脚本', '符号回归（白名单内）', 'matplotlib'],
         outputs=['候选科学发现登记表（Table 20 字段）']),
    dict(agent='Experiment Agent', page='experiment',
         purpose='编写实验代码、比较允许的方法、测量开发集表现，记录全部运行。',
         data_access=['A 发现区', 'B 开发验证区'],
         forbidden_access=['C 锁定区目标值'],
         tools=['numpy', 'pandas', '符号回归/ML（Table 14 Baseline A–D 口径）'],
         outputs=['可复算实验脚本', '开发指标表', 'append-only 实验日志']),
    dict(agent='Falsification Agent', page='falsification',
         purpose='寻找反例、空间混杂、伪相关与负对照；可建议放弃候选。',
         data_access=['A 发现区', 'B 开发验证区', '分区掩膜（row/col/zone）'],
         forbidden_access=['C 锁定区目标值'],
         tools=['空间置换', '分层/负对照构造', '残差诊断'],
         outputs=['反例清单', '负对照结果', '混杂诊断']),
    dict(agent='Physics Auditor', page='audit',
         purpose='独立审计量纲、几何、可计算物理约束及解释的过度延伸。',
         data_access=['constraints/hard_constraints.json', 'constraints/DATA_DICTIONARY.md', '全部分区掩膜'],
         forbidden_access=['C 锁定区目标值'],
         tools=['量纲检查', '几何合法性检查', '提示词禁用方向检查'],
         outputs=['物理审计表（通过/无法检验项 + 理由）']),
    dict(agent='Independent Validator', page='validation',
         purpose='独立进程持有 C 区目标值，验证后发布完整通过/失败结果，不执行发现 Agent 的调参请求。',
         data_access=['locked/zone_C_targets.csv', '已冻结候选登记'],
         forbidden_access=['不得向开发域回传 C 目标值（只发布聚合后的通过/失败与不确定性）'],
         tools=['验证协议固定脚本'],
         outputs=['完整通过/失败与不确定性报告']),
]

agent_manifest = dict(
    version=VERSION, created=CREATED,
    framework_ref='Table 10 / Table 11 / Table 12 Agent manifest',
    system_prompt_policy=dict(
        injected_files=['constraints/DATA_DICTIONARY.md', 'constraints/hard_constraints.json'],
        forbidden=[r for r in hc['no_direction_preset']],
        rule='系统提示词只注入数据字典、硬约束、计算预算与工具白名单；不得注入关系方向、函数形式、'
             '最优尺度、单一显著阈值或旧论文结论（§3.2）。',
        hash_required=True,
        audit='Physics Auditor 每轮检查提示词是否含禁用方向；prompt_sha256 记入候选登记。'),
    model_version=dict(
        note='Agent 所用基础模型版本须在 Stage 02 平台构建时声明并冻结于 Agent manifest；'
             '一旦冻结，M2 发现阶段中途不得更换（更换即视为新一轮，重走防火墙）。',
        declared=False),
    agents=AGENTS)

# ================================================================ 2) Experiment protocol
experiment_protocol = dict(
    version=VERSION, created=CREATED,
    framework_ref='Table 12 Experiment protocol；§4.3；Table 13；Table 14',
    candidate_cap=dict(
        per_round_max=50, total_fit_budget=5000,
        freeze_max=8,
        note='每轮最多 50 个候选进入开发评估；全项目 fit 预算 5000 次；最终冻结进入 C 区独立验证的候选 ≤ 8 个。'),
    dev_metrics=dict(
        primary='A 发现区空间分块交叉验证 RMSE（℃），分块=连通簇，块数≥5',
        secondary=['MAE', 'R²', 'AIC/BIC（同族比较）', '表达式复杂度（项数/参数量）'],
        must_report=['效应方向', '95% 自助置信区间', '残差空间自相关（Moran’s I of residuals）']),
    stopping_conditions=[
        '连续 200 次 fit 无开发指标改进',
        '累计 fit 达 5000 次预算',
        '冻结候选数达上限 8',
        '反例/混杂检验使所有候选被否决（允许以「暂无经证伪仍成立的候选」结束）'],
    failure_logging=dict(
        mode='append-only JSONL，禁止覆盖',
        fields=['candidate_id', 'timestamp', 'agent', 'prompt_sha256', 'code_sha256',
                'expr', 'vars', 'scale_r', 'dev_metric', 'dev_metric_value',
                'status(pass/fail/rejected)', 'reason', 'counterexamples'],
        path='logs/experiment_log.jsonl（Stage 02 创建）'),
    baselines=dict(
        A='预先指定变量的线性/GAM', B='RF/XGBoost + 可解释性',
        C='预设搜索空间的符号回归', D='无物理约束的自主 Agent',
        proposed='具物理约束与防火墙的 PAID Agent',
        note='预测更优不等于获得新规律（§6 Exp.4）。',
        frozen_specs=dict(
            A=dict(
                form='OLS: LST ~ 全部 8 个预指定变量的一次项（LST_mean,NDVI_mean,DEM_mean,'
                     'SVF_mean,Road_Dens,X_BD,X_BH,X_VolDens），逐一 Z 标准化后拟合；'
                     '不含交互项、无惩罚。GAM（样条）为并列对照但仅作定性比较。',
                fit='仅在 A 发现区拟合并冻结系数；B 区不做系数更新。',
                eval='在 C 区计算 RMSE 作为 ΔRMSE 的比较基准。',
                rationale='冻结 Baseline A 的形式与拟合域，避免"通过与一个未定义/过弱基线比较"侥幸通过。'),
            B=dict(form='RF（n_estimators=500）与 XGBoost（max_depth=6, eta=0.1）并列；'
                        '以 A 区嵌套空间分块 CV 调参。',
                   eval='在 C 区计算 RMSE 与 ΔRMSE（不作主终点，仅作公平比较，§6 Exp.4）。'),
            C=dict(form='符号回归（预设算子集 + - * / exp log，最大复杂度 15），搜索空间上限 10^4。'),
            D=dict(form='同一基础模型、同一工具白名单，但**移除**物理硬约束与防火墙（全量数据可见）的自主 Agent。'))))

# ================================================================ Table 13 七类检验（逐项登记）
table13_checks = [
    dict(no=1, name='空间分块 / 缓冲验证',
         how='分区于空间连续簇；C 与 A∪B 间距 = %d 格 ≥ R = %d 格；C 内不混入任何 A/B 格。'
             % (sm['min_distance_cells']['C_to_AB'], sm['R_cells']),
         where='split/split_manifest.json、validation_protocol'),
    dict(no=2, name='负对照及合适的空间置换',
         how='C 区目标空间置换 199 次 + 随机目标列 + 打乱行序伪候选。',
         where='validation_protocol.negative_controls'),
    dict(no=3, name='物理及量纲审计',
         how='Physics Auditor 独立审计量纲一致性、几何合法性、可计算物理约束；能量闭合标 not_computable。',
         where='constraints/hard_constraints.json、agent/agent_manifest.json'),
    dict(no=4, name='地表类型分层与异常掩膜',
         how='按 NDVI 三分位（低/中/高植被）分层报告每个候选的效应与 RMSE；C 区构成为 [%.3f, %.3f, %.3f]，'
             '须分层呈现以避免少数类型主导结论；异常值以 S00 掩膜（LST==0 填充、非物理 NDVI、'
             '边界部分格）排除，并在报告中登记被排除格数。'
             % tuple(sm['landcover_post']['locked']['ndvi_tercile_share']),
         where='validation_protocol.strata_and_outliers'),
    dict(no=5, name='测量误差传播',
         how='LST 无 QA/不确定度元数据（S00.1），故无法做正式误差传播；'
             '预注册**敏感性方案**：以 LST 观测不确定度 ±0.5 K 与 ±1.0 K 两档对目标加扰动，'
             '检验候选效应的符号与显著性是否保持；效应量须大于该扰动下的区间宽度方可宣称稳健。',
         where='validation_protocol.measurement_error'),
    dict(no=6, name='多重检验和候选记录',
         how='Holm–Bonferroni（family = 冻结候选集 ≤ 8）+ 报告未校正 p；搜索规模登记于 append-only 日志。',
         where='validation_protocol.multiplicity、experiment_protocol.failure_logging'),
    dict(no=7, name='外部时相与地区复现',
         how='D 层（新时相/新城市）独立收集；当前数据无第二时相，故 L3 结论须待外部数据补齐后给出。',
         where='validation_protocol.external（N/A 于本数据）'),
]

# 替代去相关尺度 R（更保守判据 r<0.1，建成层），取整到 5 格栅格倍数——纯整数运算，无需 numpy。
_ALT_K = sa['criterion_sensitivity']['k_at_0p1']['low_veg_max'] or 10
_ALT_R = max(10, ((int(_ALT_K) + 4) // 5) * 5)


# ================================================================ 3) Validation protocol
validation_protocol = dict(
    version=VERSION, created=CREATED,
    framework_ref='Table 12 Validation protocol；§5.3；Table 13',
    unseal_principle='哈希≠访问控制；C 区目标值存于发现 Agent 无权读取的独立目录/服务；'
                     '验证只接受已冻结候选，发布完整通过/失败（§5.3）。',
    primary_endpoint=dict(
        target='锁定区 C 的 LST_mean',
        statistic='候选表达式在 C 区的 RMSE（℃）以及相对 Baseline A 的 ΔRMSE',
        pass_rule='ΔRMSE>0（优于 Baseline A）且经 199 次空间块置换检验 p<0.05，'
                  '且 95% 置信区间不跨 0，且物理审计通过，且负对照（空间置换/随机目标）未通过。',
        note='主终点在解封前冻结；解封后不得更改模型、指标、假设或停止条件（SI-1）。'),
    spatial_inference=dict(
        split='空间划分为主：C 与 A∪B 最小间距 %d 格（%.1f km）≥ R（%d 格）。'
              % (sm['min_distance_cells']['C_to_AB'], sm['R_m'] / 1000.0, sm['R_cells']),
        block_permutation=199,
        buffer='仅 C 施加缓冲；A 与 B 同属开发域，不设内部缓冲。',
        rationale='控制相邻格空间泄漏导致的过乐观泛化（Table 13 空间分块/缓冲验证）。'),
    multiplicity=dict(
        n_frozen_candidates='≤ %d' % experiment_protocol['candidate_cap']['freeze_max'],
        control='Holm–Bonferroni（family = 冻结候选集）；同时报告未校正 p。',
        note='控制大量搜索后的偶然显著（Table 13 多重检验）。'),
    missing_data=dict(
        handling='C 区不插补；缺失/无效格显式排除并登记数量。',
        excluded_interpolated=True),
    negative_controls=['C 区目标空间置换 199 次', '随机目标列', '打乱行序的伪候选'],
    strata_and_outliers=dict(
        strata='按 NDVI 三分位（低/中/高植被）分层报告每个候选的效应、RMSE 与置信区间',
        locked_share='C 区三分位构成 [%.3f, %.3f, %.3f]（全局 1/3,1/3,1/3），偏斜须在报告中显式呈现'
                     % tuple(sm['landcover_post']['locked']['ndvi_tercile_share']),
        anomalies='排除 S00 掩膜认定的异常（LST==0 填充、非物理 NDVI、边界仅 1–2 有效像元的格）；'
                  '每一候选须报告被排除格数及其对结论的影响。',
        rule='不得以全样本显著掩盖某一分层不成立；任一分层符号相反须如实报告。'),
    measurement_error=dict(
        status='no_qa_metadata',
        note='LST 无观测时间/传感器/QA/不确定度元数据（S00.1），无法做正式测量误差传播。',
        sensitivity=['±0.5 K', '±1.0 K'],
        rule='对 C 区目标施加 ±0.5 K 与 ±1.0 K 两档扰动重算主检验；效应的符号与显著性须在'
             '两档下均保持，且效应量须大于扰动引起的区间宽度，方可宣称稳健。'),
    external=dict(
        status='not_available',
        note='当前数据仅单一时相、单一城市，D 层（新时相/新城市）不可用；'
             'L3 外部支持关系须待外部数据补齐后给出，不得以深圳单期结果替代（Table 15/19）。'),
    criterion_sensitivity=dict(
        primary_R_cells=sm['R_cells'],
        alternative_R_cells=_ALT_R,
        rule='主分析采用 R=%d 格；以更保守判据（r<0.1，建成层）得到的替代分区 R=%d 格作为'
             '**预注册的稳健性对照**，在同一批冻结候选上重算，与主结果一并报告；'
             '替代分区不改变主分析，也不得据其结果修订候选。'
             % (sm['R_cells'], _ALT_R)),
    table13_coverage=[c['name'] for c in table13_checks],
    report_rule='统一报告通过、失败及所有不确定性；失败候选不得删除。')

# ================================================================ 4) Code manifest
ROOTS = [os.path.join(C.PROJ, 'lib'), os.path.join(C.S00, 'scripts'), os.path.join(C.S01, 'scripts')]
code_files = []
for root in ROOTS:
    for p in sorted(glob.glob(os.path.join(root, '*.py'))):
        code_files.append(dict(path=os.path.relpath(p, C.PROJ).replace(os.sep, '/'),
                               bytes=os.path.getsize(p), sha256=sha256(p)))
code_manifest = dict(
    version=VERSION, created=CREATED,
    framework_ref='Table 12 Code manifest',
    environment=dict(
        python=platform.python_version(), platform=platform.system(),
        numpy=__import__('numpy').__version__, pandas=__import__('pandas').__version__,
        matplotlib=__import__('matplotlib').__version__,
        docx='python-docx', openpyxl=__import__('openpyxl').__version__,
        note='无 gdal/rasterio/geopandas/scipy/sklearn；地理 IO 由 lib/geoio.py 纯 Python 实现。'),
    data_transform_scripts=['lib/geoio.py', 'lib/config.py',
                            'stage00_data_audit/scripts/s00_*.py', 'stage01_protocol/scripts/s01_*.py'],
    candidate_model_code='Stage 02 生成后追加其哈希（本清单先冻结环境与数据变换脚本）。',
    files=code_files, n_files=len(code_files))

# ================================================================ 落盘
out = {
    'agent/agent_manifest.json': agent_manifest,
    'protocol/experiment_protocol.json': experiment_protocol,
    'protocol/validation_protocol.json': validation_protocol,
    'manifest/code_manifest.json': code_manifest,
}
for rel, obj in out.items():
    with open(os.path.join(C.S01, rel), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# ================================================================ Markdown
L = []
L.append('# S01.4 预注册清单：Agent / 实验协议 / 验证协议 / 代码\n')
L.append('框架依据：Table 12 六清单（本报告补齐其中四项）、Table 10/11/13/14、§5.3、§3.2。\n')
L.append('版本 **%s**，%s。\n' % (VERSION, CREATED))
L.append('## 1 Agent manifest\n')
L.append('> 系统提示词只注入：`DATA_DICTIONARY.md`、`hard_constraints.json`、计算预算、工具白名单；'
         '禁用 %d 条方向性主张（§3.2）。基础模型版本待 Stage 02 声明并冻结。\n' % len(hc['no_direction_preset']))
L.append('| Agent | 用途 | 可访问数据 | 禁止访问 |')
L.append('|---|---|---|---|')
for a in AGENTS:
    L.append('| %s | %s | %s | %s |' % (a['agent'], a['purpose'],
                                        '、'.join(a['data_access']), '；'.join(a['forbidden_access'])))
L.append('')
L.append('## 2 Experiment protocol\n')
ep = experiment_protocol
L.append('- 候选上限：每轮 ≤ %d 个；总 fit 预算 %d；冻结候选 ≤ %d 个。'
         % (ep['candidate_cap']['per_round_max'], ep['candidate_cap']['total_fit_budget'],
            ep['candidate_cap']['freeze_max']))
L.append('- 开发主指标：%s；并列报告 %s。' % (ep['dev_metrics']['primary'], '、'.join(ep['dev_metrics']['secondary'])))
L.append('- 停止条件：%s' % '；'.join(ep['stopping_conditions']))
L.append('- 失败记录：%s（字段：%s）。' % (ep['failure_logging']['mode'], '、'.join(ep['failure_logging']['fields'])))
L.append('- 对照组：%s + Proposed。\n' % '、'.join('Baseline ' + k for k in 'ABCD'))
L.append('## 3 Validation protocol\n')
vp = validation_protocol
L.append('- 主终点：%s；通过条件：%s' % (vp['primary_endpoint']['statistic'], vp['primary_endpoint']['pass_rule']))
L.append('- 空间推断：%s' % vp['spatial_inference']['split'])
L.append('- 多重比较：%s' % vp['multiplicity']['control'])
L.append('- 缺失处理：%s' % vp['missing_data']['handling'])
L.append('- 负对照：%s' % '；'.join(vp['negative_controls']))
L.append('- 分层与异常：%s' % vp['strata_and_outliers']['rule'])
L.append('- 测量误差：%s' % vp['measurement_error']['rule'])
L.append('- 判据敏感性：%s\n' % vp['criterion_sensitivity']['rule'])
L.append('### 3.1 Table 13 七类检验逐项落实\n')
L.append('| # | 检验 | 落实方式 | 位置 |')
L.append('|---|---|---|---|')
for c in table13_checks:
    L.append('| %d | %s | %s | %s |' % (c['no'], c['name'], c['how'], c['where']))
L.append('')
L.append('覆盖：Table 13 七类检验全部登记（第 7 类因缺第二时相/城市，标记为 not_available）。\n')
L.append('## 4 Code manifest\n')
L.append('- 环境：Python %s / numpy %s / pandas %s / matplotlib %s。'
         % (code_manifest['environment']['python'], code_manifest['environment']['numpy'],
            code_manifest['environment']['pandas'], code_manifest['environment']['matplotlib']))
L.append('- 冻结代码 **%d** 个（lib + Stage 00 + Stage 01），逐文件 SHA-256 见 `manifest/code_manifest.json`。\n'
         % code_manifest['n_files'])
L.append('## 5 交付物\n')
L.append('| 清单 | 路径 |')
L.append('|---|---|')
for rel in out:
    L.append('| %s | `%s` |' % (rel.split('/')[-1], rel))
with open(os.path.join(C.S01_REPORTS, 's01_04_protocols.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))
with open(os.path.join(C.S01_REPORTS, 's01_04_protocols.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(version=VERSION, created=CREATED,
                   agent_manifest=agent_manifest, experiment_protocol=experiment_protocol,
                   validation_protocol=validation_protocol, code_manifest=code_manifest),
              f, ensure_ascii=False, indent=2)

print(json.dumps(dict(version=VERSION,
                      n_agents=len(AGENTS), n_code_files=code_manifest['n_files'],
                      freeze_max=ep['candidate_cap']['freeze_max'],
                      fit_budget=ep['candidate_cap']['total_fit_budget'],
                      outputs=list(out)), ensure_ascii=False, indent=2))
print('\n写出: agent/agent_manifest.json, protocol/experiment_protocol.json, '
      'protocol/validation_protocol.json, manifest/code_manifest.json, reports/s01_04_protocols.md/.json')
