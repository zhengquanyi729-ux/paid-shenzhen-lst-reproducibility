"""
S05.7  行政边界派生（Fig 1 用）
================================
从作者原始矢量派生一份**仓库内可复现的小体量边界产品**，供 s05_02_figures.py 的
Fig 1 直接读取（857 MB 的原始 shapefile 不进仓库）。

  (1) 研究区**内部**的区界归属 —— 来自 `研究边界/studyarea.shp`（作者在研究区内
      切的社区面，GBK，WGS84，带 QUNAME=区名）。逐 100 m 格按其中心落在哪个社区面
      判定所属区，得到 (row,col) 上的**区归属栅格**（RLE 压缩）；Fig 1 用与配色完全
      相同的“逐类软投票 + 0.5 等值线”把它画成平滑区界，与 A/B/缓冲/C 边界同源同风格。
  (2) 深圳全市 9 个区的**外轮廓** —— 来自 `2023年县级/2023年初县矢量.shp`
      （WGS84，NAME_2='Shenzhen'），供 Fig 1 的小定位图（inset）作背景。

坐标系：WGS84(度) → UTM 49N(m) → 分析网格 (col,row)；映射见 fig_geo.py。

用法：python3 stage05_paper/scripts/s05_07_boundary.py
产物：stage05_paper/reports/shenzhen_admin_studyarea.json
"""
import os, json
import numpy as np
import pandas as pd
import fig_geo as GG

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
REP = os.path.join(S05, 'reports')
DATA = os.path.normpath(os.path.join(PROJ, '..', '..', 'data'))   # 作者 857 MB 原始数据集
if not os.path.isdir(DATA):                       # 兜底：本地挂载布局
    DATA = '/sessions/friendly-awesome-turing/mnt/data'

ZH = {'Baoan': '宝安', 'Futian': '福田', 'Longgang': '龙岗', 'Luohu': '罗湖',
      'Yantian': '盐田', 'Longhua': '龙华', 'Guangming': '光明',
      'Nanshan': '南山', 'Pingshan': '坪山'}
EN = {v: k for k, v in ZH.items()}


def _rings(geom, eps=None):
    """shp 记录 → 网格坐标下的环列表 [[N,2], ...]（可选 DP 简化）。"""
    parts, pts, _st = geom
    col, row = GG.lonlat_to_rowcol(pts[:, 0], pts[:, 1])
    parts = list(parts) + [len(pts)]
    out = []
    for k in range(len(parts) - 1):
        r = np.column_stack([col[parts[k]:parts[k + 1]], row[parts[k]:parts[k + 1]]])
        if len(r) >= 3:
            out.append(GG.simplify(r, eps) if eps else r)
    return out


def _rle(mask_1d):
    """一维布尔掩膜 → [[start, length], ...]。"""
    if not mask_1d.any():
        return []
    idx = np.flatnonzero(mask_1d)
    cuts = np.flatnonzero(np.diff(idx) > 1)
    starts = np.concatenate([[idx[0]], idx[cuts + 1]])
    ends = np.concatenate([idx[cuts], [idx[-1]]])
    return [[int(s), int(e - s + 1)] for s, e in zip(starts, ends)]


def _inaccess(grid):
    """反复腐蚀取最后存活像素 = 离边界最远点（标签落点）。"""
    cur = grid.copy()
    while cur.sum() > 1:
        nxt = cur.copy()
        nxt[1:, :] &= cur[:-1, :]; nxt[:-1, :] &= cur[1:, :]
        nxt[:, 1:] &= cur[:, :-1]; nxt[:, :-1] &= cur[:, 1:]
        if nxt.sum() == 0:
            break
        cur = nxt
    return np.argwhere(cur)[0] if cur.any() else np.argwhere(grid)[0]


def main():
    os.makedirs(REP, exist_ok=True)
    df = pd.read_csv(os.path.join(PROJ, 'stage01_protocol', 'split', 'analysis_split.csv'))
    rmin, rmax = int(df['row'].min()), int(df['row'].max())
    cmin, cmax = int(df['col'].min()), int(df['col'].max())
    R, C = rmax - rmin + 1, cmax - cmin + 1
    insc = df[df['in_main'] == 1]
    rows = insc['row'].to_numpy(int) - rmin
    cols = insc['col'].to_numpy(int) - cmin
    CX = cols + cmin + 0.5
    CY = rows + rmin + 0.5

    out = {'source': {
        'study_districts': 'data/研究边界/studyarea.shp  (community faces, GBK, WGS84; QUNAME = district)',
        'city_districts': 'data/2023年县级/2023年初县矢量.shp  (NAME_2=Shenzhen, WGS84)',
        'crs': 'WGS84 → UTM 49N (EPSG:32649, Snyder/Krüger) → grid (col,row): '
               'col=(x-794467.4184)/100, row=155-(y-2492889.4085)/100',
        'method': 'district membership assigned per 100 m cell by point-in-polygon of the cell '
                  'centre inside the author community faces; boundaries are drawn as 0.5-level '
                  'contours of the same soft class vote used for the A/B/buffer/C fills, so all '
                  'boundaries in Fig. 1 share one smoothing.',
    }}

    # ---------- 区归属栅格 ------------------------------------------------
    sb = os.path.join(DATA, '研究边界', 'studyarea')
    G = GG.read_shp(sb + '.shp')
    _f, rec = GG.read_dbf(sb + '.dbf', enc='gbk')
    names = sorted({x['QUNAME'] for x in rec if x and x['QUNAME']})
    idx_of = {n: i + 1 for i, n in enumerate(names)}
    D = np.zeros((R, C), np.uint8)
    for i, g in enumerate(G):
        if g is None or not rec[i]:
            continue
        di = idx_of[rec[i]['QUNAME']]
        hit = np.zeros(len(insc), bool)
        for r in _rings(g):
            x, y = r[:, 0], r[:, 1]
            x1, y1 = np.roll(x, -1), np.roll(y, -1)
            inside = np.zeros(len(insc), bool)
            for k in range(len(x)):
                cond = (y[k] > CY) != (y1[k] > CY)
                xint = (x1[k] - x[k]) * (CY - y[k]) / (y1[k] - y[k] + 1e-30) + x[k]
                inside ^= cond & (CX < xint)
            hit ^= inside
        free = hit & (D[rows, cols] == 0)
        D[rows[free], cols[free]] = di

    out['district_names'] = [{'zh': n, 'en': EN.get(n, n)} for n in names]
    rle = {}
    for rr in range(R):
        segs = []
        row = D[rr]
        for di in np.unique(row[row > 0]):
            for st, ln in _rle(row == di):
                segs.append([int(di), st, ln])
        if segs:
            rle[str(rr)] = segs
    out['district_rle'] = rle
    out['n_assigned'] = int((D > 0).sum())
    out['n_inscope'] = int(len(insc))

    # 标签落点 + 单元数（只给面积够大的区）
    labels = []
    for n in names:
        m = (D == idx_of[n])
        if m.sum() < 400:
            continue
        pr, pc = _inaccess(m)
        labels.append({'zh': n, 'en': EN.get(n, n), 'col': float(pc + cmin),
                       'row': float(pr + rmin), 'n_cells': int(m.sum())})
    out['district_labels'] = labels

    # ---------- 深圳全市 9 区外轮廓（inset 背景） -------------------------
    cb = os.path.join(DATA, '2023年县级', '2023年初县矢量')
    Gc = GG.read_shp(cb + '.shp')
    _fc, rc = GG.read_dbf(cb + '.dbf', enc='utf-8')
    city = []
    for i, g in enumerate(Gc):
        if g is None or not rc[i] or rc[i].get('NAME_2') != 'Shenzhen':
            continue
        nm = rc[i]['NAME_3']
        city.append({'en': nm, 'zh': ZH.get(nm, nm),
                     'rings': [np.round(r, 2).tolist() for r in _rings(g, 1.2)]})
    out['city_districts'] = city

    p = os.path.join(REP, 'shenzhen_admin_studyarea.json')
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print('[s05.7] %s  (%.1f KB)' % (os.path.relpath(p, PROJ), os.path.getsize(p) / 1024))
    print('  district raster rows            : %d / %d' % (len(rle), R))
    print('  districts labelled              : %s' % ', '.join('%s(%d)' % (d['zh'], d['n_cells']) for d in labels))
    print('  assigned %d / %d in-scope cells' % (out['n_assigned'], out['n_inscope']))
    print('  city districts for inset        : %d' % len(city))


if __name__ == '__main__':
    main()
