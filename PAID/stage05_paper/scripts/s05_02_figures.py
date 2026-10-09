"""
S05.2 图件生成 v2（期刊级；Python / matplotlib）
=====================================================
六张图，各自表达一个结论（见 figures/FIGURE_CONTRACT.md）。统一风格在 figstyle.py。
全部使用既有冻结数据产品，不重算任何结果。产出：figures/ 下每图 PDF + SVG + 600dpi PNG + 600dpi TIFF。

  fig1_protocol_split : A/B/缓冲/C 空间划分（单幅地图；配色低饱和 Nature 级）
  fig2_baselineB      : (a) 锁定区 C 的 ΔRMSE 森林图  (b) A-CV → B → C 排名反转
  fig3_search         : (a) 贪心搜索轨迹  (b) 全部候选：复杂度 vs A-CV
  fig4_validation     : (a) 主终点稳健性"规格曲线"  (b) 参考阶梯（候选 vs 地板/伪候选）
  fig5_external       : (a) 冻结式迁移  (b) 支点检验  (c) 双变量方向
  fig6_baselineD      : (a) 三区 RMSE 交叉  (b) 防火墙阶梯  (c) 种群画像

用法：python3 stage05_paper/scripts/s05_02_figures.py
"""
import os, json
from collections import deque
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.patheffects import withStroke
from PIL import Image, ImageFilter
import figstyle as FS
import fig_geo as GG

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
FIG = os.path.join(S05, 'figures')
REP = os.path.join(S05, 'reports')
FS.apply()


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def fmt(v, d=3):
    return ('%+.' + str(d) + 'f') % v


# ============================================================ Fig 1
_ADM_JSON = os.path.join(REP, 'shenzhen_admin_studyarea.json')


def _soft_classes(M, n_cls, S=6, sigma=0.45):
    """把 1× 的整数类别图 M(0..n_cls-1) 升采样 S 倍后逐类高斯平滑，
    再做 argmax 还原为**平坦配色 + 平滑边界**的类别图（等价于软投票/多数平滑）。

    逐类投票而非对“类别编号”直接平滑，可避免两个空间相邻但编号不相邻的
    类别之间被平滑出并不存在的中间类。sigma 以网格单元为单位。
    """
    R, C = M.shape
    V = np.empty((n_cls, R * S, C * S), np.float32)
    for k in range(n_cls):
        im = Image.fromarray(((M == k) * 255).astype('uint8'), 'L')
        im = im.resize((C * S, R * S), Image.NEAREST)
        im = im.filter(ImageFilter.GaussianBlur(sigma * S))
        V[k] = np.asarray(im, np.float32) / 255.0
    return V, V.argmax(0)


def _mmu(cls, S, small=4, drop=5):
    """最小上图单元（minimum mapping unit）：把**孤立**且小于 `small` 个网格单元
    的 `drop` 类（= 无数据/研究区外）小斑并回其周围多数类，避免图上出现细碎"麻点"。
    只改**显示**，不改数据；平滑后的圆角边界保持不变。返回新的全分辨率类别场。
    """
    R, C = cls.shape[0] // S, cls.shape[1] // S
    g = cls[S // 2::S, S // 2::S][:R, :C].copy()
    lab = np.zeros((R, C), np.int32)
    smalls = []
    for y in range(R):
        for x in range(C):
            if g[y, x] == drop and lab[y, x] == 0:
                cid = len(smalls) + 1
                q, pts = deque([(y, x)]), []
                lab[y, x] = cid
                while q:
                    cy, cx = q.popleft()
                    pts.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < R and 0 <= nx < C and g[ny, nx] == drop and lab[ny, nx] == 0:
                            lab[ny, nx] = cid
                            q.append((ny, nx))
                if len(pts) < small:
                    smalls.append(pts)
    if not smalls:
        return cls
    repl = g.copy()
    for pts in smalls:
        nb = []
        for (y, x) in pts:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < R and 0 <= nx < C and g[ny, nx] != drop:
                        nb.append(g[ny, nx])
        if not nb:
            continue
        vals, cnt = np.unique(nb, return_counts=True)
        for (y, x) in pts:
            repl[y, x] = vals[cnt.argmax()]
    out = cls.copy()
    for y in range(R):
        for x in range(C):
            if repl[y, x] != g[y, x]:
                blk = out[y * S:(y + 1) * S, x * S:(x + 1) * S]
                blk[blk == drop] = repl[y, x]
    return out


def _contour_segs(Z, xs, ys, level=0.5, minlen=4):
    """临时轴上取等值线折线（不落到任何输出图）。allsegs 已是 (N,2)，勿再 stack。"""
    f = plt.figure()
    a = f.add_subplot(111)
    cs = a.contour(xs, ys, Z, levels=[level])
    segs = [np.asarray(s) for s in cs.allsegs[0] if len(s) >= minlen]
    plt.close(f)
    return segs


def _mask_split(seg, keep, minlen=6):
    """按逐点布尔掩膜把折线切成若干子折线（keep=False 处断开）。"""
    out, cur = [], []
    for p, kp in zip(seg, keep):
        if kp:
            cur.append(p)
        else:
            if len(cur) >= minlen:
                out.append(np.asarray(cur))
            cur = []
    if len(cur) >= minlen:
        out.append(np.asarray(cur))
    return out


def _draw_grid(ax, cmin, cmax, rmin, rmax, foot, xs2, ys2, step,
               color='white', lw=0.4, z=2.5, keep_thr=0.55):
    """在研究区内部叠加网格线（每隔 `step` 个 100 m 格一条）。

    逐点用软投票场 foot 判定是否落在研究区内（只画内部段，不越到区外/无数据格）。
    用 LineCollection 一次性绘制，避免上千次 plot。"""
    from matplotlib.collections import LineCollection
    dxs = float(xs2[1] - xs2[0]); dys = float(ys2[1] - ys2[0])
    nr, nc = foot.shape
    def ixi(X):
        return np.clip(np.round((X - xs2[0]) / dxs).astype(int), 0, nc - 1)
    def iyi(Y):
        return np.clip(np.round((Y - ys2[0]) / dys).astype(int), 0, nr - 1)
    segs = []
    rr = np.arange(float(rmin), float(rmax) + 1e-9, 0.5)
    for c in range(int(cmin), int(cmax) + 1, step):
        vals = foot[iyi(rr), ixi(np.full(rr.shape, float(c)))]
        seg = np.column_stack([np.full(rr.shape, float(c)), rr])
        segs.extend(_mask_split(seg, vals > keep_thr, minlen=2))
    cc = np.arange(float(cmin), float(cmax) + 1e-9, 0.5)
    for r in range(int(rmin), int(rmax) + 1, step):
        vals = foot[iyi(np.full(cc.shape, float(r))), ixi(cc)]
        seg = np.column_stack([cc, np.full(cc.shape, float(r))])
        segs.extend(_mask_split(seg, vals > keep_thr, minlen=2))
    ax.add_collection(LineCollection(segs, colors=color, linewidths=lw,
                                     zorder=z, capstyle='butt'))


def fig1_protocol_split():
    df = pd.read_csv(os.path.join(PROJ, 'stage01_protocol', 'split', 'analysis_split.csv'))
    rmin, rmax = int(df['row'].min()), int(df['row'].max())
    cmin, cmax = int(df['col'].min()), int(df['col'].max())
    R, C = rmax - rmin + 1, cmax - cmin + 1

    # A/B/buffer/C 空间划分：每个 100 m 格一个角色；无记录 = 0（研究区外，透明）
    K = ['discovery', 'dev_validation', 'buffer', 'locked', 'outside']
    code = {k: i + 1 for i, k in enumerate(K)}
    M = np.zeros((R, C), np.uint8)
    for r, c, ro in zip(df['row'], df['col'], df['role']):
        M[r - rmin, c - cmin] = code[ro]
    n_out = int((df['role'] == 'outside').sum())
    counts = df['role'].value_counts()

    # 填充方式：默认逐格马赛克（每个 100 m 格一个实心方块 → 网格可见）。
    # 环境变量可切换（供预览/备选）：FIG1_MOSAIC=0 用平滑软投票填充；
    # FIG1_AGG=块大小(格)；FIG1_GRID=叠加网格线步长(格)；FIG1_TAG=输出后缀。
    MOSAIC = int(os.environ.get('FIG1_MOSAIC', '1'))
    AGG = max(1, int(os.environ.get('FIG1_AGG', '1')))
    GSTEP = int(os.environ.get('FIG1_GRID', '5'))     # round-17 默认每 5 格 = 500 m 一条参考网格
    TAG = os.environ.get('FIG1_TAG', '')
    ELW = float(os.environ.get('FIG1_ELW', '0.0'))    # 逐格白缝线宽；0 表示不画白缝（降密度）
    EA = float(os.environ.get('FIG1_EA', '1.0'))     # 白缝不透明度

    SIG = 0.80                                  # 平滑尺度（网格单元）——决定交接处圆顺度
    S = 6
    rgba = None
    if not MOSAIC:                              # 仅平滑填充模式才需要软投票 RGBA
        V, cls = _soft_classes(M, 6, S=S, sigma=SIG)
        cls = _mmu(cls, S, small=4, drop=code['outside'])   # 并掉孤立的细碎无数据斑
        rgba = np.zeros((R * S, C * S, 4), np.float32)
        for k in range(1, 6):
            sel = (cls == k)
            rgba[sel, :3] = to_rgb(FS.ROLE[K[k - 1]])
            rgba[sel, 3] = 1.0

    S2 = 3
    V2, _ = _soft_classes(M, 6, S=S2, sigma=SIG)
    xs2 = cmin + (np.arange(C * S2) + 0.5) / S2
    ys2 = rmin + (np.arange(R * S2) + 0.5) / S2
    foot = V2[1:5].sum(0)                       # 研究区（A/B/缓冲/C）的软指示场
    def _perim(seg):                            # 折线在网格坐标下的总长
        d = np.diff(seg, axis=0)
        return float(np.hypot(d[:, 0], d[:, 1]).sum())
    # 只保留研究区**外轮廓**（长环），丢弃内部零散无数据格派生的小环
    foot_segs = [s for s in _contour_segs(foot, xs2, ys2, 0.5) if _perim(s) > 150]

    # 画布加高：上方留出一条空白带，让图例与定位小图都落在坐标区**之外**，
    # 谁也不压住地图。坐标区高宽比按数据范围 (cols 373 × rows 244) 取足。
    FH = 4.30
    fig = plt.figure(figsize=(FS.W_MID, FH))
    ax = fig.add_axes([0.105, 0.115, 0.878, 0.631])
    if MOSAIC:
        Kc = [FS.ROLE[K[k - 1]] for k in range(1, 6)]
        cmap = ListedColormap(Kc)
        Ma = _mmu(M, 1, small=4, drop=code['outside'])   # 逐格显示，仍并掉孤立无数据小斑
        if AGG > 1:                              # AGG×AGG 分块多数聚合（可选）
            Rp, Cp = -(-R // AGG) * AGG, -(-C // AGG) * AGG
            Mp = np.zeros((Rp, Cp), np.uint8)
            Mp[:R, :C] = M
            blk = Mp.reshape(Rp // AGG, AGG, Cp // AGG, AGG)
            blk = blk.transpose(0, 2, 1, 3).reshape(-1, AGG * AGG)
            out = np.zeros(len(blk), np.uint8)
            for i, row in enumerate(blk):
                v, c = np.unique(row[row > 0], return_counts=True)
                out[i] = v[c.argmax()] if len(v) else 0
            Ma = out.reshape(Rp // AGG, Cp // AGG)
        Cm = np.ma.masked_equal(Ma, 0)
        xe = cmin + np.arange(Ma.shape[1] + 1) * AGG
        ye = rmin + np.arange(Ma.shape[0] + 1) * AGG
        # round-17：逐格白缝减淡以降低"太密"的观感（默认 0.04 pt 实白；FIG1_ELW<=0
        # 则完全去缝）。每格仍是一个实心方块（图注"each 100 m cell is drawn as one
        # square"仍真）。
        if ELW > 0:
            ax.pcolormesh(xe, ye, Cm, cmap=cmap, vmin=1, vmax=5, shading='flat',
                          edgecolors=(1.0, 1.0, 1.0, EA), linewidth=ELW, zorder=1)
        else:
            ax.pcolormesh(xe, ye, Cm, cmap=cmap, vmin=1, vmax=5, shading='flat',
                          edgecolors='none', zorder=1)
    else:
        ax.imshow(rgba, extent=(cmin, cmax + 1, rmax + 1, rmin), origin='upper',
                  interpolation='nearest', zorder=1, aspect='equal')
    if GSTEP > 0:                                # 叠加网格线（每 GSTEP 格一条）
        GLW = float(os.environ.get('FIG1_GLW', '0.32'))
        _draw_grid(ax, cmin, cmax, rmin, rmax, foot, xs2, ys2, GSTEP,
                   color=(1.0, 1.0, 1.0, 0.75), lw=GLW)

    # 区界（图内**唯一**的行政边界层）：来自作者权威区归属栅格（studyarea.shp
    # 社区面），用与配色同一套软投票平滑后取每区 50% 等值线；同时保留**研究区
    # 内部**的区-区界与沿外轮廓走的那一段（tot ≈ 0.5）。这一段本身就沿外轮廓
    # 闭合，所以下面不再另画一层外轮廓——全图只有这一层边界线（round-17 修订：
    # 之前同时画了区界层与外轮廓层，外轮廓段与区界外沿段并行 → 用户看到"两层"）。
    adm = load(_ADM_JSON)
    ND = len(adm['district_names'])
    D = np.zeros((R, C), np.uint8)
    for rs, segs in adm['district_rle'].items():
        rr = int(rs)
        for di, st, ln in segs:
            D[rr, st:st + ln] = di
    VD, _ = _soft_classes(D, ND + 1, S=S2, sigma=SIG)
    tot = VD[1:].sum(0)                         # 只累计"有区归属"的类：区内≈1，界外≈0
    major = {i + 1 for i, n in enumerate(adm['district_names'])
             if any(l['zh'] == n['zh'] for l in adm['district_labels'])}
    dsegs = []
    for k in range(1, ND + 1):
        if k not in major:                      # 只画 3 个成片城区，跳过滤纸状碎片
            continue
        for seg in _contour_segs(VD[k], xs2, ys2, 0.5):
            ix = np.clip(np.round((seg[:, 0] - cmin) * S2 - 0.5).astype(int),
                         0, C * S2 - 1)
            iy = np.clip(np.round((seg[:, 1] - rmin) * S2 - 0.5).astype(int),
                         0, R * S2 - 1)
            for sub in _mask_split(seg, tot[iy, ix] > 0.35, minlen=20):
                if _perim(sub) > 10:            # 去掉只有几格的小圈/毛刺
                    dsegs.append(sub)
    for sub in dsegs:                           # 白色包边 + 深色芯线 = 可压在任何底色上
        ax.plot(sub[:, 0], sub[:, 1], color='white', lw=1.5, zorder=5,
                solid_capstyle='round', solid_joinstyle='round')
        ax.plot(sub[:, 0], sub[:, 1], color='#242424', lw=1.0, zorder=6,
                solid_capstyle='round', solid_joinstyle='round')

    # 分区之间的白色细缝（矢量等值线，与配色图同一条 50% 边界）；
    # 只保留研究区**内部**的段（foot≈1），避免沿外轮廓多描一圈白边。
    for k in range(1, 5) if not MOSAIC else []:
        for seg in _contour_segs(V2[k], xs2, ys2, 0.5):
            ix = np.clip(np.round((seg[:, 0] - cmin) * S2 - 0.5).astype(int),
                         0, C * S2 - 1)
            iy = np.clip(np.round((seg[:, 1] - rmin) * S2 - 0.5).astype(int),
                         0, R * S2 - 1)
            for sub in _mask_split(seg, foot[iy, ix] > 0.85):
                ax.plot(sub[:, 0], sub[:, 1], color='white', lw=1.1, zorder=4)

    # (round-17：外层不再单画一条 study-area 外轮廓线——区界层已沿外轮廓闭合，
    #  两层并行是用户投诉"两层行政边界线"的根源。全图仅此一层边界。)

    # 区名（深字 + 白描边；英文，避免图内 CJK 字体依赖）。底色改为淡雅的
    # 紫/粉阶后，白字不再可读，改深色斜体（呼应参考底图的深色斜体地名）。
    for d in adm['district_labels']:
        ax.text(d['col'], d['row'], d['en'], ha='center',
                va='center', fontsize=6.2, style='italic', color='#3B2E44', zorder=9,
                path_effects=[withStroke(linewidth=1.7, foreground='#FFFFFF')])

    ax.set_xlim(cmin - 6, cmax + 6)
    ax.set_ylim(rmax + 6, rmin - 6)
    ax.set_xlabel('grid column  (100 m cells)')
    ax.set_ylabel('grid row  (100 m cells)')
    for s in ('top', 'right'):
        ax.spines[s].set_visible(True)
        ax.spines[s].set_color('#BBBBBB')
        ax.spines[s].set_linewidth(0.5)

    # 1 km 比例尺
    x0, y0 = cmax - 82, rmax - 58
    ax.plot([x0, x0 + 10], [y0, y0], color=FS.BLACK, lw=1.2, zorder=8)
    for xx in (x0, x0 + 10):
        ax.plot([xx, xx], [y0 - 3, y0 + 3], color=FS.BLACK, lw=1.2, zorder=8)
    ax.text(x0 + 5, y0 + 9, '1 km', ha='center', va='top', fontsize=5.6, zorder=8)
    # 指北针
    ax.annotate('', xy=(cmax - 4, rmin + 8), xytext=(cmax - 4, rmin + 28),
                arrowprops=dict(arrowstyle='-|>', color=FS.BLACK, lw=0.7), zorder=8)
    ax.text(cmax - 4, rmin + 4, 'N', ha='center', va='top', fontsize=6, zorder=8)

    # ---- 图例（图上方，两列） -------------------------------------------
    lorder = ['discovery', 'dev_validation', 'locked', 'buffer']
    handles = [Patch(facecolor=FS.ROLE[r], edgecolor='none',
                     label='%s  (%s)' % (FS.ROLE_LBL[r], format(int(counts[r]), ',')))
               for r in lorder]
    handles.append(Line2D([0], [0], color='#2E2E2E', lw=0.75,
                          label='district boundary'))
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.100, 1.008),
               ncol=3, columnspacing=1.15, labelspacing=0.34, handletextpad=0.5,
               handlelength=1.2, handleheight=1.1)
    # out-of-scope 色块 + 注记
    ax.add_patch(Rectangle((0.640, 0.030), 0.016, 0.030, transform=ax.transAxes,
                           facecolor=FS.ROLE['outside'], edgecolor='#C2BCB2', lw=0.4,
                           clip_on=False, zorder=10))
    ax.text(0.664, 0.045, 'out of scope / no data (%s cells)' % format(n_out, ','),
            transform=ax.transAxes, ha='left', va='center', fontsize=5.2,
            color='#777777', zorder=10)
    ax.text(0.968, 0.002, 'C is unsealed once, post-hoc', transform=ax.transAxes,
            ha='right', va='bottom', fontsize=5.2, style='italic', color='#777777',
            zorder=10)

    # ---- 定位小图（深圳全市 + 研究区高亮） -------------------------------
    allr = [np.asarray(r) for d in adm['city_districts'] for r in d['rings']]
    xlo = min(r[:, 0].min() for r in allr)
    xhi = max(r[:, 0].max() for r in allr)
    ylo = min(r[:, 1].min() for r in allr)
    yhi = max(r[:, 1].max() for r in allr)
    pad = 50                                    # 图框内留白：深圳轮廓四周都有余量，不被切
    inw = 0.235
    inh = inw * (FS.W_MID / FH) * (yhi - ylo + 2 * pad) / (xhi - xlo + 2 * pad)
    axi = fig.add_axes([0.075, 0.758, inw, inh])
    axi.set_facecolor('#F6F7F8')
    for d in adm['city_districts']:
        for ring in d['rings']:
            r = np.asarray(ring)
            axi.plot(r[:, 0], r[:, 1], color='#A8B1B9', lw=0.4, zorder=1)
    axi.contourf(xs2, ys2, foot, levels=[0.5, 2.0],
                 colors=[FS.ROLE['discovery']], zorder=3)
    axi.contour(xs2, ys2, foot, levels=[0.5], colors=['#1F3A52'], linewidths=0.4,
                zorder=4)
    axi.set_xlim(xlo - pad, xhi + pad)
    axi.set_ylim(yhi + pad, ylo - pad)
    axi.set_aspect('equal', adjustable='box')
    axi.set_xticks([])
    axi.set_yticks([])
    for s in axi.spines.values():
        s.set_visible(True)
        s.set_color('#B9BFC5')
        s.set_linewidth(0.5)
    axi.text(0.035, 0.945, 'Shenzhen', transform=axi.transAxes, ha='left',
             va='top', fontsize=5.2, color='#55606A', zorder=4,
             bbox=dict(boxstyle='round,pad=0.12', fc='white', ec='none', alpha=0.75))

    FS.save(fig, os.path.join(FIG, 'fig1_protocol_split' + TAG))


# ============================================================ Fig 2
def fig2_baselineB():
    d = load(os.path.join(REP, 'baselineB.json'))
    C, B, cv = d['regions']['C'], d['regions']['B'], d['A_cv']
    fig = plt.figure(figsize=(FS.W_DOUBLE, 2.55))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.28, 1.0], wspace=0.34)

    # ---- (a) forest: locked-region ΔRMSE
    ax = fig.add_subplot(gs[0, 0])
    keys = ['rf', 'gbm', 'rf_aug', 'no_dem', 'h10', 'constant']
    centers = [C[k]['delta_vs_baselineA'] for k in keys]
    los = [C[k]['ci95'][0] for k in keys]
    his = [C[k]['ci95'][1] for k in keys]
    cols = [FS.MODEL[k] for k in keys]
    ys = FS.forest(ax, [FS.MODEL_LBL[k] for k in keys], centers, los, his, cols)
    for y, k in zip(ys, keys):
        ax.text(his[keys.index(k)] + 0.02, y, fmt(C[k]['delta_vs_baselineA'], 2),
                va='center', fontsize=5.8, color='#333333')
    # emphasise the candidate by styling its own tick label (no extra text box)
    for lbl in ax.get_yticklabels():
        if lbl.get_text() == FS.MODEL_LBL['h10']:
            lbl.set_color(FS.BLUE)
            lbl.set_fontweight('bold')
    ax.set_xlim(-0.06, 1.05)
    ax.set_xlabel('ΔRMSE vs Baseline A on locked region C   (°C, higher = better)')
    ax.text(0.02, 0.03, '95% spatial-block bootstrap;  p = 0.005 (199 permutations)',
            transform=ax.transAxes, fontsize=5.5, color='#777777')
    FS.panel(ax, 'a', x=-0.34, y=1.02)

    # ---- (b) selection vs validation inversion
    ax2 = fig.add_subplot(gs[0, 1])
    for k in ['baselineA', 'h10', 'rf', 'gbm']:
        yv = [cv.get(k), B[k]['rmse'], C[k]['rmse']]
        ax2.plot([0, 1, 2], yv, '-o', color=FS.MODEL[k], lw=1.1, ms=3.2,
                 label=FS.MODEL_LBL[k])
    ax2.set_xticks([0, 1, 2])
    ax2.set_xticklabels(['A-CV\nselection', 'B\ndev', 'C\nlocked (post-hoc)'])
    ax2.set_ylabel('RMSE  (°C, lower = better)')
    ax2.set_xlim(-0.15, 2.35)
    ax2.legend(loc='upper right', bbox_to_anchor=(1.02, 1.03))
    ax2.annotate('RF / GBM reach 2.09;\nthe candidate stalls at 2.46',
                 xy=(2, C['rf']['rmse']), xycoords='data',
                 xytext=(0.03, 0.09), textcoords='axes fraction',
                 ha='left', va='bottom', fontsize=5.6, color='#333333',
                 arrowprops=dict(arrowstyle='-', lw=0.5, color='#999999'))
    FS.panel(ax2, 'b', x=-0.16, y=1.02)

    FS.save(fig, os.path.join(FIG, 'fig2_baselineB'))


# ============================================================ Fig 3
def fig3_search():
    reg = load(os.path.join(PROJ, 'stage03_discovery', 'registry', 'candidate_registry.json'))
    traj = load(os.path.join(PROJ, 'stage03_discovery', 'registry', 'experiment_trajectory.json'))
    baseA = reg['baselineA_dev_cv_rmse']
    fig = plt.figure(figsize=(FS.W_DOUBLE, 2.55))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.12], wspace=0.24)

    # ---- (a) greedy trajectory
    ax = fig.add_subplot(gs[0, 0])
    tr = traj['greedy_trace']
    ns = [t['n_terms'] for t in tr]
    cvs = [t['cv_rmse'] for t in tr]
    ax.axhline(baseA, color=FS.BLACK, ls=(0, (4, 3)), lw=0.8, zorder=1)
    ax.text(1.0, baseA + 0.02, 'Baseline A = %.3f' % baseA, fontsize=5.7, color='#333333')
    ax.plot(ns, cvs, '-o', color=FS.BLUE, ms=3.4, zorder=3)
    term = ['exp(NDVI)', 'exp(DEM)', 'SVF', 'Road density', 'NDVI×DEM']
    for i, (x, y, t) in enumerate(zip(ns, cvs, term)):
        up = (i % 2 == 0)
        dy = 12 if up else -16
        ax.annotate('+ ' + t, (x, y), textcoords='offset points', xytext=(0, dy),
                    ha='center', fontsize=5.5, color='#333333',
                    arrowprops=dict(arrowstyle='-', lw=0.4, color='#AAAAAA'))
    ax.set_xlim(0.55, 5.45)
    ax.set_ylim(min(cvs) - 0.09, max(cvs) + 0.06)
    ax.set_xlabel('terms added (greedy forward selection)')
    ax.set_ylabel('A-CV RMSE  (°C, selection metric)')
    FS.panel(ax, 'a', x=-0.20, y=1.02)

    # ---- (b) candidate set: complexity vs A-CV
    ax2 = fig.add_subplot(gs[0, 1])
    st = {'passed_dev_gain': (FS.BLUE, 'o', 'passed, dev gain'),
          'passed_dev_nogain': (FS.LGREY, 'o', 'passed, no gain'),
          'rejected_physics': (FS.ORANGE, 'X', 'rejected (physics)')}
    ytop = 5.25
    seen = set()
    for c in reg['candidates']:
        cx = c['expression']['complexity']
        cy = c['dev_evidence']['cv_rmse']
        col, mk, lab = st[c['status']]
        if cy > ytop:
            ax2.plot(cx, ytop - 0.07, marker='^', ms=5, color=col, zorder=4)
            ax2.text(cx + 0.35, ytop - 0.07, 'A-CV %.1f (off scale)' % cy, fontsize=5.4,
                     va='center', color=col)
        else:
            ax2.scatter(cx, cy, s=26, marker=mk, color=col, zorder=3,
                        linewidths=0.5 if mk == 'X' else 0)
        if c['status'] not in seen:
            ax2.scatter([], [], s=26, marker=mk, color=col,
                        linewidths=0.5 if mk == 'X' else 0, label=lab)
            seen.add(c['status'])
    ax2.axvline(15, color=FS.GREY, ls=(0, (4, 3)), lw=0.8, zorder=1)
    ax2.text(15.2, 3.70, 'complexity cap = 15', fontsize=5.5, color='#777777',
             rotation=90, ha='center', va='center')
    # frozen candidates: black ring + key number, identified in the empty upper-right
    frozen = sorted([c for c in reg['candidates'] if c['id'] in reg['frozen_ids']],
                    key=lambda c: c['dev_evidence']['cv_rmse'])
    offs = [(5, 4), (5, -9), (5, 4), (5, 4)]
    for i, (c, off) in enumerate(zip(frozen, offs), 1):
        cx = c['expression']['complexity']
        cy = min(c['dev_evidence']['cv_rmse'], ytop - 0.07)
        ax2.scatter(cx, cy, s=64, facecolors='none', edgecolors=FS.BLACK,
                    linewidths=0.6, zorder=5)
        ax2.annotate(str(i), (cx, cy), textcoords='offset points', xytext=off,
                     fontsize=5.4, fontweight='bold', color=FS.BLACK, zorder=6)
    key = '\n'.join('%d  %s   %.3f  (cx %d)'
                    % (i, c['id'].replace('S03-', ''), c['dev_evidence']['cv_rmse'],
                       c['expression']['complexity'])
                    for i, c in enumerate(frozen, 1))
    ax2.text(0.42, 0.965, 'frozen candidates\n' + key, transform=ax2.transAxes,
             va='top', ha='left', fontsize=5.2, color=FS.BLACK, linespacing=1.5)
    ax2.set_xlim(4.3, 16.6)
    ax2.set_ylim(2.72, ytop)
    ax2.set_xlabel('expression complexity  (AST nodes + terms)')
    ax2.set_ylabel('A-CV RMSE  (°C, lower = better)')
    ax2.legend(loc='upper left', bbox_to_anchor=(0.42, 0.66), frameon=False,
               markerscale=1.0)
    FS.panel(ax2, 'b', x=-0.18, y=1.02)

    FS.save(fig, os.path.join(FIG, 'fig3_search'))


# ============================================================ Fig 4
def fig4_validation():
    d = load(os.path.join(PROJ, 'stage04_validation', 'reports', 's04_validation_results.json'))
    h = d['candidates']['S03-H10-GREEDY']
    p, r25, stt, me = (h['primary_endpoint'], h['criterion_sensitivity_R25'],
                       h['strata_ndvi'], h['measurement_error'])
    ps = h['pseudo_row_shuffled']
    fig = plt.figure(figsize=(FS.W_DOUBLE, 2.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.32, 1.0], wspace=0.42)

    # ---- (a) specification curve
    ax = fig.add_subplot(gs[0, 0])
    rows = [
        ('Primary  R = 15', p['delta_rmse'], p['ci95_delta'][0], p['ci95_delta'][1], FS.OK),
        ('Alt. criterion  R = 25', r25['delta_rmse'], None, None, FS.BAD),
        ('Low-vegetation stratum', stt['low_veg']['delta_rmse'], stt['low_veg']['ci95_delta'][0], stt['low_veg']['ci95_delta'][1], FS.OK),
        ('Mid-vegetation stratum', stt['mid_veg']['delta_rmse'], stt['mid_veg']['ci95_delta'][0], stt['mid_veg']['ci95_delta'][1], FS.OK),
        ('High-vegetation stratum', stt['high_veg']['delta_rmse'], stt['high_veg']['ci95_delta'][0], stt['high_veg']['ci95_delta'][1], FS.OK),
        ('LST noise  ±0.5 K', me['sd_0.5K']['delta_mean'], me['sd_0.5K']['delta_min'], me['sd_0.5K']['delta_max'], FS.OK),
        ('LST noise  ±1.0 K', me['sd_1.0K']['delta_mean'], me['sd_1.0K']['delta_min'], me['sd_1.0K']['delta_max'], FS.OK),
    ]
    labels = [r[0] for r in rows]
    centers = [r[1] for r in rows]
    los = [r[2] for r in rows]
    his = [r[3] for r in rows]
    cols = [r[4] for r in rows]
    ys = FS.forest(ax, labels, centers, los, his, cols)
    for y, r in zip(ys, rows):
        ann = fmt(r[1], 3)
        if r[0].startswith('Primary'):
            ann += '   p = 0.005'
        elif 'R = 25' in r[0]:
            ann += '   p = 0.085 (n.s.)'
        ax.text((r[3] if r[3] else r[1]) + 0.015, y, ann, va='center', fontsize=5.6,
                color='#333333')
    ax.set_xlim(0, 0.80)
    ax.set_xlabel('ΔRMSE vs Baseline A on locked region C   (°C)')
    ax.text(0.5, -0.30, 'sign is positive in every specification except the R = 25 criterion',
            transform=ax.transAxes, ha='center', fontsize=5.5, color='#777777')
    FS.panel(ax, 'a', x=-0.33, y=1.02)

    # ---- (b) reference ladder
    ax2 = fig.add_subplot(gs[0, 1])
    vals = [('Constant floor', 0.2388, FS.GREY),
            ('Row-shuffled pseudo', ps['delta_rmse_pseudo_vs_baseline'], FS.LGREY),
            ('Candidate H10', p['delta_rmse'], FS.BLUE)]
    xs = np.arange(len(vals))
    ax2.bar(xs, [v[1] for v in vals], width=0.62,
            color=[v[2] for v in vals], zorder=2)
    for x, v in zip(xs, vals):
        ax2.text(x, v[1] + 0.008, '%.3f' % v[1], ha='center', fontsize=5.8, color='#333333')
    ax2.axhline(0, color=FS.BLACK, lw=0.7)
    ax2.set_xticks(xs)
    ax2.set_xticklabels(['constant\nfloor', 'row-shuffled\npseudo', 'candidate\nH10'])
    ax2.set_ylabel('ΔRMSE vs Baseline A on C  (°C)')
    ax2.set_ylim(0, 0.47)
    ax2.text(0.5, 0.93, 'Baseline A itself carries no spatial signal here',
             transform=ax2.transAxes, ha='center', fontsize=5.5, color='#777777')
    FS.panel(ax2, 'b', x=-0.24, y=1.02)

    FS.save(fig, os.path.join(FIG, 'fig4_validation'))


# ============================================================ Fig 5
def fig5_external():
    e = load(os.path.join(REP, 'external_replication.json'))
    forms = e['forms']
    fig = plt.figure(figsize=(FS.W_DOUBLE, 2.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.30, 1.05, 1.0], wspace=0.52)

    # ---- (a) frozen-form transfer
    ax = fig.add_subplot(gs[0, 0])
    tr = [('Baseline A*\n+ exp(NDVI)', 'BaselineA* + exp(NDVI)'),
          ('Baseline A*\n+ H10 core', 'BaselineA* + H10 nonlin core'),
          ('H10 proj\n+ built-3', 'H10-proj+built3'),
          ('H11 projection', 'H11-proj exp(NDVI)+DEM+NDVI^2+NDVI*DEM'),
          ('linear NDVI+DEM\n+ NDVI×DEM', 'lin NDVI+DEM+NDVI*DEM'),
          ('H10 projection', 'H10-proj exp(NDVI)+exp(DEM)+NDVI*DEM'),
          ('linear NDVI+DEM', 'lin NDVI+DEM (2 var)'),
          ('H10P exp(NDVI)\n+ exp(DEM)', 'H10P exp(NDVI)+exp(DEM)')]
    labels = [t[0] for t in tr]
    centers = [forms[t[1]]['delta_vs_baselineA'] for t in tr]
    cols = [FS.OK if c > 0 else FS.BAD for c in centers]
    ys = FS.forest(ax, labels, centers, [None] * len(tr), [None] * len(tr), cols)
    for y, c in zip(ys, centers):
        ax.text(c + 0.02, y, fmt(c, 3), va='center', fontsize=5.6, color='#333333')
    ax.set_xlim(-0.75, 0.18)
    ax.set_xlabel('Δ CV RMSE vs matched Baseline A*   (°C, higher = better)')
    ax.text(0.02, 0.98, 'only the exp(NDVI) term is positive\nin the external test',
            transform=ax.transAxes, va='top', fontsize=5.5, color='#777777')
    FS.panel(ax, 'a', x=-0.58, y=1.02)

    # ---- (b) pivot test
    ax2 = fig.add_subplot(gs[0, 1])
    pv = [('NDVI\n(linear)', 'pivot NDVI (linear)', FS.SKY),
          ('exp(NDVI)', 'pivot exp(NDVI)', FS.BLUE),
          ('NDVI²\n(quad.)', 'pivot NDVI+NDVI^2', FS.GREEN),
          ('exp(NDVI)\n+exp(DEM)', 'H10P exp(NDVI)+exp(DEM)', FS.ORANGE)]
    xs = np.arange(len(pv))
    ax2.bar(xs, [forms[k]['cv_rmse'] for _, k, _ in pv], width=0.62,
            color=[c for _, _, c in pv], zorder=2)
    for x, (_, k, _) in zip(xs, pv):
        ax2.text(x, forms[k]['cv_rmse'] + 0.02, '%.2f' % forms[k]['cv_rmse'],
                 ha='center', fontsize=5.6, color='#333333')
    ax2.axhline(e['baselineA_star_cv_rmse'], color=FS.BLACK, ls=(0, (4, 3)), lw=0.8)
    ax2.text(0.03, 0.97, 'matched Baseline A* (dashed) = %.2f'
             % e['baselineA_star_cv_rmse'],
             transform=ax2.transAxes, va='top', fontsize=5.4, color='#333333')
    ax2.set_xticks(xs)
    ax2.set_xticklabels([l for l, _, _ in pv])
    ax2.tick_params(axis='x', labelsize=5.6)
    ax2.set_ylabel('CV RMSE on Changchun  (°C)')
    ax2.set_ylim(0, 2.05)
    FS.panel(ax2, 'b', x=-0.26, y=1.02)

    # ---- (c) direction agreement
    ax3 = fig.add_subplot(gs[0, 2])
    bc = e['bivariate_corr']
    order = [('X_BD', FS.OK, 'building\ndensity'),
             ('X_VolDens', FS.OK, 'building volume\ndensity'),
             ('X_BH', FS.OK, 'building\nheight'),
             ('NDVI', FS.OK, 'vegetation\n(NDVI)'),
             ('DEM', FS.BAD, 'elevation\n(DEM)')]
    keymap = {'X_BD': 'X_BD', 'X_VolDens': 'X_VolDens', 'X_BH': 'X_BH',
              'NDVI': 'NDVI_mean', 'DEM': 'DEM_mean'}
    vals = [bc[keymap[k]]['pearson'] for k, _, _ in order]
    ys = np.arange(len(order))[::-1]
    ax3.barh(ys, vals, height=0.6, color=[c for _, c, _ in order], zorder=2)
    for y, v in zip(ys, vals):
        ax3.text(v + (0.03 if v > 0 else -0.03), y, '%.2f' % v,
                 va='center', ha='left' if v > 0 else 'right', fontsize=5.6, color='#333333')
    ax3.axvline(0, color=FS.BLACK, lw=0.7)
    ax3.set_yticks(ys)
    ax3.set_yticklabels([l for _, _, l in order])
    ax3.tick_params(axis='y', labelsize=6.0)
    ax3.set_xlim(-0.55, 1.05)
    ax3.set_xlabel('Pearson r with LST\n(Changchun 2021)')
    ax3.text(0.06, 0, 'no relationship\n(not reproduced)', va='center', ha='left',
             fontsize=5.3, color=FS.BAD)
    FS.panel(ax3, 'c', x=-0.36, y=1.02)

    FS.save(fig, os.path.join(FIG, 'fig5_external'))


# ============================================================ Fig 6
def fig6_baselineD():
    b = load(os.path.join(REP, 'baselineD.json'))
    ref, w = b['reference'], b['arm1_winner']
    a2, a2b, pop = b['arm2_firewall_off'], b['arm2b_train_on_all'], b['population_summary']
    fig = plt.figure(figsize=(FS.W_DOUBLE, 2.5))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.0, 0.9], wspace=0.5)

    # ---- (a) region crossing
    ax = fig.add_subplot(gs[0, 0])
    series = [('Baseline A', [ref['baselineA']['cv_rmse'], ref['baselineA']['rmse_B'], ref['baselineA']['rmse_C']], FS.BLACK, '-o'),
              ('Constrained H10', [ref['h10_constrained']['cv_rmse'], ref['h10_constrained']['rmse_B'], ref['h10_constrained']['rmse_C']], FS.BLUE, '-o'),
              ('Unconstrained agent', [w['cv_rmse'], w['rmse_B'], w['rmse_C']], FS.ORANGE, '-s')]
    for lab, yv, col, mk in series:
        ax.plot([0, 1, 2], yv, mk, color=col, lw=1.1, ms=3.3, label=lab)
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(['A-CV\nselection', 'B\ndev', 'C\nlocked'])
    ax.set_ylabel('RMSE  (°C, lower = better)')
    ax.set_xlim(-0.15, 2.55)
    ax.legend(loc='upper right', bbox_to_anchor=(1.03, 1.04))
    ax.annotate('constraints hurt here,\nhelp only here', xy=(2, w['rmse_C']),
                xytext=(0.75, 2.72), fontsize=5.6, color='#333333',
                arrowprops=dict(arrowstyle='-', lw=0.5, color='#999999'))
    FS.panel(ax, 'a', x=-0.22, y=1.02)

    # ---- (b) firewall ladder
    ax2 = fig.add_subplot(gs[0, 1])
    ladder = [('honest\n(select on A)', a2['honest_selected_by_A']['rmse_C'], FS.BLUE),
              ('refit on\nall data', a2b['c_rmse_in_sample'], FS.LGREY),
              ('select\non C (leak)', a2['selected_by_C']['rmse_C'], FS.ORANGE)]
    xs = np.arange(len(ladder))
    ax2.bar(xs, [v for _, v, _ in ladder], width=0.6, color=[c for _, _, c in ladder], zorder=2)
    for x, (_, v, _) in zip(xs, ladder):
        ax2.text(x, v + 0.015, '%.3f' % v, ha='center', fontsize=5.6, color='#333333')
    ax2.set_xticks(xs)
    ax2.set_xticklabels([l for l, _, _ in ladder])
    ax2.set_ylabel('C-region RMSE  (°C)')
    yh = a2['honest_selected_by_A']['rmse_C']
    ys_ = a2['selected_by_C']['rmse_C']
    ax2.set_ylim(2.15, 2.86)
    ax2.plot([-0.34, -0.34], [yh + 0.02, 2.74], color=FS.BAD, lw=0.8, zorder=3)
    ax2.plot([-0.34, 2.0], [2.74, 2.74], color=FS.BAD, lw=0.8, zorder=3)
    ax2.annotate('', xy=(2.0, ys_ + 0.03), xytext=(2.0, 2.74),
                 arrowprops=dict(arrowstyle='-|>', color=FS.BAD, lw=0.8))
    ax2.text(0.83, 2.755, 'apparent −%.3f °C gain = selection leakage'
             % a2['c_rmse_inflation'], ha='center', va='bottom', fontsize=5.3,
             color=FS.BAD)
    FS.panel(ax2, 'b', x=-0.26, y=1.02)

    # ---- (c) population profile
    ax3 = fig.add_subplot(gs[0, 2])
    n = b['design']['n_population']
    bars = [('rejected by the physics audit', pop['n_audit_fail']),
            ('exceeded the complexity cap (> 15)', pop['n_exceed_complexity_cap'])]
    ys = np.arange(len(bars))[::-1]
    ax3.barh(ys, [v / n * 100 for _, v in bars], height=0.34,
             color=[FS.BAD, FS.GREY], zorder=2)
    for y, (lab, v) in zip(ys, bars):
        ax3.text(v / n * 100 + 1.5, y, '%d/%d  (%.0f%%)' % (v, n, v / n * 100),
                 va='center', fontsize=5.6, color='#333333')
        ax3.text(0, y + 0.42, lab, va='bottom', ha='left', fontsize=5.4,
                 color='#333333')
    ax3.set_yticks([])
    ax3.set_ylim(-0.6, 1.80)
    ax3.set_xlim(0, 100)
    ax3.set_xlabel('share of the free-form pool  (%)')
    FS.panel(ax3, 'c', x=-0.14, y=1.02)

    FS.save(fig, os.path.join(FIG, 'fig6_baselineD'))


if __name__ == '__main__':
    fig1_protocol_split()
    fig2_baselineB()
    fig3_search()
    fig4_validation()
    fig5_external()
    fig6_baselineD()
    print('done')
