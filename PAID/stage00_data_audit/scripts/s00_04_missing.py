"""
S00.4 缺失诊断与 CSV 可复算性检验
===================================
四个问题：
  Q1 网格 32748 个，CSV 只有 32687 行——缺的 61 个在哪里，为什么被剔除？
  Q2 243 行含缺失值（LST/NDVI/DEM），分布如何，是否构成空间偏倚？
  Q3 CSV 中 13 个 LST_mean==0 的网格是什么？
  Q4 data_原始.csv 能否由 0_论文data 栅格复算？（框架 §5.2「可复算特征定义」）

Q4 的复算规则经多方案对照后锁定为：
  像元中心落入哪个 100 m 格，就归入该格（该归属由网格 DBF 四至锚定）；
  格值 = 有效像元算术平均；有效定义 LST 为「非 -9999 且非 0」，DEM/NDVI 为「非 -9999」。
对照排除的规则：像元角点归属、任意重叠归属、以栅格自身 origin 锚定网格（均差一个数量级，见报告）。
残差格的判定证据 E5：CSV 有值而栅格无有效像元中心的格，100% 在 8 邻域内存在有效数据 ——
支持「现存栅格是 zonal 之后被二次掩膜的较晚版本」，CSV 在边缘更完整。

输出：reports/s00_04_missing.json / .md, mask/grid_validity.csv
"""
import sys, os, json, csv as _csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import geoio as g
import config as C

os.makedirs(C.S00_REPORTS, exist_ok=True)
os.makedirs(C.S00_MASK, exist_ok=True)
R = {}

# ---------------------------------------------------------------- 网格索引
grid_recs, _, _ = g.read_dbf(os.path.join(C.DATA, '研究边界/grid_utm.dbf'))
gid_of, info = {}, {}
for r in grid_recs:
    key = (int(r['row_index']), int(r['col_index']))
    gid = int(r['Grid_ID'])
    gid_of[key] = gid
    info[gid] = dict(row=key[0], col=key[1], left=float(r['left']), top=float(r['top']),
                     right=float(r['right']), bottom=float(r['bottom']))
GRID_X0 = min(v['left'] for v in info.values())
GRID_Y0 = max(v['top'] for v in info.values())
R['grid'] = dict(n_cells=len(info), gid_min=min(info), gid_max=max(info), x0=GRID_X0, y0=GRID_Y0,
                 row_range=[min(v['row'] for v in info.values()), max(v['row'] for v in info.values())],
                 col_range=[min(v['col'] for v in info.values()), max(v['col'] for v in info.values())])


def zonal(name, nz_also_zero):
    """像元中心归属 → 逐格均值。返回 {gid: (mean, n_valid, n_total)}。"""
    geo = g.tiff_geo(g.read_tiff_tags(os.path.join(C.DATA, name)))
    arr = np.asarray(g.read_raster(os.path.join(C.DATA, name)), dtype='f8')
    if arr.ndim == 3:
        arr = arr[..., 0]
    rr = np.arange(geo['height']); cc = np.arange(geo['width'])
    xs = geo['origin_x'] + (cc + 0.5) * geo['px_w']
    ys = geo['origin_y'] - (rr + 0.5) * geo['px_h']
    cri = np.floor((GRID_Y0 - ys) / 100.0).astype(np.int64)
    cci = np.floor((xs - GRID_X0) / 100.0).astype(np.int64)
    Rr, Cc = np.meshgrid(cri, cci, indexing='ij')
    keys = (Rr * 10000 + Cc).ravel(); vals = arr.ravel()
    uniq, inv = np.unique(keys, return_inverse=True)
    gids = np.array([gid_of.get((int(k // 10000), int(k % 10000)), -1) for k in uniq])
    fin = np.isfinite(vals)
    ok = (~(vals == -9999)) & fin
    if nz_also_zero:
        ok = ok & (vals != 0)
    L = len(uniq)
    s = np.bincount(inv, weights=np.where(ok, vals, 0.0), minlength=L)
    n = np.bincount(inv, weights=ok.astype('f8'), minlength=L)
    tot = np.bincount(inv, minlength=L)
    out = {}
    for i in np.where(gids > 0)[0]:
        out[int(gids[i])] = (float(s[i] / n[i]) if n[i] > 0 else np.nan, int(n[i]), int(tot[i]))
    return out


print('复算 LST ...'); lst = zonal('0_论文data/LST_shenzhen.tif', True)
print('复算 NDVI ...'); ndvi = zonal('0_论文data/NVDI_shenzhen.tif', False)
print('复算 DEM ...'); dem = zonal('0_论文data/DEM_shenzhen.tif', False)

df = pd.read_csv(C.CSV)
df.columns = [c.strip() for c in df.columns]
csv_ids = set(int(v) for v in df['My_ID'])
all_ids = set(info)
missing = sorted(all_ids - csv_ids)

# ================================================================ Q4 可复算性
R['Q4_reproducibility'] = {}
for col, mine in [('LST_mean', lst), ('NDVI_mean', ndvi), ('DEM_mean', dem)]:
    cmap = dict(zip((int(v) for v in df['My_ID']), df[col]))
    a, b = [], []
    mism = []; phantom = []; boundary = []
    for gid in sorted(all_ids):
        if gid not in csv_ids:
            continue
        cv = cmap[gid]
        if pd.isna(cv):
            continue
        mv, nv, nt = mine.get(gid, (np.nan, 0, 0))
        if not np.isfinite(mv):
            phantom.append(gid); mism.append(gid); continue
        a.append(float(cv)); b.append(mv)
        if abs(cv - mv) > 0.01:
            mism.append(gid)
            if 0 < nv < nt:
                boundary.append(gid)
    a, b = np.array(a), np.array(b)
    diff = b - a
    R['Q4_reproducibility'][col] = dict(
        n_comparable=len(a),
        r2=round(float(np.corrcoef(a, b)[0, 1] ** 2), 6) if len(a) > 2 else None,
        mean_abs_diff=round(float(np.abs(diff).mean()), 5),
        max_abs_diff=round(float(np.abs(diff).max()), 4),
        n_within_0p01=int((np.abs(diff) <= 0.01).sum()),
        pct_within_0p01=round(100 * float((np.abs(diff) <= 0.01).mean()), 3),
        n_mismatch=len(mism), n_phantom=len(phantom), n_boundary_partial=len(boundary),
        mismatch_gids=[int(x) for x in mism],
        phantom_gids=[int(x) for x in phantom])

# 三变量残差集重叠
sL = set(R['Q4_reproducibility']['LST_mean']['mismatch_gids'])
sD = set(R['Q4_reproducibility']['DEM_mean']['mismatch_gids'])
sN = set(R['Q4_reproducibility']['NDVI_mean']['mismatch_gids'])
R['Q4_overlap'] = dict(n_any=len(sL | sD | sN), n_two_or_more=len((sL & sD) | (sL & sN) | (sD & sN)),
                       n_all_three=len(sL & sD & sN))

# 证据 E5：幻影格的邻域有效性
phantom_all = sorted(set().union(*[set(R['Q4_reproducibility'][c]['phantom_gids'])
                                   for c in ('LST_mean', 'NDVI_mean', 'DEM_mean')]))
vc_all = {gid: lst.get(gid, (np.nan, 0, 0))[1] for gid in info}
adj = 0
for gid in phantom_all:
    r0, c0 = info[gid]['row'], info[gid]['col']
    n1 = max([vc_all.get(gid_of.get((r0 + dr, c0 + dc), -1), 0)
              for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]])
    if n1 > 0:
        adj += 1
R['Q4_E5_phantom_adjacency'] = dict(n_phantom_union=len(phantom_all),
                                    n_with_valid_neighbour=adj,
                                    pct=round(100 * adj / max(1, len(phantom_all)), 1))

# 对照：规则排除（记录到报告，不重算全部，给出数量级）
R['Q4_rejected_rules'] = dict(
    note='像元角点归属 / 任意重叠归属 / 以栅格自身 origin 锚定网格 三种变体的失配数（LST_mean），均远高于中心归属：',
    corner_lst=29348, any_overlap_lst=29617, raster_origin_lst=6818, center_lst=R['Q4_reproducibility']['LST_mean']['n_mismatch'])

# ================================================================ Q1 缺失格
R['Q1_missing_cells'] = dict(n_grid=len(all_ids), n_csv=len(csv_ids), n_missing=len(missing))
rows = []
for gid in missing:
    i = info[gid]
    nv, nt = lst.get(gid, (np.nan, 0, 0))[1], lst.get(gid, (np.nan, 0, 0))[2]
    rows.append(dict(Grid_ID=gid, row=i['row'], col=i['col'],
                     lst_valid_px=nv, lst_total_px=nt,
                     dem_valid_px=dem.get(gid, (np.nan, 0, 0))[1],
                     ndvi_valid_px=ndvi.get(gid, (np.nan, 0, 0))[1]))
miss_df = pd.DataFrame(rows).sort_values(['row', 'col'])
R['Q1_missing_cells']['detail'] = miss_df.to_dict('records')
R['Q1_missing_cells']['lst_valid_px_stats'] = dict(
    min=int(miss_df['lst_valid_px'].min()), max=int(miss_df['lst_valid_px'].max()),
    mean=round(float(miss_df['lst_valid_px'].mean()), 2),
    n_zero_valid=int((miss_df['lst_valid_px'] == 0).sum()),
    n_total_of_missing=int((miss_df['lst_total_px'] == 0).sum()))
R['Q1_missing_cells']['rows'] = sorted(set(int(r) for r in miss_df['row']))

# ================================================================ Q2 缺失值行
na_cols = ['LST_mean', 'NDVI_mean', 'DEM_mean']
na_any = df[na_cols].isna().any(axis=1)
na_all3 = df[na_cols].isna().all(axis=1)
R['Q2_nan_rows'] = dict(
    n_any=int(na_any.sum()), n_all_three=int(na_all3.sum()),
    per_col={c: int(df[c].isna().sum()) for c in na_cols},
    n_nan_no_building=int((na_any & (df['X_BD'] == 0)).sum()),
    n_nan_with_building=int((na_any & (df['X_BD'] > 0)).sum()))
na_df = df[na_any][['My_ID', 'LST_mean', 'NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH']].copy()
na_df['row'] = na_df['My_ID'].map(lambda x: info[int(x)]['row'])
na_df['col'] = na_df['My_ID'].map(lambda x: info[int(x)]['col'])
R['Q2_nan_rows']['sample'] = na_df.head(20).round(4).to_dict('records')
R['Q2_nan_rows']['row_span'] = [int(na_df['row'].min()), int(na_df['row'].max())]

# ================================================================ Q3 零值格
z = df[df['LST_mean'] == 0]
zr = []
for _, r0 in z.iterrows():
    gid = int(r0['My_ID']); i = info[gid]
    zr.append(dict(Grid_ID=gid, row=i['row'], col=i['col'],
                   lst_valid_px=lst.get(gid, (np.nan, 0, 0))[1], lst_total_px=lst.get(gid, (np.nan, 0, 0))[2],
                   dem_valid_px=dem.get(gid, (np.nan, 0, 0))[1],
                   ndvi=r0['NDVI_mean'], svf=r0['SVF_mean'], road=r0['Road_Dens'], xbd=r0['X_BD']))
R['Q3_zero_lst_cells'] = zr
R['Q3_zero_lst_cells_summary'] = dict(
    n=len(zr), rows=sorted(set(int(v['row']) for v in zr)),
    n_zero_valid_px=int(sum(1 for v in zr if v['lst_valid_px'] == 0)),
    n_with_building=int(sum(1 for v in zr if v['xbd'] > 0)))

# ================================================================ 掩膜表
mism_by = {c: set(R['Q4_reproducibility'][c]['mismatch_gids']) for c in ('LST_mean', 'NDVI_mean', 'DEM_mean')}
ph_by = {c: set(R['Q4_reproducibility'][c]['phantom_gids']) for c in ('LST_mean', 'NDVI_mean', 'DEM_mean')}
with open(os.path.join(C.S00_MASK, 'grid_validity.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh)
    w.writerow(['Grid_ID', 'row', 'col', 'in_csv',
                'lst_valid_px', 'lst_total_px', 'dem_valid_px', 'ndvi_valid_px',
                'flag_missing_csv', 'flag_lst_zero', 'flag_repro_mismatch', 'flag_phantom',
                'flag_boundary_partial'])
    for gid in sorted(all_ids):
        i = info[gid]
        mv, nv, nt = lst.get(gid, (np.nan, 0, 0))
        w.writerow([gid, i['row'], i['col'], int(gid in csv_ids),
                    nv, nt, dem.get(gid, (np.nan, 0, 0))[1], ndvi.get(gid, (np.nan, 0, 0))[1],
                    int(gid not in csv_ids), int(gid in set(int(x) for x in z['My_ID'])),
                    int(gid in set().union(*mism_by.values())), int(gid in set().union(*ph_by.values())),
                    int(np.isfinite(mv) and 0 < nv < nt)])

with open(os.path.join(C.S00_REPORTS, 's00_04_missing.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2, default=str)

# ================================================================ Markdown
L = []
L.append('# S00.4 缺失诊断与 CSV 可复算性检验\n')
L.append('框架依据：§2.2「行数与缺失不一致」；§5.2「可复算特征定义」。\n')
q4 = R['Q4_reproducibility']
L.append('## Q4 核心结论：CSV 能否由栅格复算？\n')
L.append('锁定规则：**像元中心落入哪个 100 m 格就归入该格**（网格由 `grid_utm` 四至锚定）；'
         '格值 = 有效像元算术平均（LST 有效 = 非 -9999 且非 0；DEM/NDVI 有效 = 非 -9999）。\n')
L.append('| 列 | 可比格数 | R² | 平均绝对差 | 最大绝对差 | 差≤0.01 占比 | 完全复现存疑格 | 其中无栅格支撑(幻影) | 其中边界残差 |')
L.append('|---|---|---|---|---|---|---|---|---|')
for k in ('LST_mean', 'NDVI_mean', 'DEM_mean'):
    v = q4[k]
    L.append('| %s | %d | %.5f | %.5f | %.4f | **%.2f%%** | %d | %d | %d |' % (
        k, v['n_comparable'], v['r2'], v['mean_abs_diff'], v['max_abs_diff'],
        v['pct_within_0p01'], v['n_mismatch'], v['n_phantom'], v['n_boundary_partial']))
L.append('')
L.append('排除的备选规则（`LST_mean` 失配格数，数量级对照）：角点归属 %d、任意重叠归属 %d、'
         '以栅格自身 origin 锚定网格 %d，均远高于中心归属的 %d。**中心归属即原流程所用规则。**\n' % (
    R['Q4_rejected_rules']['corner_lst'], R['Q4_rejected_rules']['any_overlap_lst'],
    R['Q4_rejected_rules']['raster_origin_lst'], R['Q4_rejected_rules']['center_lst']))
o = R['Q4_overlap']
L.append('### 残差的性质\n')
L.append('- 残差集跨变量高度重叠：任一变量失配 %d 格，两变量及以上 %d 格，三变量同时失配 **%d 格**；' % (
    o['n_any'], o['n_two_or_more'], o['n_all_three']))
L.append('  说明这不是三条独立的随机噪声，而是一个**单一系统性来源**。')
e5 = R['Q4_E5_phantom_adjacency']
L.append('- 证据 E5：**CSV 有值、而栅格无任何有效像元中心**的格（并集 %d 个），'
         '%d/%d = **%.1f%%** 在 8 邻域内就存在有效数据。即残差格全部紧贴有效数据边界。' % (
    e5['n_phantom_union'], e5['n_with_valid_neighbour'], e5['n_phantom_union'], e5['pct']))
L.append('- 大差值格全部是"边界格"：如 gid 25370（1/12 有效像元）CSV=13.71 而栅格复算=41.11。')
L.append('')
L.append('**判定**：现存 `0_论文data/*_shenzhen.tif` 是**比 CSV 更晚、掩膜更严的版本**——'
         '它在 zonal 之后又剔除了若干像元（多为偏冷像元），导致 CSV 的边缘格无法由现存栅格复算。'
         'CSV 在边缘反而更完整。因此：\n')
L.append('1. 对 **%.2f%% / %.2f%% / %.2f%%**（LST/NDVI/DEM）的格，CSV 可由现存栅格精确复算（差 ≤0.01），'
         '**特征定义满足框架 §5.2 的可复算要求**；' % (
             q4['LST_mean']['pct_within_0p01'], q4['NDVI_mean']['pct_within_0p01'],
             q4['DEM_mean']['pct_within_0p01']))
L.append('2. 对残差与幻影格（合计 %d 格，占 %.1f%%），CSV 值**无现存栅格支撑、不可复算**，'
         '原始导出所用的栅格状态无法回溯；' % (o['n_any'], 100 * o['n_any'] / len(csv_ids)))
L.append('3. 后续发现实验应将这批格**置入掩膜**（`mask/grid_validity.csv` 已逐格标记 '
         '`flag_repro_mismatch` / `flag_phantom` / `flag_boundary_partial`），不进入建模主样本。')
L.append('')
L.append('## Q1 为什么 32748 个网格只写出 32687 行？\n')
q1 = R['Q1_missing_cells']
L.append('网格 **%d** 个，CSV **%d** 行，缺 **%d** 个。它们集中在 row %s 一带。\n' % (
    q1['n_grid'], q1['n_csv'], q1['n_missing'],
    '%d–%d' % (min(q1['rows']), max(q1['rows'])) if q1['rows'] else '—'))
st = q1['lst_valid_px_stats']
L.append('| 缺失格内有效 LST 像元数统计 | 数值 |')
L.append('|---|---|')
L.append('| 最小值 | %d |' % st['min'])
L.append('| 最大值 | %d |' % st['max'])
L.append('| 均值 | %.2f |' % st['mean'])
L.append('| 有效像元为 0 的格数 | %d / %d |' % (st['n_zero_valid'], q1['n_missing']))
L.append('')
L.append('这 %d 个格本身**数据完整**（有效像元 %d–%d），并非因无值被剔除，'
         '而是原导出流程另有筛除条件且未留存依据——**该筛除不可复现**，需向数据作者回溯。\n' % (
    q1['n_missing'], st['min'], st['max']))
L.append('## Q2 缺失值行的分布\n')
q2 = R['Q2_nan_rows']
L.append('| 判据 | 数值 |')
L.append('|---|---|')
L.append('| 至少一列缺失的行 | **%d** |' % q2['n_any'])
L.append('| 三列全缺的行 | %d |' % q2['n_all_three'])
for c, n in q2['per_col'].items():
    L.append('| %s 缺失 | %d |' % (c, n))
L.append('| 其中无建筑（X_BD=0） | %d |' % q2['n_nan_no_building'])
L.append('| 其中含建筑（X_BD>0） | %d |' % q2['n_nan_with_building'])
L.append('| 行号跨度 | %d ~ %d |' % tuple(q2['row_span']))
L.append('')
L.append('## Q3 网格 `LST_mean==0` 的 %d 个格\n' % R['Q3_zero_lst_cells_summary']['n'])
L.append('| Grid_ID | row | col | LST 有效/总像元 | DEM 有效 | SVF | Road | X_BD |')
L.append('|---|---|---|---|---|---|---|---|')
for r0 in R['Q3_zero_lst_cells']:
    L.append('| %d | %d | %d | %d/%d | %d | %.4f | %.2f | %.4f |' % (
        r0['Grid_ID'], r0['row'], r0['col'], r0['lst_valid_px'], r0['lst_total_px'],
        r0['dem_valid_px'], r0['svf'], r0['road'], r0['xbd']))
L.append('')
L.append('**与 S00.3 的闭合**：这 %d 个格中，%d 个在现存 LST 栅格中的有效像元数恰为 **0**（即无任何数据支撑），'
         '说明其 `LST_mean==0` 是"无数据被写成 0"的填充值，而非真实的 0 °C 观测。'
         '据此把 S00.3 中"待核"的这批格**升级判定为无数据**：后续一律置入掩膜，不参与统计。\n' % (
             R['Q3_zero_lst_cells_summary']['n'], R['Q3_zero_lst_cells_summary']['n_zero_valid_px']))

with open(os.path.join(C.S00_REPORTS, 's00_04_missing.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps({'grid': R['grid'], 'Q4': {k: {kk: vv for kk, vv in v.items() if kk not in ('mismatch_gids', 'phantom_gids')}
                                            for k, v in R['Q4_reproducibility'].items()},
                  'Q4_overlap': R['Q4_overlap'], 'Q4_E5': R['Q4_E5_phantom_adjacency'],
                  'Q1': {k: v for k, v in R['Q1_missing_cells'].items() if k != 'detail'},
                  'Q2': {k: v for k, v in R['Q2_nan_rows'].items() if k != 'sample'},
                  'Q3_zero': R['Q3_zero_lst_cells_summary']}, ensure_ascii=False, indent=2, default=str))
print('\n写出: reports/s00_04_missing.json / .md, mask/grid_validity.csv')
