"""论文配图统一样式。

中文用 SimSun（宋体）、西文与数字用 Times New Roman，保证 LaTeX 与 Word 端均无方框；
统一调色板、字号、线宽与导出 DPI，所有图共用同一套视觉语言。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGURES = Path(__file__).resolve().parents[1] / "paper" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

# 主色板：低饱和、印刷友好、色盲可区分
PALETTE = {
    "navy": "#1F3B73",
    "blue": "#3E6FB0",
    "sky": "#7FB2E5",
    "teal": "#2E8B84",
    "green": "#5FA05A",
    "olive": "#9BAF3B",
    "gold": "#D8A22B",
    "orange": "#E07B39",
    "red": "#C0392B",
    "rose": "#D46A8C",
    "purple": "#7A5BA6",
    "gray": "#7F8C99",
    "lightgray": "#D5DBE1",
    "ink": "#1A2028",
}
CYCLE = [PALETTE[k] for k in ("navy", "orange", "teal", "red", "purple", "gold", "sky", "green")]

# 四问/四场景的固定语义色，全文一致
SCENARIO_COLORS = {
    "Q1": PALETTE["navy"],
    "Q2": PALETTE["orange"],
    "Q3": PALETTE["teal"],
    "Q4-2": PALETTE["red"],
    "Q4-3": PALETTE["purple"],
    "legacy": PALETTE["gray"],
}


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["SimSun", "Times New Roman", "DejaVu Sans"],
            "font.serif": ["SimSun", "Times New Roman"],
            "axes.unicode_minus": False,
            "font.size": 11,
            "axes.titlesize": 12.5,
            "axes.labelsize": 11.5,
            "axes.titleweight": "bold",
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.linewidth": 0.9,
            "axes.edgecolor": PALETTE["ink"],
            "axes.labelcolor": PALETTE["ink"],
            "text.color": PALETTE["ink"],
            "xtick.color": PALETTE["ink"],
            "ytick.color": PALETTE["ink"],
            "axes.grid": True,
            "grid.color": PALETTE["lightgray"],
            "grid.linewidth": 0.6,
            "grid.alpha": 0.75,
            "axes.axisbelow": True,
            "figure.dpi": 130,
            "savefig.dpi": 330,
            "savefig.bbox": "tight",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 1.8,
            "lines.markersize": 4.5,
        }
    )


def panel_label(ax, text: str, dx: float = -0.085, dy: float = 1.06) -> None:
    """在子图左上角标注 (a)/(b)/(c)/(d)。"""
    ax.text(dx, dy, text, transform=ax.transAxes, fontsize=12.5, fontweight="bold",
            va="bottom", ha="left", color=PALETTE["ink"])


def save(fig, name: str, *, pdf: bool = True) -> Path:
    """保存 PNG（论文插图）与可选 PDF（矢量备份），返回 PNG 路径。"""
    png = FIGURES / f"{name}.png"
    fig.savefig(png)
    if pdf:
        fig.savefig(FIGURES / f"{name}.pdf")
    plt.close(fig)
    return png


def wan(value: float) -> float:
    """元 → 万元。"""
    return value / 1e4
