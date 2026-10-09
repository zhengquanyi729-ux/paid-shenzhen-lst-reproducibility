"""
S05.6 论文总览图 / 图形摘要（Python / matplotlib）
==================================================
一张图概括全篇：**协议流水线**（数据分区 → 发现侧沙箱 → 冻结哈希 → 分离式评估 →
协议审计）+ **三项对抗检验**（传统学习器 / 外部城市复现 / 约束与防火墙压力测试）+
**结论带**。设计为论文研究设计总览图（generic 版 Fig. 0，npj 版 Fig. 1），
也可直接作 graphical abstract。

逻辑连接：
  (a) 五段之间用**带杆箭头**连接；
  (a) → (b)：冻结所得候选集**被三项对抗检验压力测试**；
  (b) → (c)：三项检验**共同决定结论**。
两条带间竖向箭头 + 说明文字把三排的因果关系显式画出来。

图契约见 figures/FIGURE_CONTRACT.md（"Fig 0 — Study overview"）。
结论一句话：本研究没有建立出可移植的城市 LST 定律；它交付的是**方法学**结果——
可审计的符号搜索管线、分离式发现架构，以及一项事后实现审计（自主科学必须不仅
冻结数据与候选，还要冻结验证器的软件状态与访问史）。Stage 04 是 documented
protocol deviation 之下的 locked-region evaluation，不再是 pristine confirmatory test。

所有数字均**从既有冻结产物读取**，不在本脚本里硬编码，也不重算任何结果。
用法：python3 stage05_paper/scripts/s05_06_study_overview.py
"""
import os, json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import figstyle as FS

_HERE = os.path.dirname(os.path.abspath(__file__))
S05 = os.path.dirname(_HERE)
PROJ = os.path.dirname(S05)
FIG = os.path.join(S05, 'figures')
REP = os.path.join(S05, 'reports')

W_MM, H_MM = 183.0, 135.0
FS.apply()
FIGW, FIGH = W_MM * FS.MM, H_MM * FS.MM
ASPECT = W_MM / H_MM              # x-unit:mm ÷ y-unit:mm，用于圆形圆角/方端

BLUE, ORANGE, GREY = FS.BLUE, FS.ORANGE, FS.GREY
FILL_B = '#EAF3FA'                # 协议卡浅蓝
FILL_C = '#FDF2EA'                # 对抗检验卡浅橙
FILL_V = '#F2F2F2'                # 结论带浅灰
CONN = '#4A4A4A'                  # 带间连接箭头
NOTE = '#6E6E6E'                  # 带标/连接说明文字

X0, XW = 0.008, 0.984             # 卡片区左边界与总宽


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def th(n):
    """千位分隔用空格（与图 1 的 '25 366' 一致）。"""
    return format(int(n), ',').replace(',', ' ')


def card(ax, x, y, w, h, fc='white', ec=FS.BLACK, lw=0.7, z=1):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle='round,pad=0,rounding_size=0.013',
        mutation_aspect=ASPECT, linewidth=lw, edgecolor=ec,
        facecolor=fc, zorder=z))


def badge(ax, cx, cy, txt, color=BLUE, ms=8.0, fs=5.0):
    ax.plot(cx, cy, 'o', ms=ms, color=color, mec='none', zorder=3)
    ax.text(cx, cy, txt, color='white', fontsize=fs, fontweight='bold',
            ha='center', va='center', zorder=4)


def arrow(ax, p0, p1, color, lw=0.8, ms=6.5):
    """带杆箭头（轴线 + 实心箭头），p0→p1 均以 axes 坐标给出。"""
    ax.annotate('', xy=p1, xytext=p0, zorder=3,
                arrowprops=dict(arrowstyle='-|>', color=color, lw=lw,
                                shrinkA=0, shrinkB=0, mutation_scale=ms))


def band_label(ax, y, letter, text, y_letter=None):
    ax.text(X0 + 0.004, y if y_letter is None else y_letter, letter, fontsize=8,
            fontweight='bold', va='bottom', ha='left', color=FS.BLACK)
    ax.text(X0 + 0.032, y, text, fontsize=6.2, style='italic', va='bottom',
            ha='left', color=NOTE)


def build():
    # ---------------------------------------------------------------- 读数据
    sp = pd.read_csv(os.path.join(PROJ, 'stage01_protocol', 'split',
                                  'analysis_split.csv'))
    cnt = sp['role'].value_counts().to_dict()
    n_a, n_b = cnt['discovery'], cnt['dev_validation']
    n_c, n_buf = cnt['locked'], cnt['buffer']
    n_scope = n_a + n_b + n_c + n_buf

    reg = load(os.path.join(PROJ, 'stage03_discovery', 'registry',
                            'candidate_registry.json'))
    n_cand = reg['n_candidates']
    n_frozen = len(reg['frozen_ids'])
    fits = reg['guard']['fits']
    denials = reg['guard']['denials']
    budget = reg['budget']['total_fit_budget']
    rounds = len(reg['rounds'])
    base_a = reg['baselineA_dev_cv_rmse']
    cv_best = min(c['dev_evidence']['cv_rmse'] for c in reg['candidates']
                  if c['id'] in reg['frozen_ids'])

    v4 = load(os.path.join(PROJ, 'stage04_validation', 'reports',
                           's04_validation_results.json'))
    h = v4['candidates']['S03-H10-GREEDY']['primary_endpoint']
    d_prim, p_prim = h['delta_rmse'], h['perm_p']

    bb = load(os.path.join(REP, 'baselineB.json'))
    c_rf = bb['regions']['C']['rf']['delta_vs_baselineA']
    c_h10 = bb['regions']['C']['h10']['delta_vs_baselineA']

    ex = load(os.path.join(REP, 'external_replication.json'))
    n_ext = ex['dataset']['n_cells_used']
    r_dem = ex['bivariate_corr']['DEM_mean']['pearson']

    bd = load(os.path.join(REP, 'baselineD.json'))
    w, h10b = bd['arm1_winner'], bd['reference']['h10_constrained']
    infl = bd['arm2_firewall_off']['c_rmse_inflation']
    c_leak = bd['arm2_firewall_off']['selected_by_C']['rmse_C']

    # ---------------------------------------------------------------- 画布
    fig = plt.figure(figsize=(FIGW, FIGH))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ================================================================ (a)
    ya, ha_, gap = 0.722, 0.235, 0.026
    cw = (XW - 4 * gap) / 5
    stages = [
        ('Data & partition', BLUE, [
            'Shenzhen · 100 m grid',
            'urban morphology × LST',
            '%s cells in scope' % th(n_scope),
            'A %s · B %s' % (th(n_a), th(n_b)),
            'buffer R = 15 (1.5 km) · %s' % th(n_buf),
            'C %s — withheld' % th(n_c)]),
        ('Discovery-side sandbox', BLUE, [
            'agent reads A + B only',
            '%d candidates · %d rounds' % (n_cand, rounds),
            'greedy + local refine',
            '%s / %s fits' % (th(fits), th(budget)),
            '4 hard physics gates',
            'complexity cap ≤ 15']),
        ('Freeze & hash', BLUE, [
            '%d candidates frozen' % n_frozen,
            'SHA-256 canonical hash',
            'best A-CV %.3f °C' % cv_best,
            'Baseline A fixed (%.3f)' % base_a,
            'placebo = Baseline A',
            'evaluation budget preserved']),
        ('Separated evaluation', BLUE, [
            'C excluded from discovery-side roles',
            'frozen candidate evaluated on C',
            'ΔRMSE +%.4f °C · p = %.3f' % (d_prim, p_prim),
            '95%% CI > 0 · Holm, family = %d' % n_frozen,
            'physics audit + negative controls',
            'endpoint passes; placebo fails']),
        ('Protocol audit', BLUE, [
            'post-hoc implementation audit',
            'discovery-side isolation retained',
            'single-access design failed',
            'validation chronology unresolved',
            'Stage 04 reclassified as a',
            'locked-region evaluation (deviation)'])]
    for i, (title, col, body) in enumerate(stages):
        x = X0 + i * (cw + gap)
        card(ax, x, ya, cw, ha_, fc=FILL_B, ec=col, lw=0.8)
        badge(ax, x + 0.018, ya + ha_ - 0.030, str(i + 1), col)
        ax.text(x + 0.033, ya + ha_ - 0.030, title, fontsize=6.2,
                fontweight='bold', color=col, va='center', ha='left')
        ax.text(x + 0.015, ya + ha_ - 0.060, '\n'.join(body), fontsize=5.6,
                color=FS.BLACK, va='top', ha='left', linespacing=1.65)
        if i < 4:                       # 带杆箭头跨越卡间空隙
            arrow(ax, (x + cw + 0.0015, ya + ha_ / 2),
                  (x + cw + gap - 0.0015, ya + ha_ / 2), col, lw=0.8, ms=6.5)
    band_label(ax, 0.970, 'a',
               'the protocol: a spatial partition, a sandboxed search, and a separated evaluation',
               y_letter=0.964)

    # ================================================================ (b)
    yb, hb, gb = 0.355, 0.285, 0.024
    cwb = (XW - 2 * gb) / 3
    checks = [
        ('Conventional learners', [
            'RF and GBM, same 7 covariates',
            'out-predict the candidate on C',
            'ΔC +%.4f vs +%.4f °C' % (c_rf, c_h10),
            '',
            '→ the candidate’s advantage is',
            'two-region-specific, not a',
            'transferable law']),
        ('External replication', [
            'Changchun 2021 · %s cells' % th(n_ext),
            '(post-hoc; 500 m vs Shenzhen 100 m)',
            '',
            'partial overlap: nonlinear NDVI',
            'cooling; building warming;',
            'vegetation × building',
            '',
            'does not transfer: exp(DEM)',
            'worst; DEM r = %+.2f' % r_dem]),
        ('Constraint & firewall stress test', [
            'exploratory combined-pipeline test',
            'unconstrained: A-CV %.3f' % w['cv_rmse'],
            '(vs H10 %.3f), but worse on C' % h10b['cv_rmse'],
            'C RMSE %.3f (vs %.3f)' % (w['rmse_C'], h10b['rmse_C']),
            '→ directional, not confirmatory',
            'firewall off manufactures',
            '+%.4f °C from leakage' % infl])]
    for j, (title, body) in enumerate(checks):
        x = X0 + j * (cwb + gb)
        card(ax, x, yb, cwb, hb, fc=FILL_C, ec=ORANGE, lw=0.8)
        ax.plot(x + 0.018, yb + hb - 0.030, marker='s', ms=3.8, color=ORANGE,
                zorder=3)
        ax.text(x + 0.034, yb + hb - 0.030, title, fontsize=6.2,
                fontweight='bold', color=ORANGE, va='center', ha='left')
        ax.text(x + 0.019, yb + hb - 0.060, '\n'.join(body), fontsize=5.6,
                color=FS.BLACK, va='top', ha='left', linespacing=1.80)
    band_label(ax, 0.651, 'b', 'three adversarial checks on the frozen result',
               y_letter=0.645)

    # ================================================================ (c)
    yc, hc = 0.040, 0.230
    card(ax, X0, yc, XW, hc, fc=FILL_V, ec=FS.BLACK, lw=0.9)
    ax.text(X0 + 0.018, yc + hc - 0.026, 'Verdict', fontsize=7.4,
            fontweight='bold', color=FS.BLACK, va='top', ha='left')
    verdict = ('No portable urban land-surface-temperature law is established here. '
               'The contribution is methodological:\n'
               'an auditable symbolic-search pipeline, a separated discovery-side '
               'architecture, and a post-hoc\n'
               'implementation audit showing that autonomous-science workflows must freeze '
               'not only data and candidates\n'
               'but also validator software state and access history. What remains is a '
               'locked-region evaluation under a\n'
               'documented protocol deviation, plus post-hoc adversarial benchmarking and replication.')
    ax.text(X0 + 0.018, yc + hc - 0.062, verdict, fontsize=6.3, color=FS.BLACK,
            va='top', ha='left', linespacing=1.62)
    ax.text(X0 + 0.018, yc + 0.016,
            'The locked-region evaluation is reported under a documented protocol deviation; the '
            'Changchun replication and the Stage-05 adversarial benchmarks are post-hoc.',
            fontsize=5.5, style='italic', color=NOTE, va='bottom', ha='left')
    band_label(ax, 0.281, 'c', 'what the protocol returned', y_letter=0.275)

    # ================================================ 带间逻辑连接（a→b→c）
    # (a) → (b)：冻结所得候选被三项对抗检验压力测试
    arrow(ax, (0.5, ya - 0.002), (0.5, yb + hb + 0.002), CONN, lw=0.9, ms=7)
    ax.text(0.516, (ya + yb + hb) / 2,
            'the frozen candidates are then stress-tested',
            fontsize=5.6, style='italic', color=NOTE, va='center', ha='left')
    # (b) → (c)：三项检验共同决定结论
    arrow(ax, (0.5, yb - 0.002), (0.5, yc + hc + 0.002), CONN, lw=0.9, ms=7)
    ax.text(0.516, (yb + yc + hc) / 2,
            'the three checks jointly determine the verdict',
            fontsize=5.6, style='italic', color=NOTE, va='center', ha='left')

    FS.save(fig, os.path.join(FIG, 'fig0_study_overview'))


if __name__ == '__main__':
    build()
