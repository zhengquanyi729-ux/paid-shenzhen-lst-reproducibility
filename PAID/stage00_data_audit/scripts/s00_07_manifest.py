"""
S00.7 SHA-256 清单
===================
对原始数据与 Stage 00 全部产物计算 SHA-256，生成两清单：
  manifest/data_sha256.txt      原始数据（只读，用于冻结"数据基线"）
  manifest/stage00_outputs_sha256.txt  Stage 00 产物
框架依据：§4「冻结哈希清单」；§8.2 Stage 00 交付物。
输出：manifest/*.txt, reports/s00_07_manifest.json
"""
import sys, os, json, hashlib, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import config as C

os.makedirs(C.S00_MANIFEST, exist_ok=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # stage00_data_audit


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk_manifest(root, out_txt, patterns=None):
    rows = []
    for dirpath, dirs, files in os.walk(root):
        if os.path.basename(dirpath) == 'manifest':
            continue
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            if patterns and not any(fn.lower().endswith(e) for e in patterns):
                continue
            rel = os.path.relpath(p, root)
            rows.append((rel.replace(os.sep, '/'), os.path.getsize(p), sha256(p)))
    rows.sort()
    with open(out_txt, 'w') as fh:
        for rel, size, h in rows:
            fh.write('%s  %10d  %s\n' % (h, size, rel))
    return rows


print('扫描原始数据 ...')
# 原始数据：全部文件（给定数据目录，只读）
data_files = []
for dirpath, dirs, files in os.walk(C.DATA):
    for fn in files:
        if fn == '.DS_Store':
            continue
        data_files.append(os.path.join(dirpath, fn))
data_rows = []
for p in sorted(data_files):
    rel = os.path.relpath(p, C.DATA).replace(os.sep, '/')
    data_rows.append((rel, os.path.getsize(p), sha256(p)))
with open(os.path.join(C.S00_MANIFEST, 'data_sha256.txt'), 'w') as fh:
    fh.write('# 原始数据 SHA-256 基线（相对 data/ 目录）\n')
    for rel, size, h in data_rows:
        fh.write('%s  %10d  %s\n' % (h, size, rel))
print('  原始数据 %d 个文件' % len(data_rows))

print('扫描 Stage 00 产物 ...')
out_rows = walk_manifest(ROOT, os.path.join(C.S00_MANIFEST, 'stage00_outputs_sha256.txt'),
                         patterns=('.md', '.json', '.csv', '.txt', '.png', '.py', '.docx'))
print('  产物 %d 个文件' % len(out_rows))

R = dict(n_data=len(data_rows), n_outputs=len(out_rows),
         data_bytes=sum(r[1] for r in data_rows), output_bytes=sum(r[1] for r in out_rows),
         data_files=[dict(path=r[0], size=r[1], sha256=r[2]) for r in data_rows],
         output_files=[dict(path=r[0], size=r[1], sha256=r[2]) for r in out_rows])
with open(os.path.join(C.S00_REPORTS, 's00_07_manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2)

print(json.dumps(dict(n_data=R['n_data'], n_outputs=R['n_outputs'],
                      data_MB=round(R['data_bytes'] / 1e6, 1), output_MB=round(R['output_bytes'] / 1e6, 2)),
                 ensure_ascii=False, indent=2))
print('\n写出: manifest/data_sha256.txt, manifest/stage00_outputs_sha256.txt, reports/s00_07_manifest.json')
