from __future__ import annotations
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "paper" / "figures"
INK = "#1A2028"
NAVY = "#1F3B73"
BANDS = [
    ("数据层", "#E8F0FA", "#3E6FB0"),
    ("统一内核", "#E6F4F1", "#2E8B84"),
    ("四问模型", "#FBF0DE", "#D8A22B"),
    ("求解算法", "#EDE9F6", "#7A5BA6"),
    ("验证交付", "#EAF3E8", "#5FA05A"),
]
CONTENT = [
    ["附件 1\n典型日电价·负载·光伏", "附件 2\n全年 144 时段负载与光伏实际值",
     "附件 3\n每日 4 次未来 24 h 光伏预报", "附件 4\n全年 144 时段实时电价"],
    ["母线能量平衡\n式 (1)", "储能 SOC 状态转移\n$S_t=S_{t-1}+\\eta_c C_t-H_t/\\eta_d$\n式 (2) 核心状态方程",
     "容量与功率限值\n式 (3) (4)", "购电非负与弃光上界\n式 (5) (6)"],
    ["问题一\n确定性日前 LP\n首末 SOC 闭环",
     "问题二\n因果预测·报童定价\n$5$ 倍电价 $\\Rightarrow$ $0.2$ 分位点\n实时储能反馈",
     "问题三\n四时刻滚动优化\n两种结算口径\n分别重优化",
     "问题四\n波动电价重算\nperfect / causal\n价格信息边界"],
    ["HiGHS 线性规划\n原始—对偶容差 $10^{-9}$", "三层词典序目标\n费用 → 吞吐量 → 弃光",
     "滚动在线选型\n仅用已发生误差", "因果偏差校正\n分发布节点分位数"],
    ["物理残差校验\n平衡/SOC 残差 $<10^{-12}$", "未来信息泄漏\nmutation 测试",
     "结算口径单元测试\n与 legacy 回归", "官方 result1–4\nExcel 回填与回读"],
]
def main() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["SimSun", "Times New Roman", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "mathtext.fontset": "dejavusans",
    })
    band_h = 1.0
    gap = 0.34
    n_bands = len(BANDS)
    fig_h = n_bands * band_h + (n_bands - 1) * gap + 0.5
    fig, ax = plt.subplots(figsize=(13.2, fig_h * 1.35))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    left = 1.42
    box_w = 2.79
    box_gap = 0.155
    for b, (band_name, fill, edge) in enumerate(BANDS):
        y = fig_h - 0.25 - (b + 1) * band_h - b * gap
        ax.add_patch(FancyBboxPatch(
            (0.10, y), 13.00, band_h,
            boxstyle="round,pad=0.008,rounding_size=0.10",
            facecolor=fill, edgecolor=edge, linewidth=1.5, alpha=0.55, zorder=1,
        ))
        ax.text(0.72, y + band_h / 2, band_name, ha="center", va="center",
                fontsize=11.0, fontweight="bold", color=edge, rotation=90, zorder=3)
        for j, text in enumerate(CONTENT[b]):
            x = left + j * (box_w + box_gap)
            emphasized = b == 1 and j == 1
            ax.add_patch(FancyBboxPatch(
                (x, y + 0.09), box_w, band_h - 0.18,
                boxstyle="round,pad=0.01,rounding_size=0.09",
                facecolor="white", edgecolor=edge,
                linewidth=2.0 if emphasized else 1.1, zorder=2,
            ))
            ax.text(x + box_w / 2, y + band_h / 2, text, ha="center", va="center",
                    fontsize=9.8 if emphasized else 10.2, color=INK, zorder=3, linespacing=1.55)
    for b in range(n_bands - 1):
        y_top = fig_h - 0.25 - (b + 1) * band_h - b * gap
        y_bottom = y_top - gap
        for j in range(4):
            x = left + j * (box_w + box_gap) + box_w / 2
            ax.add_patch(FancyArrowPatch(
                (x, y_top), (x, y_bottom + 0.001),
                arrowstyle="-|>", mutation_scale=13,
                linewidth=1.5, color=NAVY, alpha=0.75, zorder=4,
                shrinkA=0, shrinkB=0,
            ))
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "technical_route.png", dpi=320, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGS / "technical_route.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[fig] technical_route 完成 →", FIGS / "technical_route.png")
if __name__ == "__main__":
    main()
