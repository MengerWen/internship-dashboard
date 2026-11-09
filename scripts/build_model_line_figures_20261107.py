"""生成 2026-11-07 模型线汇报的六张插图。

数据只读研究仓库已提交的两份证据：
- reports/2026-11/2026-11-08-model-szse344-absolute-returns-evidence.json（选优检查点曲线、入选点）
- reports/2026-11/2026-11-09-model-szse344-collinearity-shap-evidence.json（PCA 特征值、SHAP 分组份额）

用法：python scripts/build_model_line_figures_20261107.py <sirui-quant-research 仓库根>
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "assets" / "model-line-2026-11-07"

ABS_EVIDENCE = "reports/2026-11/2026-11-08-model-szse344-absolute-returns-evidence.json"
SHAP_EVIDENCE = "reports/2026-11/2026-11-09-model-szse344-collinearity-shap-evidence.json"

# 站点 DESIGN.md 的墨色与三种已过色盲校验的类别色（dataviz validate_palette，浅色底）
INK = "#15212b"
MUTED = "#68716f"
SOFT = "#c8c1b4"
PAPER = "#f8f4eb"
BLUE = "#2a6fa8"  # 11:30
CORAL = "#d9654f"  # 收盘；示意图中的强调
GOLD = "#c9a227"
HORIZON = {"morning": ("11:30", BLUE), "close": ("收盘", CORAL)}

plt.rcParams.update(
    {
        "font.family": ["Microsoft YaHei", "SimHei", "sans-serif"],
        "axes.unicode_minus": False,
        "font.size": 10.5,
        "axes.edgecolor": SOFT,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": SOFT,
        "grid.linewidth": 0.6,
        "grid.alpha": 0.6,
        "legend.frameon": False,
        "savefig.dpi": 200,
        "savefig.facecolor": PAPER,
    }
)


def load(repo: Path, rel: str) -> tuple[dict, str]:
    raw = (repo / rel).read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def save(fig, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


# ---------- 第五节 ----------

def selection_curves(abs_ev: dict) -> None:
    """每个周期一张横图：文章样式把图高限制在 560px，竖排两面板会被压窄。"""
    from matplotlib.lines import Line2D

    d18 = abs_ev["d18"]
    chosen = {(s["horizon"], s["tree_id"]): s for s in d18["selected"]}
    for horizon, name in (("morning", "selection-curves-morning.png"), ("close", "selection-curves-close.png")):
        label, color = HORIZON[horizon]
        fig, ax = plt.subplots(figsize=(7.6, 4.3))
        curves = [c for c in d18["checkpoints"] if c["horizon"] == horizon]
        for c in curves:
            if (horizon, c["tree_id"]) in chosen:
                continue
            xs = [p["iteration"] for p in c["curve"]]
            ys = [p["absolute_mean_bp"] for p in c["curve"]]
            ax.plot(xs, ys, color=MUTED, lw=0.8, alpha=0.45, zorder=1)
        for c in curves:
            pick = chosen.get((horizon, c["tree_id"]))
            if pick is None:
                continue
            xs = [p["iteration"] for p in c["curve"]]
            ys = [p["absolute_mean_bp"] for p in c["curve"]]
            at = dict(zip(xs, ys))[pick["iteration"]]
            assert abs(at - pick["mean_bp"]) < 1e-6, (c["tree_id"], at, pick["mean_bp"])
            ax.plot(xs, ys, color=color, lw=1.8, zorder=3)
            ax.scatter([pick["iteration"]], [at], s=46, color=color, edgecolor=PAPER, linewidth=1.5, zorder=4)
        for r, txt in zip((50, 100, 150, 200), ("31→16", "16→8", "8→4", "4→2")):
            ax.axvline(r, color=INK, lw=0.8, ls=(0, (4, 3)), alpha=0.55, zorder=2)
            ax.text(r + 4, 0.03, txt, transform=ax.get_xaxis_transform(), color=MUTED, fontsize=8.5)
        ax.set_title(f"{label} 周期：31 套树的 L5 随训练轮数变化（原种子）", loc="left")
        ax.set_xlabel("训练轮数（每 10 轮一个检查点；虚线为减半位置）")
        ax.set_ylabel("开发段 OOF 绝对 L5（bp）")
        ax.set_xlim(0, max(p["iteration"] for c in curves for p in c["curve"]) + 10)
        top = max(p["absolute_mean_bp"] for c in curves for p in c["curve"])
        ax.set_ylim(top - 12, top + 1)
        handles = [
            Line2D([], [], color=color, lw=1.8, marker="o", ms=6, mec=PAPER, label="入选的 5 套树；圆点＝选中的检查点"),
            Line2D([], [], color=MUTED, lw=0.8, alpha=0.6, label="其余树；线的终点＝该树停止（被减半淘汰或早停）"),
        ]
        ax.legend(handles=handles, loc="lower right" if horizon == "morning" else "upper right", fontsize=9)
        fig.tight_layout()
        save(fig, name)


def box(ax, x, y, w, h, title, body, *, accent=False):
    face = "#fbe9e4" if accent else "white"
    edge = CORAL if accent else INK
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06", fc=face, ec=edge, lw=1.1, zorder=3))
    ax.text(x + 0.14, y + h - 0.14, title, ha="left", va="top", fontsize=11, fontweight="bold", color=INK, zorder=4)
    ax.text(x + 0.14, y + h - 0.5, body, ha="left", va="top", fontsize=9.5, color=MUTED, linespacing=1.5, zorder=4)


def arrow(ax, pts, *, accent=False):
    xs, ys = zip(*pts)
    color = CORAL if accent else MUTED
    ax.plot(xs, ys, color=color, lw=1.2, zorder=2, solid_capstyle="butt")
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, mutation_scale=11), zorder=2)


def canvas(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 8)
    ax.set_ylim(0, 8 * height / width)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


COLS = (0.05, 4.25)
W = 3.7


def wrap_down(ax, src_x, src_y, dst_x, dst_y, **kw):
    """从上一行的框底部下到行间，再水平移到目标框上方，最后进入目标框顶部。"""
    mid = (src_y + dst_y) / 2
    arrow(ax, [(src_x, src_y), (src_x, mid), (dst_x, mid), (dst_x, dst_y)], **kw)


def selection_flow() -> None:
    fig, ax = canvas(7.6, 6.9)
    h = 1.6
    rows = (5.45, 3.0, 0.55)
    nodes = [
        ("① 搜索留下的检查点", "62 套树，每 10 轮存一个检查点，\n共 685 个；每个点记下开发段\nOOF 上的 L5 和 Sharpe"),
        ("② 每套树只留一个点", "在 Sharpe ≥ 3 的检查点里，\n取 L5 最高的那一个；\n这一轮就是以后的固定轮数"),
        ("③ 每个周期取前 5 套", "按②的 L5 排序；被减半淘汰的树照样参加，\n10 个入选位置里有 7 个来自它们"),
        ("④ 5 个种子 × 15 折重训", "每周期 25 份 OOF 预测，算集成成绩；\n原种子与搜索时逐位一致；\n种子间 L5 标准差 0.4–1.7 bp"),
        ("⑤ 用全部开发段重训", "425 天 × 25 个模型，\n预测等权平均就是最终分数"),
        ("⑥ 冻结，再看 Test", "已看段、未看段分开报告；\n看过之后不再改成员、轮数和种子"),
    ]
    for i, (title, body) in enumerate(nodes):
        box(ax, COLS[i % 2], rows[i // 2], W, h, title, body, accent=(i == 5))
    for r in range(3):
        y = rows[r] + h / 2
        arrow(ax, [(COLS[0] + W, y), (COLS[1], y)], accent=(r == 2))
    for r in range(2):
        wrap_down(ax, COLS[1] + W / 2, rows[r], COLS[0] + W / 2, rows[r + 1] + h)
    ax.text(COLS[0] + W + 0.08, rows[2] + h / 2 + 0.1, "冻结", color=CORAL, fontsize=9, fontweight="bold")
    save(fig, "selection-flow.png")


# ---------- 第八节 ----------

def shares(eigs: list[float]) -> list[float]:
    pos = [max(e, 0.0) for e in eigs]
    total = sum(pos)
    out, acc = [], 0.0
    for e in pos:
        acc += e / total
        out.append(acc)
    return out


def pca_cumulative(s1: dict) -> None:
    series = [
        ("因子值（344 列）", GOLD, shares(s1["feature_pca"]["all"]["eigenvalues"])),
        ("IC 表 · 11:30", BLUE, shares(s1["ic_pca"]["morning"]["eigenvalues"])),
        ("IC 表 · 收盘", CORAL, shares(s1["ic_pca"]["close"]["eigenvalues"])),
    ]
    n = 40
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    styles = {GOLD: dict(lw=2.2), BLUE: dict(lw=3.2), CORAL: dict(lw=1.6, ls=(0, (5, 3)))}
    for name, color, cum in series:
        xs = list(range(1, n + 1))
        ax.plot(xs, [c * 100 for c in cum[:n]], color=color, label=name, **styles[color])
    for y in (80, 90):
        ax.axhline(y, color=INK, lw=0.7, ls=(0, (4, 3)), alpha=0.5)
        ax.text(n + 0.4, y, f"{y}%", va="center", color=MUTED, fontsize=9)
    f, m, c = (s[2] for s in series)
    ax.annotate(f"因子值：第 1 个成分占 {f[0]*100:.1f}%，\n要 39 个成分才到 90%", xy=(1, f[0] * 100), xytext=(9, 30),
                fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.annotate(f"IC 表：第 1 个成分就占 {m[0]*100:.1f}%（11:30）/ {c[0]*100:.1f}%（收盘），\n4–5 个成分到 90%",
                xy=(1, m[0] * 100), xytext=(6, 62), fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlim(0, n + 3)
    ax.set_ylim(0, 102)
    ax.set_xlabel("主成分个数")
    ax.set_ylabel("累计解释的方差占比（%）")
    ax.set_title("同样 344 列：因子值分散，IC 的日间波动高度集中", loc="left")
    ax.legend(loc="lower right", fontsize=9.5, title="两条 IC 线几乎重合", title_fontsize=9)
    fig.tight_layout()
    save(fig, "pca-cumulative.png")


def shap_concentration(s2: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    total = None
    for horizon in ("morning", "close"):
        label, color = HORIZON[horizon]
        system = s2["horizons"][horizon]["systems"]["base"]
        sh = sorted((g["share"] for g in system["groups"]), reverse=True)
        total = len(sh)
        cum, acc = [], 0.0
        for v in sh:
            acc += v
            cum.append(acc * 100)
        xs = list(range(1, total + 1))
        ax.plot(xs, cum, color=color, lw=2, label=f"{label}：等效约 {system['participation_groups']:.0f} 组")
        ax.scatter([1, 5], [cum[0], cum[4]], s=30, color=color, edgecolor=PAPER, zorder=4)
        ty = 16 if horizon == "morning" else 7
        ax.annotate(f"{label}：最大一组 {cum[0]:.0f}%，前 5 组 {cum[4]:.0f}%", xy=(5, cum[4]), xytext=(42, ty),
                    color=color, fontsize=9.5, fontweight="bold", arrowprops=dict(arrowstyle="-", color=color, lw=0.8))
    ax.plot([0, total], [0, 100], color=INK, lw=0.8, ls=(0, (4, 3)), alpha=0.5)
    ax.text(total * 0.66, 58, f"{total} 组完全平均", color=MUTED, fontsize=9)
    ax.set_xlim(0, total + 2)
    ax.set_ylim(0, 102)
    ax.set_xlabel("按份额从大到小排列的基础因子组（共 129 组）")
    ax.set_ylabel("累计 SHAP 份额（%）")
    ax.set_title("模型的归因分散在几十个基础因子上", loc="left")
    ax.legend(loc="lower right", fontsize=9.5)
    fig.tight_layout()
    save(fig, "shap-concentration.png")


def class_share(s1: dict, s2: dict) -> None:
    names = {"algorithm": "算法因子", "cancel_phase": "撤单相位", "depth_match": "深度匹配"}
    counts = s1["category_counts"]
    total = sum(counts.values())
    order = ["algorithm", "cancel_phase", "depth_match"]
    share = {h: {g["id"]: g["share"] for g in s2["horizons"][h]["systems"]["category"]["groups"]} for h in ("morning", "close")}
    rows = [
        ("列数占比", "#a39c90", [counts[k] / total for k in order]),
        ("SHAP 份额 · 11:30", BLUE, [share["morning"][k] for k in order]),
        ("SHAP 份额 · 收盘", CORAL, [share["close"][k] for k in order]),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    bar_h = 0.24
    for j, (lab, color, vals) in enumerate(rows):
        ys = [i + (j - 1) * (bar_h + 0.03) for i in range(len(order))]
        ax.barh(ys, [v * 100 for v in vals], height=bar_h, color=color, label=lab)
        for y, v in zip(ys, vals):
            ax.text(v * 100 + 0.8, y, f"{v*100:.1f}%", va="center", fontsize=9, color=INK)
    ax.set_yticks(range(len(order)), [f"{names[k]}（{counts[k]} 列）" for k in order])
    ax.invert_yaxis()
    ax.set_xlim(0, 90)
    ax.set_xlabel("占比（%）")
    ax.grid(axis="y", visible=False)
    ax.set_title("深度匹配只占 7% 的列，却拿到 21%–28% 的归因", loc="left")
    ax.legend(loc="lower right", fontsize=9.5)
    fig.tight_layout()
    save(fig, "class-share.png")


def comparison_flow() -> None:
    fig, ax = canvas(7.6, 7.1)
    box(ax, COLS[0], 5.75, 7.9, 1.25, "两侧固定不动",
        "10 套树及各自轮数 · 5 个种子 · 15 折 · 训练目标 R1 · 开发段日期\n与冻结基准完全相同；不重新搜索，也不重选轮数")
    h = 1.45
    box(ax, COLS[0], 3.55, W, h, "基准", "344 列\n已登记的 OOF 预测，直接复用")
    box(ax, COLS[1], 3.55, W, h, "新模型", "344 列 + 新因子列\n只换特征矩阵，重训一遍")
    box(ax, COLS[0], 0.55, W, 1.75, "逐日 L5 差", "308 个 OOF 日上，两个周期集成的\n全市场 L5，每天新减旧")
    box(ax, COLS[1], 0.55, W, 1.75, "判断", "报差值的均值、标准误、t 值；\n以 0.4–1.7 bp 的种子波动作噪声底", accent=True)
    left = COLS[0] + W * 0.35
    arrow(ax, [(left, 3.55), (left, 2.3)])
    wrap_down(ax, COLS[1] + W / 2, 3.55, COLS[0] + W * 0.7, 2.3)
    arrow(ax, [(COLS[0] + W, 1.425), (COLS[1], 1.425)], accent=True)
    save(fig, "comparison-flow.png")


def main() -> None:
    repo = Path(sys.argv[1]).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    abs_ev, abs_sha = load(repo, ABS_EVIDENCE)
    shap_ev, shap_sha = load(repo, SHAP_EVIDENCE)
    s1 = shap_ev["documents"]["s1.json"]["value"]
    s2 = shap_ev["documents"]["s2.json"]["value"]
    selection_curves(abs_ev)
    selection_flow()
    pca_cumulative(s1)
    shap_concentration(s2)
    class_share(s1, s2)
    comparison_flow()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    source = {
        "report_date": "2026-11-07",
        "generator": "scripts/build_model_line_figures_20261107.py",
        "research_repo_head": head,
        "inputs": {ABS_EVIDENCE: abs_sha, SHAP_EVIDENCE: shap_sha},
        "figures": sorted(p.name for p in OUT.glob("*.png")),
    }
    (OUT / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
