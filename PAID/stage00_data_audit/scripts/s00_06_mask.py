"""
S00.6 生成有效数据掩膜
=======================
汇总 S00.3–S00.5 的判定，输出逐格掩膜与"可用主样本"清单，并画出掩膜空间分布图。
框架依据：§2.2「建立有效掩膜」；§8.2 Stage 00 交付物。

排除规则（主样本 use_main）：
  1) 不在 CSV（61 个，原因不可复现）
  2) 核心列缺失：LST/NDVI/DEM/SVF/Road 任一为 NaN
  3) 幻影格：LST 栅格无任何有效像元中心（CSV 值无栅格支撑）
  4) LST_mean==0：确认为"无数据写成 0"的填充值
  5) 不可复算格：CSV 值与栅格复算不符（含边界残差；其值由 1–2 个像元决定，噪声大）
放宽样本（use_relaxed）：只排除 1)2)3)4)，保留 5)。
另记录 grid_validity.csv 的 flag_boundary_partial（0<有效像元<总）作为诊断量，不直接用于排除。

输出：mask/analysis_mask.csv, mask/valid_ids_main.txt, reports/s00_06_mask.json / .md,
      reports/figures/s00_06_mask_map.png
"""
import sys, os, json, csv as _csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import geoio as g
import config as C
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs(C.S00_REPORTS, exist_ok=True)
os.makedirs(C.S00_MASK, exist_ok=True)
FIG = os.path.join(C.S00_REPORTS, 'figures')
os.makedirs(FIG, exist_ok=True)
R = {}

# ---- 读取网格与已有标记
grid_recs, _, _ = g.read_dbf(os.path.join(C.DATA, '研究边界/grid_utm.dbf'))
info = {}
for r in grid_recs:
    gid = int(r['Grid_ID'])
    info[gid] = dict(row=int(r['row_index']), col=int(r['col_index']),
                     left=float(r['left']), top=float(r['top']))
gv = pd.read_csv(os.path.join(C.S00_MASK, 'grid_validity.csv'))
gv = gv.set_index('Grid_ID')
df = pd.read_csv(C.CSV)
df.columns = [c.strip() for c in df.columns]
df = df.set_index('My_ID')

core_cols = ['LST_mean', 'NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens']
all_ids = sorted(info)

reason = {}
use_main = {}
use_relaxed = {}
for gid in all_ids:
    rs = []
    if gid not in gv.index:
        rs.append('not_in_grid_validity')
    if gid not in df.index:
        rs.append('not_in_csv')
        reason[gid] = rs
        continue
    row = df.loc[gid]
    if any(pd.isna(row[c]) for c in core_cols):
        rs.append('core_nan')
    if int(gv.loc[gid, 'flag_phantom']) == 1:
        rs.append('phantom_no_raster_support')
    if int(gv.loc[gid, 'flag_lst_zero']) == 1:
        rs.append('lst_zero_fill')
    if int(gv.loc[gid, 'flag_repro_mismatch']) == 1:
        rs.append('not_reproducible')
    reason[gid] = rs
    use_main[gid] = (len(rs) == 0)
    use_relaxed[gid] = all(r0 in ('not_reproducible',) for r0 in rs) or len(rs) == 0

# 也把 core_nan 之外的其它列情况记下：SVF/Road 缺失会落在 core_nan
n_main = sum(use_main.values())
n_relaxed = sum(use_relaxed.values())
R['mask'] = dict(n_grid=len(all_ids), n_main=n_main, n_relaxed=n_relaxed,
                 n_in_csv=int((df.index.isin(all_ids)).sum()))
# 漏斗
funnel = []
step = set(all_ids)
funnel.append(('网格总数', len(step)))
step &= set(df.index)
funnel.append(('在 CSV 中', len(step)))
nan_set = set(gid for gid in step if any(pd.isna(df.loc[gid, c]) for c in core_cols))
funnel.append(('核心列完整', len(step - nan_set)))
step -= nan_set
ph = set(gv.index[gv['flag_phantom'] == 1]) & step
funnel.append(('LST 有栅格支撑', len(step - ph)))
step -= ph
lz = set(gv.index[gv['flag_lst_zero'] == 1]) & step
funnel.append(('非 LST 零填充（放宽样本）', len(step - lz)))
step -= lz
bp = set(gv.index[gv['flag_repro_mismatch'] == 1]) & step
funnel.append(('值可复现（主样本）', len(step - bp)))
R['funnel'] = funnel
# 边界诊断：被 not_reproducible 排除的格里，LST 有效像元占比分布
excl = sorted(bp)
fr = [(float(gv.loc[g, 'lst_valid_px']) / max(1.0, float(gv.loc[g, 'lst_total_px']))) for g in excl if float(gv.loc[g, 'lst_total_px']) > 0]
R['not_reproducible_diag'] = dict(
    n=len(excl),
    n_valid_frac_lt_0p5=int(sum(1 for x in fr if x < 0.5)),
    n_valid_frac_lt_0p2=int(sum(1 for x in fr if x < 0.2)),
    n_boundary_partial_in_union=int(len(set(gv.index[gv['flag_boundary_partial'] == 1]) & set(excl))))
R['exclusion_counts'] = {}
for rs in reason.values():
    for r0 in rs:
        R['exclusion_counts'][r0] = R['exclusion_counts'].get(r0, 0) + 1

# ---- 输出掩膜表
with open(os.path.join(C.S00_MASK, 'analysis_mask.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh)
    w.writerow(['Grid_ID', 'row', 'col', 'use_main', 'use_relaxed', 'exclusion'])
    for gid in all_ids:
        i = info[gid]
        w.writerow([gid, i['row'], i['col'], int(use_main.get(gid, False)),
                    int(use_relaxed.get(gid, False)), ';'.join(reason.get(gid, []))])
with open(os.path.join(C.S00_MASK, 'valid_ids_main.txt'), 'w') as fh:
    fh.write('\n'.join(str(g) for g in all_ids if use_main.get(g, False)))
with open(os.path.join(C.S00_MASK, 'valid_ids_relaxed.txt'), 'w') as fh:
    fh.write('\n'.join(str(g) for g in all_ids if use_relaxed.get(g, False)))

# ---- 掩膜图
fig, ax = plt.subplots(figsize=(12, 9), dpi=150)
xs = np.array([info[g]['left'] for g in all_ids]) / 1000.0
ys = np.array([-info[g]['top'] for g in all_ids]) / 1000.0
cat = np.array([0 if g not in df.index else (1 if not use_relaxed.get(g, False) else (2 if not use_main.get(g, False) else 3))
                for g in all_ids])
labels = ['invalid/not in CSV', 'excluded (NaN/phantom/zero-fill)', 'relaxed (incl. non-reproducible)', 'main sample']
colors = ['#d9d9d9', '#f4a582', '#fddbc7', '#2166ac']
for k in range(4):
    m = cat == k
    ax.scatter(xs[m], ys[m], s=1.2, c=colors[k], label='%s (n=%d)' % (labels[k], int(m.sum())), linewidths=0)
ax.set_aspect('equal'); ax.legend(markerscale=8, fontsize=9, loc='upper right')
ax.set_xlabel('UTM49N Easting (km)'); ax.set_ylabel('UTM49N Northing (km, shown negated)')
ax.set_title('S00.6 valid-data mask, 100 m grid (n=%d cells)' % len(all_ids))
fig.tight_layout(); fig.savefig(os.path.join(FIG, 's00_06_mask_map.png')); plt.close(fig)

with open(os.path.join(C.S00_REPORTS, 's00_06_mask.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2)

# ---- Markdown
L = []
L.append('# S00.6 有效数据掩膜\n')
L.append('框架依据：§2.2「建立有效掩膜」；§8.2 Stage 00 交付物。\n')
L.append('## 逐级排除漏斗\n')
L.append('| 步骤 | 剩余格数 |')
L.append('|---|---|')
for name, n in funnel:
    L.append('| %s | %d |' % (name, n))
L.append('')
L.append('## 排除原因计数（同一格可命中多条）\n')
L.append('| 原因 | 格数 |')
L.append('|---|---|')
for k, v in sorted(R['exclusion_counts'].items(), key=lambda kv: -kv[1]):
    L.append('| `%s` | %d |' % (k, v))
L.append('')
L.append('## 掩膜分层\n')
L.append('| 层 | 格数 | 用途 |')
L.append('|---|---|---|')
L.append('| 全部网格 | %d | 边界 |' % R['mask']['n_grid'])
L.append('| **主样本 `use_main`** | **%d** | 发现/建模主样本（值可复现、字段完整） |' % R['mask']['n_main'])
L.append('| 放宽样本 `use_relaxed` | %d | 敏感性检验（额外保留不可复算的边界格） |' % R['mask']['n_relaxed'])
L.append('')
d = R['not_reproducible_diag']
L.append('## 被主样本排除的"不可复算格"诊断\n')
L.append('- 共 %d 格，其中 LST 有效像元占比 <50%% 的 %d 格、<20%% 的 %d 格；' % (d['n'], d['n_valid_frac_lt_0p5'], d['n_valid_frac_lt_0p2']))
L.append('  与 `flag_boundary_partial` 交集 %d 格。可见被排除者绝大多数是**有效像元很少的边界格**。\n' % d['n_boundary_partial_in_union'])
L.append('## 说明\n')
L.append('- 主样本口径：核心列完整、LST 有栅格支撑（非幻影）、非零填充、且 **CSV 值可由栅格复算**。')
L.append('- 放宽样本额外保留"值不可复算"的边界格，仅用于稳健性检验；两类样本的差异会量化"边界格对结论的影响"。')
L.append('- 若后续实证显示边界格并不显著影响结论，可将放宽样本并入，但**必须以预注册方式声明**（Stage 01）。')
L.append('- 掩膜逐格清单见 `mask/analysis_mask.csv`；主样本 ID 列表见 `mask/valid_ids_main.txt`。')

with open(os.path.join(C.S00_REPORTS, 's00_06_mask.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps({'mask': R['mask'], 'funnel': funnel, 'exclusion_counts': R['exclusion_counts']},
                 ensure_ascii=False, indent=2))
print('\n写出: mask/analysis_mask.csv, valid_ids_main.txt, reports/s00_06_mask.json / .md, figures/s00_06_mask_map.png')
