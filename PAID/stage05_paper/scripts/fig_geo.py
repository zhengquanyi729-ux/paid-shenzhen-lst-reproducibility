"""
fig_geo — 最小几何工具（无 geopandas / pyproj 依赖）
=====================================================
为 Fig 1 提供：WGS84 → UTM 49N 正算，SHP/DBF 读取，UTM → 分析网格 (col,row) 映射。

只用 numpy + struct，保证在仅有 numpy/pandas/matplotlib/Pillow 的环境可复现。

网格映射（由 stage 冻结的 grid_utm.shp 记录反推，固定不变）：
    left(col)  = 794467.4184 + col * 100           (m, UTM 49N)
    top(row)   = 2492889.4085 - (row - 155) * 100  (m, UTM 49N)
故：
    col_f = (x - 794467.4184) / 100
    row_f = 155 - (y - 2492889.4085) / 100
"""
import struct
import numpy as np

# --- WGS84 / UTM 49N 常量 --------------------------------------------------
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2 - _F)
_K0 = 0.9996
_LON0 = 111.0                      # 中央经线
_FE = 500000.0

# --- 冻结网格原点（m, UTM 49N） -------------------------------------------
GRID_X0 = 794467.4184              # col = 0 左边界
GRID_Y0 = 2492889.4085             # row = 155 上边界
CELL = 100.0
ROW_REF = 155


def wgs84_to_utm49(lon, lat):
    """WGS84 经纬度（度）→ UTM 49N 平面坐标（m）。Snyder/Krüger 级数，mm 级精度。"""
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    p = np.radians(lat)
    l = np.radians(lon)
    l0 = np.radians(_LON0)
    e2, ep2 = _E2, _E2 / (1.0 - _E2)
    sp, cp, tp = np.sin(p), np.cos(p), np.tan(p)
    N = _A / np.sqrt(1.0 - e2 * sp ** 2)
    T = tp ** 2
    C = ep2 * cp ** 2
    Ac = (l - l0) * cp
    M = _A * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * p
              - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * np.sin(2 * p)
              + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * np.sin(4 * p)
              - (35 * e2 ** 3 / 3072) * np.sin(6 * p))
    x = _K0 * N * (Ac + (1 - T + C) * Ac ** 3 / 6
                   + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * Ac ** 5 / 120) + _FE
    y = _K0 * (M + N * tp * (Ac ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * Ac ** 4 / 24
                             + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * Ac ** 6 / 720))
    return x, y


def utm_to_rowcol(x, y):
    """UTM 49N (m) → 分析网格浮点坐标 (col_f, row_f)。"""
    col_f = (np.asarray(x, float) - GRID_X0) / CELL
    row_f = ROW_REF - (np.asarray(y, float) - GRID_Y0) / CELL
    return col_f, row_f


def lonlat_to_rowcol(lon, lat):
    return utm_to_rowcol(*wgs84_to_utm49(lon, lat))


# --- 极简 Shapefile / DBF 读取 ---------------------------------------------
def read_shp(path):
    """返回 [(parts, pts(N,2), shapetype), ...]；已删除记录为 None。"""
    with open(path, 'rb') as fh:
        b = fh.read()
    off, n, out = 100, len(b), []
    while off < n:
        _rn, clen = struct.unpack('>ii', b[off:off + 8])
        off += 8
        c = b[off:off + clen * 2]
        off += clen * 2
        st = struct.unpack('<i', c[0:4])[0]
        if st == 0:
            out.append(None)
            continue
        nparts = struct.unpack('<i', c[36:40])[0]
        npo = struct.unpack('<i', c[40:44])[0]
        parts = list(struct.unpack('<%di' % nparts, c[44:44 + 4 * nparts]))
        pts = np.frombuffer(c, dtype='<f8', count=2 * npo,
                            offset=44 + 4 * nparts).reshape(-1, 2)
        out.append((parts, pts, st))
    return out


def read_dbf(path, enc='utf-8'):
    """返回 [{field: str}, ...]；已删除记录为 None。"""
    with open(path, 'rb') as fh:
        b = fh.read()
    nrec, hdlen, rlen = struct.unpack('<IHH', b[4:12])
    nf = (hdlen - 33) // 32
    fields = []
    for i in range(nf):
        o = 32 + 32 * i
        fields.append((b[o:o + 11].split(b'\x00')[0].decode('latin1'),
                       chr(b[o + 11]), b[o + 16]))
    recs = []
    for r in range(nrec):
        o = hdlen + r * rlen
        row = b[o:o + rlen]
        if row[:1] == b'*':
            recs.append(None)
            continue
        p, d = 1, {}
        for nm, _tp, ln in fields:
            v = row[p:p + ln]
            p += ln
            try:
                d[nm] = v.decode(enc).strip()
            except Exception:
                d[nm] = v.decode('latin1').strip()
        recs.append(d)
    return fields, recs


# --- 折线简化（Douglas–Peucker，纯 numpy 递归） -----------------------------
def _dp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    L = np.hypot(*ab)
    if L == 0:
        d = np.hypot(*(pts - a).T)
    else:
        v = pts - a
        d = np.abs(ab[0] * v[:, 1] - ab[1] * v[:, 0]) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        left = _dp(pts[:i + 1], eps)
        right = _dp(pts[i:], eps)
        return np.vstack([left[:-1], right])
    return np.vstack([a, b])


def simplify(pts, eps=0.35):
    """eps 单位 = 网格单元（100 m）；默认 0.35 单元 ≈ 35 m。"""
    return _dp(np.asarray(pts, float), eps)
