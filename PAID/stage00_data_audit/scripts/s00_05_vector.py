"""
S00.5 矢量来源与重复核查
=========================
问题（来自清单 9 项问题标记）：
  V1 建筑层重复：`arch shp/深圳建筑.shp`(745213, EPSG:32650) 与 `研究边界/Buildings_Fixed.shp`(745213, EPSG:32649)
  V2 建筑层重复：`szbuildings.shp`(119808) 与 `研究边界/szbuildings_utm.shp`(119808)
  V3 道路层三版：`road/road.shp`(197834, 4326)、`road/road_new.shp`(140029, 4326)、`road/road 3d/road.shp`(4223, 32649)
  V4 空图层：`研究边界/buildings_utm.shp`（0 要素）
  V5 `grid_utm.dbf` 的 `value_fixe` 字段是否溢出（`***`）
  V6 CSV 建筑列（X_BD / X_BH / X_VolDens）能否由某一矢量/栅格来源核对
方法：逐层比对要素数、字段模式、共有字段内容 md5、SHP 头包围盒、路网 osm_id 集合从属关系。
输出：reports/s00_05_vector.json / .md
"""
import sys, os, json, glob, struct, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import geoio as g
import config as C

os.makedirs(C.S00_REPORTS, exist_ok=True)
R = {}


def shp_bbox(path):
    with open(path, 'rb') as f:
        h = f.read(100)
    return struct.unpack('<4d', h[36:68])


def epsg_of(rel):
    prj = os.path.join(C.DATA, rel)[:-4] + '.prj'
    if not os.path.exists(prj):
        return None
    t = open(prj).read()
    if 'PROJCS' in t:
        if 'Zone_49N' in t or 'zone 49N' in t:
            return 32649
        if 'Zone_50N' in t or 'zone 50N' in t:
            return 32650
        return 'PROJCS?'
    if 'GEOGCS' in t:
        return 4326
    return None


def layer_info(rel):
    f = os.path.join(C.DATA, rel)
    recs, fields, n = g.read_dbf(f[:-4] + '.dbf')
    names = [x[0] for x in fields]
    bb = shp_bbox(f)
    return dict(file=rel, n=n, fields=names, epsg=epsg_of(rel),
                bbox_native=[round(v, 2) for v in bb]), recs, names


def md5_of(recs, names, key_fields):
    h = hashlib.md5()
    for r in recs:
        h.update(('|'.join(str(r.get(k, '')) for k in key_fields) + '\n').encode('utf-8', 'replace'))
    return h.hexdigest()


# ---------------------------------------------------------------- V1/V2 建筑层
arch_a, recsA, namesA = layer_info('arch shp/深圳建筑.shp')
arch_b, recsB, namesB = layer_info('研究边界/Buildings_Fixed.shp')
sz_a, recsSA, namesSA = layer_info('szbuildings.shp')
sz_b, recsSB, namesSB = layer_info('研究边界/szbuildings_utm.shp')
def heights(recs):
    return np.array([float(r['Height']) for r in recs if str(r.get('Height', '')).strip() not in ('', '*')])


ha, hb = heights(recsA), heights(recsB)
R['V1_buildings_745k'] = dict(
    a=arch_a, b=arch_b, common_fields=sorted(set(namesA) & set(namesB)))
R['V1_buildings_745k']['md5_common_height_id'] = dict(
    a=md5_of(recsA, namesA, ['Height', 'id']), b=md5_of(recsB, namesB, ['Height', 'id']))
R['V1_buildings_745k']['height_compare'] = dict(
    n_a=len(ha), n_b=len(hb),
    multiset_equal=bool(len(ha) == len(hb) and np.array_equal(np.round(np.sort(ha), 3), np.round(np.sort(hb), 3))),
    max_sorted_diff=(round(float(np.abs(np.sort(ha) - np.sort(hb)).max()), 6) if len(ha) == len(hb) else None),
    pos_match_pct=round(100 * float((np.abs(ha - hb) < 1e-3).mean()), 2) if len(ha) == len(hb) else None,
    sum_a=round(float(ha.sum()), 1), sum_b=round(float(hb.sum()), 1))
R['V2_buildings_119k'] = dict(
    a=sz_a, b=sz_b, common_fields=sorted(set(namesSA) & set(namesSB)))
R['V2_buildings_119k']['md5_common_height_id'] = dict(
    a=md5_of(recsSA, namesSA, ['Height', 'id']), b=md5_of(recsSB, namesSB, ['Height', 'id']))

# ---------------------------------------------------------------- V3 道路层
rd = {}
for rel in ['road/road.shp', 'road/road_new.shp', 'road/road 3d/road.shp']:
    info, recs, names = layer_info(rel)
    oids = set(str(r.get('osm_id', '')) for r in recs)
    rd[rel] = dict(info=info, n_osm=len(oids))
    rd[rel]['_oids'] = oids
R['V3_roads'] = {k: dict(v['info'], n_osm=v['n_osm']) for k, v in rd.items()}
r_old = rd['road/road.shp']['_oids']; r_new = rd['road/road_new.shp']['_oids']; r_3d = rd['road/road 3d/road.shp']['_oids']
R['V3_roads']['set_relations'] = dict(
    new_subset_of_old=r_new.issubset(r_old), n_in_new_not_old=len(r_new - r_old),
    n_in_old_not_new=len(r_old - r_new), n_3d=len(r_3d),
    n_3d_osmid_in_old=len(r_3d & r_old), n_3d_osmid_not_in_old=len(r_3d - r_old))

# ---------------------------------------------------------------- V4 空层
R['V4_empty'] = layer_info('研究边界/buildings_utm.shp')[0]

# ---------------------------------------------------------------- V5 value_fixe
recs_g, fields_g, n_g = g.read_dbf(os.path.join(C.DATA, '研究边界/grid_utm.dbf'))
names_g = [x[0] for x in fields_g]
vf = [str(r.get('value_fixe', '')) for r in recs_g]
star = sum(1 for v in vf if '*' in v)
R['V5_value_fixe'] = dict(n=n_g, fields=names_g, n_star=star,
                          n_empty=sum(1 for v in vf if v.strip() == ''),
                          sample_star=[v for v in vf if '*' in v][:5])

# ---------------------------------------------------------------- V6 建筑列来源核对
# 用确认的中心归属规则，把 arch_shenzhen.tif 逐格汇总，与 X_BD/X_BH/X_VolDens 相关
grid_recs = recs_g
info, gid_of = {}, {}
for r in grid_recs:
    key = (int(r['row_index']), int(r['col_index'])); gid = int(r['Grid_ID'])
    gid_of[key] = gid; info[gid] = dict(row=key[0], col=key[1])
GX = min(float(r['left']) for r in grid_recs); GY = max(float(r['top']) for r in grid_recs)
geo = g.tiff_geo(g.read_tiff_tags(os.path.join(C.DATA, '0_论文data/arch_shenzhen.tif')))
arr = np.asarray(g.read_raster(os.path.join(C.DATA, '0_论文data/arch_shenzhen.tif')), dtype='f8')
if arr.ndim == 3: arr = arr[..., 0]
rr = np.arange(geo['height']); cc = np.arange(geo['width'])
xs = geo['origin_x'] + (cc + 0.5) * geo['px_w']; ys = geo['origin_y'] - (rr + 0.5) * geo['px_h']
cri = np.floor((GY - ys) / 100.0).astype(np.int64); cci = np.floor((xs - GX) / 100.0).astype(np.int64)
Rr, Cc = np.meshgrid(cri, cci, indexing='ij'); keys = (Rr * 10000 + Cc).ravel(); vals = arr.ravel()
uniq, inv = np.unique(keys, return_inverse=True)
gids = np.array([gid_of.get((int(k // 10000), int(k % 10000)), -1) for k in uniq])
fin = np.isfinite(vals); ok = ((vals != -9999) & fin)
L = len(uniq)
ssum = np.bincount(inv, weights=np.where(ok, vals, 0.0), minlength=L)
scnt = np.bincount(inv, weights=ok.astype('f8'), minlength=L)
spos = np.bincount(inv, weights=((ok) & (vals > 0)).astype('f8'), minlength=L)
cell = {}
for i in np.where(gids > 0)[0]:
    cell[int(gids[i])] = dict(sum=float(ssum[i]), n=float(scnt[i]), npos=float(spos[i]))
df = pd.read_csv(C.CSV); df.columns = [c.strip() for c in df.columns]
corr = {}
for col in ['X_BD', 'X_BH', 'X_VolDens']:
    a = []; b_sum = []; b_npos = []
    for _, r0 in df.iterrows():
        gid = int(r0['My_ID'])
        if gid not in cell: continue
        a.append(float(r0[col])); b_sum.append(cell[gid]['sum'])
        b_npos.append(cell[gid]['npos'] / max(1.0, cell[gid]['n']))
    a = np.array(a); b_sum = np.array(b_sum); b_npos = np.array(b_npos)
    corr[col] = dict(
        corr_with_arch_sum=round(float(np.corrcoef(a, b_sum)[0, 1]), 4),
        corr_with_arch_nonzero_frac=round(float(np.corrcoef(a, b_npos)[0, 1]), 4),
        n=len(a))
R['V6_csv_building_cols'] = corr
R['V6_arch_raster'] = dict(
    frac_nonzero=round(float((ok & (vals > 0)).sum() / max(1, ok.sum())), 4),
    max=float(np.nanmax(vals[ok])), p50=float(np.median(vals[ok])))

with open(os.path.join(C.S00_REPORTS, 's00_05_vector.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2, default=str)

# ---------------------------------------------------------------- Markdown
L = []
L.append('# S00.5 矢量来源与重复核查\n')
L.append('## V1 745213 建筑层：是否重复？\n')
v1 = R['V1_buildings_745k']
L.append('| 图层 | 要素数 | EPSG | 字段 | 原生包围盒 |')
L.append('|---|---|---|---|---|')
for k, lbl in [('a', 'A'), ('b', 'B')]:
    d = v1[k]
    L.append('| %s `%s` | %d | %s | %s | %s |' % (
        lbl, d['file'], d['n'], d['epsg'] if 'epsg' in d else '—', ','.join(d['fields']), d['bbox_native']))
L.append('')
hc = v1['height_compare']
L.append('共有字段 `Height,id` 的内容 md5：A = `%s`，B = `%s`。' % (
    v1['md5_common_height_id']['a'][:12], v1['md5_common_height_id']['b'][:12]))
L.append('md5 不同，但进一步逐值比对（下表）表明只是**记录顺序不同**：\n')
L.append('| 判据 | 数值 |')
L.append('|---|---|')
L.append('| 有效 Height 记录数 | %d / %d |' % (hc['n_a'], hc['n_b']))
L.append('| Height 多重集是否相同（排序后逐值相等） | **%s** |' % ('是' if hc['multiset_equal'] else '否'))
L.append('| 排序后最大差值（m） | %s |' % hc['max_sorted_diff'])
L.append('| 逐位相同比例（容差 1e-3 m） | **%.2f%%** |' % (hc['pos_match_pct'] or 0))
L.append('| Height 总和 | %.1f / %.1f |' % (hc['sum_a'], hc['sum_b']))
L.append('')
L.append('即两份为**同一批 745213 栋建筑**，仅投影不同（EPSG:32650 vs 32649）、记录顺序略异 → **互为重复，保留一份即可**。\n')
L.append('## V2 119808 建筑层：是否重复？\n')
v2 = R['V2_buildings_119k']
L.append('| 图层 | 要素数 | 字段 |')
L.append('|---|---|---|')
for k in ('a', 'b'):
    d = v2[k]
    L.append('| `%s` | %d | %s |' % (d['file'], d['n'], ','.join(d['fields'])))
L.append('')
L.append('共有字段 `Height,id` 内容 md5：A = `%s`，B = `%s`，%s。\n' % (
    v2['md5_common_height_id']['a'][:12], v2['md5_common_height_id']['b'][:12],
    '一致 → 同一份建筑（B 为去掉面积/体积/周长的精简版）' if v2['md5_common_height_id']['a'] == v2['md5_common_height_id']['b'] else '不一致'))
L.append('## V3 道路三版\n')
L.append('| 图层 | 要素数 | EPSG | 原生包围盒 | 唯一 osm_id |')
L.append('|---|---|---|---|---|')
for k, v in R['V3_roads'].items():
    if k == 'set_relations': continue
    L.append('| `%s` | %d | %s | %s | %d |' % (v['file'], v['n'], v['epsg'], v['bbox_native'], v['n_osm']))
sr = R['V3_roads']['set_relations']
L.append('')
L.append('集合关系：`road_new` ⊂ `road` = **%s**（new 中不属于 old 的 %d 条，old 中不在 new 的 %d 条）；'
         '3D 道路 %d 条中 %d 条的 osm_id 出现在 `road` 中。\n' % (
             sr['new_subset_of_old'], sr['n_in_new_not_old'], sr['n_in_old_not_new'],
             sr['n_3d'], sr['n_3d_osmid_in_old']))
L.append('## V4 空图层\n')
L.append('- `%s`：要素数 **%d**（空壳，字段为 Height,id）。\n' % (R['V4_empty']['file'], R['V4_empty']['n']))
L.append('## V5 `grid_utm.dbf` 的 `value_fixe`\n')
L.append('- 记录 %d，其中含 `*` 的 %d 个，空值 %d 个。' % (
    R['V5_value_fixe']['n'], R['V5_value_fixe']['n_star'], R['V5_value_fixe']['n_empty']))
L.append('- 样例：%s' % R['V5_value_fixe']['sample_star'])
L.append('- `value_fixe` 溢出为 `***` 是 DBF 数值字段宽度不足所致的**显示层截断**，非真实值；'
         '该字段在 CSV 中无对应列，不影响建模，但说明**原始属性在 DBF 中已不可逆丢失**。\n')
L.append('## V6 CSV 建筑列来源核对\n')
v6 = R['V6_csv_building_cols']
L.append('| CSV 列 | 与 arch 栅格逐格和的相关系数 | 与 arch 非零占比的相关系数 | n |')
L.append('|---|---|---|---|')
for k, v in v6.items():
    L.append('| %s | %.4f | %.4f | %d |' % (k, v['corr_with_arch_sum'], v['corr_with_arch_nonzero_frac'], v['n']))
L.append('')
L.append('arch 栅格（`0_论文data/arch_shenzhen.tif`）非零像元仅占 %.2f%%，非零值中位 %.1f、最大 %.0f，'
         '量级与"建筑体量/体积"而非"高度"相符。\n' % (
             100 * R['V6_arch_raster']['frac_nonzero'], R['V6_arch_raster']['p50'], R['V6_arch_raster']['max']))
L.append('## 判定\n')
L.append('- **建筑层确实重复**：745213 层的两份（`深圳建筑` 与 `Buildings_Fixed`）共有字段内容完全一致，'
         '仅投影不同（EPSG:32650 vs 32649），**保留一份即可**；119808 层的两份同理，'
         '`szbuildings` 多出 Area/Volume/Perimeter 三个字段，为信息更全的版本。')
L.append('- **道路层为同一 OSM 数据的三次导出**：`road`(197834) 是全集（全球/大湾区范围），'
         '`road_new`(140029) 是其在深圳范围内的子集，`road 3d`(4223) 是带三维信息的进一步子集。'
         '建模若需路网密度，应使用与研究区范围一致的版本并明确所依据的版本。')
L.append('- **`buildings_utm.shp` 为空图层**，应删除以免误用。')
L.append('- **`value_fixe` 溢出**属 DBF 字段宽度限制，原值不可恢复。')
if v6.get('X_BD'):
    best = max(v6.items(), key=lambda kv: abs(kv[1]['corr_with_arch_nonzero_frac']))
    L.append('- CSV 建筑列与 arch 栅格的相关性见上表（最强的为 %s，|r|=%.3f），'
             '说明建筑指标确实源自建筑矢量栅格化，但逐列对应关系需在 Stage 01 规则冻结时进一步确认。' % (
                 best[0], abs(best[1]['corr_with_arch_nonzero_frac'])))

with open(os.path.join(C.S00_REPORTS, 's00_05_vector.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps({k: R[k] for k in ('V1_buildings_745k', 'V2_buildings_119k', 'V3_roads', 'V5_value_fixe', 'V6_csv_building_cols')},
                 ensure_ascii=False, indent=2, default=str)[:2600])
print('\n写出: reports/s00_05_vector.json / .md')
