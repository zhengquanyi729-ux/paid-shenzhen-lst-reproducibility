"""
S01.2 空间划分（发现—验证防火墙分区）
=====================================
目的：依据 S01.1 定的去相关尺度 R，把 31760 格主样本切成 **A 发现区 / B 开发验证区 / C 锁定区**，
      并对锁定区 C 施加 ≥R 的空间缓冲，冻结 split manifest。

框架依据：
  §5.1 数据隔离设计：A 约 60%（Agent 可反复实验）；B 约 20%（方法筛选与稳健性；参与调参后不再
       视为独立确认）；C 约 20%（仅独立验证服务持有目标值，候选冻结后解封）。
  §5.2 需冻结对象：Split manifest（空间分块规则、分区 ID、缓冲规则、随机种子、版本）。
  §6 Exp.3：空间分块 / 缓冲验证，控制相邻网格造成的过乐观泛化。

关键设计决策（理由随报告一并冻结）：
  1) **分区必须连通**：采用对 100 m 格中心坐标的 k-means（k=5，种子固定）产生 5 个连通 Voronoi 簇，
     再把簇整体指派给 A/B/C。随机抽格会造成大量空间泄漏，已由 S01.1 排除。
  2) **缓冲只施加于 C**：A 与 B 同属"开发域"（B 显式声明为非独立），二者相邻不构成防火墙漏洞；
     真正需要防泄漏的是 C 与其余样本。故只把 C 中距 A∪B < R 的格剔除为缓冲格。
  3) **簇指派规则**：在 3^5 个指派中，先筛出 A/B/C 占比落在 (0.60,0.20,0.20)±0.03 的指派，
     再取"锁定区 C 的地表覆盖（NDVI 三分位）偏离全局最小"者——以免 C 成为一个特殊的植被/建成子集。
  4) 缓冲会削减 C 的实际格数，最终有效占比以本脚本输出为准。

输出：
  split/analysis_split.csv      逐格分区表（全部 32748 格）
  split/zone_A_open.csv         A 区（开放，含全部列）
  split/zone_B_devval.csv       B 区（开发验证，含全部列）
  locked/zone_C_targets.csv     C 区（锁定，仅 Grid_ID 与 LST 目标值）
  locked/README.txt             锁定区访问规约
  split/split_manifest.json     冻结清单（含分块规则、种子、规模、地表覆盖、最小间距、哈希）
  reports/s01_02_split.json / .md, figures/s01_02_split_map.png
"""
import sys, os, json, hashlib, itertools, csv as _csv
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import geoio as g
import config as C
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs(C.S01_REPORTS, exist_ok=True)
SPLIT = os.path.join(C.S01, 'split')
LOCKED = os.path.join(C.S01, 'locked')
FIG = os.path.join(C.S01_REPORTS, 'figures')
for d in (SPLIT, LOCKED, FIG):
    os.makedirs(d, exist_ok=True)

R_REPORT = json.load(open(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.json'), encoding='utf-8'))
R_CELLS = int(R_REPORT['recommendation']['R_cells'])
SEED = 20260924
K = 5
VERSION = 'stage01-split-v1'
OFF = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
ROLE = {1: 'discovery', 2: 'dev_validation', 3: 'locked', 0: 'outside'}

# ------------------------------------------------------------------ 装载
grid_recs, _, _ = g.read_dbf(os.path.join(C.DATA, '研究边界/grid_utm.dbf'))
info = {}
for r in grid_recs:
    gid = int(r['Grid_ID'])
    info[gid] = dict(row=int(r['row_index']), col=int(r['col_index']),
                     left=float(r['left']), top=float(r['top']))
all_ids = sorted(info)
id2i = {g: i for i, g in enumerate(all_ids)}
NR = max(info[g]['row'] for g in all_ids) + 1
NC = max(info[g]['col'] for g in all_ids) + 1

main_ids = [int(x) for x in open(os.path.join(C.S00_MASK, 'valid_ids_main.txt')).read().split()]
df = pd.read_csv(C.CSV)
df.columns = [c.strip() for c in df.columns]
df = df.set_index('My_ID')
cols9 = ['LST_mean', 'NDVI_mean', 'DEM_mean', 'SVF_mean', 'Road_Dens', 'X_BD', 'X_BH', 'X_VolDens']

mR = np.array([info[g]['row'] for g in main_ids])
mC = np.array([info[g]['col'] for g in main_ids])
ndvi = np.array([float(df.loc[g, 'NDVI_mean']) for g in main_ids])
T = len(main_ids)
incell = np.zeros((NR, NC), bool)
incell[mR, mC] = True

# ------------------------------------------------------------------ 工具
def dilate(m, k):
    o = m.copy()
    for _ in range(k):
        n = o.copy()
        for dr, dc in OFF:
            a = np.zeros_like(o)
            a[max(0, dr):NR + min(0, dr), max(0, dc):NC + min(0, dc)] = \
                o[max(0, -dr):NR + min(0, -dr), max(0, -dc):NC + min(0, -dc)]
            n |= a
        o = n
    return o


def kmeans(pts, k, seed, it=80, restarts=10):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(restarts):
        cen = pts[rng.choice(len(pts), k, replace=False)].copy()
        for _ in range(it):
            d = ((pts[:, None, :] - cen[None, :, :]) ** 2).sum(-1)
            lab = d.argmin(1)
            for j in range(k):
                if (lab == j).any():
                    cen[j] = pts[lab == j].mean(0)
        inertia = float(((pts - cen[lab]) ** 2).sum())
        if best is None or inertia < best[0]:
            best = (inertia, lab)
    return best[1], best[0]


def n_components(cells):
    """cells: (row,col) 数组，8 邻域连通分量数。"""
    idx = {p: i for i, p in enumerate(cells)}
    par = list(range(len(cells)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    for i, (r, c) in enumerate(cells):
        for dr, dc in OFF:
            j = idx.get((r + dr, c + dc))
            if j is not None:
                a, b = find(i), find(j)
                if a != b:
                    par[a] = b
    return len({find(i) for i in range(len(cells))})


# ------------------------------------------------------------------ 1) k-means 连通分区
pts = np.c_[mR / (NR - 1.0), mC / (NC - 1.0)]
lab, inertia = kmeans(pts, K, SEED)
cluster_cells = [np.where(lab == j)[0] for j in range(K)]
cluster_ncomp = {}
for j in range(K):
    cells = list(zip(mR[cluster_cells[j]], mC[cluster_cells[j]]))
    cluster_ncomp[j] = n_components(cells)

# ------------------------------------------------------------------ 2) 簇指派搜索
q1, q2 = np.quantile(ndvi, [1 / 3, 2 / 3])
tc = np.where(ndvi <= q1, 0, np.where(ndvi <= q2, 1, 2))
gshare = np.array([np.mean(tc == t) for t in (0, 1, 2)])
TOL = 0.03
cands = []
for asg in itertools.product((1, 2, 3), repeat=K):
    if len(set(asg)) < 3:
        continue
    # 用格数算占比
    fs = [sum(len(cluster_cells[j]) for j in range(K) if asg[j] == z) / T for z in (1, 2, 3)]
    if abs(fs[0] - 0.6) > TOL or abs(fs[1] - 0.2) > TOL or abs(fs[2] - 0.2) > TOL:
        continue
    # 先按 C 构建格（pre-buffer）评估 C 的表覆盖
    cidx = np.concatenate([cluster_cells[j] for j in range(K) if asg[j] == 3])
    sh = np.array([np.mean(tc[cidx] == t) for t in (0, 1, 2)])
    lc = float(np.abs(sh - gshare).sum())
    cands.append((round(lc, 4), -len(cidx), asg, fs, sh))
if not cands:
    raise SystemExit('无满足 ±3% 的指派，需放宽 TOL')
cands.sort(key=lambda x: (x[0], x[1]))
lc_div, _, ASG, fs_pre, cshare_pre = cands[0]

tag = np.zeros(len(main_ids), np.int8)
for j in range(K):
    tag[cluster_cells[j]] = ASG[j]
Z = np.zeros((NR, NC), np.int8)
Z[mR, mC] = tag

# ------------------------------------------------------------------ 3) 对 C 施加 R 缓冲
AorB = (Z == 1) | (Z == 2)
nearAB = np.zeros((NR, NC), bool)      # A∪B 向外膨胀 1 格的邻域
for dr, dc in OFF:
    a = np.zeros_like(nearAB)
    a[max(0, dr):NR + min(0, dr), max(0, dc):NC + min(0, dc)] = \
        AorB[max(0, -dr):NR + min(0, -dr), max(0, -dc):NC + min(0, -dc)]
    nearAB |= a
# 与 A∪B 距离 < R 的 C 格 -> 缓冲格
too_close = dilate(nearAB, max(0, R_CELLS - 1)) & (Z == 3) & incell

role_grid = np.full((NR, NC), 0, np.int8)          # 0 outside
role_grid[incell & (Z == 1)] = 1
role_grid[incell & (Z == 2)] = 2
role_grid[incell & (Z == 3)] = 3
role_grid[too_close] = 4                            # 4 = buffer（原属 C，被缓冲剔除）

# C 缓冲后仍连通吗
c_keep_cells = np.array(np.where((role_grid == 3)))
c_keep_rc = list(zip(c_keep_cells[0], c_keep_cells[1]))
ncomp_C = n_components(c_keep_rc) if c_keep_rc else 0

# ------------------------------------------------------------------ 4) 最近距离（C 与 A∪B；A 与 B）
def min_dist(rc_from, rc_to, maxd=90):
    """返回 rc_to 中各点到 rc_from 集合的最小距离（8 邻域逐圈膨胀，八边形近似）。"""
    tgt = np.zeros((NR, NC), bool)
    f = np.array(rc_from)
    tgt[f[:, 0], f[:, 1]] = True
    t = np.array(rc_to)
    cur = tgt.copy()
    for k in range(1, maxd + 1):
        cur = dilate(cur, 1)
        if cur[t[:, 0], t[:, 1]].any():
            return k
    return None

Crc = list(zip(*np.where(role_grid == 3)))
ABrc = list(zip(*np.where((role_grid == 1) | (role_grid == 2))))
Arc = list(zip(*np.where(role_grid == 1)))
Brc = list(zip(*np.where(role_grid == 2)))
d_C_AB = min_dist(ABrc, Crc)
d_C_A = min_dist(Arc, Crc)
d_C_B = min_dist(Brc, Crc)
d_A_B = min_dist(Arc, Brc)

# ------------------------------------------------------------------ 5) 写出分区文件
with open(os.path.join(SPLIT, 'analysis_split.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh)
    w.writerow(['Grid_ID', 'row', 'col', 'in_main', 'zone', 'role'])
    for gid in all_ids:
        r, c = info[gid]['row'], info[gid]['col']
        rg = int(role_grid[r, c])
        zone = {1: 1, 2: 2, 3: 3, 4: 3}.get(rg, 0)
        role = 'buffer' if rg == 4 else ROLE.get(rg, 'outside')
        w.writerow([gid, r, c, int(incell[r, c]), zone, role])

zone_ids = {1: [], 2: [], 3: []}
for gid in main_ids:
    rg = int(role_grid[info[gid]['row'], info[gid]['col']])
    if rg in (1, 2, 3):
        zone_ids[rg].append(gid)

for z, fn in [(1, 'zone_A_open.csv'), (2, 'zone_B_devval.csv')]:
    with open(os.path.join(SPLIT, fn), 'w', newline='', encoding='utf-8-sig') as fh:
        w = _csv.writer(fh)
        w.writerow(['Grid_ID'] + cols9)
        for gid in zone_ids[z]:
            w.writerow([gid] + [df.loc[gid, c] for c in cols9])

with open(os.path.join(LOCKED, 'zone_C_targets.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh)
    w.writerow(['Grid_ID', 'LST_mean'])
    for gid in zone_ids[3]:
        w.writerow([gid, df.loc[gid, 'LST_mean']])

with open(os.path.join(LOCKED, 'README.txt'), 'w', encoding='utf-8') as fh:
    fh.write(
        '锁定区 C 目标值（Stage 01 冻结）\n'
        '================================\n'
        '本目录仅允许 Independent Validator 读取。\n'
        '规则：\n'
        '  1) 候选表达式与检验程序冻结之前，Discovery/Experiment/Falsification/Physics 四类\n'
        '     Agent 及其工具链不得读取本目录任何文件；\n'
        '  2) 验证服务只在收到已冻结候选后解封，并公布完整的通过/失败结果；\n'
        '  3) 若检验失败，可启动新一轮探索，但不得把"看过本目录后修订的模型"继续称作同一轮独立确认；\n'
        '  4) 哈希仅证明文件完整性，不替代访问控制——物理隔离须在 Stage 02 平台层实现。\n')

# ------------------------------------------------------------------ 6) 冻结清单
def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


pre_n = {z: int(np.sum(Z == z)) for z in (1, 2, 3)}
post_n = {z: int(np.sum(role_grid == z)) for z in (1, 2, 3)}
n_buf = int(np.sum(role_grid == 4))
post_T = sum(post_n.values())

lc_post = {}
for z in (1, 2, 3):
    sel = role_grid == z
    sel_main = np.array([sel[info[g]['row'], info[g]['col']] for g in main_ids])
    lc_post[ROLE[z]] = dict(
        n=int(sel_main.sum()),
        ndvi_tercile_share=[round(float(np.mean(tc[sel_main] == t)), 4) for t in (0, 1, 2)],
    )

manifest = dict(
    version=VERSION, created='2026-09-24', seed=SEED,
    rule=dict(
        partition='对 100 m 格中心坐标做 k-means（k=%d，seed=%d，10 次重启取最优惯量）得到 %d 个'
                  '连通 Voronoi 簇，整簇指派给 A/B/C。' % (K, SEED, K),
        assignment={'clusters_to_zone': {str(j): int(ASG[j]) for j in range(K)}},
        selection='在 3^%d 指派中筛出 A/B/C 占比落在 (0.60,0.20,0.20)±%.2f，'
                  '再取锁定区 C 的 NDVI 三分位构成偏离全局最小者。' % (K, TOL),
        buffer='仅对锁定区 C 施加：剔除 C 中距 A∪B < R 的格（R=%d 格=%.1f km），记为 buffer。'
               % (R_CELLS, R_CELLS * 0.1),
        buffer_rationale='A 与 B 同属开发域（B 参与调参后不再视为独立确认），二者之间不设缓冲；'
                         '防火墙独立性由 C 与 A∪B 的 ≥R 间距保证。',
    ),
    R_cells=R_CELLS, R_m=R_CELLS * 100,
    zone_label={1: 'A 发现区 discovery', 2: 'B 开发验证区 dev_validation', 3: 'C 锁定区 locked'},
    zone_size_pre_buffer=pre_n, zone_size_post_buffer=post_n, buffer_cells=n_buf,
    fractions_post_buffer={ROLE[z]: round(post_n[z] / post_T, 4) for z in (1, 2, 3)},
    connectivity=dict(cluster_ncomp=cluster_ncomp, C_components_after_buffer=ncomp_C),
    landcover_post=lc_post, ndvi_tercile_global=[round(float(x), 4) for x in gshare],
    min_distance_cells=dict(C_to_A=d_C_A, C_to_B=d_C_B, C_to_AB=d_C_AB, A_to_B=d_A_B),
    files={},
)
for rel in ['split/analysis_split.csv', 'split/zone_A_open.csv', 'split/zone_B_devval.csv',
            'locked/zone_C_targets.csv']:
    manifest['files'][rel] = sha256(os.path.join(C.S01, rel))
manifest['input_hashes'] = {
    'mask/valid_ids_main.txt': sha256(os.path.join(C.S00_MASK, 'valid_ids_main.txt')),
    'reports/s01_01_spatial_autocorr.json': sha256(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.json')),
}
with open(os.path.join(SPLIT, 'split_manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)
with open(os.path.join(SPLIT, 'split_manifest.sha256'), 'w', encoding='utf-8') as fh:
    fh.write('%s  split_manifest.json\n' % sha256(os.path.join(SPLIT, 'split_manifest.json')))

# ------------------------------------------------------------------ 7) 图（北向上·经纬度；叠加研究区与全市社区轮廓）
from matplotlib.collections import LineCollection
# 格中心（UTM49N）-> 经纬度；注意 grid_utm(32649) 与社区/研究区 shp(4326) 不同坐标系
cx = np.array([info[g]['left'] + 50.0 for g in all_ids])
cy = np.array([info[g]['top'] - 50.0 for g in all_ids])
lon_all, lat_all = g.utm_to_lonlat(cx, cy, 49)
grid_lon = {g: lon_all[i] for i, g in enumerate(all_ids)}
grid_lat = {g: lat_all[i] for i, g in enumerate(all_ids)}
xs = np.array([grid_lon[g] for g in all_ids])
ys = np.array([grid_lat[g] for g in all_ids])
cpre = np.array([int(Z[info[g]['row'], info[g]['col']]) for g in all_ids])
cpost = np.array([int(role_grid[info[g]['row'], info[g]['col']]) for g in all_ids])
colmap = {0: '#d9d9d9', 1: '#2166ac', 2: '#f4a582', 3: '#1a9850', 4: '#000000'}
leg = {1: 'A discovery', 2: 'B dev-validation', 3: 'C locked', 4: 'C buffer (dropped)', 0: 'not in main sample'}


def _rings(path):
    shp = g.read_shp(path)
    return [ring for s in shp['shapes'] for ring in s['parts'] if len(ring) >= 3]


city_rings = _rings(os.path.join(C.DATA, '边界/广东省深圳市各社区.shp'))     # 全市 668 社区（EPSG:4326）
sa_rings = _rings(os.path.join(C.DATA, '研究边界/studyarea.shp'))            # 研究区 299 社区（EPSG:4326）

fig, axes = plt.subplots(1, 2, figsize=(15, 7.2), dpi=150)
for ax, cz, ttl in [(axes[0], cpre, '(a) zones before buffer'),
                    (axes[1], cpost, '(b) zones after C-only buffer (R=%d cells)' % R_CELLS)]:
    ax.add_collection(LineCollection(city_rings, colors='#c8c8c8', linewidths=0.25))  # 全市轮廓（背景）
    for k in (0, 1, 2, 3, 4):
        m = cz == k
        if not m.any():
            continue
        ax.scatter(xs[m], ys[m], s=1.4, c=colmap[k], linewidths=0, label='%s (n=%d)' % (leg[k], int(m.sum())))
    for ring in sa_rings:                                                            # 研究区边界（黑）
        ax.plot(ring[:, 0], ring[:, 1], '-', color='k', lw=0.6)
    ax.set_xlabel('longitude (deg E)')
    ax.set_ylabel('latitude (deg N)')
    ax.set_aspect(1.0 / np.cos(np.deg2rad(22.55)))
    ax.set_xlim(113.70, 114.68)
    ax.set_ylim(22.36, 22.90)
    ax.set_title(ttl, fontsize=10)
    ax.grid(alpha=0.2)
axes[1].legend(markerscale=9, fontsize=8, loc='lower right')
fig.suptitle('S01.2 spatial split (north-up, lon/lat). Grey = all 668 Shenzhen communities; '
             'black = study area (299 communities); main sample n=%d, seed=%d' % (T, SEED), fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 's01_02_split_map.png'))
plt.close(fig)

# ------------------------------------------------------------------ 8) 报告
rep = dict(manifest=manifest,
           zone_sizes=dict(pre=pre_n, post=post_n, buffer=n_buf),
           landcover=lc_post)
with open(os.path.join(C.S01_REPORTS, 's01_02_split.json'), 'w', encoding='utf-8') as fh:
    json.dump(rep, fh, ensure_ascii=False, indent=2)

L = []
L.append('# S01.2 空间划分（发现—验证防火墙分区）\n')
L.append('框架依据：§5.1 数据隔离设计；§5.2 Split manifest；§6 Exp.3 空间分块 / 缓冲验证。\n')
L.append('## 1 规则\n')
L.append('- 分区几何：对 100 m 格中心坐标做 k-means（k=%d，seed=%d，10 次重启），得 %d 个连通 Voronoi 簇，'
         '整簇指派给 A/B/C —— **不做随机抽格**（S01.1 已证 LST 强空间自相关）。' % (K, SEED, K))
L.append('- 簇连通性：各簇 8 邻域连通分量数 = %s。' % list(cluster_ncomp.values()))
L.append('- 指派：%s（在 3^%d 指派中先筛占比落在 (0.60,0.20,0.20)±%.2f，再取 C 的地表覆盖偏离全局最小者）。'
         % (dict((j, int(ASG[j])) for j in range(K)), K, TOL))
L.append('- 缓冲：**只对锁定区 C** 剔除距 A∪B < R 的格（R=%d 格 = %.1f km，来自 S01.1）。'
         'A 与 B 同属开发域，之间不设缓冲。\n' % (R_CELLS, R_CELLS * 0.1))
L.append('## 2 规模\n')
L.append('| 区 | 缓冲前格数 | 缓冲前占比 | 缓冲后格数 | 缓冲后占比 |')
L.append('|---|---|---|---|---|')
for z in (1, 2, 3):
    L.append('| %s | %d | %.1f%% | **%d** | **%.1f%%** |'
             % (manifest['zone_label'][z], pre_n[z], 100 * pre_n[z] / T, post_n[z], 100 * post_n[z] / post_T))
L.append('| 缓冲格（自 C 剔除） | — | — | %d | — |' % n_buf)
L.append('| 合计（有效分析样本） | %d | 100%% | %d | 100%% |' % (T, post_T))
L.append('')
L.append('- C 缓冲后连通分量数 = **%d**。' % ncomp_C)
L.append('- 最小间距（棋盘距离，格）：C↔A = %s，C↔B = %s，**C↔A∪B = %s**（应 ≥ R = %d）；A↔B = %s（不设约束）。'
         % (d_C_A, d_C_B, d_C_AB, R_CELLS, d_A_B))
L.append('')
L.append('## 3 地表覆盖构成（NDVI 三分位，缓冲后）\n')
L.append('| 区 | 格数 | 低植被 | 中植被 | 高植被 |')
L.append('|---|---|---|---|---|')
for z in (1, 2, 3):
    s = lc_post[ROLE[z]]['ndvi_tercile_share']
    L.append('| %s | %d | %.3f | %.3f | %.3f |' % (manifest['zone_label'][z], lc_post[ROLE[z]]['n'], s[0], s[1], s[2]))
L.append('| 全局 | %d | %.3f | %.3f | %.3f |' % (T, gshare[0], gshare[1], gshare[2]))
L.append('')
L.append('> 空间连通分区 + 深圳地表覆盖的强空间聚集，使各区 NDVI 构成无法完全均衡；'
         '锁定区 C 的构成偏离（L1 距离 %.3f）须在验证协议中以**分层报告**处理，不得用以挑选结论。\n' % lc_div)
L.append('## 4 冻结产物\n')
L.append('| 文件 | 说明 | SHA-256（前 16 位） |')
L.append('|---|---|---|')
desc = {'split/analysis_split.csv': '逐格分区表（全部 %d 格）' % len(all_ids),
        'split/zone_A_open.csv': 'A 发现区（开放全列）',
        'split/zone_B_devval.csv': 'B 开发验证区（开发全列）',
        'locked/zone_C_targets.csv': 'C 锁定区（仅 ID + LST 目标）'}
for rel, h in manifest['files'].items():
    L.append('| `%s` | %s | `%s` |' % (rel, desc.get(rel, ''), h[:16]))
L.append('')
L.append('- 清单版本 **%s**，种子 %d；输入哈希见 `split_manifest.json`。' % (VERSION, SEED))
L.append('- 锁定区访问规约见 `locked/README.txt`。访问控制的**物理实现**（独立目录/服务、发现 Agent 无权读取）属 Stage 02 平台任务；本阶段先冻结分区与目标文件。')

with open(os.path.join(C.S01_REPORTS, 's01_02_split.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps(dict(cluster_ncomp=cluster_ncomp, assignment={j: int(ASG[j]) for j in range(K)},
                      lc_div=lc_div, pre=pre_n, post=post_n, buffer=n_buf,
                      C_components=ncomp_C,
                      dist=dict(C_A=d_C_A, C_B=d_C_B, C_AB=d_C_AB, A_B=d_A_B),
                      landcover=lc_post), ensure_ascii=False, indent=2))
print('\n写出: split/, locked/, reports/s01_02_split.json / .md, figures/s01_02_split_map.png')
