"""
S01.5 预注册协议与 Stage 01 哈希清单
======================================
目的：把 Stage 01 的规则冻结为一份可审计、可哈希的预注册文档，并冻结全部产物哈希。

框架依据：
  Table 17「Stage 01 规则冻结：定义约束、空间切分、主指标、预算与权限 → 交付物：预注册协议与清单哈希。」
  Table 12 六清单；§5.2 需要冻结的对象；§7 证据分类；§10 关键风险。

输出：
  PREREGISTRATION.md
  manifest/stage01_hashes.txt
  reports/s01_05_preregistration.json
"""
import sys, os, json, hashlib, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import config as C

CREATED = '2026-09-24'
PREREG_VERSION = 'stage01-prereg-v1'

# ---------------------------------------------------------------- 汇总上游结论
sa = json.load(open(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.json'), encoding='utf-8'))
sm = json.load(open(os.path.join(C.S01, 'split', 'split_manifest.json'), encoding='utf-8'))
hc = json.load(open(os.path.join(C.S01_CONSTRAINTS, 'hard_constraints.json'), encoding='utf-8'))
am = json.load(open(os.path.join(C.S01, 'agent', 'agent_manifest.json'), encoding='utf-8'))
ep = json.load(open(os.path.join(C.S01, 'protocol', 'experiment_protocol.json'), encoding='utf-8'))
vp = json.load(open(os.path.join(C.S01, 'protocol', 'validation_protocol.json'), encoding='utf-8'))
cm = json.load(open(os.path.join(C.S01_MANIFEST, 'code_manifest.json'), encoding='utf-8'))

R_cells = sa['recommendation']['R_cells']
zpost = sm['zone_size_post_buffer']
fpost = sm['fractions_post_buffer']

# ---------------------------------------------------------------- 证据分类
EVID = [
    ('L1 探索性模式', '仅在发现/开发集存在', '待确认候选，不称为新规律'),
    ('L2 空间稳健关系', '深圳锁定空间区（C）重复成立', '适用于被检验的观测条件'),
    ('L3 外部支持关系', '独立时相/城市（D）重复成立', '明确迁移范围及条件'),
    ('L4 机制进一步验证', '补充独立物理或干预证据', '可谨慎讨论机制，不超越证据'),
]

# ---------------------------------------------------------------- 需要冻结的对象
FREEZE = [
    ('Data manifest', '数据来源/版本/掩膜/路径/SHA-256', 'stage00_data_audit/manifest/data_sha256.txt'),
    ('Split manifest', '空间分块规则/分区 ID/缓冲/种子/版本', 'split/split_manifest.json'),
    ('Agent manifest', '模型版本/系统提示词/工具白名单/权限/预算', 'agent/agent_manifest.json'),
    ('Experiment protocol', '候选上限/开发指标/停止条件/失败记录', 'protocol/experiment_protocol.json'),
    ('Validation protocol', '主终点/空间推断/多重比较/缺失/通过条件', 'protocol/validation_protocol.json'),
    ('Code manifest', '依赖环境/数据变换脚本/哈希', 'manifest/code_manifest.json'),
]

# ---------------------------------------------------------------- Markdown 预注册
L = []
L.append('# 预注册协议（Stage 01 规则冻结）\n')
L.append('**项目**：物理约束下城市地表热环境规律的 AI 自主科学发现研究框架（PAID）  ')
L.append('**阶段**：Stage 01 规则冻结（Table 17）  ')
L.append('**版本**：%s  |  **冻结日期**：%s\n' % (PREREG_VERSION, CREATED))
L.append('> 本协议在开放正式发现环境（Stage 02 及以后）之前冻结。')
L.append('> 一旦冻结，M2 发现阶段中途不得更改约束、切分、主指标、预算与权限；')
L.append('> 任何更改都构成新一轮预注册，须重走防火墙（§5.3）。\n')

L.append('## 1 研究范围限定（源自 Stage 00）\n')
L.append('- 观测元数据（时间/传感器/反演算法/QA）不可恢复 → 研究**限定为单一时相的空间分异**；')
L.append('  日/夜、季节、热恢复动态分析一律不开展（S00.1，硬约束 MB-4）。')
L.append('- 数据基线：`data/` 99 个原始文件、896.6 MB，SHA-256 见 Stage 00 manifest。')
L.append('- 分析单元：100 m×100 m 网格（EPSG:32649），共 32748 格；')
L.append('  **主样本 %d 格**（发现与建模），放宽样本 %d 格（仅稳健性复核）。\n'
         % (hc['n_main'], 32246))

L.append('## 2 数据隔离设计（§5.1 发现—验证防火墙）\n')
L.append('空间划分依据 S01.1 的**去相关尺度 R**：去趋势残差仍显著自相关'
         '（Moran’s I=%.3f，伪 p=%.4f），建成/中层 r(k) 降至 0.2 的最大滞后 %d 格，'
         '故取 **R = %d 格 = %.1f km**。\n'
         % (sa['morans_I_detrended']['I'], sa['morans_I_detrended']['p_value'],
            sm['R_cells'], R_cells, sm['R_m'] / 1000.0))
L.append('> 注：下表「格数/占比」为**缓冲后分析样本**（A+B+C = %d 格；主样本 %d 格中的 3407 格'
         '进入缓冲带、不再参与发现或验证），分母非主样本。\n'
         % (zpost['1'] + zpost['2'] + zpost['3'], hc['n_main']))
L.append('| 数据层 | 格数 | 占缓冲后样本 | 权限 |')
L.append('|---|---|---|---|')
L.append('| A 发现区 | %d | %.1f%% | Agent 可多次实验、修改假设 |' % (zpost['1'], 100 * fpost['discovery']))
L.append('| B 开发验证区 | %d | %.1f%% | 方法筛选与稳健性；参与调参后不再视为独立确认 |' % (zpost['2'], 100 * fpost['dev_validation']))
L.append('| C 锁定区 | %d | %.1f%% | 仅 Independent Validator 持有目标值，候选冻结后解封 |' % (zpost['3'], 100 * fpost['locked']))
L.append('| D 外部验证集 | — | — | 新时相/新地区，独立收集，不从 A–C 再切分 |')
L.append('')
L.append('- 缓冲：仅对 C 施加，剔除 C 中距 A∪B < R 的 %d 格；A 与 B 同属开发域，不设内部缓冲。'
         % sm['buffer_cells'])
L.append('- 距离核验：C↔A∪B = %d 格 ≥ R = %d 格（八邻域膨胀测距）。'
         % (sm['min_distance_cells']['C_to_AB'], sm['R_cells']))
L.append('- C 区连通性：缓冲后连通分量数 = %d（保持空间连续，非碎片化）。'
         % sm['connectivity']['C_components_after_buffer'])
L.append('- 禁随机抽格：划分基于 5 个连通 k-means 簇整簇指派（seed %d）。\n' % sm['seed'])

L.append('## 3 已知局限（须在论文如实声明）\n')
L.append('1. **地表覆盖偏斜**：连通分块下 C 区的 NDVI 三分位构成为 [%.3f, %.3f, %.3f]，'
         '偏离全局 [0.333, 0.333, 0.333]（指派时的 L1 距离 0.2445，见 S01.2 报告）。'
         '这是连续空间分区与深圳地表覆盖空间聚集共同导致的内在局限，非抽样失误；'
         'L2 结论的适用范围须据此限定。'
         % (sm['landcover_post']['locked']['ndvi_tercile_share'][0],
            sm['landcover_post']['locked']['ndvi_tercile_share'][1],
            sm['landcover_post']['locked']['ndvi_tercile_share'][2]))
L.append('2. **口径未确认的协变量**：X_BD（max %.2f）、X_BH（max %.1f m）、X_VolDens（与 X_BD·X_BH '
         '恒等式未证实）、DEM（%.0f–%.0f m，不合地形）、Road_Dens（量纲未明）——'
         '仅可无量纲化入模，且须登记口径假设（§3 硬约束 DG-2 / PC-3）。'
         % (hc['measured_domain']['X_BD']['max'], hc['measured_domain']['X_BH']['max'],
            hc['measured_domain']['DEM_mean']['min'], hc['measured_domain']['DEM_mean']['max']))
L.append('3. **不可逆缺口**：观测元数据缺失；CSV 导出时的 61 格剔除条件与栅格二次掩膜依据未留存。')
L.append('4. **预训练先验**：不得宣称 Agent 无绝对先验；可操作主张为「提示词不注入目标领域结论、'
         '研究者不按结果引导、全过程可审计」（§4.3）。\n')

L.append('## 4 物理约束与无方向预设（§3）\n')
L.append('- 硬约束 **%d 条**（可执行 %d / 仅声明 %d / 不可计算 %d），见 `constraints/hard_constraints.json`。'
         % (hc['summary']['n_rules'], hc['summary']['enforceable'],
            hc['summary']['declared_only'], hc['summary']['not_computable']))
L.append('- 能量闭合、DEM 高程推断标为 **not_computable**：缺通量输入、DEM 值不合地形，'
         '禁止伪造能量残差或机制叙事。')
L.append('- 无方向预设：冻结 %d 条系统提示词禁用主张（NDVI/SVF/建高方向、最优尺度、固定函数式、'
         '单一显著阈值、交互组合），见 `constraints/no_direction_preset.md`。\n' % len(hc['no_direction_preset']))

L.append('## 5 冻结六清单（Table 12）\n')
L.append('| 清单 | 最低内容 | 路径 |')
L.append('|---|---|---|')
for nm, cont, path in FREEZE:
    L.append('| %s | %s | `%s` |' % (nm, cont, path))
L.append('')

L.append('## 6 Agent 权限与预算\n')
L.append('| Agent | 可访问数据 | 禁止访问 |')
L.append('|---|---|---|')
for a in am['agents']:
    L.append('| %s | %s | %s |' % (a['agent'], '、'.join(a['data_access']), '；'.join(a['forbidden_access'])))
L.append('')
L.append('- 候选上限：每轮 ≤ %d；总 fit 预算 %d；冻结候选 ≤ %d。'
         % (ep['candidate_cap']['per_round_max'], ep['candidate_cap']['total_fit_budget'],
            ep['candidate_cap']['freeze_max']))
L.append('- 开发主指标：%s。' % ep['dev_metrics']['primary'])
L.append('- 停止条件：%s\n' % '；'.join(ep['stopping_conditions']))

L.append('## 7 验证协议要点\n')
L.append('- 主终点：%s；通过条件：%s' % (vp['primary_endpoint']['statistic'], vp['primary_endpoint']['pass_rule']))
L.append('- 空间推断：%d 次空间块置换；多重比较：%s缺失：%s'
         % (vp['spatial_inference']['block_permutation'],
            vp['multiplicity']['control'].replace('。', '；'),
            vp['missing_data']['handling']))
L.append('- 解封原则：哈希≠访问控制；C 目标值存于发现 Agent 无权读取的独立目录/服务；'
         '验证只接受已冻结候选，发布完整通过/失败（§5.3）。\n')

L.append('## 8 证据分类与结论边界（§7）\n')
L.append('| 类别 | 证据要求 | 表述边界 |')
L.append('|---|---|---|')
for a, b, c in EVID:
    L.append('| %s | %s | %s |' % (a, b, c))
L.append('')
L.append('允许 AI 最终得出「尚无经独立验证的新规律」的结论；科学价值由可复核的发现与证据决定，'
         '而非候选数量或预测精度（§10）。\n')

L.append('## 9 Stage 02 门禁条件\n')
L.append('- [x] 数据基线与掩膜冻结（Stage 00）；')
L.append('- [x] 去相关尺度 R 与空间划分冻结（S01.1–01.2）；')
L.append('- [x] 硬约束与无方向预设冻结（S01.3）；')
L.append('- [x] 四清单（Agent/实验/验证/代码）冻结（S01.4）；')
L.append('- [x] 预注册协议与产物哈希冻结（S01.5）；')
L.append('- [ ] **待用户确认**：授权进入 Stage 02（平台构建：Agent、沙箱、追加日志、验证服务）。\n')
L.append('> Stage 02 首要任务是**访问控制的物理实现**与**泄漏测试**：')
L.append('> C 区目标值移入发现 Agent 无权读取的独立目录/服务，并以泄漏测试验证防火墙有效（Table 17）。\n')

with open(os.path.join(C.S01, 'PREREGISTRATION.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))

# ---------------------------------------------------------------- Stage 01 哈希清单
# 两份元文件互相自指，故分两步：先冻结 json（不含自身与清单），再据此写清单（含 json）。
META_JSON = 'reports/s01_05_preregistration.json'
META_HASH = 'manifest/stage01_hashes.txt'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


OS_JUNK = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}


def walk_rows():
    out = []
    for dirpath, dirs, files in os.walk(C.S01):
        for fn in sorted(files):
            if fn.startswith('.') or fn in OS_JUNK:   # 排除 OS 元数据，非研究产物
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, C.S01).replace(os.sep, '/')
            if rel in (META_HASH, META_JSON):
                continue
            out.append((rel, os.path.getsize(p), sha256(p)))
    return sorted(out)


rows = walk_rows()                       # 除两份元文件外的全部产物
R = dict(prereg_version=PREREG_VERSION, created=CREATED,
         n_stage01_files=len(rows) + 1,  # +1 = 本 json 自身（由 stage01_hashes.txt 冻结）
         files=[dict(path=r[0], bytes=r[1], sha256=r[2]) for r in rows],
         freeze_version=dict(split=sm['version'], constraints=hc['version'],
                             agent=am['version'], experiment=ep['version'],
                             validation=vp['version'], code=cm['version']))
json_path = os.path.join(C.S01_REPORTS, 's01_05_preregistration.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(R, f, ensure_ascii=False, indent=2)

# 清单 = 全部产物（含最终的 json，不含清单自身）
rows_final = sorted(rows + [(META_JSON, os.path.getsize(json_path), sha256(json_path))])
with open(os.path.join(C.S01_MANIFEST, 'stage01_hashes.txt'), 'w') as f:
    f.write('# Stage 01 产物 SHA-256 清单（相对 stage01_protocol/；不含本清单自身）\n')
    for rel, size, h in rows_final:
        f.write('%s  %10d  %s\n' % (h, size, rel))

print(json.dumps(dict(prereg_version=PREREG_VERSION, n_stage01_files=len(rows_final),
                      freeze_version=R['freeze_version']), ensure_ascii=False, indent=2))
print('\n写出: PREREGISTRATION.md, manifest/stage01_hashes.txt, reports/s01_05_preregistration.json')
