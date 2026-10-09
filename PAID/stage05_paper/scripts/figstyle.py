"""
figstyle — Stage 05 publication figure style (Python / matplotlib)
==================================================================
Shared contract for all Stage 05 figures so the set reads as one visual language.

Design rules (journal-neutral, high-impact default):
  * double column = 183 mm (7.20 in); single column = 89 mm (3.50 in)
  * Arial-metric sans (Liberation/Nimbus fallback), base 7 pt, min 5.5 pt
  * colour-blind-safe palette; every colour carries a fixed meaning across figures
  * no top/right spines; outward ticks; embedded TrueType for PDF/SVG
  * panel letters bold, lowercase, top-left outside the axes
  * export: vector PDF + SVG, 900-dpi PNG, 900-dpi TIFF

All figures must be built through apply() and save(); do not set rcParams locally.
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

MM = 1.0 / 25.4
W_SINGLE = 89 * MM      # 3.50 in
W_MID = 120 * MM        # 4.72 in
W_DOUBLE = 183 * MM     # 7.20 in

# --- colour-blind-safe palette (Okabe–Ito family) --------------------------
BLUE = '#0072B2'
SKY = '#56B4E9'
GREEN = '#009E73'
YELLOW = '#E69F00'
ORANGE = '#D55E00'
PURPLE = '#CC79A7'
GREY = '#8C8C8C'
LGREY = '#C9C9C9'
BLACK = '#111111'

# --- fixed semantics (identical across every figure) ----------------------
# Spatial-partition palette (Fig 1 map): a muted, desaturated hypsometric-style
# violet→pink ramp on a pale off-white ground (referenced from a Sichuan
# elevation-tint reference the author supplied). The four analysis roles step
# monotonically in lightness so the classes stay separable while the map reads
# as one calm, low-contrast ramp; the sealed/locked region C is the darkest,
# most saturated plum — the figure's focal colour — and out-of-scope / no-data
# cells sit just off the page ground so the footprint carries no white holes.
ROLE = {'discovery': '#A185BC', 'dev_validation': '#C9AACB',
        'buffer': '#E8DEEA', 'locked': '#67487F', 'outside': '#F2EFEC'}
ROLE_LBL = {'discovery': 'A  discovery', 'dev_validation': 'B  dev-validation',
            'buffer': 'buffer (R = 15)', 'locked': 'C  locked'}

MODEL = {'baselineA': BLACK, 'h10': BLUE, 'no_dem': SKY, 'rf': ORANGE,
         'gbm': YELLOW, 'rf_aug': PURPLE, 'constant': GREY}
MODEL_LBL = {'baselineA': 'Baseline A (linear)', 'h10': 'Candidate H10',
             'no_dem': 'Candidate (no DEM)', 'rf': 'Random forest',
             'gbm': 'Gradient boosting', 'rf_aug': 'RF (augmented)',
             'constant': 'Constant floor'}

OK = GREEN        # reproduced / passes / eligible
BAD = ORANGE      # rejected / does not transfer


def apply():
    """Install the shared rcParams. Idempotent."""
    mpl.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'Liberation Sans',
                            'Nimbus Sans', 'DejaVu Sans'],
        'font.size': 7, 'axes.labelsize': 7, 'axes.titlesize': 7,
        'xtick.labelsize': 6.5, 'ytick.labelsize': 6.5, 'legend.fontsize': 6.5,
        'axes.linewidth': 0.6, 'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
        'xtick.minor.width': 0.5, 'ytick.minor.width': 0.5,
        'xtick.major.size': 2.6, 'ytick.major.size': 2.6,
        'xtick.minor.size': 1.4, 'ytick.minor.size': 1.4,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.major.pad': 1.8, 'ytick.major.pad': 1.8,
        'axes.labelpad': 2.0, 'axes.spines.top': False, 'axes.spines.right': False,
        'legend.frameon': False, 'legend.handlelength': 1.4,
        'legend.handletextpad': 0.5, 'legend.labelspacing': 0.35,
        'legend.borderpad': 0.2, 'legend.borderaxespad': 0.3,
        'lines.linewidth': 1.0, 'lines.markersize': 3.0,
        'lines.solid_capstyle': 'round',
        'figure.dpi': 200, 'savefig.dpi': 900, 'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.02, 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.unicode_minus': True, 'figure.constrained_layout.use': False,
    })


def panel(ax, letter, x=-0.16, y=1.06):
    """Bold lowercase panel letter, top-left, outside the axes."""
    ax.text(x, y, letter, transform=ax.transAxes, fontsize=8, fontweight='bold',
            va='bottom', ha='left')


def save(fig, base):
    """Write vector PDF + SVG and 900-dpi PNG + TIFF, then close."""
    os.makedirs(os.path.dirname(base), exist_ok=True)
    fig.savefig(base + '.pdf')
    fig.savefig(base + '.svg')
    fig.savefig(base + '.png', dpi=900)
    try:
        fig.savefig(base + '.tif', dpi=900, pil_kwargs={'compression': 'tiff_lzw'})
    except Exception as exc:                     # pragma: no cover
        print('  (tiff skipped: %s)' % exc)
    plt.close(fig)
    print('[fig] %s  (pdf/svg/png/tif)' % os.path.basename(base))


# --- forest / interval helper ---------------------------------------------
def forest(ax, labels, centers, los, his, colors, xline=0.0, ms=3.4,
           lw=1.4, xline_lbl=None, zero_lbl='0'):
    """Horizontal point + 95% CI rows (top-to-bottom = given order)."""
    ys = np.arange(len(labels))[::-1]
    for y, c, lo, hi, col in zip(ys, centers, los, his, colors):
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [y, y], color=col, lw=lw, zorder=2)
        ax.plot(c, y, 'o', color=col, ms=ms, zorder=3, mec='white', mew=0.45)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.axvline(xline, color='#9A9A9A', lw=0.6, ls=(0, (4, 3)), zorder=1)
    if xline_lbl:
        ax.text(xline, len(labels) - 0.35, xline_lbl, fontsize=5.6, color='#7A7A7A',
                ha='center', va='bottom')
    ax.set_ylim(-0.6, len(labels) - 0.4)
    return ys


# --- schematic helpers -----------------------------------------------------
def box(ax, cx, cy, w, h, txt, fc='white', ec='#444444', lw=0.7, fs=6.2,
        weight='normal', tc=BLACK, rounding=0.02):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                 boxstyle='round,pad=0.004,rounding_size=%s' % rounding,
                 linewidth=lw, edgecolor=ec, facecolor=fc, mutation_scale=1.0))
    ax.text(cx, cy, txt, ha='center', va='center', fontsize=fs, fontweight=weight,
            color=tc, linespacing=1.35)


def arrow(ax, p0, p1, ls='-', color='#444444', lw=0.7, label=None, lfs=5.6,
          rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>', mutation_scale=6,
                 lw=lw, color=color, linestyle=ls, shrinkA=1.5, shrinkB=1.5,
                 connectionstyle='arc3,rad=%s' % rad))
    if label:
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        ax.text(mx, my + 0.025, label, ha='center', va='bottom', fontsize=lfs,
                color='#555555')
