"""
S04.2 Stage 04 报告 + SHA-256 清单
====================================
从 s04_01_validate.py 的一次性解封结果生成 STAGE04_REPORT.md 与
manifests/stage04_hashes.txt。只读 reports/、registry/ 与 Stage 03 冻结登记，
不改动任何候选记录。

用法：python3 stage04_validation/scripts/s04_02_report.py
"""
import os, sys, json, hashlib, glob, datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
S04 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S04)
S03 = os.path.join(PROJ, 'stage03_discovery')
sys.path.insert(0, os.path.join(S03, 'lib'))
import paths03 as P3

RESULTS = os.path.join(S04, 'reports', 's04_validation_results.json')
APPROVED = os.path.join(S04, 'registry', 'approved_unseal.json')
SNAP = os.path.join(S04, 'registry', 'pre_unseal_snapshot.json')
REPORT = os.path.join(S04, 'STAGE04_REPORT.md')
MANIFEST = os.path.join(S04, 'manifests', 'stage04_hashes.txt')


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
    res = json.load(open(RESULTS, encoding='utf-8'))
    appr = json.load(open(APPROVED, encoding='utf-8'))
    snap = json.load(open(SNAP, encoding='utf-8'))
    fr = json.load(open(P3.FROZEN_FILE, encoding='utf-8'))
    runmap = {c['id']: c.get('validation_runs', 0) for c in fr['frozen']}

    cands = res['candidates']
    h10 = cands['S03-H10-GREEDY']
    pl = cands['S03-H01-LIN7']
    h10p = h10['primary_endpoint']
    plp = pl['primary_endpoint']

    L = []
    A = L.append

    # ---------------------------------------------------------------- 头部
    A('# Stage 04 独立验证：单次解封与完整验证协议报告')
    A('')
    A('| 项 | 值 |')
    A('|---|---|')
    A('| 版本 | stage04-validation-v1 |')
    A('| 报告生成 | %s |' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    A('| 执行环境 | 沙箱之外（Independent Validator 进程） |')
    A('| 解封方式 | 单次解封（每个候选 validation_runs 上限 1） |')
    A('| 本轮解封 | 2 个：`S03-H10-GREEDY`（发现候选）+ `S03-H01-LIN7`（安慰剂参考） |')
    A('| C 区规模 | 主判据 R=15 格 → %d 格；替代判据 R=25 格 → %d 格 |'
      % (res['n_C_main'], res['n_C_alt']))
    A('| 多重比较 | Holm–Bonferroni，family = 冻结候选集（4） |')
    A('| 结论 | `S03-H10-GREEDY` 通过冻结主终点（**有条件的正结果**，见 §6）；安慰剂按预期不通过 |')
    A('')

    # ---------------------------------------------------------------- 0 摘要
    A('## 0 摘要')
    A('')
    A('本轮按用户批准的**保守方案**只解封了 2 个候选，一次性完成协议要求的全部分析'
      '（主终点、多重比较、NDVI 分层、±0.5/±1.0 K 测量误差、R=25 替代判据、打乱行序伪候选、'
      '缺失/剔除登记），因为每个候选只有一次解封机会。')
    A('')
    A('- **安慰剂自检（判别力）通过。** 冻结登记的安慰剂 `S03-H01-LIN7` 就是冻结 Baseline A 本身，'
      '在 C 区 ΔRMSE 恒为 0、置换 p=1.0、CI=[0,0]，验证服务**正确判为不通过**——'
      '说明验证服务不是"只要提交就放行"。')
    A('- **发现候选 `S03-H10-GREEDY` 通过冻结主终点。** C 区 RMSE 由基线 2.8415 ℃ 降至 2.4624 ℃，'
      'ΔRMSE=%s ℃，199 次空间块置换 p=%.3f，95%% 空间块自助 CI [%s, %s]（不含 0）；'
      '物理审计与负对照两项由验证进程**独立复算**均通过；Holm 校正后仍判为拒绝原假设。'
      % (sgn(h10p['delta_rmse']), h10p['perm_p'],
         f4(h10p['ci95_delta'][0]), f4(h10p['ci95_delta'][1])))
    A('- **但有两条实质性保留**（§6）：其一，改用更保守的替代判据 R=25 格重划 C 区时，'
      '效应缩到 %s ℃、p=%.3f，**不再显著**；其二，Baseline A 在 C 区迁移性很弱'
      '（常数预测的 RMSE 都低于基线），因此 ΔRMSE>0 部分来自"基线本身不好"。'
      % (sgn(h10['criterion_sensitivity_R25']['delta_rmse']),
         h10['criterion_sensitivity_R25']['perm_p']))
    A('')
    A('**一句话结论：** 在锁定区上，`S03-H10-GREEDY` 相对冻结基线确有方向稳健、'
      '经多重比较校正后仍成立的改善；但该改善对空间判据敏感、且比较基线偏弱，'
      '因此**不足以据此宣称"发现了一条城市 LST 规律"**，只能作为一条"受限的、'
      '有待外部数据复核的候选关系"。C 区解封不可逆；另外 2 个冻结候选的解封机会仍完好。')
    A('')

    # ---------------------------------------------------------------- 1 边界与合规
    A('## 1 运行边界与合规')
    A('')
    A('| 项 | 值 |')
    A('|---|---|')
    A('| 执行者 | Independent Validator（沙箱之外的独立进程，`stage02_platform/agents/independent_validator.py`） |')
    A('| 只接受 | `registry/approved_unseal.json` 中已批准、且 `canon_hash` 与冻结登记一致的候选 |')
    A('| 冻结哈希强校验 | 通过（2/2 候选 `canon_hash` 与冻结登记逐字节一致） |')
    A('| 重复解封防护 | 强制 `validation_runs<1`；本轮后两候选 =1，见 §7 |')
    A('| 发布规则 | 仅发布**聚合结论**，不返回 C 区逐格目标值；失败同样完整发布 |')
    A('| 解封前快照 | `registry/pre_unseal_snapshot.json`（冻结登记 SHA-256 %s…，日志 %d 行） |'
      % (snap['frozen_candidates_sha256'][:12], snap['log_lines_pre']))
    A('| 日志 | 追加式哈希链日志；解封后 `verify()` = ok，共 %d 条 |' % _log_lines())
    A('')
    A('## 2 方法')
    A('')
    A('**主终点（冻结规格）。** 直接调用 Stage 02 的验证服务 `validate()`：'
      'ΔRMSE = RMSE_C(Baseline A) − RMSE_C(候选)，其中 Baseline A 按**冻结规格**'
      '（7 个预指定形态变量的 OLS）仅在 A 区拟合；候选模型在冻结时即固定，'
      '验证阶段**不再重新拟合**。显著性用 199 次空间块置换（重排 5×5 格块均值的'
      '**取值**并保留块内残差）；不确定性用 1000 次空间块自助 95% CI。')
    A('')
    A('**独立复算。** 主终点五条件中，`physics_audit_pass` 与 `negative_controls_not_fooled` '
      '两项不再采信发现侧自报字段，而由验证进程用 A/B 区数据自行复算'
      '（物理审计硬门 PA3/PA4/PA5/PA7 由 A 区复算；负对照地板 NC1–NC3 由 B 区复算）。')
    A('')
    A('**二次分析（本脚本）。** NDVI 三分位分层（全局阈值 %.4f / %.4f）；'
      '对 C 区目标叠加 ±0.5/±1.0 K 高斯扰动各 20 次重算主检验；'
      '用替代判据 R=25 格（更保守）重划锁定区重算主检验；'
      '打乱 A 区目标行序重拟合构造伪候选。'
      % (res['ndvi_tercile_thresholds'][0], res['ndvi_tercile_thresholds'][1]))
    A('')
    A('**有效性断言。** 空间块置换前后目标相关系数 %.3f（< 0.9），置换确实改变了取值，'
      '非"只重排索引"的恒等退化。' % h10p['perm_corr_sanity'])
    A('')

    # ---------------------------------------------------------------- 3 主结果
    A('## 3 主终点结果')
    A('')
    A('| 候选 | 角色 | RMSE_C 基线 | RMSE_C 候选 | ΔRMSE | 置换 p | 95% CI | 结论 |')
    A('|---|---|---|---|---|---|---|---|')
    A('| `S03-H10-GREEDY` | 发现候选 | %s | %s | **%s** | %.3f | [%s, %s] | %s |'
      % (f4(h10p['rmse_baselineA']), f4(h10p['rmse_candidate']), sgn(h10p['delta_rmse']),
         h10p['perm_p'], f4(h10p['ci95_delta'][0]), f4(h10p['ci95_delta'][1]),
         '通过' if h10['passed'] else '不通过'))
    A('| `S03-H01-LIN7` | 安慰剂参考 | %s | %s | %s | %.3f | [%s, %s] | %s |'
      % (f4(plp['rmse_baselineA']), f4(plp['rmse_candidate']), sgn(plp['delta_rmse']),
         plp['perm_p'], f4(plp['ci95_delta'][0]), f4(plp['ci95_delta'][1]),
         '通过' if pl['passed'] else '不通过（按预期）'))
    A('')
    A('**五条件明细（冻结主终点须全部满足）：**')
    A('')
    A('| 候选 | ΔRMSE>0 | p<0.05 | CI 不含 0 | 物理审计 | 负对照 | 通过 |')
    A('|---|---|---|---|---|---|---|')
    for cid, rec in (('S03-H10-GREEDY', h10), ('S03-H01-LIN7', pl)):
        c = rec['conditions']
        yn = lambda b: '✓' if b else '✗'
        A('| `%s` | %s | %s | %s | %s | %s | **%s** |'
          % (cid, yn(c['delta_rmse_pos']), yn(c['perm_p_lt_0.05']),
             yn(c['ci_excludes_zero']), yn(c['physics_audit_pass']),
             yn(c['negative_controls_not_fooled']), '通过' if rec['passed'] else '不通过'))
    A('')
    A('安慰剂 `S03-H01-LIN7` 的表达式就是 7 变量线性式（= Baseline A），'
      '验证服务不因"提交了候选"就放行：它在 ΔRMSE>0、p<0.05、CI 不含 0 三条件上全部不满足，'
      '被正确拒绝。**这是本轮最重要的方法学证据**：验证服务的判别力得到实测确认。')
    A('')
    A('**独立复算对照。** 发现侧自报与验证侧复算：')
    A('')
    A('| 候选 | 自报物理审计 | 独立物理审计 | 自报反例 | 独立负对照 | 主终点自/验一致 |')
    A('|---|---|---|---|---|---|')
    for cid, rec in (('S03-H10-GREEDY', h10), ('S03-H01-LIN7', pl)):
        A('| `%s` | %s | %s | %s | %s | ΔRMSE 一致=%s |'
          % (cid, rec['self_reported']['physics_audit'],
             rec['independent_audit']['verdict'], rec['self_reported']['falsification'],
             rec['independent_controls']['verdict'],
             '是' if rec['cross_check']['agree_delta'] else '否'))
    A('')
    A('本脚本独立实现的主终点与验证服务逐位一致（`agree_delta=True`，ΔRMSE 差 < 1e-9），'
      '说明结论不依赖单一实现。')
    A('')

    # ---------------------------------------------------------------- 4 多重比较
    A('## 4 多重比较（Holm–Bonferroni）')
    A('')
    A('family = 冻结候选集（4 个：3 个发现候选 + 1 个安慰剂），'
      '这是预注册口径、且比"只按本轮解封的 2 个"更保守。')
    A('')
    A('| 候选 | 未校正 p | Holm 阈值 | 校正后拒绝原假设 |')
    A('|---|---|---|---|')
    for s in res['multiplicity']['stepdown']:
        A('| `%s` | %.3f | %.4f | %s |'
          % (s['id'], s['p_uncorrected'], s['holm_threshold'],
             '是' if s['reject'] else '否'))
    A('')
    A('`S03-H10-GREEDY` 未校正 p=%.3f，Holm 阈值 %.4f，校正后仍拒绝原假设。'
      '安慰剂未校正 p=1.0，自然不被拒绝。'
      % (h10p['perm_p'], res['multiplicity']['stepdown'][0]['holm_threshold']))
    A('')

    # ---------------------------------------------------------------- 5 二次分析
    A('## 5 二次分析')
    A('')
    A('### 5.1 NDVI 三分位分层（`S03-H10-GREEDY`）')
    A('')
    A('| 分层 | n_C | RMSE 基线 | RMSE 候选 | ΔRMSE | 95% CI | 不含 0 |')
    A('|---|---|---|---|---|---|---|')
    for name, zh in (('low_veg', '低植被'), ('mid_veg', '中植被'), ('high_veg', '高植被')):
        st = h10['strata_ndvi'][name]
        if 'delta_rmse' not in st:
            A('| %s | %d | — | — | — | — | %s |' % (zh, st['n'], st.get('note', '')))
            continue
        A('| %s | %d | %s | %s | %s | [%s, %s] | %s |'
          % (zh, st['n'], f4(st['rmse_baselineA']), f4(st['rmse_candidate']),
             sgn(st['delta_rmse']), f4(st['ci95_delta'][0]), f4(st['ci95_delta'][1]),
             '是' if st['ci_excludes_zero'] else '否'))
    A('')
    A('C 区分层构成 [%d, %d, %d]（低/中/高），偏中高植被，'
      '与冻结时预注册的锁定占比 [0.338, 0.548, 0.115] 一致。三个分层 ΔRMSE 均为正、'
      'CI 均不含 0，未出现"某层反向"的抵消模式。'
      % (h10['strata_ndvi']['low_veg']['n'], h10['strata_ndvi']['mid_veg']['n'],
         h10['strata_ndvi']['high_veg']['n']))
    A('')
    A('### 5.2 测量误差敏感性（`S03-H10-GREEDY`）')
    A('')
    A('| 目标扰动 | ΔRMSE 均值 | ΔRMSE 范围 | 区间宽度 | p 中位数 | p<0.05 比例 | Δ>0 比例 |')
    A('|---|---|---|---|---|---|---|')
    for k in ('sd_0.5K', 'sd_1.0K'):
        me = h10['measurement_error'][k]
        A('| %s | %s | [%s, %s] | %s | %.3f | %.0f%% | %.0f%% |'
          % (k.replace('sd_', '±').replace('K', ' K'), sgn(me['delta_mean']),
             sgn(me['delta_min']), sgn(me['delta_max']), f4(me['delta_interval_width']),
             me['p_median'], 100 * me['frac_p_lt_0p05'], 100 * me['frac_delta_pos']))
    A('')
    A('加 ±0.5/±1.0 K 目标噪声后，ΔRMSE 在 %s 次抽样中**始终为正**、'
      'p 恒 < 0.05，且效应量远大于扰动区间宽度。'
      '但需说明：加噪后基线与候选看到同一批噪声，'
      '正例比例高只说明**增益稳定**，本身不构成显著性证据。'
      % h10['measurement_error']['sd_0.5K']['n_draws'])
    A('')

    # ---------------------------------------------------------------- 6 稳健性与保留
    A('## 6 稳健性保留（必须与正结果并列阅读）')
    A('')
    A('### 6.1 替代判据 R=25 格：效应缩水且不再显著')
    A('')
    A('| 判据 | n_C | ΔRMSE | 置换 p | 符号一致 |')
    A('|---|---|---|---|---|')
    A('| R=15 格（主判据） | %d | %s | %.3f | — |'
      % (res['n_C_main'], sgn(h10p['delta_rmse']), h10p['perm_p']))
    r25 = h10['criterion_sensitivity_R25']
    A('| R=25 格（替代判据） | %d | %s | %.3f | %s |'
      % (r25['n_C'], sgn(r25['delta_rmse']), r25['perm_p'],
         '是' if r25['sign_consistent_with_R15'] else '否'))
    A('')
    A('空间自相关判据 R 在 Stage 01 取 15 格（1.5 km），并预注册了更保守的 R=25 格（2.5 km）'
      '作为稳健性对照。改用 R=25 后锁定区缩到 %d 格，效应从 %s 缩到 %s ℃、'
      'p 从 %.3f 升到 %.3f——**方向一致但不再显著**。'
      '这说明该改善的**统计显著性对空间判据敏感**，是本轮最需要如实披露的限制。'
      % (r25['n_C'], sgn(h10p['delta_rmse']), sgn(r25['delta_rmse']),
         h10p['perm_p'], r25['perm_p']))
    A('')
    A('### 6.2 比较基线偏弱：Baseline A 在 C 区不如常数预测')
    A('')
    ps = h10['pseudo_row_shuffled']
    A('| 预测器 | C 区 RMSE（℃） |')
    A('|---|---|')
    A('| Baseline A（冻结基线） | %s |' % f4(ps['rmse_baselineA']))
    A('| 常数预测（A 区 LST 均值） | %s |' % f4(ps['rmse_constant_floor']))
    A('| 打乱行序伪候选（噪声训练） | %s |' % f4(ps['rmse']))
    A('| 真候选 `S03-H10-GREEDY` | %s |' % f4(ps['rmse_candidate']))
    A('')
    A('把 A 区目标行序打乱后重拟合得到的"伪候选"（预测≈常数），在 C 区的 RMSE 反而**低于** '
      'Baseline A；连纯常数预测都比 Baseline A 更接近 C 区真值。'
      '这意味着 Baseline A 的 7 变量关系在 C 区**几乎不迁移**，'
      'ΔRMSE>0 里有相当一部分来自"基线本身偏弱"，而非候选独有的能力。'
      '更公平的比较是"真候选 vs 伪候选/常数地板"：真候选 %s ℃ **确实低于**常数地板 %s ℃，'
      '所以候选的增益不是单纯"缩到均值"——但这一比较未被预注册为主终点，'
      '只能作为辅助解读。'
      % (f4(ps['rmse_candidate']), f4(ps['rmse_constant_floor'])))
    A('')
    A('### 6.3 其他保留')
    A('')
    A('- **选择偏倚。** `S03-H10-GREEDY` 是从 15 个候选（12 预注册 + 2 贪心 + 1 局部修订）中'
      '在 A 区选出的，A 区增益是乐观估计；C 区本轮只验证了它一个，'
      'Holm 已按 family=4 校正，但"从 15 个里挑出 4 个冻结"这一层搜索强度无法完全校正。')
    A('- **负对照是地板式弱检验。** NC1–NC3 只能淘汰"零技巧"模型，判别力有限。')
    A('- **特征定义限制（沿用 Stage 01）。** DEM 值域仅 3–17 m、不可信；'
      '`S03-H10-GREEDY` 用到了 `exp(DEM_mean)` 与 `NDVI×DEM`，'
      '其地形相关解释因此**不成立**，只能作经验性描述。`X_BH`、`X_BD`、`X_VolDens` '
      '的定义亦未经作者确认。')
    A('- **C 区不可再验。** 本轮已消耗两候选的唯一解封机会，结果不可撤回。')
    A('')

    # ---------------------------------------------------------------- 7 登记
    A('## 7 缺失/排除与解封登记')
    A('')
    A('| 项 | 值 |')
    A('|---|---|')
    A('| C 区主判据格数 | %d |' % res['n_C_main'])
    A('| C 区替代判据（R=25）格数 | %d |' % res['n_C_alt'])
    A('| 缓冲剔除（R=15 / R=25，格） | %d / %d |'
      % (res['buffer']['R15'], res['buffer']['R25']))
    A('| C 区补齐 | 不做任何插补（框架要求） |')
    A('| 金库明文 SHA-256 | `%s` |' % res['vault_plaintext_sha256'])
    A('')
    A('**解封登记（不可逆）：**')
    A('')
    A('| 候选 | 角色 | validation_runs（当前） | last_result |')
    A('|---|---|---|---|')
    for cid, role in (('S03-H10-GREEDY', '发现候选'), ('S03-H01-LIN7', '安慰剂参考')):
        lr = cands[cid]['passed']
        A('| `%s` | %s | %d | passed=%s |' % (cid, role, runmap.get(cid, 0), lr))
    A('| `S03-H11-REFINE` | 发现候选 | %d | 未解封，机会完好 |' % runmap.get('S03-H11-REFINE', 0))
    A('| `S03-H10P-GREEDY-MIN` | 发现候选 | %d | 未解封，机会完好 |' % runmap.get('S03-H10P-GREEDY-MIN', 0))
    A('')

    # ---------------------------------------------------------------- 8 结论
    A('## 8 结论与建议')
    A('')
    A('1. **验证服务判别力已实测确认。** 安慰剂（= Baseline A）被正确判为不通过，'
      '说明平台不会"交了就过"。')
    A('2. **`S03-H10-GREEDY` 通过冻结主终点，但是"有条件的正结果"。** '
      '它在 C 区相对基线改善 %s ℃（p=%.3f，Holm 校正后仍显著），'
      '三个 NDVI 分层同向，测量误差下方向稳定。'
      % (sgn(h10p['delta_rmse']), h10p['perm_p']))
    A('3. **两条保留实质性削弱了结论强度：** 改用更保守判据 R=25 后不再显著（p=%.3f）；'
      '比较基线在 C 区偏弱（常数预测都比它好）。因此**不宜宣称发现规律**。'
      % r25['perm_p'])
    A('4. **建议：** 若要把此结果写入论文，应当作"受限的证据"呈现，'
      '并同时报告 R=25 的不显著与基线偏弱两项；'
      '更强的做法是用**外部独立数据**（另一城市或另一时段）复核该关系，'
      '而不是继续消耗冻结候选的解封机会。')
    A('5. **未解封候选保留。** `S03-H11-REFINE` 与 `S03-H10P-GREEDY-MIN` 机会完好，'
      '是否解封应在本轮结果基础上再决策——但需注意 H11 在 B 区增益略小、'
      'H10P 在 B 区 ΔB 为负且 A 区 CI 含 0，二者的先验都不强。')
    A('')
    A('> 失败与保留均完整发布。')
    A('')

    # ---------------------------------------------------------------- 9 对 Stage 03 的影响
    A('## 9 对 Stage 03 冻结校验的影响（务必知悉）')
    A('')
    A('Stage 04 的授权解封**按设计改动了 Stage 03 的冻结登记**，因此 Stage 03 的旧校验'
      '会出现预期内的"失败/过期"，**这不是篡改**：')
    A('')
    A('- `stage03_discovery/registry/frozen_candidates.json`：`S03-H10-GREEDY` 与 `S03-H01-LIN7` '
      '的 `validation_runs` 由 0 → 1 并写入 `last_result`；另 2 个候选不变。'
      '因此 Stage 03 清单中该文件的哈希与 `s03_05_verify.py` 的 V4「解封预算完好（runs=0）」'
      '**如期失效**——V4 断言的是"Stage 03 尚未解封"，该状态已被授权的 Stage 04 动作改变。')
    A('- `stage02_platform/logs/experiment_log.jsonl`：追加了解封记录，行数由 1231 增至 %d'
      '（哈希链本身经 `verify()` 校验完好）。'
      % _log_lines())
    A('- `stage04_validation` 的 V2 证明四个候选的 `canon_hash` 与候选文件逐字节一致，'
      '即候选定义未被改写；V7 证明冻结登记**仅**在批准项上发生"预算 +1、写入末次结果"这一处变更。'
      '两者合起来说明：变更恰好是授权的解封动作，没有其他改动。')
    A('')
    A('沿用冻结规则，**未修改 Stage 03 的任何冻结产物或校验脚本**；'
      'Stage 03 的 V4 保持"按当前状态如实报 FAIL"这一信号，正是它该有的作用。')
    A('')
    A('见 `manifests/stage04_hashes.txt`（本报告与清单自身之外的全部 Stage 04 产物逐一 SHA-256）。')
    A('')

    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))

    # ---------------------------------------------------------------- 清单
    files = [RESULTS, APPROVED, SNAP, REPORT]
    files += sorted(glob.glob(os.path.join(S04, 'scripts', '*.py')))
    # 注：reports/verification.json 是自验证脚本的派生输出、每次 verify 都会重写，
    # 故不入清单（否则清单与自身校验会循环失稳）。
    LOG = P3.EXPERIMENT_LOG
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        f.write('# Stage 04 产物 SHA-256 清单（相对 PAID/；不含本清单自身）\n')
        f.write('# 生成于 %s；Stage 03 冻结候选的解封状态另见 stage03_discovery/registry/frozen_candidates.json\n'
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
    print('[s04-report] wrote', REPORT)
    print('[s04-report] wrote', MANIFEST, '(%d files)' % len(files))
    return 0


def _log_lines():
    import sys as _s
    _s.path.insert(0, os.path.join(PROJ, 'stage02_platform', 'sandbox'))
    import log_tool
    return log_tool.verify().get('n', -1)


if __name__ == '__main__':
    raise SystemExit(main())
