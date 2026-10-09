"""
S01.3 物理约束与硬约束规则（§3.1 / §3.2）
==========================================
目的：冻结「M1 物理约束」清单，把可计算/可执行的硬约束写死为机器可读规则，
并明确声明**哪些物理约束在当前数据下无法检验**，防止后续 Agent 伪造物理一致性。

框架依据：
  §3.1 硬约束（Table 3）：温度与辐射、量纲与几何、能量守恒、测量边界、统计诚信。
  §3.2 软约束：不得预设关系方向（NDVI 单调降温 / SVF 升温或降温 / 建高方向），
       不得预设最优尺度、固定函数式、单一显著阈值或特定交互组合。
  Table 11「1 M1 物理约束：独立发布可计算硬约束，不发布关系方向。」
  Table 12 Data manifest（数据来源、版本、质量掩膜、路径与 SHA-256）。

本脚本做四件事：
  A) 从主样本（31760 格）复算每个变量的实测域，作为**数据有效性硬约束**的取值依据；
  B) 生成机器可读硬约束集 hard_constraints.json（分 data_validity / dimension_geometry /
     measurement_boundary / physics_consistency / statistical_integrity 五类，逐条标注
     status = enforceable | declared_only | not_computable）；
  C) 生成**中性数据字典** DATA_DICTIONARY.md：只给计算定义与实测域，不给关系方向；
  D) 生成 no_direction_preset.md：系统提示词禁用词与禁用主张的显式声明。

为什么这里只做「数据有效性」级的硬约束：
  实测显示多数"物理"协变量口径未确认（见 hard_constraints.json 的 definition_uncertainty）：
  X_BD 最大值 1.77（非 [0,1] 覆盖率）、X_BH 最大 224 m（非 100 m 格平均高度）、
  X_VolDens 与 X_BD·X_BH 的几何恒等式未被证实（比值中位数 2.02）、
  DEM 全域 3–17 m（不符合深圳地形，疑为掩膜或重标定）、Road_Dens 量纲未明。
  因此当前可执行的硬约束只能到「量纲/取值域/几何合法性」层面；
  能量闭合等机制性检查在补齐通量数据前**一律标为 not_computable**，不得伪造。

输出：constraints/hard_constraints.json / constraints/DATA_DICTIONARY.md /
      constraints/no_direction_preset.md / reports/s01_03_constraints.json / .md
"""
import sys, os, json, hashlib, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import config as C

os.makedirs(C.S01_CONSTRAINTS, exist_ok=True)
os.makedirs(C.S01_REPORTS, exist_ok=True)

VERSION = 'stage01-constraints-v1'
CREATED = '2026-09-24'

# ---------------------------------------------------------------- A) 主样本实测域
df = pd.read_csv(C.CSV)
df.columns = [c.strip() for c in df.columns]
df = df.set_index('My_ID')
main_ids = [int(x) for x in open(os.path.join(C.S00_MASK, 'valid_ids_main.txt')).read().split()]
relaxed_ids = [int(x) for x in open(os.path.join(C.S00_MASK, 'valid_ids_relaxed.txt')).read().split()] \
    if os.path.exists(os.path.join(C.S00_MASK, 'valid_ids_relaxed.txt')) else []
d = df.loc[main_ids]

VARS = ['LST_mean', 'NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens']
domain = {}
for c in VARS:
    v = pd.to_numeric(d[c], errors='coerce')
    domain[c] = dict(
        n=int(v.notna().sum()),
        min=round(float(np.nanmin(v)), 4), p05=round(float(np.nanquantile(v, .05)), 4),
        median=round(float(np.nanmedian(v)), 4), p95=round(float(np.nanquantile(v, .95)), 4),
        max=round(float(np.nanmax(v)), 4), zeros=int((v == 0).sum()),
        nan=int(v.isna().sum()),
    )
n_main = len(d)

# 几何恒等式核验：X_VolDens ?= X_BD * X_BH
bd, bh, vd = (pd.to_numeric(d[c], errors='coerce').to_numpy() for c in ('X_BD', 'X_BH', 'X_VolDens'))
m = (bd > 0) & (bh > 0)
with np.errstate(divide='ignore', invalid='ignore'):
    ratio = vd[m] / (bd[m] * bh[m])
ratio = ratio[np.isfinite(ratio)]
geo = dict(n_bd_pos=int(m.sum()),
           ratio_p05=round(float(np.quantile(ratio, .05)), 4),
           ratio_median=round(float(np.median(ratio)), 4),
           ratio_p95=round(float(np.quantile(ratio, .95)), 4),
           identity_holds=bool(abs(float(np.median(ratio)) - 1.0) < 0.05),
           corr_bd_vol=round(float(np.corrcoef(bd, vd)[0, 1]), 4))

# ---------------------------------------------------------------- B) 硬约束集
def rule(cid, category, statement, status, check=None, basis=None, note=None):
    return dict(id=cid, category=category, statement=statement, status=status,
                check=check, basis=basis, note=note)


HC = []
# --- 数据有效性（可执行） ---
HC += [
    rule('DV-1', 'data_validity', '主样本 LST_mean 必须落在实测域 [%.3f, %.3f] ℃ 内（逐格有效像元均值）。' % (domain['LST_mean']['min'], domain['LST_mean']['max']),
         'enforceable', 'range(LST_mean) ⊆ [%.4f, %.4f]' % (domain['LST_mean']['min'], domain['LST_mean']['max']),
         'S00.4 像元中心归属 + 有效像元均值；S00.6 主样本'),
    rule('DV-2', 'data_validity', 'NDVI_mean ∈ [%.4f, %.4f]（实测域）。' % (domain['NDVI_mean']['min'], domain['NDVI_mean']['max']),
         'enforceable', 'range(NDVI_mean) ⊆ [%.4f, %.4f]' % (domain['NDVI_mean']['min'], domain['NDVI_mean']['max']),
         '主样本实测域'),
    rule('DV-3', 'data_validity', 'SVF_mean ∈ [%.4f, %.4f]（0=全天空遮蔽，1=无遮蔽）。' % (domain['SVF_mean']['min'], domain['SVF_mean']['max']),
         'enforceable', 'range(SVF_mean) ⊆ [%.4f, %.4f]' % (domain['SVF_mean']['min'], domain['SVF_mean']['max']),
         '主样本实测域'),
    rule('DV-4', 'data_validity', '分析仅使用主样本 (n=%d)；放宽样本 (n=%d) 仅用于稳健性复核，二者不得混入同一训练/评估切分。' % (n_main, len(relaxed_ids)),
         'enforceable', 'train/eval rows ⊆ valid_ids_main；稳健性复核 ⊆ valid_ids_relaxed',
         'S00.6 掩膜策略'),
    rule('DV-5', 'data_validity', '缺失值（NaN）不得插补后参与主估计；含缺失的行须显式排除并登记。',
         'enforceable', 'isna(row)==False for used rows', 'S00.6 / 统计诚信'),
    rule('DV-6', 'data_validity', '全市域 LST==0 判为区外制图填充，一律无效；任何以 0 为真实温度的推断被禁止。',
         'enforceable', 'LST==0 → invalid', 'S00.3 四重证据'),
]
# --- 量纲与几何 ---
HC += [
    rule('DG-1', 'dimension_geometry', '所有候选项/表达式两侧量纲必须一致或已无量纲化；指数、对数、三角函数的自变量必须无量纲。',
         'enforceable', 'dim(LHS)==dim(RHS)；transcendental arg is dimensionless', 'Table 3 量纲与几何'),
    rule('DG-2', 'dimension_geometry', 'X_BD、X_BH、X_VolDens、Road_Dens 的**口径未确认**，只允许在无量纲化（标准化/排序/比值）后入模，且必须在候选登记中标注口径假设。',
         'declared_only', 'flags definition_uncertainty for these columns', None,
         '见 definition_uncertainty：X_BD max=%.3f、X_BH max=%.1f、几何恒等式 identity_holds=%s' %
         (domain['X_BD']['max'], domain['X_BH']['max'], geo['identity_holds'])),
    rule('DG-3', 'dimension_geometry', '几何派生量（覆盖率、高度、体量密度）必须满足几何合法性（非负、覆盖率不应显著 >1，体量非负）；越界须报告而非截断。',
         'enforceable', 'X_BD>=0, X_BH>=0, X_VolDens>=0, Road_Dens>=0',
         'Table 3 几何合法性；注意 X_BD 实测 >1 已登记为口径问题'),
    rule('DG-4', 'dimension_geometry', '温度运算区分 ℃ 与 K；涉及辐射（如 T⁴、Stefan–Boltzmann）时必须用绝对温度 T_K = T_℃ + 273.15。',
         'enforceable', 'radiation terms use T_K', 'Table 3 温度与辐射'),
]
# --- 测量边界 ---
HC += [
    rule('MB-1', 'measurement_boundary', 'LST 观测支持尺度为 30 m 像元；100 m 格为聚合单元。不得把重采样/聚合表述为"新的温度观测分辨率"。',
         'declared_only', None, 'S00.2 / Table 3 测量边界'),
    rule('MB-2', 'measurement_boundary', 'SVF 为 5 m 源，与 30 m LST 不同源；不得视为 5 m 温度观测，使用前须显式重采样并声明。',
         'declared_only', None, 'S00.2'),
    rule('MB-3', 'measurement_boundary', 'LST 不可当作气温（air temperature）使用。',
         'declared_only', None, 'Table 3'),
    rule('MB-4', 'measurement_boundary', '观测时间为单一时相、元数据不可恢复；禁止开展日/夜、季节、热恢复动态推断。',
         'enforceable', 'no time-phase claims', 'S00.1 / §2.2'),
]
# --- 物理一致性 ---
HC += [
    rule('PC-1', 'physics_consistency', '能量闭合 Rn + QF = H + LE + G 在当前数据下**无法求解**：无净辐射、人为热、感热、潜热、地热通量任一输入。',
         'not_computable', None, '§3.1 注：缺通量不得伪造能量残差。',
         '禁止构造能量残差或据其宣称物理一致性；该项留待增补通量数据（Table 16 进阶）。'),
    rule('PC-2', 'physics_consistency', '当前只允许执行"有数据支持"的物理一致性检查：量纲一致性、几何合法性、取值域、单调性/符号的**事后**审计（非预设）。',
         'declared_only', None, '§3.1'),
    rule('PC-3', 'physics_consistency', 'DEM 全域 3–17 m，不符合深圳实际地形（最高约 900 m 级）；在澄清口径前，DEM_mean 不得作为真实海拔或用于坡度/高程物理推断。',
         'not_computable', None, 'S00.2 与主样本实测域',
         'DEM_mean 实测 [%.1f, %.1f] m；疑为掩膜或重标定，须回溯作者。' % (domain['DEM_mean']['min'], domain['DEM_mean']['max'])),
]
# --- 统计诚信 ---
HC += [
    rule('SI-1', 'statistical_integrity', '看到锁定区 C 的测试结果后，不得修改同一轮的模型、指标、假设或停止条件。',
         'enforceable', 'protocol hash frozen before unsealing', 'Table 3 / §5.3'),
    rule('SI-2', 'statistical_integrity', '每轮实验只追加记录，不得覆盖失败结果；失败候选与反例必须保留。',
         'enforceable', 'append-only log', '§4.3'),
    rule('SI-3', 'statistical_integrity', '必须处理多重比较；搜索规模（候选数×检验数）须登记，偶然显著须以置换/分层等方法控制。',
         'enforceable', 'search size logged; multiplicity controlled', 'Table 13'),
    rule('SI-4', 'statistical_integrity', 'B 区参与调参后不再视为独立确认；仅 C 区（锁定）与 D（外部）可用于独立确认。',
         'enforceable', 'independent-confirmation source ∈ {C, D}', '§5.1 Table 11'),
]

# ---------------------------------------------------------------- 口径不确定清单
definition_uncertainty = [
    dict(var='X_BD', issue='最大值 %.3f > 1，不是 [0,1] 建筑覆盖率口径。' % domain['X_BD']['max'],
         evidence='主样本实测域', action='入模前无量纲化，登记口径假设；向作者回溯定义'),
    dict(var='X_BH', issue='最大值 %.1f m，作为 100 m 格"平均建筑高度"不合理（疑为最大值或求和）。' % domain['X_BH']['max'],
         evidence='主样本实测域', action='同上'),
    dict(var='X_VolDens', issue='与 X_BD·X_BH 的几何恒等式未证实：比值 p05/中位/p95 = %.3f/%.3f/%.3f。' % (geo['ratio_p05'], geo['ratio_median'], geo['ratio_p95']),
         evidence='主样本比值分布', action='不得假定恒等式；需作者给出体量密度定义'),
    dict(var='DEM_mean', issue='全域 3–17 m；深圳地形可达 ~900 m，疑为掩膜或重标定。',
         evidence='0_论文data/DEM_shenzhen.tif 与 DEM_30m_Final.tif', action='禁止高程物理推断，回溯作者'),
    dict(var='Road_Dens', issue='量纲未明（0–%.2f，%.0f%% 为 0）。' % (domain['Road_Dens']['max'], 100.0 * domain['Road_Dens']['zeros'] / n_main),
         evidence='主样本实测域', action='仅按无量纲/序数处理'),
    dict(var='NDVI 研究区栅格', issue='文件名拼写为 NVDI_shenzhen.tif。', evidence='data/0_论文data/',
         action='记录，不影响数值；登记为命名瑕疵'),
]

# ---------------------------------------------------------------- §3.2 无方向预设
NO_DIRECTION = [
    '禁止在系统提示词中规定 NDVI 必须单调降温（或升温）。',
    '禁止规定 SVF 必须升温或必须降温。',
    '禁止规定建筑高度/体量必须产生某一方向的热响应。',
    '禁止预设最优空间尺度（不得指定唯一 r）。',
    '禁止预设固定函数形式（不得指定线性/幂律/树模型等）。',
    '禁止预设单一显著阈值（不得写死如 p<0.05 作为唯一判据）。',
    '禁止预设特定交互组合或变量清单。',
    '不得注入旧论文结论、相关矩阵或用于引导特定发现的文献摘要。',
    '允许：数据字典、计算定义、基础物理知识、预注册的计算工具与搜索预算。',
]

# ---------------------------------------------------------------- C) 数据字典
DD = []
DD.append('# Stage 01 中性数据字典（S01.3）\n')
DD.append('> 本字典只提供**计算定义与实测域**，不含任何关系方向、函数形式或显著性结论。\n')
DD.append('> 生成版本 %s，%s；主样本 n=%d（100 m 格）。\n' % (VERSION, CREATED, n_main))
DD.append('| 变量 | 计算定义（口径状态） | 单位 | 主样本实测域 [min, p05, 中位, p95, max] | 0 值数 | 口径可靠性 |')
DD.append('|---|---|---|---|---|---|')
DDDEF = {
    'LST_mean': ('格内 30 m 有效像元 LST 算术均值（有效=非 −9999 且非 0）', '℃', '高'),
    'NDVI_mean': ('格内 30 m 有效像元 NDVI 算术均值（有效=非 −9999）', '无量纲', '中（全市场栅格有非物理值）'),
    'DEM_mean': ('格内 30 m 有效像元 DEM 算术均值', 'm（存疑）', '低（域 3–17 m 不合地形）'),
    'SVF_mean': ('格内 5 m SVF 聚合均值（0 全遮蔽—1 全开阔）', '无量纲', '中（5 m 源，需显式重采样）'),
    'Road_Dens': ('道路密度（口径未确认）', '未确认', '低（量纲未明）'),
    'X_BD': ('建筑覆盖指标（口径未确认；max>1）', '未确认', '低'),
    'X_BH': ('建筑高度指标（口径未确认；max 达 224 m）', 'm（存疑）', '低'),
    'X_VolDens': ('建筑体量密度（口径未确认；与 BD·BH 恒等式未证实）', '未确认', '低'),
}
for c in VARS:
    e = domain[c]
    defn, unit, rel = DDDEF[c]
    DD.append('| `%s` | %s | %s | [%.4f, %.4f, %.4f, %.4f, %.4f] | %d | %s |'
              % (c, defn, unit, e['min'], e['p05'], e['median'], e['p95'], e['max'], e['zeros'], rel))
DD.append('')
DD.append('空间坐标：分析网格为 100 m×100 m，EPSG:32649，行索引=北向、列索引=东向；')
DD.append('分区（A/B/C）见 `split/split_manifest.json`，本字典不披露任何分区与目标的分配。\n')
DD.append('## 口径不确定性（须回溯作者，不参与入模方向假设）\n')
for u in definition_uncertainty:
    DD.append('- **%s**：%s（依据：%s；处理：%s）' % (u['var'], u['issue'], u['evidence'], u['action']))

with open(os.path.join(C.S01_CONSTRAINTS, 'DATA_DICTIONARY.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(DD))

# ---------------------------------------------------------------- D) 无方向预设声明
NP = []
NP.append('# §3.2 无方向预设声明（系统提示词禁用清单）\n')
NP.append('框架依据：§3.2「不得在系统提示词中规定 NDVI 必须单调降温、SVF 必须升温或降温或')
NP.append('建筑高度必须产生某一方向的热响应；不预设最优空间尺度、固定函数形式、单一显著阈值或特定交互组合。」\n')
NP.append('因此，向任何发现/实验 Agent 注入的系统提示词中，**以下主张与词条一律禁止**：\n')
for i, s in enumerate(NO_DIRECTION, 1):
    NP.append('%d. %s' % (i, s))
NP.append('\n**允许注入**：本目录 `DATA_DICTIONARY.md`、`hard_constraints.json`、计算预算、工具白名单。')
NP.append('\n**审计**：每轮实验前，Agent manifest 需声明所用系统提示词哈希；')
NP.append('Physics Auditor 独立检查提示词是否含上列禁用方向（S01.4 冻结）。')

with open(os.path.join(C.S01_CONSTRAINTS, 'no_direction_preset.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(NP))

# ---------------------------------------------------------------- JSON 落盘
HCJ = dict(version=VERSION, created=CREATED, n_main=n_main,
           source={'csv': 'data/data_原始.csv', 'mask': 'stage00_data_audit/mask/valid_ids_main.txt'},
           measured_domain=domain, geometry_identity_check=geo,
           hard_constraints=HC, definition_uncertainty=definition_uncertainty,
           no_direction_preset=NO_DIRECTION,
           summary=dict(
               n_rules=len(HC),
               enforceable=int(sum(1 for r in HC if r['status'] == 'enforceable')),
               declared_only=int(sum(1 for r in HC if r['status'] == 'declared_only')),
               not_computable=int(sum(1 for r in HC if r['status'] == 'not_computable'))))
with open(os.path.join(C.S01_CONSTRAINTS, 'hard_constraints.json'), 'w', encoding='utf-8') as f:
    json.dump(HCJ, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- Markdown 报告
L = []
L.append('# S01.3 物理约束与硬约束规则\n')
L.append('框架依据：§3.1 硬约束（Table 3）、§3.2 无方向预设、Table 11 M1「独立发布可计算硬约束，不发布关系方向」。\n')
L.append('清单版本 **%s**，%s。\n' % (VERSION, CREATED))
L.append('## 1 主样本实测域（硬约束取值依据）\n')
L.append('| 变量 | min | p05 | 中位 | p95 | max | 0 值 |')
L.append('|---|---|---|---|---|---|---|')
for c in VARS:
    e = domain[c]
    L.append('| `%s` | %.4f | %.4f | %.4f | %.4f | %.4f | %d |'
             % (c, e['min'], e['p05'], e['median'], e['p95'], e['max'], e['zeros']))
L.append('')
L.append('几何恒等式核验：X_VolDens/(X_BD·X_BH) 的 p05/中位/p95 = %.3f/%.3f/%.3f，**identity_holds=%s**。'
         % (geo['ratio_p05'], geo['ratio_median'], geo['ratio_p95'], geo['identity_holds']))
L.append('')
L.append('## 2 硬约束集（%d 条）\n' % len(HC))
L.append('| ID | 类别 | 约束 | 状态 |')
L.append('|---|---|---|---|')
CATCN = {'data_validity': '数据有效性', 'dimension_geometry': '量纲与几何',
         'measurement_boundary': '测量边界', 'physics_consistency': '物理一致性',
         'statistical_integrity': '统计诚信'}
STCN = {'enforceable': '可执行', 'declared_only': '仅声明', 'not_computable': '不可计算'}
for r in HC:
    L.append('| %s | %s | %s | %s |' % (r['id'], CATCN[r['category']], r['statement'], STCN[r['status']]))
L.append('')
L.append('汇总：可执行 **%d** 条、仅声明 %d 条、不可计算 %d 条。'
         % (HCJ['summary']['enforceable'], HCJ['summary']['declared_only'], HCJ['summary']['not_computable']))
L.append('')
L.append('> **不可计算项的现实依据**：能量闭合缺全部通量输入；DEM 全域 3–17 m 不符合深圳地形。')
L.append('> 二者在补齐数据前不得据此宣称任何物理机制一致性（禁止伪造能量残差）。\n')
L.append('## 3 口径不确定性（须回溯作者）\n')
L.append('| 变量 | 问题 | 处理 |')
L.append('|---|---|---|')
for u in definition_uncertainty:
    L.append('| %s | %s | %s |' % (u['var'], u['issue'], u['action']))
L.append('')
L.append('## 4 无方向预设（§3.2）\n')
L.append('已冻结 %d 条系统提示词禁用主张，完整清单见 `constraints/no_direction_preset.md`。' % len(NO_DIRECTION))
L.append('允许注入的只有：`DATA_DICTIONARY.md`、`hard_constraints.json`、计算预算与工具白名单。\n')
L.append('## 5 交付物\n')
L.append('| 类型 | 路径 |')
L.append('|---|---|')
L.append('| 机器可读硬约束 | `constraints/hard_constraints.json` |')
L.append('| 中性数据字典 | `constraints/DATA_DICTIONARY.md` |')
L.append('| 无方向预设声明 | `constraints/no_direction_preset.md` |')
L.append('| 本报告 | `reports/s01_03_constraints.md` / `.json` |')

with open(os.path.join(C.S01_REPORTS, 's01_03_constraints.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))
with open(os.path.join(C.S01_REPORTS, 's01_03_constraints.json'), 'w', encoding='utf-8') as f:
    json.dump(HCJ, f, ensure_ascii=False, indent=2)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


print(json.dumps(dict(version=VERSION, n_rules=len(HC), summary=HCJ['summary'],
                      identity_holds=geo['identity_holds'],
                      dom={k: [v['min'], v['max']] for k, v in domain.items()}),
                 ensure_ascii=False, indent=2))
print('\n写出: constraints/hard_constraints.json, constraints/DATA_DICTIONARY.md, '
      'constraints/no_direction_preset.md, reports/s01_03_constraints.md/.json')
