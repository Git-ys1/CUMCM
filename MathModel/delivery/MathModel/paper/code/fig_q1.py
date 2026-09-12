from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from MathModel.solve.io_data import DT_HOURS, read_attachment1
from MathModel.solve.plot_style import PALETTE, apply_style, panel_label, save
apply_style()
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
def main() -> None:
    frame = pd.read_csv(ROOT / "outputs" / "q1" / "solution.csv", encoding="utf-8-sig")
    day1 = read_attachment1()
    hours = frame["slot"].to_numpy() / 6.0
    fig = plt.figure(figsize=(13.6, 7.6))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.24)
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(hours, day1.load_kw / 1e3, color=PALETTE["navy"], linewidth=1.9, label="小区负载")
    ax.plot(hours, day1.pv_kw / 1e3, color=PALETTE["gold"], linewidth=1.9, label="光伏预测出力")
    ax.fill_between(hours, day1.pv_kw / 1e3, day1.load_kw / 1e3,
                    where=(day1.pv_kw < day1.load_kw), color=PALETTE["sky"], alpha=0.35, label="净负荷缺口")
    ax.fill_between(hours, day1.pv_kw / 1e3, day1.load_kw / 1e3,
                    where=(day1.pv_kw >= day1.load_kw), color=PALETTE["green"], alpha=0.32, label="光伏富余")
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("功率 / MW")
    ax.set_title("典型日净负荷结构")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=8.5, ncol=2)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    no_storage = np.maximum((day1.load_kw - day1.pv_kw) * DT_HOURS, 0)
    ax.plot(hours, frame["grid_kwh"] * 6 / 1e3, color=PALETTE["navy"], linewidth=1.9, label="含储能最优购电")
    ax.plot(hours, no_storage * 6 / 1e3, color=PALETTE["gray"], linewidth=1.6, linestyle="--", label="无储能基准购电")
    ax.fill_between(hours, frame["grid_kwh"] * 6 / 1e3, no_storage * 6 / 1e3,
                    where=(no_storage > frame["grid_kwh"]), color=PALETTE["teal"], alpha=0.25, label="储能削减的购电")
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("购电功率 / MW")
    ax.set_title("储能对购电曲线的削峰填谷")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=8.5)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[1, 0])
    ax.bar(hours, frame["charge_kwh"], width=0.13, color=PALETTE["purple"],
           edgecolor=PALETTE["ink"], linewidth=0.5, label="充电量")
    ax.bar(hours, -frame["discharge_kwh"], width=0.13, color=PALETTE["teal"],
           edgecolor=PALETTE["ink"], linewidth=0.5, label="放电量")
    ax.axhline(0, color=PALETTE["ink"], linewidth=0.8)
    ax.axhline(833.33, color=PALETTE["red"], linestyle=":", linewidth=1.0)
    ax.axhline(-833.33, color=PALETTE["red"], linestyle=":", linewidth=1.0)
    ax.text(0.2, 860, "单时段功率上限 833.33 kWh", fontsize=8, color=PALETTE["red"])
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("电量 / kWh（10 min）")
    ax.set_title("储能充放电计划")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=9)
    panel_label(ax, "(c)")
    ax = fig.add_subplot(gs[1, 1])
    ax.plot(hours, frame["soc_kwh"] / 1e3, color=PALETTE["navy"], linewidth=2.2)
    ax.fill_between(hours, frame["soc_kwh"] / 1e3, 1.2, color=PALETTE["sky"], alpha=0.3)
    ax.axhline(1.2, color=PALETTE["red"], linestyle="--", linewidth=1.1)
    ax.axhline(10.8, color=PALETTE["red"], linestyle="--", linewidth=1.1)
    ax.axhline(6.0, color=PALETTE["gray"], linestyle=":", linewidth=1.0)
    ax.text(0.2, 1.35, "下限 1200 kWh", fontsize=8.5, color=PALETTE["red"])
    ax.text(0.2, 10.95, "上限 10800 kWh", fontsize=8.5, color=PALETTE["red"])
    ax.text(0.2, 6.15, "首末储电量 6000 kWh", fontsize=8.5, color=PALETTE["gray"])
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("储电量 / MWh")
    ax.set_title("储电量日内轨迹（首末闭合）")
    ax.set_xlim(0, 24)
    ax.set_ylim(0.5, 12.2)
    panel_label(ax, "(d)")
    save(fig, "q1_dispatch")
    print("[fig] q1_dispatch 完成")
if __name__ == "__main__":
    main()
