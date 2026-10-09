"""
S01.1 空间自相关诊断
=====================
目的：为「发现—验证防火墙」的空间划分确定**去相关尺度 R**，据以冻结分块与缓冲带宽。
框架依据：§5.1「60/20/20 为起始设计，并非统计最优比例；须在正式研究前依据空间相关范围、
地表覆盖、样本与边界条件冻结。必要时设置空间缓冲区。」

本脚本做四件事：
  A) 全局 Moran's I（8 邻域 queen）：原始 LST 与**去趋势残差**各算一次，各做 199 次置换检验；
  B) 各向相关图 r(k)：原始与去趋势残差；
  C) 分层相关图：以 NDVI 三分位作地表覆盖代理（低/中/高植被），检验"地表覆盖"对相关长度的影响；
  D) 由去相关尺度给出建议 R（缓冲带宽）与分区尺度，并给出敏感性说明。

为什么必须去趋势：
  研究区 LST 存在大尺度趋势（沿海—内陆、城市核心—边缘的连续梯度）。若直接在原始场上算
  相关图，会把这个确定性趋势的长程相关误当作随机过程的相关长度，显著高估 R。故本脚本
  以三阶二维多项式趋势面作为大尺度项，对残差（即需要防泄漏的随机部分）估计去相关尺度。

输出：reports/s01_01_spatial_autocorr.json / .md, figures/s01_01_correlogram.png
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
import numpy as np
import pandas as pd
import geoio as g
import config as C
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.makedirs(C.S01_REPORTS, exist_ok=True)
FIG = os.path.join(C.S01_REPORTS, 'figures')
os.makedirs(FIG, exist_ok=True)
R = {}
rng_seed = 20260924

# ---------------------------------------------------------------- 装载主样本 -> 规则网格
grid_recs, _, _ = g.read_dbf(os.path.join(C.DATA, '研究边界/grid_utm.dbf'))
info = {}
for r in grid_recs:
    gid = int(r['Grid_ID'])
    info[gid] = (int(r['row_index']), int(r['col_index']))
NR = max(v[0] for v in info.values()) + 1
NC = max(v[1] for v in info.values()) + 1

main_ids = [int(x) for x in open(os.path.join(C.S00_MASK, 'valid_ids_main.txt')).read().split()]
df = pd.read_csv(C.CSV)
df.columns = [c.strip() for c in df.columns]
df = df.set_index('My_ID')

rr = np.array([info[g][0] for g in main_ids])          # 行索引（=北向）
cc = np.array([info[g][1] for g in main_ids])          # 列索引（=东向）
z = np.array([float(df.loc[g, 'LST_mean']) for g in main_ids])
ndvi = np.array([float(df.loc[g, 'NDVI_mean']) for g in main_ids])
n_valid = len(z)

Z = np.full((NR, NC), np.nan)
Z[rr, cc] = z
mask = np.isfinite(Z)
D_raw = np.where(mask, Z - np.nanmean(Z), 0.0)
den_raw = float((D_raw ** 2).sum())

R['grid'] = dict(shape=[NR, NC], n_valid=n_valid,
                 mean=round(float(z.mean()), 4), std=round(float(z.std(ddof=0)), 4))

# ---------------------------------------------------------------- 去趋势（三阶二维多项式趋势面）
def trend_design(r, c, deg):
    # 先把坐标标准化到 [-1,1]，避免高阶多项式设计阵病态
    rn = (r - r.mean()) / (0.5 * (r.max() - r.min()))
    cn = (c - c.mean()) / (0.5 * (c.max() - c.min()))
    cols = []
    for d in range(deg + 1):
        for k in range(d + 1):
            cols.append((rn ** k) * (cn ** (d - k)))
    return np.array(cols, dtype='f8').T


def detrend(deg):
    X = trend_design(rr, cc, deg)
    beta, _, _, _ = np.linalg.lstsq(X, z, rcond=None)
    res = z - X @ beta
    r2 = 1.0 - float((res ** 2).sum()) / float(((z - z.mean()) ** 2).sum())
    return res, r2, X.shape[1]


DEG = 3
res, trend_r2, n_terms = detrend(DEG)
Zres = np.full((NR, NC), np.nan)
Zres[rr, cc] = res
D_res = np.where(mask, Zres - np.nanmean(Zres), 0.0)
den_res = float((D_res ** 2).sum())
R['detrend'] = dict(degree=DEG, n_terms=n_terms, trend_r2=round(trend_r2, 4),
                    resid_std=round(float(res.std(ddof=0)), 4))
R['detrend_sensitivity'] = {str(d): round(detrend(d)[1], 4) for d in (1, 2, 3, 4, 5)}

# ---------------------------------------------------------------- Moran's I + 置换检验
SHIFTS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def morans(D, mk):
    num = 0.0
    W = 0
    for dr, dc in SHIFTS:
        a = D[max(0, dr):NR + min(0, dr), max(0, dc):NC + min(0, dc)]
        b = D[max(0, -dr):NR + min(0, -dr), max(0, -dc):NC + min(0, -dc)]
        m = mk[max(0, dr):NR + min(0, dr), max(0, dc):NC + min(0, dc)] & \
            mk[max(0, -dr):NR + min(0, -dr), max(0, -dc):NC + min(0, -dc)]
        num += float((a * b)[m].sum())
        W += int(m.sum())
    return (n_valid / W) * (num / (D ** 2).sum()), W


def to_grid(values):
    Zg = np.full((NR, NC), np.nan)
    Zg[rr, cc] = values
    return Zg


def morans_perm(values, nperm=199, seed=rng_seed):
    """values: 长度 n_valid 的一维向量（按主样本顺序）。"""
    Zg = to_grid(values)
    Dv = np.where(mask, Zg - float(np.mean(values)), 0.0)
    I_obs, W = morans(Dv, mask)
    rng = np.random.default_rng(seed)
    perm = np.empty(nperm)
    for i in range(nperm):
        p = values.copy()
        rng.shuffle(p)
        perm[i] = morans(np.where(mask, to_grid(p) - float(np.mean(p)), 0.0), mask)[0]
    pval = (1 + int((perm >= I_obs).sum())) / (1 + nperm)
    return dict(I=round(float(I_obs), 4), W=int(W), n=n_valid,
                perm_mean=round(float(perm.mean()), 4), perm_std=round(float(perm.std()), 4),
                z=round(float((I_obs - perm.mean()) / perm.std()), 2), p_value=round(float(pval), 4))


R['morans_I_raw'] = morans_perm(z)
R['morans_I_detrended'] = morans_perm(res)

# ---------------------------------------------------------------- 相关图
def correlogram(D, den, mk, dr, dc, klim=40, min_pairs=30):
    out = []
    for k in range(1, klim + 1):
        a = D[max(0, dr * k):NR + min(0, dr * k), max(0, dc * k):NC + min(0, dc * k)]
        b = D[max(0, -dr * k):NR + min(0, -dr * k), max(0, -dc * k):NC + min(0, -dc * k)]
        m = mk[max(0, dr * k):NR + min(0, dr * k), max(0, dc * k):NC + min(0, dc * k)] & \
            mk[max(0, -dr * k):NR + min(0, -dr * k), max(0, -dc * k):NC + min(0, -dc * k)]
        if m.sum() < min_pairs:
            break
        out.append((k, round(float((a * b)[m].sum() / (den * m.sum() / int(mk.sum()))), 4)))
    return out


def lengths(series):
    def first_below(thr):
        for k, r in series:
            if r < thr:
                return k
        return None
    return dict(r_at_1=series[0][1] if series else None,
                k_at_1e=first_below(1 / np.e),
                k_at_0p2=first_below(0.2),
                k_at_0p1=first_below(0.1))


DIRS = {'row(竖直 / N-S)': (1, 0), 'col(水平 / E-W)': (0, 1), 'diag(对角)': (1, 1)}
corr_raw = {nm: correlogram(D_raw, den_raw, mask, dr, dc) for nm, (dr, dc) in DIRS.items()}
corr_res = {nm: correlogram(D_res, den_res, mask, dr, dc) for nm, (dr, dc) in DIRS.items()}
R['correlogram_raw'] = corr_raw
R['correlogram_detrended'] = corr_res
R['correlation_length_cells_100m'] = {
    'raw': {nm: lengths(s) for nm, s in corr_raw.items()},
    'detrended': {nm: lengths(s) for nm, s in corr_res.items()},
}

# ---------------------------------------------------------------- 分层：NDVI 三分位（地表覆盖代理）
q1, q2 = np.quantile(ndvi, [1 / 3, 2 / 3])
GRP = np.full((NR, NC), -1, np.int8)
GRP[rr, cc] = np.where(ndvi <= q1, 0, np.where(ndvi <= q2, 1, 2))
STRATA = {'low_veg(建成主导)': 0, 'mid_veg': 1, 'high_veg(植被主导)': 2}
strata_out = {}
for nm, gi in STRATA.items():
    mk = mask & (GRP == gi)
    Ds = np.where(mk, Zres - np.nanmean(Zres[mk]), 0.0)
    den = float((Ds ** 2).sum())
    entry = {'n': int(mk.sum()), 'resid_std': round(float(np.nanstd(Zres[mk])), 4),
             'share_of_sample': round(float(mk.sum()) / n_valid, 4)}
    for dnm, (dr, dc) in DIRS.items():
        entry[dnm] = lengths(correlogram(Ds, den, mk, dr, dc))
    strata_out[nm] = entry
R['strata_correlation_length_cells'] = strata_out


def max_at(stratum, key):
    vals = [stratum[d][key] for d in DIRS if stratum[d][key]]
    return int(max(vals)) if vals else None


lens_low = max_at(strata_out['low_veg(建成主导)'], 'k_at_0p2')
lens_mid = max_at(strata_out['mid_veg'], 'k_at_0p2')
base_02 = max([x for x in (lens_low, lens_mid) if x] or [10])
R_cells = max(10, int(np.ceil(base_02 / 5.0) * 5))     # 取到 5 格（500 m）的整数倍
R['recommendation'] = dict(
    criterion='r(k) 降至 0.2 的滞后，取建成/中层各向最大值并向上取整到 500 m',
    base_k_at_0p2={'low_veg': lens_low, 'mid_veg': lens_mid},
    R_cells=R_cells, R_m=R_cells * 100,
    note='缓冲只施加于锁定区 C（C 与 A∪B 的最小间距 ≥ R）；A 与 B 同属开发域，不设内部缓冲。',
)

# ---------------------------------------------------------------- 阈值敏感性（判据选择的影响）
def alt_criterion_lengths():
    """同一去趋势残差场在 1/e、0.2、0.1 三个判据下的去相关滞后（取各向最大）。"""
    out = {}
    for nm in ('k_at_1e', 'k_at_0p2', 'k_at_0p1'):
        glob = [lengths(corr_res[d])[nm] for d in DIRS]
        glob = [x for x in glob if x]
        low = [strata_out['low_veg(建成主导)'][d][nm] for d in DIRS]
        low = [x for x in low if x]
        mid = [strata_out['mid_veg'][d][nm] for d in DIRS]
        mid = [x for x in mid if x]
        out[nm] = dict(global_max=max(glob) if glob else None,
                       low_veg_max=max(low) if low else None,
                       mid_veg_max=max(mid) if mid else None)
    return out


R['criterion_sensitivity'] = alt_criterion_lengths()
_cs = R['criterion_sensitivity']
R['criterion_sensitivity']['note'] = (
    '主判据取 0.2：1/e 判据过于宽松（残差场 r(1)≈0.9，1/e 仅 6–8 格，小于建成层形态尺度）；'
    '0.1 判据受残余大尺度趋势影响（全局列向 lag 达 %s 格≈%.1f km），且该长滞后仅出现在'
    '高植被/全局场，与建成层形态尺度不符。故取 0.2 作为"随机部分基本去相关"的折中，'
    '并在验证协议中预先声明更保守判据（0.1→%s 格）下的稳健性对照。'
    % (_cs['k_at_0p1']['global_max'], _cs['k_at_0p1']['global_max'] * 0.1,
       max(10, int(np.ceil((_cs['k_at_0p1']['low_veg_max'] or 10) / 5.0) * 5))))

# ---------------------------------------------------------------- 图：原始 vs 去趋势
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), dpi=150, sharey=True)
for ax, corr, ttl in [(axes[0], corr_raw, '(a) raw LST'), (axes[1], corr_res, '(b) detrended (deg-3)')]:
    for nm, s in corr.items():
        if not s:
            continue
        ax.plot([p[0] * 0.1 for p in s], [p[1] for p in s], marker='.', ms=3, label=nm)
    ax.axhline(1 / np.e, color='grey', ls='--', lw=1)
    ax.axhline(0.2, color='grey', ls=':', lw=1)
    ax.text(0.05, 1 / np.e + 0.02, '1/e', color='grey', fontsize=8)
    ax.text(0.05, 0.22, '0.2', color='grey', fontsize=8)
    ax.set_xlabel('lag (km, 100 m cells)')
    ax.set_title(ttl, fontsize=10)
    ax.grid(alpha=0.3)
axes[0].set_ylabel('autocorrelation r(k)')
axes[0].legend(fontsize=8)
fig.suptitle('S01.1 LST spatial correlogram, main sample (n=%d cells)' % n_valid, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(FIG, 's01_01_correlogram.png'))
plt.close(fig)

with open(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.json'), 'w', encoding='utf-8') as fh:
    json.dump(R, fh, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------- Markdown
Rkm = rec_R_km = R['recommendation']['R_m'] / 1000.0
L = []
L.append('# S01.1 空间自相关诊断\n')
L.append('框架依据：§5.1「60/20/20 … 须在正式研究前依据空间相关范围、地表覆盖、样本与边界条件冻结。必要时设置空间缓冲区。」\n')
L.append('## 1 样本与去趋势\n')
L.append('- 主样本有效格 **%d**（%d×%d 规则网格，100 m）。全局 LST 均值 %.2f ℃、标准差 %.2f ℃。'
         % (n_valid, R['grid']['shape'][0], R['grid']['shape'][1], R['grid']['mean'], R['grid']['std']))
L.append('- 三阶二维多项式趋势面解释方差 **R²=%.3f**（残差标准差 %.2f ℃，趋势项 %d 个）。'
         % (trend_r2, R['detrend']['resid_std'], n_terms))
L.append('- 趋势阶数敏感性：R² 随阶数 1→2→3→4→5 为 %s。取三阶作为折中。\n'
         % ', '.join('%s:%.3f' % (k, v) for k, v in R['detrend_sensitivity'].items()))
L.append('> LST 含大尺度确定性梯度；**不去趋势**会把趋势的长程相关误当随机相关，显著高估缓冲带宽。'
         '故下文以**去趋势残差**为设计依据。\n')
L.append('## 2 全局 Moran’s I（8 邻域，199 次置换）\n')
L.append('| 场 | Moran’s I | 置换均值±标准差 | z | 伪 p 值 |')
L.append('|---|---|---|---|---|')
for key, nm in [('morans_I_raw', '原始 LST'), ('morans_I_detrended', '去趋势残差')]:
    m = R[key]
    L.append('| %s | **%.4f** | %.4f ± %.4f | %.2f | %.4f |' % (nm, m['I'], m['perm_mean'], m['perm_std'], m['z'], m['p_value']))
L.append('')
L.append('## 3 去相关尺度（100 m 格为步长；×100 m 即实际距离）\n')
L.append('| 场 | 方向 | r(1) | 降至 1/e | 降至 0.2 | 降至 0.1 |')
L.append('|---|---|---|---|---|---|')
for key, nm in [('raw', '原始'), ('detrended', '去趋势')]:
    for d in DIRS:
        v = R['correlation_length_cells_100m'][key][d]
        L.append('| %s | %s | %s | %s | %s | %s |' % (nm, d, v['r_at_1'], v['k_at_1e'], v['k_at_0p2'], v['k_at_0p1']))
L.append('')
L.append('## 4 分层（NDVI 三分位作地表覆盖代理）\n')
L.append('去趋势残差，各层各向的"降至 0.2"滞后：\n')
L.append('| 层 | 格数（占样本） | 残差 sd | 行 | 列 | 对角 |')
L.append('|---|---|---|---|---|---|')
for nm, e in strata_out.items():
    L.append('| %s | %d（%.1f%%） | %.2f | %s | %s | %s |'
             % (nm, e['n'], e['share_of_sample'] * 100, e['resid_std'],
                e['row(竖直 / N-S)']['k_at_0p2'], e['col(水平 / E-W)']['k_at_0p2'], e['diag(对角)']['k_at_0p2']))
L.append('')
L.append('植被主导层在长滞后仍呈高相关，主因是该层像元在空间上高度聚集（东部山地/海岸带），'
         '并非真实过程长度；故设计取值不采用该层长滞后值。\n')
L.append('## 5 建议去相关尺度与缓冲\n')
L.append('| 项 | 取值 |')
L.append('|---|---|')
L.append('| 判据 | %s |' % R['recommendation']['criterion'])
L.append('| 建成层 r<0.2 最大滞后 | %s 格 |' % lens_low)
L.append('| 中层 r<0.2 最大滞后 | %s 格 |' % lens_mid)
L.append('| **建议去相关尺度 R** | **%d 格（%.1f km）** |' % (R_cells, Rkm))
L.append('')
L.append('**判定**：去趋势残差仍呈显著正空间自相关（Moran’s I = %.3f，伪 p = %.4f），'
         '建成/中层去相关尺度约 %d 格（%.1f km）。故：\n'
         % (R['morans_I_detrended']['I'], R['morans_I_detrended']['p_value'], R_cells, Rkm))
L.append('1. 空间划分**必须按空间分区**，不得随机抽格；')
L.append('2. 锁定区 C 与其余区（A∪B）保持 **≥ R = %.1f km** 的空间缓冲；' % Rkm)
L.append('3. A 与 B 同属"开发域"（B 参与调参后不再视为独立确认），二者之间不设缓冲；')
L.append('4. 分区几何与样本量由 S01.2 依据 R、样本量与边界形状一并确定。')
L.append('')
L.append('### 5.1 判据敏感性（为什么取 0.2）\n')
L.append('同一去趋势残差场在不同判据下的去相关滞后（格，取各向最大）：\n')
L.append('| 判据 | 全局 | 建成层 | 中层 |')
L.append('|---|---|---|---|')
for nm, lbl in [('k_at_1e', 'r<1/e'), ('k_at_0p2', 'r<0.2'), ('k_at_0p1', 'r<0.1')]:
    e = _cs[nm]
    L.append('| %s | %s | %s | %s |' % (lbl, e['global_max'], e['low_veg_max'], e['mid_veg_max']))
L.append('')
L.append(_cs['note'] + '\n')
L.append('更保守判据（r<0.1，取建成层）对应的替代 R = **%d 格**；该替代分区将作为预注册的'
         '**稳健性对照**在 Stage 04 报告中给出（见 `protocol/validation_protocol.json`），'
         '但**不改变**主分析采用的 R = %d 格。\n'
         % (max(10, int(np.ceil((_cs['k_at_0p1']['low_veg_max'] or 10) / 5.0) * 5)), R_cells))

with open(os.path.join(C.S01_REPORTS, 's01_01_spatial_autocorr.md'), 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(L))

print(json.dumps({'grid': R['grid'], 'detrend': R['detrend'],
                  'morans_raw': R['morans_I_raw'], 'morans_detrended': R['morans_I_detrended'],
                  'detrended_lengths': R['correlation_length_cells_100m']['detrended'],
                  'recommendation': R['recommendation']}, ensure_ascii=False, indent=2))
print('\n写出: reports/s01_01_spatial_autocorr.json / .md, figures/s01_01_correlogram.png')
