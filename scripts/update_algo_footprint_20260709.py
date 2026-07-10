from __future__ import annotations

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ALGOBENCH = Path(r"D:\MG\！Internship\26 Summer\❗思瑞投资\因子\algobench")
ASSET_DIR = ROOT / "site" / "assets" / "algo-footprint-2026-07-09"


def configure_chinese_font() -> None:
    preferred = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    installed = {font.name for font in fm.fontManager.ttflist}
    selected = next((name for name in preferred if name in installed), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [selected, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False


def box(ax: plt.Axes, x: float, y: float, w: float, h: float, text: str, color: str, size: float = 13) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.008",
        linewidth=1.6,
        edgecolor="#333333",
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, linespacing=1.2)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.0,
            color="#8a8a8a",
            shrinkA=2,
            shrinkB=2,
        )
    )


def draw_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(13.64, 7.87))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("给因子做体检的 5 层流水线", fontsize=20, pad=16)

    input_x, input_w, input_h = 0.035, 0.25, 0.14
    input_ys = [0.73, 0.46, 0.19]
    input_labels = [
        "参照物 Anchors\n量化席位 / 融券 /\n回购 / 融资",
        "因子登记表\n类别 / 方向 / 所用特征",
        "因子面板\n每天的股票日因子值",
    ]
    for y, label in zip(input_ys, input_labels):
        box(ax, input_x, y, input_w, input_h, label, "#dce8f5", 13)

    layer_x, layer_w, layer_h = 0.40, 0.31, 0.115
    layer_ys = [0.77, 0.615, 0.46, 0.305, 0.15]
    layer_labels = [
        "L0 剥离流动性\n控制回归 + 残差",
        "L1 选择性矩阵\n匹配对照 + 聚类 bootstrap",
        "L2 事件检验\n前后差 + DID",
        "L3 时间分布指纹\n寿命 / 到达间隔 + 置换检验",
        "L4 稳定性 + 冗余 + 增量",
    ]
    for y, label in zip(layer_ys, layer_labels):
        box(ax, layer_x, y, layer_w, layer_h, label, "#f3cbb5", 12.5)

    report_x, report_y, report_w, report_h = 0.79, 0.38, 0.17, 0.22
    box(ax, report_x, report_y, report_w, report_h, "体检报告\nScorecard\n每因子 A / B / C / D\n+ caveats", "#d8ead1", 13)

    registry_point = (input_x + input_w, input_ys[1] + input_h / 2)
    for y in layer_ys:
        arrow(ax, registry_point, (layer_x, y + layer_h / 2))
    arrow(ax, (input_x + input_w, input_ys[0] + input_h / 2), (layer_x, layer_ys[1] + layer_h / 2))
    arrow(ax, (input_x + input_w, input_ys[2] + input_h / 2), (layer_x, layer_ys[0] + layer_h / 2))
    for y in layer_ys:
        arrow(ax, (layer_x + layer_w, y + layer_h / 2), (report_x, report_y + report_h / 2))

    fig.tight_layout()
    fig.savefig(ASSET_DIR / "pipeline_5layers.png", dpi=100, bbox_inches="tight")
    plt.close(fig)


def draw_anchor_counts() -> None:
    path = ALGOBENCH / "outputs" / "anchors" / "anchor_stock_day.parquet"
    day = pd.read_parquet(path, columns=["date", "anchor_active", "anchor_passive", "anchor_noise"])
    labels = ["主动 active\n量化 / T0", "被动 passive\n回购 / 执行", "噪音 noise\n散户 / 游资"]
    cols = ["anchor_active", "anchor_passive", "anchor_noise"]
    values = [int(pd.to_numeric(day[col], errors="coerce").fillna(0).sum()) for col in cols]
    colors = ["#d4837c", "#77a9cc", "#f2c46d"]

    fig, ax = plt.subplots(figsize=(11.0, 4.3))
    bars = ax.bar(labels, values, color=colors, edgecolor="#333333", linewidth=1.2)
    ax.set_yscale("log")
    ax.set_ylim(15, max(values) * 1.85)
    ax.set_ylabel("命中的“股票 × 交易日”数（对数轴）", fontsize=12)
    ax.set_title(f"三类参照物的真实命中数（当前表覆盖 {day['date'].nunique()} 个日期）", fontsize=14, pad=10)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.05, f"{value}", ha="center", va="bottom", fontsize=14, weight="bold")
    ax.text(0.02, -0.28, "主动与噪音参照物仍明显稀缺，三条轴的统计功效不相等。", transform=ax.transAxes, color="#bf3d36", fontsize=11)
    ax.grid(axis="y", which="major", alpha=0.2)
    fig.tight_layout()
    fig.savefig(ASSET_DIR / "anchor_counts.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    configure_chinese_font()
    draw_pipeline()
    draw_anchor_counts()


if __name__ == "__main__":
    main()
