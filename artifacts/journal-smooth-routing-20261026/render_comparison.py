import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Circle, Rectangle

folder = Path(__file__).parent
plt.rcParams['font.family'] = 'Microsoft YaHei'
paper, ink = '#f3f0e7', '#15212b'
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), dpi=180, facecolor=paper)
for ax, version, title in zip(axes, ['before', 'after'], ['修改前', '修改后']):
    svg = (folder / f'{version}-1100-atlas.svg').read_text(encoding='utf-8')
    root = ET.fromstring(svg[svg.index('<svg'):])
    ax.set(facecolor=paper, xlim=(945, 1110), ylim=(1790, 1620), aspect='equal')
    ax.axis('off')
    ax.set_title(title, fontsize=14, color=ink, pad=12)
    for group in root.findall('.//g'):
        classes = group.get('class', '')
        for el in group.findall('path'):
            kind, d = el.get('class', ''), el.get('d', '')
            if kind == 'journal-handoff-path':
                tokens = re.findall(r'[MC]|-?\d+(?:\.\d+)?(?:e[+-]?\d+)?', d, re.I)
                vertices, codes, i = [], [], 0
                while i < len(tokens):
                    cmd = tokens[i]
                    i += 1
                    for code in ([MplPath.MOVETO] if cmd == 'M' else [MplPath.CURVE4] * 3):
                        vertices.append((float(tokens[i]), float(tokens[i + 1])))
                        codes.append(code)
                        i += 2
                patch = PathPatch(MplPath(vertices, codes), fill=False, color=ink, alpha=.3, linewidth=1, capstyle='round', joinstyle='round', zorder=1)
                if el.get('stroke-dasharray'):
                    patch.set_linestyle((0, tuple(float(n) for n in el.get('stroke-dasharray').split())))
                ax.add_patch(patch)
            elif 'journal-chain-line' in kind:
                values = re.findall(r'-?\d+(?:\.\d+)?', d)
                if len(values) == 3:
                    x, y, end = map(float, values)
                    ax.plot([x, x], [y, end], color=ink, linewidth=1, zorder=2)
    for el in root.findall('.//mask/*'):
        if el.get('fill') != 'black':
            continue
        if el.tag == 'circle':
            ax.add_patch(Circle((float(el.get('cx')), float(el.get('cy'))), float(el.get('r')), color=paper, zorder=3))
        elif el.tag == 'rect':
            ax.add_patch(Rectangle((float(el.get('x')), float(el.get('y'))), float(el.get('width')), float(el.get('height')), color=paper, zorder=3))
    for el in root.iter():
        kind = el.get('class', '')
        if el.tag == 'circle' and kind.startswith('journal-dot '):
            ax.add_patch(Circle((float(el.get('cx')), float(el.get('cy'))), float(el.get('r')), facecolor=ink if 'is-artifact' in kind else paper, edgecolor=paper, linewidth=1, zorder=4))
        elif el.tag == 'rect' and 'journal-seal' in kind:
            ax.add_patch(Rectangle((float(el.get('x')), float(el.get('y'))), float(el.get('width')), float(el.get('height')), facecolor=ink, zorder=4))
fig.text(.5, .035, '由实际 SVG 路径离线绘制，用于比较连线形状', ha='center', fontsize=9, color=ink)
fig.subplots_adjust(left=.04, right=.96, top=.9, bottom=.11, wspace=.08)
fig.savefig(folder / 'comparison.png', facecolor=paper)
print(folder / 'comparison.png')
