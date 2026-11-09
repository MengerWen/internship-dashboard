"""生成 2026-11-07 模型线汇报的插图。

数据只读研究仓库已提交的证据和报告，来源及 SHA-256 写入 source.json。

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
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content" / "assets" / "model-line-2026-11-07"

ABS_EVIDENCE = "reports/2026-11/2026-11-08-model-szse344-absolute-returns-evidence.json"
SHAP_EVIDENCE = "reports/2026-11/2026-11-09-model-szse344-collinearity-shap-evidence.json"
U7_EVIDENCE = "reports/2026-11/2026-11-03-model-szse344-u7-evidence"
V4_RESULTS = (
    "reports/2026-11/2026-11-04-model-szse344-learning-rates-v4-rerun-evidence"
    "/final-acceptance-and-unit-summary.json"
)
V5_REPLAY = "reports/2026-11/2026-11-05-model-szse344-stopping-v5-evidence/replay.json"
STAGE1_RESULTS = "reports/2026-11/2026-11-05-model-szse344-b6-stage1-evidence/stage1-complete-source.json"
METHOD_REFERENCES = (
    "decisions/2026-11-03-szse344-model-design.md",
    "reports/2026-11/2026-11-05-model-szse344-b6-stage1.md",
    "reports/2026-11/2026-11-06-model-szse344-b6-w5-resume2.md",
    "reports/2026-11/2026-11-08-model-szse344-baseline-registration.md",
)

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


def sample_splits() -> None:
    fig, ax = canvas(8.2, 4.15)
    ax.text(0.1, 3.83, "308 个 OOF 日来自 425 日开发段内部", fontsize=14, fontweight="bold", color=INK)

    spans = (
        (0.1, 1.93, "前 117 日", "初始训练", SOFT, INK),
        (1.93, 4.85, "后 308 日", "逐折生成 OOF", BLUE, "white"),
        (5.1, 6.66, "176 日", "已看 Test", "#ded8cb", INK),
        (6.66, 7.9, "82 日", "未看 Test", "#fbe9e4", INK),
    )
    ax.text(2.47, 3.28, "Development · 425 日", ha="center", fontweight="bold", color=INK)
    ax.text(6.5, 3.28, "冻结后评价", ha="center", fontweight="bold", color=INK)
    for left, right, count, label, fill, text in spans:
        ax.add_patch(Rectangle((left, 2.57), right - left, 0.55, facecolor=fill, edgecolor=PAPER))
        ax.text((left + right) / 2, 2.85, f"{count}  {label}", color=text, ha="center", va="center", fontsize=9.3)
    ax.vlines(4.97, 2.46, 3.18, color=CORAL, linestyles="--", linewidth=1.4)
    ax.text(4.97, 2.36, "冻结", color=CORAL, ha="center", va="top", fontsize=9.5)

    ax.text(0.1, 2.06, "扩张训练示意", fontweight="bold", color=INK)
    for y, label, stop in ((1.66, "第 1 折", 1.93), (1.17, "第 2 折", 2.44), (0.68, "第 15 折", 4.34)):
        ax.text(0.1, y, label, va="center", color=INK, fontsize=9.5)
        ax.barh(y, stop - 0.95, left=0.95, height=0.26, color=SOFT, zorder=1)
        ax.barh(y, 0.51, left=stop, height=0.26, color=BLUE, zorder=1)
    ax.scatter([5.23, 5.23], [1.56, 1.05], marker="s", s=63, color=[SOFT, BLUE])
    ax.text(5.39, 1.56, "只用之前的日期训练", va="center", color=INK, fontsize=9.5)
    ax.text(5.39, 1.05, "预测当月，拼入 OOF", va="center", color=INK, fontsize=9.5)
    ax.text(0.1, 0.17, "只示意第 1、2、15 折。横向长度不按交易日数等比绘制。", color=MUTED, fontsize=9)
    save(fig, "sample-splits-oof.png")


def trade_timeline() -> None:
    fig, axes = plt.subplots(
        1, 3, figsize=(8.2, 3.45), sharey=True, gridspec_kw={"width_ratios": [2.8, 1.15, 1.15]}
    )
    fig.subplots_adjust(left=0.07, right=0.96, top=0.74, bottom=0.29, wspace=0.19)
    fig.text(0.07, 0.9, "09:35 决策，之后按各窗口计算标签", color=INK, fontsize=14, fontweight="bold")
    fig.text(0.07, 0.08, "分段时间轴。横线两端是窗口边界，窗口不含右端时刻。", color=MUTED, fontsize=9)
    morning, noon, close = axes
    ticks = (([0, 5, 6, 15, 16], ["09:30", "09:35", "09:36", "09:45", "09:46"]),
             ([0, 30], ["11:00", "11:30"]), ([0, 30], ["14:27", "14:57"]))
    for ax, (positions, labels) in zip(axes, ticks):
        ax.set_facecolor(PAPER)
        ax.set_ylim(-0.4, 2.75)
        ax.set_yticks([])
        ax.set_xticks(positions, labels, fontsize=9)
        ax.tick_params(axis="x", length=3)
        ax.spines["left"].set_visible(False)
        ax.grid(False)
    morning.set_xlim(-0.7, 16.8)
    morning.set_xticklabels(["09:30", "", "", "", ""])
    morning.text(5.5, -0.78, "09:35–09:36", ha="center", va="top", color=INK, fontsize=8.7)
    morning.text(15.5, -0.78, "09:45–09:46", ha="center", va="top", color=INK, fontsize=8.7)
    morning.vlines(5, -0.35, 2.45, color=CORAL, linestyle="--", linewidth=1.35)
    morning.text(5.2, 2.36, "09:35 选股", color=CORAL, fontweight="bold", va="top")
    morning.barh(1.63, 5, left=0, height=0.25, color=SOFT)
    morning.text(0, 1.94, "可见因子", color=INK, fontsize=9.5)
    morning.barh(0.73, 1, left=5, height=0.25, color=GOLD)
    morning.text(6.35, 0.38, "入场 · 卖一 TWAP", ha="left", va="top", color=INK, fontsize=9)
    morning.barh(0.73, 1, left=15, height=0.25, color=MUTED)
    morning.text(15.4, 1.03, "10 分钟对照\n买一 TWAP", ha="right", va="bottom", color=INK, fontsize=9)
    for ax, title, color in ((noon, "午间退出", BLUE), (close, "收盘退出", CORAL)):
        ax.set_xlim(-4, 34)
        ax.barh(0.73, 30, left=0, height=0.25, color=color)
        ax.text(15, 1.33, f"{title}\n买一 TWAP", ha="center", va="bottom", color=INK, fontsize=9.5)
        ax.plot(
            [-0.055, 0.035], [-0.04, 0.04], transform=ax.transAxes,
            clip_on=False, color=MUTED, linewidth=1.1,
        )
    save(fig, "trade-timeline.png")


def search_throughput(resource: dict, stops: dict) -> None:
    assert stops["common_stops_bitwise_equal"]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.5), sharey=True)
    fig.subplots_adjust(left=0.19, right=0.94, top=0.72, bottom=0.29, wspace=0.28)
    ratio = resource["throughput_ratio"]
    fig.text(0.07, 0.91, f"独立进程评价后，模型轮吞吐提高到 {ratio:.2f} 倍", color=INK, fontsize=14, fontweight="bold")
    jobs = [
        ("全程有效核", "核", "effective_cores", "effective_core_ratio", 17.5),
        ("模型轮吞吐", "模型·轮次 / 秒", "model_rounds_per_second", "throughput_ratio", 50),
    ]
    for ax, (title, unit, field, ratio, bound) in zip(axes, jobs):
        new = resource[field]
        values = [new / resource[ratio], new]
        ax.set_facecolor(PAPER)
        ax.barh([1, 0], values, height=0.48, color=[SOFT, BLUE], zorder=3)
        ax.set_title(title, loc="left", color=INK, pad=12)
        ax.set_xlim(0, bound)
        ax.set_xlabel(unit, fontsize=9)
        ax.set_yticks([1, 0], ["B5b 试跑", "U7 复测"], fontsize=9.5)
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="y", visible=False)
        ax.spines["left"].set_visible(False)
        for y, value in zip([1, 0], values):
            ax.text(value + bound * 0.025, y, f"{value:.2f}", va="center", color=INK, fontsize=10)
    total = stops["new_completed"] + resource["censored"]
    fig.text(
        0.07, 0.12,
        f"同一 {total} 单元：B5b 完成 {stops['old_completed']}/{total}，U7 完成 {stops['new_completed']}/{total}。",
        color=INK, fontsize=9.5,
    )
    fig.text(
        0.07, 0.055, f"重叠的 {stops['comparisons']} 个单元，停止轮次和原因一致。", color=MUTED, fontsize=9.5,
    )
    save(fig, "search-throughput.png")


def learning_rate_results(v4: dict) -> None:
    rates = (0.01, 0.03, 0.05, 0.10)
    colors = {"R1": BLUE, "R3": GOLD, "R5": CORAL}
    lines = {"S": "-", "D": "--"}
    units = {
        (row["horizon"], row["target"], row["tree"], row["rate"]): row["best"]["L:0.2"]["metrics"]
        for row in v4["unit_summary"] if row["target"] in colors
    }
    assert len(units) == 48 and all(row["days"] == 104 for row in units.values())
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.2), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.13, right=0.96, top=0.74, bottom=0.28, wspace=0.13)
    fig.text(0.065, 0.91, "V4 实测：同一目标、同一套树换四档学习率",
             color=INK, fontsize=14, fontweight="bold")
    for ax, (horizon, (label, _)) in zip(axes, HORIZON.items()):
        ax.set_title(label, loc="left", color=INK)
        ax.set_facecolor(PAPER)
        ax.axhline(0, linewidth=0.8, color=MUTED, zorder=1)
        for target, color in colors.items():
            for tree, line in lines.items():
                y = [units[horizon, target, tree, rate]["mean_bp"] for rate in rates]
                ax.plot(rates, y, color=color, linestyle=line, marker="o", markersize=3.6, linewidth=1.5)
        ax.set_xticks(rates, [f"{rate:.2f}" for rate in rates])
        ax.set_xlabel("学习率", fontsize=9.5)
    axes[0].set_ylabel("最佳超额 L20（bp）", fontsize=9.5)
    handles = [Line2D([], [], marker="o", linestyle="none", color=color, label=target)
               for target, color in colors.items()]
    handles.extend(Line2D([], [], linestyle=style, color=MUTED, label=label)
                   for style, label in (("-", "浅树"), ("--", "深树")))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.1), ncol=5, fontsize=9)
    fig.text(0.065, 0.052, "每个点是一次独立试跑的最佳检查点。5 折、104 个 OOF 日，仅画回归试验。",
             color=MUTED, fontsize=9)
    save(fig, "learning-rate-v4-results.png")


def stopping_replay_results(replay: dict) -> None:
    units = [row for row in replay["candidates"] if row["rate"] == 0.1 and row["k"] == 0.5]
    summary = replay["summary"]["primary_lr_0.10"]["k=0.5"]
    assert len(units) == summary["units"] == 14 and not any(row["censored"] for row in units)
    fig, ax = plt.subplots(figsize=(8.2, 3.75))
    fig.subplots_adjust(left=0.14, right=0.96, top=0.77, bottom=0.28)
    fig.text(0.065, 0.91, "V5 回放：少跑多少轮，损失多少最佳 L20",
             color=INK, fontsize=14, fontweight="bold")
    ax.set_facecolor(PAPER)
    for horizon, (label, color) in HORIZON.items():
        rows = [row for row in units if row["horizon"] == horizon]
        ax.scatter([row["rounds_saved_fraction"] * 100 for row in rows],
                   [row["lanes"]["L:0.2"]["loss"]["mean_bp"] for row in rows],
                   label=label, color=color, s=43, alpha=0.75, edgecolors=PAPER, linewidths=0.6, zorder=3)
    loss = summary["lanes"]["L:0.2"]["mean_bp"]["max_loss"]
    saved = summary["pooled_rounds_saved_fraction"] * 100
    ax.text(0.04, 0.92, f"合计少跑 {saved:.2f}% 的轮数\n最佳 L20 最大损失 {loss:.2f} bp",
            transform=ax.transAxes, ha="left", va="top", color=INK, fontsize=9.5)
    ax.set_xlim(-2, 52)
    ax.set_ylim(-0.032, 0.36)
    ax.set_xlabel("相对原停止规则节省的轮数（%）", fontsize=9.5)
    ax.set_ylabel("最佳超额 L20 损失（bp）", fontsize=9.5)
    ax.legend(loc="upper right", fontsize=9)
    fig.text(0.065, 0.05, "学习率 0.10、门槛 0.5 倍标准误。14 个单元按已有检查点回放，相同坐标的点重叠。",
             color=MUTED, fontsize=9)
    save(fig, "stopping-v5-replay.png")


def stage1_regression_results(stage1: dict) -> None:
    targets = ("R1", "R2", "R3", "R4", "R5")
    methods = stage1["summary"]["methods"]
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.05), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.12, right=0.96, top=0.74, bottom=0.23, wspace=0.16)
    fig.text(0.065, 0.91, "B6 第一段：两个周期的回归 L5 均由 R1 领先",
             color=INK, fontsize=14, fontweight="bold")
    for ax, (horizon, (label, color)) in zip(axes, HORIZON.items()):
        ax.set_title(label, loc="left", color=INK)
        ax.set_facecolor(PAPER)
        ax.axvline(0, color=MUTED, linestyle="--", linewidth=0.8)
        for y, target in enumerate(targets):
            rows = [row for row in methods if row["horizon"] == horizon and row["target_id"] == target]
            values = [row["lanes"]["L:0.05"]["mean_bp"] for row in rows]
            assert len({row["history_id"] for row in rows}) == 7
            full = next(row["lanes"]["L:0.05"]["mean_bp"] for row in rows if row["history_id"] == "full_no_decay")
            ink = color if target == "R1" else MUTED
            ax.scatter(values, [y] * len(values), color=ink, alpha=0.64, s=24, linewidths=0, zorder=3)
            ax.scatter(full, y, color=ink, edgecolors=PAPER, marker="D", s=53, zorder=4)
            if target == "R1":
                ax.text(full, y - 0.25, f"{full:.2f}", ha="center", va="bottom",
                        fontsize=9, color=color, fontweight="bold")
        ax.set_xlim(-6, 27)
        ax.set_ylim(4.53, -0.63)
        ax.set_yticks(range(len(targets)), targets)
        ax.set_xlabel("最佳超额 L5（bp）", fontsize=9.5)
        ax.grid(axis="y", visible=False)
    fig.text(0.065, 0.06, "每个目标试 7 个历史窗口。◆ 全历史不衰减。5 折、104 个 OOF 日，仅回归方法。",
             color=MUTED, fontsize=9)
    save(fig, "b6-stage1-regression-results.png")


def two_stage_search() -> None:
    fig, ax = canvas(8.2, 3.8)
    ax.text(0.1, 3.48, "先缩方法，再把全折预算给树", color=INK, fontsize=14, fontweight="bold")
    box(
        ax, 0.08, 0.98, 3.35, 1.97, "第一段 · 比方法",
        "63 种方法 · 5 折 · 104 个 OOF 日\n两个周期的回归 L5 均由 R1 领先\n全历史 L5：24.26 / 21.65 bp\n预算每周期只容 1 个回归名额",
    )
    box(
        ax, 4.57, 0.98, 3.35, 1.97, "第二段 · 比树",
        "每周期 31 套树 · 15 折\n308 个 OOF 日，按检查点减半\n保存各树已完成的检查点，\n供下一节按 L5 与 Sharpe 选优",
    )
    arrow(ax, [(3.43, 1.79), (4.57, 1.79)], accent=True)
    ax.text(4, 2.06, "R1\n全历史", ha="center", color=CORAL, fontsize=9.5, fontweight="bold")
    ax.text(0.1, 0.35, "第一段比较目标和历史窗口。进入第二段后固定方法，再扩大树配置和折数。", color=MUTED, fontsize=9.5)
    save(fig, "two-stage-search.png")


def return_basis_recheck(abs_ev: dict) -> None:
    audit = abs_ev["d18"]
    checkpoint_rows = {(row["horizon"], row["tree_id"]): row["curve"] for row in audit["checkpoints"]}
    fig, (flow, chart) = plt.subplots(
        1, 2, figsize=(8.2, 4.5), gridspec_kw={"width_ratios": [1, 1.28]}
    )
    fig.subplots_adjust(left=0.05, right=0.95, top=0.8, bottom=0.23, wspace=0.33)
    fig.text(0.05, 0.91, "同一批预测重算收益，再复核 Sharpe 门槛", color=INK, fontsize=14, fontweight="bold")
    flow.set_xlim(0, 3.6)
    flow.set_ylim(0, 4.1)
    flow.axis("off")
    box(flow, 0.1, 3.13, 3.4, 0.91, "冻结预测", "相同成员、轮数、种子")
    box(flow, 0.1, 1.84, 3.4, 0.92, "D19 · 超额 L5", "纯多收益 − 同期中间价基准")
    box(flow, 0.1, 0.45, 3.4, 1.0, "D20 · 绝对 L5", "按对手价计算纯多收益", accent=True)
    arrow(flow, [(0.1, 3.52), (0.025, 3.52), (0.025, 2.26), (0.1, 2.26)])
    arrow(flow, [(3.5, 3.52), (3.58, 3.52), (3.58, 0.93), (3.5, 0.93)], accent=True)

    chart.set_title("10 个入选检查点 · 配对核对", loc="left", color=INK, pad=9)
    chart.set_facecolor(PAPER)
    chart.axvline(audit["threshold"], color=MUTED, linestyle="--", linewidth=1)
    for i, row in enumerate(audit["selected"]):
        points = checkpoint_rows[row["horizon"], row["tree_id"]]
        old = next(point["old_sharpe"] for point in points if point["iteration"] == row["iteration"])
        new = row["sharpe"]
        y = 10 - i - (1 if i >= 5 else 0)
        chart.plot([old, new], [y, y], color=SOFT, linewidth=1.5)
        chart.scatter(old, y, s=25, facecolors=PAPER, edgecolors=MUTED, zorder=3)
        chart.scatter(new, y, s=26, color=HORIZON[row["horizon"]][1], zorder=4)
    chart.set_ylim(-0.55, 10.7)
    chart.set_xlim(2.8, 5.65)
    chart.set_yticks([8, 2], ["11:30", "收盘"], fontsize=9)
    chart.set_xticks([3, 3.5, 4, 4.5, 5, 5.5])
    chart.set_xlabel("年化 Sharpe", fontsize=9.5)
    chart.grid(axis="y", visible=False)
    chart.spines["left"].set_visible(False)
    chart.tick_params(axis="y", length=0)
    fig.text(0.5, 0.089, "○ 超额口径   ● 绝对口径   虚线 = 3", color=MUTED, fontsize=9)
    count = sum(len(row["curve"]) for row in audit["checkpoints"])
    assert audit["unchanged"]
    fig.text(0.05, 0.045, f"另复核全部 {count} 个检查点，成员和固定轮数沿用。", color=INK, fontsize=9.5)
    save(fig, "return-basis-recheck.png")


def l5_metric(summary: dict) -> dict:
    metric = next(
        row for row in summary["metrics"] if (row["strategy"], row["subset"], row["q"]) == ("L", "all", 0.05)
    )
    assert metric["return_basis"] == "absolute" and metric["status"] == "complete"
    return metric


def l5_test_distribution(abs_ev: dict) -> None:
    groups = {(row["stage"], row["horizon"]): row for row in abs_ev["evaluation"]}
    stages = (
        ("development", "开发 OOF", BLUE, "o"),
        ("seen", "已看 Test", GOLD, "^"),
        ("unseen", "未看 Test", CORAL, "s"),
    )
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.15), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.13, right=0.96, top=0.74, bottom=0.29, wspace=0.14)
    fig.text(0.065, 0.91, "未看段两个周期的单模型 L5 都低于零", color=INK, fontsize=14, fontweight="bold")
    for ax, (horizon, (label, _)) in zip(axes, HORIZON.items()):
        ax.set_facecolor(PAPER)
        ax.set_title(label, loc="left", color=INK)
        ax.axvline(0, color=MUTED, linestyle="--", linewidth=1, zorder=2)
        ax.axhline(0, color=MUTED, linestyle="--", linewidth=1, zorder=2)
        for stage, _, color, marker in stages:
            group = groups[stage, horizon]
            models = [l5_metric(model) for model in group["models"]]
            ensemble = l5_metric(group["ensemble"])
            assert len({(row["tree_id"], row["seed"]) for row in group["models"]}) == len(models) == 25
            assert stage != "unseen" or all(row["mean_bp"] < 0 for row in models)
            ax.scatter([row["mean_bp"] for row in models], [row["sharpe"] for row in models],
                       color=color, marker=marker, alpha=0.46, s=20, linewidths=0, zorder=3)
            ax.scatter(ensemble["mean_bp"], ensemble["sharpe"],
                       color=color, edgecolors=INK, marker="D", s=41, linewidths=0.75, zorder=4)
            ax.annotate(
                f"{ensemble['mean_bp']:+.2f}",
                (ensemble["mean_bp"], ensemble["sharpe"]),
                xytext=(-6, 9), textcoords="offset points", ha="right", fontsize=8.2, color=INK,
            )
        ax.set_ylim(-2.65, 6.1)
        ax.set_xlim(-30, 44)
        ax.set_xticks([-20, 0, 20, 40])
        ax.set_xlabel("全市场绝对 L5（bp）", fontsize=9.2)
    axes[0].set_ylabel("年化 Sharpe", fontsize=9.5)
    handles = [
        Line2D([], [], marker=marker, color=color, linestyle="none",
               label=f"{label} · {groups[stage, 'morning']['days']} 日")
        for stage, label, color, marker in stages
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.095), ncol=3, fontsize=9)
    fig.text(0.065, 0.05, "每组 25 个单模型。描边菱形为集成。横纵坐标均为原始统计值，重叠点保留。",
             color=MUTED, fontsize=9)
    save(fig, "l5-test-distribution.png")


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
    resource_path = f"{U7_EVIDENCE}/resource-summary.json"
    stops_path = f"{U7_EVIDENCE}/common-stops.json"
    resource, resource_sha = load(repo, resource_path)
    stops, stops_sha = load(repo, stops_path)
    v4, v4_sha = load(repo, V4_RESULTS)
    v5, v5_sha = load(repo, V5_REPLAY)
    stage1, stage1_sha = load(repo, STAGE1_RESULTS)
    s1 = shap_ev["documents"]["s1.json"]["value"]
    s2 = shap_ev["documents"]["s2.json"]["value"]
    sample_splits()
    trade_timeline()
    search_throughput(resource, stops)
    learning_rate_results(v4)
    stopping_replay_results(v5)
    stage1_regression_results(stage1)
    two_stage_search()
    selection_curves(abs_ev)
    selection_flow()
    return_basis_recheck(abs_ev)
    l5_test_distribution(abs_ev)
    pca_cumulative(s1)
    shap_concentration(s2)
    class_share(s1, s2)
    comparison_flow()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    source = {
        "report_date": "2026-11-07",
        "generator": "scripts/build_model_line_figures_20261107.py",
        "research_repo_head": head,
        "inputs": {
            ABS_EVIDENCE: abs_sha,
            SHAP_EVIDENCE: shap_sha,
            resource_path: resource_sha,
            stops_path: stops_sha,
            V4_RESULTS: v4_sha,
            V5_REPLAY: v5_sha,
            STAGE1_RESULTS: stage1_sha,
            **{path: hashlib.sha256((repo / path).read_bytes()).hexdigest() for path in METHOD_REFERENCES},
        },
        "figures": sorted(p.name for p in OUT.glob("*.png")),
    }
    (OUT / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
