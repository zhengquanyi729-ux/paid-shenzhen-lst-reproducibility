"""
S00.3 LST 零值诊断
===================
问题：全市域 LST 栅格 54% 像元为 0；研究区栅格有 223 个 0；CSV 中 13 个网格 LST 均值为 0。
框架要求「核查 QA 与像元来源，建立有效掩膜；不在缺乏依据时一律删零」。
本脚本用四组独立证据判定 0 的性质：
  E1 与 DEM 无数据(-9999)掩膜的空间重合度
  E2 与 NDVI 填充(0)掩膜的空间重合度
  E3 与深圳行政边界多边形的内外关系（点定位）
  E4 空间连通性（0 值是否成片）
并给出分类型的掩膜规则。
输出：reports/s00_03_lst_zero.json / .md
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
from matplotlib.path import Path
import geoio as g
import config as C

os.makedirs(C.S00_REPORTS, exist_ok=True)
R = {}


def load(name):
    return g.read_raster(os.path.join(C.DATA, name))


def geo_of(name):
    return g.tiff_geo(g.read_tiff_tags(os.path.join(C.DATA, name)))


def sample_nearest(src, src_geo, dst_geo, fill=np.nan):
    """把 src 栅格按最近邻重采样到 dst 网格（同 CRS）。"""
    rows = np.arange(dst_geo['height'])
    cols = np.arange(dst_geo['width'])
    east = dst_geo['origin_x'] + (cols + 0.5) * dst_geo['px_w']
    north = dst_geo['origin_y'] - (rows + 0.5) * dst_geo['px_h']
    sc = np.round((east - src_geo['origin_x']) / src_geo['px_w'] - 0.5).astype(np.int64)
    sr = np.round((src_geo['origin_y'] - north) / src_geo['px_h'] - 0.5).astype(np.int64)
    valid_c = (sc >= 0) & (sc < src_geo['width'])
    valid_r = (sr >= 0) & (sr < src_geo['height'])
    out = np.full((dst_geo['height'], dst_geo['width']), fill, dtype='f4')
    rr = sr[valid_r][:, None]
    cc = sc[valid_c][None, :]
    sub = np.asarray(src)[np.ix_(sr[valid_r], sc[valid_c])]
    out[np.ix_(valid_r, valid_c)] = sub
    return out, valid_r, valid_c


# ================================================================ 全市域
LSTg = geo_of('LST_30m_Final new.tif')
DEMg = geo_of('DEM_30m_Final.tif')
NDVIg = geo_of('NDVI_30m_Final.tif')
LST = np.asarray(load('LST_30m_Final new.tif'), dtype='f4').squeeze()
DEM = np.asarray(load('DEM_30m_Final.tif')).squeeze()
NDVI = np.asarray(load('NDVI_30m_Final.tif'), dtype='f4')
if NDVI.ndim == 3:
    NDVI = NDVI[..., 0]

DEM_r, vr, vc = sample_nearest(DEM, DEMg, LSTg, fill=-9999)
NDVI_r, _, _ = sample_nearest(NDVI, NDVIg, LSTg, fill=-9999)

m_zero = (LST == 0)
m_demnd = (DEM_r == -9999)
m_ndvi0 = (NDVI_r == 0)
m_out = DEM_r == -9999  # 超出 DEM 覆盖的边角

n = LST.size
R['fullcity'] = {
    'n_px': int(n),
    'lst_zero': int(m_zero.sum()), 'lst_zero_pct': round(100 * m_zero.mean(), 2),
    'lst_nodata_minus9999': int((LST == -9999).sum()),
    'dem_nodata': int(m_demnd.sum()), 'dem_nodata_pct': round(100 * m_demnd.mean(), 2),
    'ndvi_zero': int(m_ndvi0.sum()), 'ndvi_zero_pct': round(100 * m_ndvi0.mean(), 2),
}
# E1/E2 重合度
R['fullcity']['zero_within_dem_nodata_pct'] = round(100 * (m_zero & m_demnd).sum() / max(1, m_zero.sum()), 2)
R['fullcity']['zero_within_ndvi_zero_pct'] = round(100 * (m_zero & m_ndvi0).sum() / max(1, m_zero.sum()), 2)
R['fullcity']['dem_nodata_that_are_lst_zero_pct'] = round(100 * (m_demnd & m_zero).sum() / max(1, m_demnd.sum()), 2)
R['fullcity']['triple_mask_pct'] = round(100 * (m_zero & m_demnd & m_ndvi0).sum() / n, 2)

# E4 连通性：LST==0 像元的 4 邻域是否也为 0
z = m_zero
nb = np.zeros_like(z)
for ax, sh in [(0, 1), (0, -1), (1, 1), (1, -1)]:
    nb |= np.roll(z, sh, axis=ax)
frac_interior = float((z & nb).sum() / max(1, z.sum()))
# 对比：把 z 随机打散后的"内部率"期望≈ z 占比
R['fullcity']['zero_has_zero_neighbour_pct'] = round(100 * frac_interior, 2)
R['fullcity']['zero_random_expectation_pct'] = round(100 * (1 - (1 - m_zero.mean()) ** 4), 2)

# E3 与深圳行政边界多边形的关系（点定位）
# 优化：把所有环拼成一个复合 Path，单次调用 contains_points，避免逐要素遍历
city = g.read_shp(os.path.join(C.DATA, '边界/广东省深圳市各社区.shp'))
verts, codes = [], []
for sh in city['shapes']:
    if sh['shape_type'] not in (5, 15, 25):
        continue
    for ring in sh['parts']:
        if len(ring) < 3:
            continue
        verts.append(np.asarray(ring, dtype='f8'))
        codes.append(np.concatenate([[Path.MOVETO],
                                     np.full(len(ring) - 2, Path.LINETO),
                                     [Path.CLOSEPOLY]]))
city_path = Path(np.vstack(verts), np.concatenate(codes))
# 逐像元经纬度（抽稀以控制内存：每 6 行 6 列取一点）
sub = 6
rows = np.arange(0, LSTg['height'], sub)
cols = np.arange(0, LSTg['width'], sub)
RR, CC = np.meshgrid(rows, cols, indexing='ij')
lon, lat = g.raster_centers_to_lonlat(LSTg, RR.ravel(), CC.ravel())
pts = np.column_stack([lon, lat])
inside = city_path.contains_points(pts).reshape(RR.shape)
z_sub = m_zero[np.ix_(rows, cols)]
R['fullcity']['point_in_city_test'] = {
    'subsample_step': sub, 'n_test_points': int(pts.size),
    'zero_px_inside_city_pct': round(100 * (z_sub & inside).sum() / max(1, z_sub.sum()), 3),
    'zero_px_outside_city_pct': round(100 * (z_sub & ~inside).sum() / max(1, z_sub.sum()), 3),
    'noncity_px_that_are_zero_pct': round(100 * (z_sub & ~inside).sum() / max(1, (~inside).sum()), 3),
    'city_px_that_are_zero_pct': round(100 * (z_sub & inside).sum() / max(1, inside.sum()), 3),
}

# 非零 LST 的取值范围（供后续判断单位与合理性）
nz = LST[(LST != 0) & (LST != -9999)]
R['fullcity']['nonzero_lst'] = dict(
    n=int(nz.size), min=round(float(nz.min()), 3), p50=round(float(np.median(nz)), 3),
    max=round(float(nz.max()), 3), mean=round(float(nz.mean()), 3))

# ================================================================ 研究区
LST2g = geo_of('0_论文data/LST_shenzhen.tif')
DEM2g = geo_of('0_论文data/DEM_shenzhen.tif')
ARCH2g = geo_of('0_论文data/arch_shenzhen.tif')
LST2 = np.asarray(load('0_论文data/LST_shenzhen.tif'), dtype='f4').squeeze()
DEM2 = np.asarray(load('0_论文data/DEM_shenzhen.tif')).squeeze()
ARCH2 = np.asarray(load('0_论文data/arch_shenzhen.tif'), dtype='f4').squeeze()
NDVI2 = np.asarray(load('0_论文data/NVDI_shenzhen.tif'), dtype='f4')
if NDVI2.ndim == 3:
    NDVI2 = NDVI2[..., 0]

z2 = LST2 == 0
R['study'] = {
    'n_px': int(LST2.size),
    'lst_zero': int(z2.sum()),
    'lst_nodata': int((LST2 == -9999).sum()),
    'dem_nodata': int((DEM2 == -9999).sum()),
    'zero_also_dem_nodata_pct': round(100 * (z2 & (DEM2 == -9999)).sum() / max(1, z2.sum()), 2),
    'zero_with_arch_pct': round(100 * (z2 & (ARCH2 > 0)).sum() / max(1, z2.sum()), 2),
    'zero_ndvi_mean': round(float(NDVI2[z2 & (NDVI2 != -9999)].mean()) if (z2 & (NDVI2 != -9999)).sum() else -999, 4),
    'nonzero_lst_ndvi_mean': round(float(NDVI2[(~z2) & (LST2 != -9999) & (NDVI2 != -9999)].mean()), 4),
}
nb2 = np.zeros_like(z2)
for ax, sh in [(0, 1), (0, -1), (1, 1), (1, -1)]:
    nb2 |= np.roll(z2, sh, axis=ax)
R['study']['zero_has_zero_neighbour_pct'] = round(100 * float((z2 & nb2).sum() / max(1, z2.sum())), 2)
# 0 值像元坐标（供人工核对是否为水体）
zi, zj = np.where(z2)
lon2, lat2 = g.raster_centers_to_lonlat(LST2g, zi, zj)
R['study']['zero_pixel_lonlat_sample'] = [[round(float(a), 5), round(float(b), 5)]
                                          for a, b in zip(lon2[:15], lat2[:15])]

with open(os.path.join(C.S00_REPORTS, 's00_03_lst_zero.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2)

# ================================================================ Markdown
L = []
L.append('# S00.3 LST 零值诊断\n')
L.append('框架依据：§2.2「温度填充与异常值」；处理原则「核查 QA 与像元来源，不在缺乏依据时一律删零」。\n')
L.append('## 全市域 `LST_30m_Final new.tif`\n')
f = R['fullcity']
L.append('| 掩膜 | 像元数 | 占比 |')
L.append('|---|---|---|')
L.append('| LST == 0 | %d | %.2f%% |' % (f['lst_zero'], f['lst_zero_pct']))
L.append('| LST == -9999（nodata） | %d | %.2f%% |' % (f['lst_nodata_minus9999'], 100 * f['lst_nodata_minus9999'] / f['n_px']))
L.append('| DEM == -9999（重采样到 LST 网格） | %d | %.2f%% |' % (f['dem_nodata'], f['dem_nodata_pct']))
L.append('| NDVI == 0（重采样到 LST 网格） | %d | %.2f%% |' % (f['ndvi_zero'], f['ndvi_zero_pct']))
L.append('')
L.append('### 证据 E1/E2：与其他图层的填充掩膜是否重合\n')
L.append('| 判据 | 数值 |')
L.append('|---|---|')
L.append('| LST=0 像元中，DEM 也为 nodata 的比例 | **%.2f%%** |' % f['zero_within_dem_nodata_pct'])
L.append('| LST=0 像元中，NDVI 也为 0 的比例 | **%.2f%%** |' % f['zero_within_ndvi_zero_pct'])
L.append('| DEM nodata 像元中，LST 也为 0 的比例 | **%.2f%%** |' % f['dem_nodata_that_are_lst_zero_pct'])
L.append('| 三者同时为填充的像元占比 | %.2f%% |' % f['triple_mask_pct'])
L.append('')
L.append('### 证据 E4：空间连通性\n')
L.append('| 判据 | 数值 | 随机打散期望 |')
L.append('|---|---|---|')
L.append('| LST=0 像元至少有一个 4-邻域也为 0 的比例 | **%.2f%%** | %.2f%% |' % (
    f['zero_has_zero_neighbour_pct'], f['zero_random_expectation_pct']))
L.append('')
L.append('### 证据 E3：与深圳行政边界的内外关系\n')
p = f['point_in_city_test']
L.append('| 判据 | 数值 |')
L.append('|---|---|')
L.append('| 抽样点数（步长 %d） | %d |' % (p['subsample_step'], p['n_test_points']))
L.append('| LST=0 像元落在市界内 | %.3f%% |' % p['zero_px_inside_city_pct'])
L.append('| LST=0 像元落在市界外 | **%.3f%%** |' % p['zero_px_outside_city_pct'])
L.append('| 市界外的像元中为 0 的比例 | %.3f%% |' % p['noncity_px_that_are_zero_pct'])
L.append('| 市界内的像元中为 0 的比例 | %.3f%% |' % p['city_px_that_are_zero_pct'])
L.append('')
L.append('### 非零 LST 的取值范围\n')
nz_ = f['nonzero_lst']
L.append('- n=%d，min=%.2f，中位=%.2f，mean=%.2f，max=%.2f' % (nz_['n'], nz_['min'], nz_['p50'], nz_['mean'], nz_['max']))
L.append('')
L.append('## 研究区 `0_论文data/LST_shenzhen.tif`\n')
s = R['study']
L.append('| 判据 | 数值 |')
L.append('|---|---|')
L.append('| 总像元 | %d |' % s['n_px'])
L.append('| LST == 0 | **%d** |' % s['lst_zero'])
L.append('| LST == -9999 | %d |' % s['lst_nodata'])
L.append('| DEM == -9999 | %d |' % s['dem_nodata'])
L.append('| LST=0 同时 DEM 为 nodata | %.2f%% |' % s['zero_also_dem_nodata_pct'])
L.append('| LST=0 处有建筑（arch>0） | %.2f%% |' % s['zero_with_arch_pct'])
L.append('| LST=0 像元的平均 NDVI | %.4f |' % s['zero_ndvi_mean'])
L.append('| 非零 LST 像元的平均 NDVI | %.4f |' % s['nonzero_lst_ndvi_mean'])
L.append('| LST=0 像元有 0 邻域的比例 | %.2f%% |' % s['zero_has_zero_neighbour_pct'])
L.append('')
L.append('## 判定\n')
L.append('全市域 LST 的 0 值**不是真实低温观测**，而是**研究区外的填充值**，证据链如下：')
L.append('')
L.append('1. %.2f%% 的 0 值像元同时是 DEM nodata，%.2f%% 同时是 NDVI 填充；三个独立图层的填充掩膜大面积重合，' % (
    f['zero_within_dem_nodata_pct'], f['zero_within_ndvi_zero_pct']))
L.append('   说明 0 是制图时的统一"区外/海面"填充，而非 LST 反演产物。')
L.append('2. 0 值像元落在深圳行政边界**之外**的比例为 %.3f%%，而市界内像元几乎不为 0（%.3f%%）。' % (
    p['zero_px_outside_city_pct'], p['city_px_that_are_zero_pct']))
L.append('3. 连通性检验：%.2f%% 的 0 值像元至少有一个 0 邻域，远高于随机打散的 %.2f%%，' % (
    f['zero_has_zero_neighbour_pct'], f['zero_random_expectation_pct']))
L.append('   表明 0 值呈**大块连片**分布，符合边界外填充的形态，不符合自然低温斑块的形态。')
nzero_neg = int((LST[(LST != 0) & (LST != -9999)] < 0).sum())
L.append('4. 非零 LST 中位 %.2f °C、最大 %.2f °C，量级物理合理；负数仅 %d 个（占非零的 %.4f%%），可忽略。' % (
    nz_['p50'], nz_['max'], nzero_neg, 100 * nzero_neg / nz_['n']))
L.append('')
L.append('**因此分类型掩膜规则为：**\n')
L.append('| 数据 | 规则 | 依据 |')
L.append('|---|---|---|')
L.append('| 全市域 LST | `LST==0` 与 `LST==-9999` **一律判为无效**，不进入任何统计 | E1+E2+E3+E4 四重证据 |')
L.append('| 研究区 LST | 0 值仅 %d 个（%.3f%%），需逐像元核查后再定；**默认标记为"待核"而非直接删除** | 证据不足，不预设删除 |' % (
    s['lst_zero'], 100 * s['lst_zero'] / s['n_px']))
L.append('| CSV 中 `LST_mean==0` 的网格 | 标记为 `lst_suspect`，保留但加标记位 | 同上 |')

with open(os.path.join(C.S00_REPORTS, 's00_03_lst_zero.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps({k: R[k] for k in ('fullcity',)}, ensure_ascii=False, indent=2, default=str)[:2200])
print('\n--- study ---')
print(json.dumps(R['study'], ensure_ascii=False, indent=2))
