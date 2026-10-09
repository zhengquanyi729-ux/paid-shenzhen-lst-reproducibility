"""
geoio.py — PAID 项目纯 Python 地理数据读取与几何工具
=====================================================
运行环境无 gdal / rasterio / geopandas / pyproj / shapely，故自行实现：
  - GeoTIFF 元数据与像元数组读取（元数据手工解析 IFD，数组走 imageio）
  - Shapefile(.shp) 几何 + .dbf 属性读取
  - WGS84 ↔ UTM 横轴墨卡托正反算（用于跨带/跨坐标系核验）
  - 多边形射线法点定位（含内环）

约定：所有函数只读，不修改原始数据。
"""

import struct
import numpy as np

# ---------------------------------------------------------------- 椭球常数
_A = 6378137.0
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)
_EP2 = _E2 / (1.0 - _E2)
_K0 = 0.9996

# ---------------------------------------------------------------- GeoTIFF

_TIFF_TYPE_SIZE = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
_TIFF_FMT = {1: 'B', 3: 'H', 4: 'I', 5: 'I', 6: 'b', 8: 'h', 9: 'i', 10: 'i', 11: 'f', 12: 'd', 2: 'c'}


def read_tiff_tags(path):
    """解析 TIFF 第一个 IFD，返回 {tag: value}。支持 BigTIFF。"""
    with open(path, 'rb') as f:
        data = f.read()
    bo = '<' if data[:2] == b'II' else '>'
    magic = struct.unpack(bo + 'H', data[2:4])[0]
    if magic == 42:
        big, off = False, struct.unpack(bo + 'I', data[4:8])[0]
    elif magic == 43:
        big, off = True, struct.unpack(bo + 'Q', data[8:16])[0]
    else:
        raise ValueError('not a TIFF: %s' % path)
    nent_size = 8 if big else 2   # IFD 头部「条目数」字段宽度
    cnt_size = 8 if big else 4    # 条目的「值个数」字段宽度
    val_size = 8 if big else 4    # 条目的「值或偏移」字段宽度
    es = 20 if big else 12        # 单条目字节数

    def readifd(o):
        n = struct.unpack(bo + ('Q' if big else 'H'), data[o:o + nent_size])[0]
        tags = {}
        for i in range(n):
            e = o + nent_size + i * es
            tag, typ = struct.unpack(bo + 'HH', data[e:e + 4])
            cnt = struct.unpack(bo + ('Q' if big else 'I'), data[e + 4:e + 4 + cnt_size])[0]
            valoff = e + 4 + cnt_size
            sz = _TIFF_TYPE_SIZE.get(typ, 1) * cnt
            if sz <= val_size:
                raw = data[valoff:valoff + sz]
            else:
                ptr = struct.unpack(bo + ('Q' if big else 'I'), data[valoff:valoff + val_size])[0]
                raw = data[ptr:ptr + sz]
            try:
                if typ == 2:
                    v = raw.split(b'\x00')[0].decode('ascii', 'ignore')
                else:
                    v = struct.unpack(bo + str(cnt) + _TIFF_FMT[typ], raw[:cnt * _TIFF_TYPE_SIZE[typ]])
                    if len(v) == 1:
                        v = v[0]
            except Exception as exc:
                v = ('ERR', repr(exc))
            tags[tag] = v
        p = o + nent_size + n * es
        nxt = struct.unpack(bo + ('Q' if big else 'I'), data[p:p + val_size])[0]
        return tags, nxt

    tags, _ = readifd(off)
    return tags


def tiff_geo(tags):
    """从 TIFF 标签提取 (crs_epsg, origin_x, origin_y, px_w, px_h, width, height, nodata)。"""
    width = tags.get(256)
    height = tags.get(257)
    nodata = tags.get(42113)
    if isinstance(nodata, str):
        try:
            nodata = float(nodata)
        except ValueError:
            nodata = None

    epsg = None
    gk = tags.get(34735)
    citation = None
    if gk:
        arr = list(gk)
        keys = {}
        for i in range(4, len(arr), 4):
            keys[arr[i]] = (arr[i + 2], arr[i + 3])  # (location, value)
        if 3072 in keys:
            epsg = keys[3072][1]
    if 34737 in tags:
        citation = tags[34737]

    scale = tags.get(33550)
    tie = tags.get(33922)
    ox = oy = None
    px_w = px_h = None
    if scale and tie:
        px_w, px_h = float(scale[0]), float(scale[1])
        ox, oy = float(tie[3]), float(tie[4])
    return dict(epsg=epsg, citation=citation, origin_x=ox, origin_y=oy,
                px_w=px_w, px_h=px_h, width=width, height=height, nodata=nodata)


def read_raster(path):
    """读取栅格为 numpy 数组（bands, rows, cols）或 (rows, cols)。使用 imageio。"""
    import imageio.v3 as iio
    a = iio.imread(path)
    return np.asarray(a)


# ---------------------------------------------------------------- DBF

def read_dbf(path, encoding='gbk'):
    """读取 DBF，返回 (records:list[dict], fields:list[(name, len)], nrec)。"""
    with open(path, 'rb') as f:
        h = f.read(32)
        nrec = struct.unpack('<I', h[4:8])[0]
        hlen = struct.unpack('<H', h[8:10])[0]
        rlen = struct.unpack('<H', h[10:12])[0]
        fields = []
        while True:
            b = f.read(32)
            if not b or b[0:1] == b'\x0d':
                break
            name = b[0:11].split(b'\x00')[0].decode('utf-8', 'replace')
            fields.append((name, b[16]))
        f.seek(hlen)
        out = []
        for _ in range(nrec):
            r = f.read(rlen)
            if len(r) < rlen:
                break
            d, p = {}, 1
            for name, ln in fields:
                raw = r[p:p + ln]
                try:
                    v = raw.decode(encoding).strip()
                except Exception:
                    v = raw.decode('utf-8', 'replace').strip()
                d[name] = v
                p += ln
            out.append(d)
    return out, fields, nrec


def dbf_num(rec, key):
    """安全取数值字段（DBF 溢出为 **** 时返回 None）。"""
    v = rec.get(key, '')
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- SHP

_SHP_TYPE = {0: 'Null', 1: 'Point', 3: 'Polyline', 5: 'Polygon', 8: 'MultiPoint',
             11: 'PointZ', 13: 'PolylineZ', 15: 'PolygonZ', 18: 'MultiPointZ',
             21: 'PointM', 23: 'PolylineM', 25: 'PolygonM', 28: 'MultiPointM', 31: 'MultiPatch'}


def read_shp(path):
    """读取 SHP，返回 dict(type, bbox, shapes)。
    每个 shape 为 dict(shape_type, parts, points, bbox)；
    parts 为 rings 索引分段（Polygon/Polyline 时为 list[array(N,2)]）。
    """
    with open(path, 'rb') as f:
        data = f.read()
    if struct.unpack('>i', data[0:4])[0] != 9994:
        raise ValueError('not a shapefile: %s' % path)
    shape_type = struct.unpack('<i', data[32:36])[0]
    bbox = struct.unpack('<4d', data[36:68])
    shapes = []
    off = 100
    n = len(data)
    while off + 8 <= n:
        clen = struct.unpack('>i', data[off + 4:off + 8])[0]
        if clen <= 0:
            break
        rec = data[off + 8:off + 8 + clen * 2]
        off += 8 + clen * 2
        if len(rec) < 4:
            break
        st = struct.unpack('<i', rec[0:4])[0]
        if st == 0:
            shapes.append(dict(shape_type=0, parts=[], points=np.empty((0, 2))))
            continue
        if st in (5, 15, 25, 3, 13, 23):
            nparts, npoints = struct.unpack('<ii', rec[36:44])
            parts_idx = struct.unpack('<%di' % nparts, rec[44:44 + 4 * nparts])
            p0 = 44 + 4 * nparts
            pts = np.frombuffer(rec[p0:p0 + 16 * npoints], dtype='<f8').reshape(-1, 2)
            parts = [pts[parts_idx[i]:(parts_idx[i + 1] if i + 1 < nparts else npoints)]
                     for i in range(nparts)]
            shapes.append(dict(shape_type=st, parts=parts, points=pts))
        elif st in (1, 11, 21):
            x, y = struct.unpack('<2d', rec[4:20])
            shapes.append(dict(shape_type=st, parts=[np.array([[x, y]])], points=np.array([[x, y]])))
        else:
            shapes.append(dict(shape_type=st, parts=[], points=np.empty((0, 2))))
    return dict(type=shape_type, type_name=_SHP_TYPE.get(shape_type, str(shape_type)),
                bbox=bbox, shapes=shapes)


def points_in_polygon(pts, rings):
    """射线法：pts (N,2) 是否落在 rings（可能含内环）围成的多边形内。偶奇规则。"""
    inside = np.zeros(len(pts), dtype=bool)
    x, y = pts[:, 0], pts[:, 1]
    for ring in rings:
        if len(ring) < 3:
            continue
        x1, y1 = ring[:-1, 0], ring[:-1, 1]
        x2, y2 = ring[1:, 0], ring[1:, 1]
        cond = ((y1 > y) != (y2 > y))
        with np.errstate(divide='ignore', invalid='ignore'):
            xint = (x2 - x1) * (y - y1) / (y2 - y1) + x1
        inside ^= cond & (x < xint)
    return inside


def shapely_union_mask(pts, shapes, bbox_pad=0.0):
    """pts 是否落在 shapes（Polygon 集合）中任意一个之内。"""
    m = np.zeros(len(pts), dtype=bool)
    if bbox_pad:
        pass
    for sh in shapes:
        if sh['shape_type'] not in (5, 15, 25) or not sh['parts']:
            continue
        m |= points_in_polygon(pts, sh['parts'])
    return m


# ---------------------------------------------------------------- UTM <-> WGS84

def utm_to_lonlat(easting, northing, zone, northern=True):
    """UTM 反算到 WGS84 经纬度（度）。"""
    e = np.asarray(easting, dtype='f8')
    nn = np.asarray(northing, dtype='f8')
    x = e - 500000.0
    y = nn - (0.0 if northern else 10000000.0)
    lon0 = np.radians(-183.0 + 6.0 * zone)

    M = y / _K0
    mu = M / (_A * (1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256))
    e1 = (1 - np.sqrt(1 - _E2)) / (1 + np.sqrt(1 - _E2))
    phi1 = (mu
            + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * np.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * np.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * np.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * np.sin(8 * mu))
    C1 = _EP2 * np.cos(phi1) ** 2
    T1 = np.tan(phi1) ** 2
    N1 = _A / np.sqrt(1 - _E2 * np.sin(phi1) ** 2)
    R1 = _A * (1 - _E2) / (1 - _E2 * np.sin(phi1) ** 2) ** 1.5
    D = x / (N1 * _K0)

    lat = phi1 - (N1 * np.tan(phi1) / R1) * (
        D ** 2 / 2
        - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * _EP2) * D ** 4 / 24
        + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * _EP2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = lon0 + (D
                  - (1 + 2 * T1 + C1) * D ** 3 / 6
                  + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * _EP2 + 24 * T1 ** 2) * D ** 5 / 120) / np.cos(phi1)
    return np.degrees(lon), np.degrees(lat)


def lonlat_to_utm(lon, lat, zone, northern=True):
    """WGS84 经纬度（度）正算到 UTM。"""
    lon = np.radians(np.asarray(lon, dtype='f8'))
    lat = np.radians(np.asarray(lat, dtype='f8'))
    lon0 = np.radians(-183.0 + 6.0 * zone)
    N = _A / np.sqrt(1 - _E2 * np.sin(lat) ** 2)
    T = np.tan(lat) ** 2
    C = _EP2 * np.cos(lat) ** 2
    Aa = (lon - lon0) * np.cos(lat)
    M = _A * ((1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256) * lat
              - (3 * _E2 / 8 + 3 * _E2 ** 2 / 32 + 45 * _E2 ** 3 / 1024) * np.sin(2 * lat)
              + (15 * _E2 ** 2 / 256 + 45 * _E2 ** 3 / 1024) * np.sin(4 * lat)
              - (35 * _E2 ** 3 / 3072) * np.sin(6 * lat))
    easting = _K0 * N * (Aa + (1 - T + C) * Aa ** 3 / 6
                         + (5 - 18 * T + T ** 2 + 72 * C - 58 * _EP2) * Aa ** 5 / 120) + 500000.0
    northing = _K0 * (M + N * np.tan(lat) * (Aa ** 2 / 2
                                             + (5 - T + 9 * C + 4 * C ** 2) * Aa ** 4 / 24
                                             + (61 - 58 * T + T ** 2 + 600 * C - 330 * _EP2) * Aa ** 6 / 720))
    if not northern:
        northing += 10000000.0
    return easting, northing


def raster_centers_to_lonlat(geo, rows, cols):
    """把栅格 (row, col) 索引转为像元中心的 WGS84 经纬度。zone 由 geo['epsg'] 推断。"""
    epsg = geo['epsg']
    zone = epsg - 32600 if epsg and 32601 <= epsg <= 32660 else 49
    east = geo['origin_x'] + (np.asarray(cols) + 0.5) * geo['px_w']
    north = geo['origin_y'] - (np.asarray(rows) + 0.5) * geo['px_h']
    return utm_to_lonlat(east, north, zone)
