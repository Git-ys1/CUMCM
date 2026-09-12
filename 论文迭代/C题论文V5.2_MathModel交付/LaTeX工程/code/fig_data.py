from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from MathModel.solve.io_data import (
    DEFAULT_DATA_ROOT,
    DT_HOURS,
    hourly_to_ten_min,
    read_attachment1,
    read_attachment2,
    read_attachment3,
    read_attachment4,
)
from MathModel.solve.plot_style import PALETTE, apply_style, panel_label, save
apply_style()
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import TwoSlopeNorm
MONTH_EDGES = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
MONTH_LABELS = [f"{m}月" for m in range(1, 13)]
DAYS_PER_MONTH = np.diff(MONTH_EDGES)
def fig_data_overview(root: Path = DEFAULT_DATA_ROOT) -> None:
    day1 = read_attachment1(root)
    annual = read_attachment2(root)
    price = read_attachment4(root)
    fig = plt.figure(figsize=(13.6, 8.2))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.22)
    ax = fig.add_subplot(gs[0, 0])
    hours = (np.arange(144) + 1) / 6.0
    ax.plot(hours, day1.load_kw / 1e3, color=PALETTE["navy"], label="小区负载")
    ax.plot(hours, day1.pv_kw / 1e3, color=PALETTE["gold"], label="光伏发电预测")
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("功率 / MW")
    ax.set_title("典型日负载与光伏出力的错配")
    ax.set_xlim(0, 24)
    ax.set_xticks(range(0, 25, 4))
    ax2 = ax.twinx()
    ax2.plot(hours, day1.price, color=PALETTE["red"], linestyle="--", linewidth=1.5, label="外网电价")
    ax2.set_ylabel("电价 /（元·kWh$^{-1}$）", color=PALETTE["red"])
    ax2.tick_params(axis="y", colors=PALETTE["red"])
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    handles1, labels1 = ax.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(handles1 + handles2, labels1 + labels2, loc="upper left", ncol=1, fontsize=9)
    panel_label(ax, "(a)")
    for idx, (data, title, cmap, unit) in enumerate(
        [
            (annual.load_kw, "全年负载分布", "YlGnBu", "kW"),
            (annual.pv_kw, "全年光伏出力分布", "YlOrBr", "kW"),
            (price.price, "全年实时电价分布", "RdYlBu_r", "元/kWh"),
        ]
    ):
        ax = fig.add_subplot(gs[(1 + idx) // 2, (1 + idx) % 2])
        im = ax.imshow(
            data / (1e3 if unit == "kW" else 1),
            aspect="auto",
            cmap=cmap,
            interpolation="nearest",
            extent=[0, 24, 365, 1],
        )
        ax.set_xlabel("时刻 / h")
        ax.set_ylabel("日期（第 n 天）")
        ax.set_title(title)
        ax.set_xticks(range(0, 25, 4))
        ax.grid(False)
        cb = fig.colorbar(im, ax=ax, pad=0.02)
        cb.set_label("MW" if unit == "kW" else "元/kWh", fontsize=9)
        cb.ax.tick_params(labelsize=8.5)
        panel_label(ax, "(%s)" % "bcd"[idx])
    save(fig, "data_overview")
def fig_netload_season(root: Path = DEFAULT_DATA_ROOT) -> None:
    annual = read_attachment2(root)
    net = annual.load_kw - annual.pv_kw
    month_of_day = np.repeat(np.arange(12), DAYS_PER_MONTH)
    fig = plt.figure(figsize=(13.6, 4.4))
    gs = fig.add_gridspec(1, 3, wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    data = [net[month_of_day == m].ravel() / 1e3 for m in range(12)]
    bp = ax.boxplot(data, patch_artist=True, widths=0.62, showfliers=False,
                    medianprops=dict(color=PALETTE["ink"], linewidth=1.3),
                    whiskerprops=dict(color=PALETTE["gray"]),
                    capprops=dict(color=PALETTE["gray"]),
                    boxprops=dict(facecolor=PALETTE["sky"], edgecolor=PALETTE["navy"], linewidth=0.9))
    ax.axhline(0, color=PALETTE["red"], linewidth=1.1, linestyle="--")
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{m}" for m in range(1, 13)], fontsize=9)
    ax.set_xlabel("月份")
    ax.set_ylabel("净负荷 / MW")
    ax.set_title("净负荷的月度分布")
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    penetration = annual.pv_kw / np.maximum(annual.load_kw, 1e-9)
    data = [np.clip(penetration[month_of_day == m].ravel(), 0, 3) for m in range(12)]
    parts = ax.violinplot(data, showmedians=True, widths=0.85)
    for body in parts["bodies"]:
        body.set_facecolor(PALETTE["gold"])
        body.set_edgecolor(PALETTE["orange"])
        body.set_alpha(0.75)
    for key in ("cmedians", "cbars", "cmins", "cmaxes"):
        parts[key].set_color(PALETTE["ink"])
        parts[key].set_linewidth(1.1)
    ax.axhline(1.0, color=PALETTE["red"], linestyle="--", linewidth=1.1)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{m}" for m in range(1, 13)], fontsize=9)
    ax.set_xlabel("月份")
    ax.set_ylabel("光伏/负载 比值")
    ax.set_title("光伏渗透率的月度分布")
    ax.set_ylim(0, 3)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[0, 2])
    surplus_slots = (annual.pv_kw - annual.load_kw > 0).sum(axis=1)
    big_surplus = (annual.pv_kw - annual.load_kw > 5000).sum(axis=1)
    hours_surplus = np.array([surplus_slots[month_of_day == m].mean() * 10 / 60 for m in range(12)])
    hours_big = np.array([big_surplus[month_of_day == m].mean() * 10 / 60 for m in range(12)])
    x = np.arange(12)
    ax.bar(x - 0.2, hours_surplus, width=0.4, color=PALETTE["green"], label="光伏富余时段")
    ax.bar(x + 0.2, hours_big, width=0.4, color=PALETTE["red"], label="富余超 5000 kW 时段")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}" for m in range(1, 13)], fontsize=9)
    ax.set_xlabel("月份")
    ax.set_ylabel("日均时长 / h")
    ax.set_title("光伏富余的月度强度")
    ax.legend(fontsize=9)
    panel_label(ax, "(c)")
    save(fig, "netload_season")
def fig_forecast_diagnosis(root: Path = DEFAULT_DATA_ROOT) -> None:
    annual = read_attachment2(root)
    forecasts = read_attachment3(root)
    month_of_day = np.repeat(np.arange(12), DAYS_PER_MONTH)
    err = np.zeros_like(forecasts.hourly_kw)
    for node in range(4):
        for hour in range(24):
            target_slot = (node * 36 + (hour + 1) * 6 - 1) % 144
            target_day = np.arange(365) + (node * 36 + (hour + 1) * 6 - 1) // 144
            valid = target_day < 365
            err[valid, node, hour] = forecasts.hourly_kw[valid, node, hour] - annual.pv_kw[target_day[valid], target_slot]
    fig = plt.figure(figsize=(13.6, 4.6))
    gs = fig.add_gridspec(1, 3, wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    labels = ["0:00", "6:00", "12:00", "18:00"]
    colors = [PALETTE["navy"], PALETTE["orange"], PALETTE["teal"], PALETTE["purple"]]
    for n, (label, color) in enumerate(zip(labels, colors)):
        values = np.sort(np.abs(err[:, n, :].ravel()))
        values = np.maximum(values, 1e-3)
        share = np.arange(1, values.size + 1) / values.size
        step = max(1, values.size // 4000)
        ax.plot(values[::step], share[::step], color=color, linewidth=2.1, label=label)
        p95 = np.percentile(values, 95)
        ax.plot([p95], [0.95], marker="o", color=color, markersize=6,
                markeredgecolor="white", markeredgewidth=1.0, zorder=5)
    ax.axhline(0.95, color=PALETTE["gray"], linestyle=":", linewidth=1.0)
    ax.text(1.6, 0.955, "$P_{95}$", fontsize=9, color=PALETTE["gray"])
    ax.set_xscale("log")
    ax.set_xlim(1, 6000)
    ax.set_ylim(0, 1.0)
    ax.set_xlabel("绝对预报误差 / kW（对数轴）")
    ax.set_ylabel("经验累积分布 ECDF")
    ax.set_title("分发布时刻的预报误差累积分布")
    ax.legend(fontsize=9, loc="lower right", title="发布时刻", title_fontsize=9)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    mae = [np.mean(np.abs(err[month_of_day == m])) for m in range(12)]
    bias = [np.mean(err[month_of_day == m]) for m in range(12)]
    x = np.arange(12)
    ax.bar(x, mae, color=PALETTE["sky"], edgecolor=PALETTE["navy"], linewidth=0.7, label="MAE")
    ax.plot(x, bias, color=PALETTE["red"], marker="o", markersize=4.5, label="平均偏差")
    ax.axhline(0, color=PALETTE["ink"], linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}" for m in range(1, 13)], fontsize=9)
    ax.set_xlabel("月份")
    ax.set_ylabel("误差 / kW")
    ax.set_title("预报误差的月度演变")
    ax.legend(fontsize=9)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[0, 2])
    raw_step, raw_linear = [], []
    for d in range(365):
        for n in range(4):
            lo = n * 36
            hi = lo + 36
            actual = annual.pv_kw[d, lo:hi]
            raw_step.append(np.mean(np.abs(hourly_to_ten_min(forecasts.hourly_kw[d, n], "step")[:36] - actual)))
            raw_linear.append(np.mean(np.abs(hourly_to_ten_min(forecasts.hourly_kw[d, n], "linear")[:36] - actual)))
    mae_step, mae_linear = float(np.mean(raw_step)), float(np.mean(raw_linear))
    bars = ax.bar(["阶梯保持", "线性插值"], [mae_step, mae_linear],
                  color=[PALETTE["gray"], PALETTE["teal"]], width=0.5,
                  edgecolor=PALETTE["ink"], linewidth=0.8)
    for bar, value in zip(bars, [mae_step, mae_linear]):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.02, f"{value:.1f} kW",
                ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("执行块 MAE / kW")
    ax.set_title("小时预报降尺度方法的精度对比")
    ax.set_ylim(0, max(mae_step, mae_linear) * 1.25)
    panel_label(ax, "(c)")
    save(fig, "forecast_diagnosis")
    print(f"[fig] 降尺度执行块 MAE：阶梯={mae_step:.4f} kW，线性={mae_linear:.4f} kW")
def fig_correlation(root: Path = DEFAULT_DATA_ROOT) -> None:
    annual = read_attachment2(root)
    price = read_attachment4(root)
    load = annual.load_kw.ravel()
    pv = annual.pv_kw.ravel()
    net = load - pv
    p = price.price.ravel()
    slot_phase = np.tile(np.arange(144) / 144.0, 365)
    frame = {
        "小区负载": load, "光伏出力": pv, "净负荷": net,
        "实时电价": p, "日内相位": slot_phase,
    }
    keys = list(frame)
    matrix = np.corrcoef(np.stack([frame[k] for k in keys]))
    matrix = matrix / np.sqrt(np.outer(np.diag(matrix), np.diag(matrix)))
    fig = plt.figure(figsize=(13.0, 4.8))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.15], wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    im = ax.imshow(matrix, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(keys, rotation=32, ha="right", fontsize=9)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(keys, fontsize=9)
    for i in range(len(keys)):
        for j in range(len(keys)):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=9.5,
                    color="white" if abs(matrix[i, j]) > 0.55 else PALETTE["ink"])
    ax.grid(False)
    ax.set_title("关键变量的相关系数矩阵")
    cb = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.9)
    cb.set_label("Pearson 相关系数", fontsize=9)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    sample = np.random.default_rng(0).choice(load.size, size=min(50000, load.size), replace=False)
    hb = ax.hexbin(load[sample] / 1e3, net[sample] / 1e3, gridsize=48, cmap="viridis",
                   bins="log", mincnt=1, linewidths=0)
    ax.axhline(0, color=PALETTE["red"], linestyle="--", linewidth=1.2)
    ax.set_xlabel("小区负载 / MW")
    ax.set_ylabel("净负荷 / MW")
    ax.set_title("负载—净负荷联合分布（含零线）")
    cb = fig.colorbar(hb, ax=ax, pad=0.02, shrink=0.9)
    cb.set_label("时段数（对数）", fontsize=9)
    panel_label(ax, "(b)")
    save(fig, "correlation_structure")
def main() -> None:
    root = DEFAULT_DATA_ROOT
    fig_data_overview(root)
    fig_netload_season(root)
    fig_forecast_diagnosis(root)
    fig_correlation(root)
    print("[fig] 数据层配图完成 →", (Path(__file__).resolve().parents[1] / "paper" / "figures"))
if __name__ == "__main__":
    main()
