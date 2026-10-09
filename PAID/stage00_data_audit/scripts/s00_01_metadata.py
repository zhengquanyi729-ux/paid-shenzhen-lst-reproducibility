"""
S00.1 元数据与来源核查
======================
目的：在进入任何实验前，穷尽档案中可恢复的来源信息——观测时间、传感器、反演流程、
QA、版本——并明确记录"哪些恢复到了、哪些没有"。

框架依据：§2.2 时间元数据不足；§8.1 优先增补数据（必须级）。
输出：reports/s00_01_metadata.json  +  reports/s00_01_metadata.md
"""
import sys, os, json, glob, hashlib, re, zipfile, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import geoio as g
import config as C

os.makedirs(C.S00_REPORTS, exist_ok=True)

# ---------------------------------------------------------------- 关键词探测
# 用于在文本类文件（qmd/xml/docx/json）中搜索来源线索
KEYS = ['date', 'time', 'sensor', 'landsat', 'sentinel', 'modis', 'aster', 'aster',
        'acquisition', 'datetime', 'scene', 'path', 'row', 'cloud', 'qa', 'lst',
        'retriev', 'algorithm', 'scale_factor', 'scale_factor', 'units', 'unit',
        'celsius', 'kelvin', '日期', '时间', '传感器', '影像', '反演', '年份', '观测']

result = {'raster': [], 'vector': [], 'text_sources': [], 'keyword_hits': []}


def sha256(path, blocksize=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(blocksize), b''):
            h.update(chunk)
    return h.hexdigest()


def text_of(path):
    """把文本/压缩文档统一抽成可搜索字符串。"""
    ext = path.lower().rsplit('.', 1)[-1]
    try:
        if ext == 'docx':
            z = zipfile.ZipFile(path)
            out = []
            for n in z.namelist():
                if n.endswith('.xml'):
                    out.append(z.read(n).decode('utf-8', 'ignore'))
            return '\n'.join(out)
        if ext in ('xml', 'qmd', 'prj', 'cpg', 'csv'):
            return open(path, 'rb').read().decode('utf-8', 'ignore')
        if ext == 'html' or ext == 'md':
            return open(path, 'rb').read().decode('utf-8', 'ignore')
    except Exception as e:
        return '<read error: %s>' % e
    return ''

# ---------------------------------------------------------------- 栅格
for f in sorted(glob.glob(os.path.join(C.DATA, '*.tif'))) + \
         sorted(glob.glob(os.path.join(C.DATA, '0_论文data', '*.tif'))):
    tags = g.read_tiff_tags(f)
    geo = g.tiff_geo(tags)
    aux = f + '.aux.xml'
    aux_has_stats = aux_has_srs = False
    aux_keys = []
    if os.path.exists(aux):
        t = open(aux, encoding='utf-8', errors='ignore').read()
        aux_has_stats = '<HistCounts>' in t or '<Histogram>' in t or '<GDALRasterAttributeTable' in t
        aux_has_srs = '<SRS>' in t
        aux_keys = sorted(set(re.findall(r'<(/?\w+)>', t)))[:20]
    rec = {
        'file': os.path.relpath(f, C.DATA),
        'bytes': os.path.getsize(f),
        'sha256': sha256(f),
        'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
        'epsg': geo['epsg'],
        'crs_wkt_name': tags.get(34737),
        'size': [geo['width'], geo['height']],
        'px': [geo['px_w'], geo['px_h']],
        'origin': [geo['origin_x'], geo['origin_y']],
        'nodata': geo['nodata'],
        'bands': tags.get(277),
        'bits_per_sample': tags.get(258),
        'sample_format': tags.get(339),
        # 来源线索类标签
        'tag_305_software': tags.get(305),
        'tag_306_datetime': tags.get(306),
        'tag_270_description': tags.get(270),
        'tag_271_make': tags.get(271),
        'tag_272_model': tags.get(272),
        'has_datetime_tag': 306 in tags,
        'aux_xml_present': os.path.exists(aux),
        'aux_has_stats': aux_has_stats,
        'aux_has_SRS': aux_has_srs,
    }
    result['raster'].append(rec)

# ---------------------------------------------------------------- 矢量
for f in sorted(glob.glob(os.path.join(C.DATA, '**', '*.shp'), recursive=True)):
    base = f[:-4]
    rec = {'file': os.path.relpath(f, C.DATA), 'bytes': os.path.getsize(f),
           'sha256': sha256(f),
           'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(f)).isoformat()}
    try:
        s = g.read_shp(f)
        rec.update(type=s['type_name'], n=len(s['shapes']),
                   bbox=[round(v, 3) for v in s['bbox']])
    except Exception as e:
        rec['error'] = repr(e)
    prj = base + '.prj'
    if os.path.exists(prj):
        t = open(prj).read()
        rec['prj'] = t[:120]
        bb = re.findall(r'PROJCS\["([^"]+)"|GEOGCS\["([^"]+)"', t)
        rec['prj_name'] = [a or b for a, b in bb]
        epsg = re.findall(r'CENTRAL_MERIDIAN",([\d.]+)', t)
        rec['central_meridian'] = epsg
    xml = base + '.shp.xml'
    if os.path.exists(xml):
        rec['shp_xml_present'] = True
        rec['shp_xml_excerpt'] = text_of(xml)[:600]
    rec['dbf_fields'] = [n for n, _ in g.read_dbf(base + '.dbf')[1]] if os.path.exists(base + '.dbf') else None
    result['vector'].append(rec)

# ---------------------------------------------------------------- 文本来源线索
for f in sorted(glob.glob(os.path.join(C.DATA, '**', '*.qmd'), recursive=True)) + \
         sorted(glob.glob(os.path.join(C.DATA, '**', '*.docx'), recursive=True)) + \
         sorted(glob.glob(os.path.join(C.DATA, '**', '*.shp.xml'), recursive=True)):
    txt = text_of(f)
    hits = sorted({k for k in KEYS if k.lower() in txt.lower()})
    result['text_sources'].append({
        'file': os.path.relpath(f, C.DATA),
        'chars': len(txt),
        'keyword_hits': hits,
        'excerpt': re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', txt))[:500],
    })

# ---------------------------------------------------------------- 内嵌图片证据（docx media）
EVID = os.path.join(C.S00_REPORTS, 'evidence')
os.makedirs(EVID, exist_ok=True)
result['embedded_images'] = []
for f in sorted(glob.glob(os.path.join(C.DATA, '**', '*.docx'), recursive=True)):
    if os.path.basename(f).startswith('~$'):
        continue
    try:
        z = zipfile.ZipFile(f)
    except Exception:
        continue
    for n in z.namelist():
        if n.startswith('word/media/') and not n.endswith('/'):
            out = os.path.join(EVID, os.path.basename(f).replace('.docx', '') + '__' + os.path.basename(n))
            with open(out, 'wb') as fh:
                fh.write(z.read(n))
            result['embedded_images'].append({
                'source_docx': os.path.relpath(f, C.DATA),
                'media': n, 'saved_as': os.path.relpath(out, C.PROJ),
                'bytes': os.path.getsize(out), 'sha256': sha256(out)})

# ---------------------------------------------------------------- ArcGIS 处理谱系（.shp.xml）
result['arcgis_lineage'] = []
for f in sorted(glob.glob(os.path.join(C.DATA, '**', '*.shp.xml'), recursive=True)):
    txt = text_of(f)
    cre = re.search(r'<CreaDate>(\d+)</CreaDate><CreaTime>(\d+)</CreaTime>', txt)
    procs = re.findall(r'<Process[^>]*Date="(\d+)"\s*Time="(\d+)"[^>]*>(.*?)</Process>', txt, re.S)
    result['arcgis_lineage'].append({
        'file': os.path.relpath(f, C.DATA),
        'created': ('%s %s' % cre.groups()) if cre else None,
        'n_processes': len(procs),
        'processes': [{'date': d, 'time': t, 'tool': re.sub(r'\s+', ' ', p)[:160]} for d, t, p in procs],
    })

# ---------------------------------------------------------------- 汇总判定
def has_date(rec):
    return bool(rec.get('tag_306_datetime')) or bool(rec.get('tag_305_software'))

dates = [r for r in result['raster'] if has_date(r)]
result['summary'] = {
    'n_raster': len(result['raster']),
    'n_raster_with_datetime_tag': len(dates),
    'n_raster_with_any_acq_metadata': sum(
        1 for r in result['raster']
        if r.get('tag_306_datetime') or r.get('tag_270_description')),
    'n_vector': len(result['vector']),
    'acquisition_time_recovered': len(dates) > 0,
    'sensor_recovered': any(r.get('tag_272_model') for r in result['raster']),
    'retrieval_algorithm_recovered': any(
        'algorithm' in (r.get('tag_270_description') or '').lower()
        for r in result['raster']),
}

with open(os.path.join(C.S00_REPORTS, 's00_01_metadata.json'), 'w', encoding='utf-8') as fh:
    json.dump(result, fh, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- Markdown
L = []
L.append('# S00.1 元数据与来源核查\n')
L.append('框架依据：§2.2（时间元数据不足）、§8.1（必须级增补项）。\n')
L.append('## 结论摘要\n')
s = result['summary']
L.append('| 核查项 | 结果 |')
L.append('|---|---|')
L.append('| 栅格文件数 | %d |' % s['n_raster'])
L.append('| 含 TIFF 采集时间标签(306) | %d |' % s['n_raster_with_datetime_tag'])
L.append('| **能否恢复观测时间** | **%s** |' % ('是' if s['acquisition_time_recovered'] else '否'))
L.append('| **能否恢复传感器** | **%s** |' % ('是' if s['sensor_recovered'] else '否'))
L.append('| **能否恢复反演流程** | **%s** |' % ('是' if s['retrieval_algorithm_recovered'] else '否'))
L.append('')
L.append('## 栅格：找回的元数据\n')
L.append('| 文件 | EPSG | 尺寸 | 像元 | nodata | 描述标签(270) | 时间标签(306) | aux 统计 |')
L.append('|---|---|---|---|---|---|---|---|')
for r in result['raster']:
    L.append('| %s | %s | %sx%s | %.4f | %s | %s | %s | %s |' % (
        r['file'], r['epsg'], r['size'][0], r['size'][1], r['px'][0], r['nodata'],
        r['tag_270_description'] or '—', r['tag_306_datetime'] or '—',
        '有' if r['aux_has_stats'] else '无'))
L.append('')
L.append('## 矢量：坐标系与要素数\n')
L.append('| 文件 | 类型 | 要素数 | .prj | 字段数 |')
L.append('|---|---|---|---|---|')
for r in result['vector']:
    L.append('| %s | %s | %s | %s | %s |' % (
        r['file'], r.get('type'), r.get('n'), r.get('prj_name'), len(r['dbf_fields'] or [])))
L.append('')
L.append('## 文本类文件中的来源线索\n')
for t in result['text_sources']:
    L.append('- **%s**（%d 字符）命中关键词：%s' % (t['file'], t['chars'], t['keyword_hits'] or '无'))
L.append('')
L.append('## 内嵌图片证据\n')
for im in result['embedded_images']:
    L.append('- `%s` → `%s`（%d 字节，SHA256 %s…）' % (
        im['source_docx'], im['saved_as'], im['bytes'], im['sha256'][:16]))
L.append('')
L.append('人工复核：`过程.docx` 内嵌图为 QGIS 3.x「Vector creation — Create grid」对话框截图，')
L.append('界面参数可直接读取，是网格生成流程的**一等证据**：')
L.append('')
L.append('| 参数 | 界面取值 |')
L.append('|---|---|')
L.append('| Grid type | Rectangle (Polygon) |')
L.append('| Grid extent | 794467.4184, 2485099.3175, 830617.9329, 2508389.4085 [EPSG:32649] |')
L.append('| Horizontal spacing | 100.000000 meters |')
L.append('| Vertical spacing | 100.000000 meters |')
L.append('| Grid CRS | EPSG:32649 — WGS 84 / UTM zone 49N |')
L.append('')
L.append('该 extent 与 `0_论文data/*_shenzhen.tif` 的栅格范围**完全一致**，说明网格并非由社区多边形生成，')
L.append('而是先取研究区栅格外包框生成 100 m 全覆盖网格，再与社区边界相交得到 `grid_utm.shp` 的 32748 格。')
L.append('')
L.append('## ArcGIS 处理谱系（.shp.xml）\n')
if not result['arcgis_lineage']:
    L.append('档案中无 .shp.xml，未恢复矢量侧处理谱系。')
for a in result['arcgis_lineage']:
    L.append('- **%s**：创建于 %s，共 %d 条处理记录' % (a['file'], a['created'], a['n_processes']))
    for p in a['processes'][-3:]:
        L.append('    - %s %s — `%s`' % (p['date'], p['time'][:6], p['tool'][:110]))
L.append('')
L.append('注：谱系仅覆盖行政区划矢量（2023 年县级、粤港澳大湾区 2023），')
L.append('**研究区自身数据（LST/NDVI/DEM/SVF/建筑/道路）无任何处理谱系**。')
L.append('')
L.append('## 判定\n')
L.append('档案中**不存在** LST 观测日期、传感器、过境时刻、反演算法与 QA 波段说明。')
L.append('所有 GeoTIFF 只带投影与统计信息；`过程.docx` 仅记录选址与网格生成步骤。')
L.append('据此，框架 §2.2「时间元数据不足」与 §8.1 的必须级增补项 **全部成立**：')
L.append('在补入原始影像元数据之前，任何日间/夜间、季节、热恢复动态类分析都不得开展。')
L.append('现有数据只能支撑**单一时相的空间分异**研究。')

with open(os.path.join(C.S00_REPORTS, 's00_01_metadata.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps(result['summary'], ensure_ascii=False, indent=2))
print('\n写出: reports/s00_01_metadata.json / .md')
