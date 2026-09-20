"""Matplotlib chart renderers for the dashboard's research reports.

Figures are emitted as inline SVG so the page stays self-contained and the
enlarge dialog can clone the node. Text is kept as text (`svg.fonttype='none'`)
and picks up the page font, matching the depth-match report's figures.
"""
from __future__ import annotations

import io
import re

import matplotlib
import numpy as np

matplotlib.use('Agg')

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

TEAL, RUST, BLUE, GRAY = '#087b78', '#b24f35', '#446994', '#78837a'
INK, GRID, SPINE, SAND = '#243648', '#e4e8e2', '#b7c1bf', '#c8a27a'

plt.rcParams.update({
    'svg.fonttype': 'none',
    # Metrics come from the one CJK font present on the build machine; the
    # emitted font-family is rewritten to the page token so any viewer resolves it.
    'font.family': ['Microsoft YaHei'],
    'font.size': 12,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white',
    'text.color': INK,
    'axes.labelcolor': INK,
    'axes.edgecolor': SPINE,
    'xtick.color': INK,
    'ytick.color': INK,
    'axes.axisbelow': True,
    'legend.frameon': False,
    'axes.unicode_minus': False,
})

_rendered = [0]


def style_axes(ax, *, grid='y', zero_line=False):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    for side in ('left', 'bottom'):
        ax.spines[side].set_linewidth(0.8)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.7)
    if zero_line:
        ax.axhline(0, color=SPINE, linewidth=1.0)
    return ax


def nice_ticks(ax, axis='y', *, from_zero=False, count=6):
    """Round tick values. `from_zero` pins a non-negative quantity's axis at 0."""
    target = ax.yaxis if axis == 'y' else ax.xaxis
    target.set_major_locator(MaxNLocator(nbins=count, steps=[1, 2, 2.5, 5, 10], prune=None))
    if from_zero:
        lo, hi = (ax.get_ylim() if axis == 'y' else ax.get_xlim())
        (ax.set_ylim if axis == 'y' else ax.set_xlim)(0, hi)
    return ax


def render(fig, title, key=None, png_path=None):
    """Serialize one figure to inline SVG with document-unique element ids.

    Several figures share one HTML document, so every id matplotlib emits is
    namespaced and its `#id` references rewritten to match.
    """
    _rendered[0] += 1
    prefix = f'{key or "f"}{_rendered[0]:02d}'
    buffer = io.StringIO()
    try:
        fig.savefig(buffer, format='svg', bbox_inches='tight', pad_inches=0.12)
        if png_path is not None:
            fig.savefig(png_path, format='png', dpi=150, bbox_inches='tight', pad_inches=0.12)
    finally:
        plt.close(fig)
    svg = buffer.getvalue()
    svg = svg[svg.index('<svg'):].strip()
    svg = re.sub(r'<metadata>.*?</metadata>\s*', '', svg, flags=re.S)

    ids = sorted(set(re.findall(r'id="([^"]+)"', svg)), key=len, reverse=True)
    if ids:
        alternation = '|'.join(re.escape(i) for i in ids)
        svg = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}-{m.group(1)}"', svg)
        svg = re.sub(rf'#({alternation})(?![\w-])', lambda m: f'#{prefix}-{m.group(1)}', svg)

    # Let the container decide the size; keep the viewBox for aspect ratio.
    svg = re.sub(r'(<svg\b[^>]*?)\s+width="[^"]*"\s+height="[^"]*"', r'\1', svg, count=1)
    # One page font token instead of matplotlib's resolved fallback chain.
    svg = re.sub(r"font-family: [^;\"]+", 'font-family: var(--sans)', svg)

    escaped = (title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
               .replace('"', '&quot;'))
    svg = svg.replace('<svg ', f'<svg role="img" aria-label="{escaped}" ', 1)
    svg = svg.replace('>', f'><title>{escaped}</title>', 1)
    return svg


def figure(size=(11.0, 4.6)):
    return plt.subplots(figsize=size)


def annotate_traded(ax, rows):
    """Mark which score deciles each strategy actually trades, under the axis.

    `rows` is [(y, [(label, first_decile, last_decile, color), ...]), ...].
    """
    for y, spans in rows:
        for label, first, last, color in spans:
            ax.annotate(
                '', xy=(first - 0.42, y), xytext=(last + 0.42, y),
                xycoords=('data', 'axes fraction'), textcoords=('data', 'axes fraction'),
                arrowprops=dict(arrowstyle='-', color=color, linewidth=6, alpha=0.3),
                annotation_clip=False,
            )
            ax.text((first + last) / 2, y, label, color=color, ha='center', va='center',
                    fontsize=10.5, transform=ax.get_xaxis_transform(), clip_on=False)


TRADED_ROWS = [
    (-0.20, [('纯空卖 D1–D2', 1, 2, BLUE), ('纯多买 D9–D10', 9, 10, TEAL)]),
    (-0.30, [('多空卖 D1', 1, 1, RUST), ('多空买 D10', 10, 10, RUST)]),
]


def newey_west_se(values, lag=None):
    """Standard error of the mean with a Bartlett kernel; lag defaults to 4(T/100)^(2/9)."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return float('nan')
    if lag is None:
        lag = int(np.floor(4 * (n / 100.0) ** (2 / 9)))
    e = x - x.mean()
    variance = float(e @ e) / n
    for k in range(1, lag + 1):
        cov = float(e[k:] @ e[:-k]) / n
        variance += 2 * (1 - k / (lag + 1)) * cov
    variance = max(variance, 0.0)
    return float(np.sqrt(variance / n))
