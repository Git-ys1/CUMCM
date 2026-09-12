from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from MathModel.solve.plot_style import (
    CYCLE,
    PALETTE,
    SCENARIO_COLORS,
    apply_style,
    panel_label,
    save,
)
apply_style()
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "outputs" / "variants" / "model_audit"
FIGS = ROOT / "paper" / "figures"
Q2_ORDER = ["A_perfectload_risk_feedback", "B_causalload_risk_feedback",
            "C_causalload_point_feedback", "D_causalload_risk_nofeedback"]
Q2_LABEL = {
    "A_perfectload_risk_feedback": "A 完美负载\n风险边际·有反馈",
    "B_causalload_risk_feedback": "B 因果负载\n风险边际·有反馈",
    "C_causalload_point_feedback": "C 因果负载\n点预测·有反馈",
    "D_causalload_risk_nofeedback": "D 因果负载\n风险边际·无反馈",
}
Q3_ORDER = ["S0_0", "S1_0_6", "S2_0_6_12", "S3_0_6_12_18"]
Q3_LABEL = {"S0_0": "S0\n仅0:00", "S1_0_6": "S1\n+6:00", "S2_0_6_12": "S2\n+12:00", "S3_0_6_12_18": "S3\n+18:00"}
Q4_ORDER = ["q42_perfect_price", "q42_causal_price", "q43_perfect_price", "q43_causal_price"]
Q4_LABEL = {"q42_perfect_price": "Q4-2\n附件4直用", "q42_causal_price": "Q4-2\n因果扩展",
            "q43_perfect_price": "Q4-3\n附件4直用", "q43_causal_price": "Q4-3\n因果扩展"}
def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
def load_group(*parts: str) -> dict:
    *dirs, stem = parts
    return load(VARIANTS.joinpath(*dirs) / f"{stem}.json")
def _bar_labels(ax, bars, values, fmt="{:.2f}", dy=0.012, fontsize=9.5):
    span = ax.get_ylim()[1] - ax.get_ylim()[0]
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + span * dy,
                fmt.format(value), ha="center", va="bottom", fontsize=fontsize, fontweight="bold")
def fig_q2_attribution() -> None:
    summary = load_group("q2", "summary")
    totals = [summary[k]["total_cost_yuan"] / 1e4 for k in Q2_ORDER]
    emergencies = [summary[k]["emergency_energy_kwh"] / 1e3 for k in Q2_ORDER]
    curtails = [summary[k]["curtailment_energy_kwh"] / 1e3 for k in Q2_ORDER]
    c = {k: summary[k]["total_cost_yuan"] / 1e4 for k in Q2_ORDER}
    fig = plt.figure(figsize=(13.8, 8.6))
    gs = fig.add_gridspec(2, 2, hspace=0.48, wspace=0.26)
    ax = fig.add_subplot(gs[0, 0])
    colors = [PALETTE["blue"], PALETTE["teal"], PALETTE["yellow"] if "yellow" in PALETTE else PALETTE["gold"], PALETTE["red"]]
    bars = ax.bar(range(4), totals, color=colors, edgecolor=PALETTE["ink"], linewidth=0.8, width=0.62)
    ax.set_xticks(range(4))
    ax.set_xticklabels([Q2_LABEL[k] for k in Q2_ORDER], fontsize=9)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("问题二四种信息集/机制组合的总费用")
    ax.set_ylim(0, max(totals) * 1.16)
    _bar_labels(ax, bars, totals, "{:.1f}")
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    x = np.arange(4)
    bars = ax.bar(x - 0.19, emergencies, width=0.38, color=PALETTE["orange"],
                  edgecolor=PALETTE["ink"], linewidth=0.7, label="紧急购电")
    bars2 = ax.bar(x + 0.19, curtails, width=0.38, color=PALETTE["sky"],
                   edgecolor=PALETTE["ink"], linewidth=0.7, label="弃光")
    ax.set_xticks(x)
    ax.set_xticklabels([Q2_LABEL[k] for k in Q2_ORDER], fontsize=9)
    ax.set_ylabel("电量 / MWh")
    ax.set_title("紧急购电与弃光电量")
    ax.legend(fontsize=9)
    _bar_labels(ax, bars, emergencies, "{:.0f}")
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[1, 0])
    delta_load = c["B_causalload_risk_feedback"] - c["A_perfectload_risk_feedback"]
    delta_pv = c["C_causalload_point_feedback"] - c["B_causalload_risk_feedback"]
    delta_fb = c["D_causalload_risk_nofeedback"] - c["B_causalload_risk_feedback"]
    labels = ["完美负载信息\n$\\Delta C_{load}$", "去掉光伏风险边际\n$\\Delta C_{PVrisk}$", "去掉实时储能反馈\n$\\Delta C_{feedback}$"]
    values = [delta_load, delta_pv, delta_fb]
    bars = ax.bar(range(3), values, width=0.55,
                  color=[PALETTE["red"], PALETTE["orange"], PALETTE["gold"]],
                  edgecolor=PALETTE["ink"], linewidth=0.8)
    _bar_labels(ax, bars, values, "{:+.1f}")
    for i, value in enumerate(values):
        share = 100 * value / c["B_causalload_risk_feedback"]
        ax.text(i, value * 0.5, f"占因果基准\n{share:.1f}%", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=8.8)
    ax.set_ylabel("费用增量 / 万元")
    ax.set_title("三项机制各自的费用贡献（万元）")
    ax.set_ylim(0, max(values) * 1.24)
    panel_label(ax, "(c)")
    ax = fig.add_subplot(gs[1, 1])
    rows = []
    for key in Q2_ORDER:
        m = summary[key]
        rows.append([m["plan_purchase_cost_yuan"] / 1e4, m["emergency_cost_yuan"] / 1e4])
    rows = np.asarray(rows)
    ax.bar(range(4), rows[:, 0], width=0.62, color=PALETTE["navy"], label="计划购电费",
           edgecolor=PALETTE["ink"], linewidth=0.8)
    ax.bar(range(4), rows[:, 1], bottom=rows[:, 0], width=0.62, color=PALETTE["orange"],
           label="紧急购电费", edgecolor=PALETTE["ink"], linewidth=0.8)
    for i, (plan, em) in enumerate(rows):
        ax.text(i, plan / 2, f"{plan:.0f}", ha="center", va="center", color="white", fontsize=9.5, fontweight="bold")
        ax.text(i, plan + em + max(rows[:, 0]) * 0.012, f"{plan + em:.1f}", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold")
    ax.set_xticks(range(4))
    ax.set_xticklabels([Q2_LABEL[k] for k in Q2_ORDER], fontsize=9)
    ax.set_ylabel("费用 / 万元")
    ax.set_title("费用构成：计划购电与紧急购电")
    ax.set_ylim(0, (rows.sum(axis=1).max()) * 1.16)
    ax.legend(fontsize=9)
    panel_label(ax, "(d)")
    save(fig, "q2_attribution")
def fig_q3_forecast_value() -> None:
    summary = load_group("q3_additive", "summary")
    costs = np.array([summary[k]["total_cost_yuan"] / 1e4 for k in Q3_ORDER])
    fig = plt.figure(figsize=(13.8, 8.6))
    gs = fig.add_gridspec(2, 2, hspace=0.46, wspace=0.26)
    ax = fig.add_subplot(gs[0, 0])
    ax.plot(range(4), costs, marker="o", color=PALETTE["navy"], markersize=7, linewidth=2.2)
    for i, value in enumerate(costs):
        ax.annotate(f"{value:.1f}", (i, value), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(range(4))
    ax.set_xticklabels([Q3_LABEL[k] for k in Q3_ORDER], fontsize=9)
    ax.set_xlabel("可用的决策更新节点")
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("新增决策节点带来的费用下降")
    ax.set_ylim(costs.min() * 0.965, costs.max() * 1.022)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    controls = [summary["C1_load6"]["total_cost_yuan"], summary["C2_load12"]["total_cost_yuan"],
                summary["C3_load18"]["total_cost_yuan"]]
    load_value = np.array([summary[Q3_ORDER[i]]["total_cost_yuan"] - controls[i] for i in range(3)]) / 1e4
    pv_value = np.array([controls[i] - summary[Q3_ORDER[i + 1]]["total_cost_yuan"] for i in range(3)]) / 1e4
    labels = ["$V_6$", "$V_{12}$", "$V_{18}$"]
    bars = ax.bar(labels, load_value, color=PALETTE["orange"],
                  edgecolor=PALETTE["ink"], linewidth=0.8, width=0.55, label="负载观测刷新")
    ax.bar(labels, pv_value, bottom=load_value, color=PALETTE["teal"],
           edgecolor=PALETTE["ink"], linewidth=0.8, width=0.55, label="光伏预报刷新")
    values = load_value + pv_value
    ax.axhline(0, color=PALETTE["ink"], linewidth=0.9)
    for index, value in enumerate(values):
        ax.text(index, value + max(values) * 0.025, f"{value:+.1f}", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold")
    ax.set_ylabel("增量价值 / 万元")
    ax.set_title("节点价值的配对分解")
    ax.set_ylim(min(0, min(values)) - 12, max(values) * 1.24)
    ax.legend(fontsize=8.5)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[1, 0])
    by_season = []
    for key in Q3_ORDER:
        frame = pd.read_csv(VARIANTS / "q3_additive" / key / "by_season.csv", encoding="utf-8-sig")
        frame = frame.set_index("season").reindex(["spring", "summer", "autumn", "winter"])
        by_season.append(frame)
    seasons = ["spring", "summer", "autumn", "winter"]
    names = ["春季", "夏季", "秋季", "冬季"]
    matrix = np.array([[f.loc[s, "total_cost_yuan"] / 1e4 for s in seasons] for f in by_season])
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(4))
    ax.set_xticklabels(names)
    ax.set_yticks(range(4))
    ax.set_yticklabels([Q3_LABEL[k].replace("\n", " ") for k in Q3_ORDER], fontsize=9)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{matrix[i, j]:.0f}", ha="center", va="center", fontsize=9.5,
                    color="white" if matrix[i, j] > matrix.mean() else PALETTE["ink"])
    ax.grid(False)
    ax.set_title("季节维度的费用下降（万元）")
    cb = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.92)
    cb.set_label("万元", fontsize=9)
    panel_label(ax, "(c)")
    ax = fig.add_subplot(gs[1, 1])
    up = [summary[k]["up_adjustment_energy_kwh"] / 1e3 for k in Q3_ORDER]
    down = [summary[k]["down_adjustment_energy_kwh"] / 1e3 for k in Q3_ORDER]
    em = [summary[k]["emergency_energy_kwh"] / 1e3 for k in Q3_ORDER]
    x = np.arange(4)
    ax.bar(x - 0.21, up, width=0.4, color=PALETTE["red"], label="向上调整",
           edgecolor=PALETTE["ink"], linewidth=0.7)
    ax.bar(x + 0.21, np.array(down) * -1, width=0.4, color=PALETTE["green"], label="向下调整",
           edgecolor=PALETTE["ink"], linewidth=0.7)
    ax.plot(x, em, color=PALETTE["orange"], marker="s", markersize=6, linewidth=2.0, label="紧急购电")
    ax.axhline(0, color=PALETTE["ink"], linewidth=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([Q3_LABEL[k] for k in Q3_ORDER], fontsize=9)
    ax.set_ylabel("电量 / MWh")
    ax.set_title("调整电量与紧急购电")
    ax.legend(fontsize=9, ncol=1)
    panel_label(ax, "(d)")
    save(fig, "q3_forecast_value")
def fig_q3_settlement() -> None:
    repl = load_group("q3_replacement", "summary")
    addi = load_group("q3_additive", "summary")
    fig, axes = plt.subplots(1, 3, figsize=(13.8, 4.4))
    plt.subplots_adjust(wspace=0.3)
    ax = axes[0]
    x = np.arange(4)
    r = [repl[k]["total_cost_yuan"] / 1e4 for k in Q3_ORDER]
    a = [addi[k]["total_cost_yuan"] / 1e4 for k in Q3_ORDER]
    ax.bar(x - 0.2, r, width=0.4, color=PALETTE["navy"], label="replacement 口径",
           edgecolor=PALETTE["ink"], linewidth=0.8)
    ax.bar(x + 0.2, a, width=0.4, color=PALETTE["gold"], label="additive 口径",
           edgecolor=PALETTE["ink"], linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([Q3_LABEL[k] for k in Q3_ORDER], fontsize=9)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("两种结算口径分别重优化")
    ax.set_ylim(0, max(a) * 1.16)
    ax.legend(fontsize=8.5)
    panel_label(ax, "(a)")
    ax = axes[1]
    gap = [a[i] - r[i] for i in range(4)]
    bars = ax.bar(x, gap, width=0.55, color=PALETTE["rose"], edgecolor=PALETTE["ink"], linewidth=0.8)
    _bar_labels(ax, bars, gap, "{:+.2f}")
    ax.set_xticks(x)
    ax.set_xticklabels([Q3_LABEL[k] for k in Q3_ORDER], fontsize=9)
    ax.set_ylabel("additive − replacement / 万元")
    ax.set_title("口径差异（同一优化问题的两种目标）")
    ax.set_ylim(0, max(gap) * 1.25)
    panel_label(ax, "(b)")
    ax = axes[2]
    for label, data, color in (("replacement", r, PALETTE["navy"]), ("additive", a, PALETTE["gold"])):
        ax.plot(range(4), data, marker="o", color=color, linewidth=2.0, markersize=6.5, label=label)
    ax.set_xticks(range(4))
    ax.set_xticklabels([Q3_LABEL[k] for k in Q3_ORDER], fontsize=9)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("预报时刻价值的口径稳健性")
    ax.legend(fontsize=9)
    panel_label(ax, "(c)")
    save(fig, "q3_settlement")
def fig_q4_price_value() -> None:
    summary = load_group("q4", "summary")
    costs = np.array([summary[k]["total_cost_yuan"] / 1e4 for k in Q4_ORDER])
    fig = plt.figure(figsize=(13.8, 4.6))
    gs = fig.add_gridspec(1, 3, wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    colors = [PALETTE["sky"], PALETTE["red"], PALETTE["teal"], PALETTE["purple"]]
    bars = ax.bar(range(4), costs, color=colors, edgecolor=PALETTE["ink"], linewidth=0.8, width=0.6)
    ax.set_xticks(range(4))
    ax.set_xticklabels([Q4_LABEL[k] for k in Q4_ORDER], fontsize=8.5)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("波动电价下的四组结果")
    ax.set_ylim(0, costs.max() * 1.16)
    _bar_labels(ax, bars, costs, "{:.1f}")
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    value_q2 = costs[1] - costs[0]
    value_q3 = costs[3] - costs[2]
    value_roll_perfect = costs[0] - costs[2]
    value_roll_causal = costs[1] - costs[3]
    labels = ["Q4-2\n发布信息差额", "Q4-3\n发布信息差额", "附件4直用下\n滚动调整价值", "因果扩展下\n滚动调整价值"]
    values = [value_q2, value_q3, value_roll_perfect, value_roll_causal]
    bars = ax.bar(range(4), values,
                  color=[PALETTE["red"], PALETTE["purple"], PALETTE["teal"], PALETTE["green"]],
                  edgecolor=PALETTE["ink"], linewidth=0.8, width=0.6)
    _bar_labels(ax, bars, values, "{:+.1f}")
    ax.set_xticks(range(4))
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("费用差额 / 万元")
    ax.set_title("价格信息与滚动调整的价值")
    ax.set_ylim(0, max(values) * 1.28)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[0, 2])
    frame = pd.read_csv(VARIANTS / "q4" / "q43_causal_price" / "price_forecast_log.csv", encoding="utf-8-sig")
    frame["hour"] = frame["decision_time"].str.slice(0, 2).astype(int)
    grouped = frame.groupby("hour")["price_mae"].mean()
    hours = grouped.index.values
    ax.bar(hours, grouped.values, color=PALETTE["purple"], edgecolor=PALETTE["ink"], linewidth=0.7, width=0.6)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h}" for h in hours])
    ax.set_xlabel("决策时刻 / h")
    ax.set_ylabel("电价预测 MAE /（元·kWh$^{-1}$）")
    ax.set_title("因果电价预测的分时精度")
    panel_label(ax, "(c)")
    save(fig, "q4_price_value")
def fig_sensitivity() -> None:
    sens = load_group("sensitivity", "summary")
    terminal = sens["terminal"]
    efficiency = sens["efficiency"]
    fig = plt.figure(figsize=(13.8, 4.6))
    gs = fig.add_gridspec(1, 3, wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    policies = ["daily_cycle", "free"]
    names = ["daily_cycle\n(计划 S$_1$$_4$$_4$=S$_0$)", "free\n(无终端约束)"]
    totals = [terminal[p]["total_cost_yuan"] / 1e4 for p in policies]
    bars = ax.bar(range(2), totals, color=[PALETTE["navy"], PALETTE["gold"]],
                  edgecolor=PALETTE["ink"], linewidth=0.8, width=0.5)
    _bar_labels(ax, bars, totals, "{:.1f}")
    ax.set_xticks(range(2))
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("终端储电量策略敏感性")
    ax.set_ylim(0, max(totals) * 1.16)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    keys = list(efficiency)
    short = ["E1\n$\\eta_c=\\eta_d=0.90$", "E2\n$\\eta_c=\\eta_d=\\sqrt{0.9}$"]
    totals = [efficiency[k]["total_cost_yuan"] / 1e4 for k in keys]
    throughput = [efficiency[k]["storage_throughput_kwh"] / 1e3 for k in keys]
    bars = ax.bar(range(len(keys)), totals, color=[PALETTE["teal"], PALETTE["rose"]],
                  edgecolor=PALETTE["ink"], linewidth=0.8, width=0.5)
    _bar_labels(ax, bars, totals, "{:.1f}")
    for i, value in enumerate(throughput):
        ax.text(i, totals[i] * 0.5, f"吞吐\n{value:.0f} MWh", ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(short, fontsize=9)
    ax.set_ylabel("全年总费用 / 万元")
    ax.set_title("储能效率口径敏感性")
    ax.set_ylim(0, max(totals) * 1.16)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[0, 2])
    data = [terminal[p]["daily_boundary_soc"]["mean"] for p in policies]
    x = np.arange(2)
    ax.bar(x, data, color=[PALETTE["navy"], PALETTE["gold"]], edgecolor=PALETTE["ink"],
           linewidth=0.8, width=0.5, label="日均日末储电量")
    for i, p in enumerate(policies):
        info = terminal[p]["daily_boundary_soc"]
        ax.errorbar(i, info["mean"], yerr=[[info["mean"] - info["min"]], [info["max"] - info["mean"]]],
                    fmt="none", ecolor=PALETTE["ink"], elinewidth=1.4, capsize=7)
        ax.text(i, info["max"] + 200, f"std={info['std']:.0f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("日末储电量 / kWh")
    ax.set_title("日边界储电量的分布")
    ax.set_ylim(0, 12500)
    panel_label(ax, "(c)")
    save(fig, "sensitivity")
def fig_dispatch_overview(day_label: str = "2025-06-21", scenario: str = "q3_additive/S3_0_6_12_18") -> None:
    path = VARIANTS / scenario / "solution.csv"
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame = frame[frame["date"] == day_label].reset_index(drop=True)
    if frame.empty:
        raise ValueError(f"{day_label} not found in {path}")
    hours = (frame["slot"].to_numpy()) / 6.0
    fig = plt.figure(figsize=(13.8, 8.4))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.24)
    ax = fig.add_subplot(gs[0, 0])
    ax.fill_between(hours, 0, frame["load_kw"] / 1e3, color=PALETTE["sky"], alpha=0.55, label="小区负载")
    ax.plot(hours, frame["actual_pv_kw"] / 1e3, color=PALETTE["gold"], linewidth=1.9, label="实际光伏")
    ax.plot(hours, frame["discharge_actual_kwh"] * 6 / 1e3, color=PALETTE["teal"], linewidth=1.5, label="储能放电功率")
    ax.plot(hours, -frame["charge_actual_kwh"] * 6 / 1e3, color=PALETTE["purple"], linewidth=1.5, label="储能充电功率")
    ax.axhline(0, color=PALETTE["ink"], linewidth=0.8)
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("功率 / MW")
    ax.set_title(f"{day_label} 功率平衡与储能充放电")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=8.5, ncol=2)
    panel_label(ax, "(a)")
    ax = fig.add_subplot(gs[0, 1])
    ax.plot(hours, frame["baseline_grid_kwh"] * 6 / 1e3, color=PALETTE["gray"], linewidth=1.6,
            linestyle="--", label="0:00 基准计划 $G^{p}$")
    ax.plot(hours, frame["adjusted_grid_kwh"] * 6 / 1e3, color=PALETTE["navy"], linewidth=1.9,
            label="最终调整购电 $G^{a}$")
    ax.fill_between(hours, frame["baseline_grid_kwh"] * 6 / 1e3, frame["adjusted_grid_kwh"] * 6 / 1e3,
                    where=(frame["adjusted_grid_kwh"] > frame["baseline_grid_kwh"]),
                    color=PALETTE["red"], alpha=0.28, label="向上调整")
    ax.fill_between(hours, frame["baseline_grid_kwh"] * 6 / 1e3, frame["adjusted_grid_kwh"] * 6 / 1e3,
                    where=(frame["adjusted_grid_kwh"] <= frame["baseline_grid_kwh"]),
                    color=PALETTE["green"], alpha=0.28, label="向下调整")
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("购电功率 / MW")
    ax.set_title("计划与调整购电策略")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=8.5)
    panel_label(ax, "(b)")
    ax = fig.add_subplot(gs[1, 0])
    ax.plot(hours, frame["soc_actual_kwh"] / 1e3, color=PALETTE["navy"], linewidth=2.0)
    ax.fill_between(hours, frame["soc_actual_kwh"] / 1e3, 1.2, color=PALETTE["sky"], alpha=0.28)
    ax.axhline(1.2, color=PALETTE["red"], linestyle="--", linewidth=1.1)
    ax.axhline(10.8, color=PALETTE["red"], linestyle="--", linewidth=1.1)
    ax.text(0.2, 1.35, "SOC 下限 1200 kWh", fontsize=8.5, color=PALETTE["red"])
    ax.text(0.2, 10.95, "SOC 上限 10800 kWh", fontsize=8.5, color=PALETTE["red"])
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("储电量 / MWh")
    ax.set_title("储能荷电状态的日内轨迹")
    ax.set_xlim(0, 24)
    ax.set_ylim(0.5, 12.2)
    panel_label(ax, "(c)")
    ax = fig.add_subplot(gs[1, 1])
    ax.bar(hours, frame["emergency_kwh"] * 6, width=0.13, color=PALETTE["red"],
           edgecolor=PALETTE["ink"], linewidth=0.5, label="紧急购电")
    ax.bar(hours, frame["curtail_actual_kwh"] * 6, width=0.13, color=PALETTE["olive"],
           edgecolor=PALETTE["ink"], linewidth=0.5, label="弃光")
    ax.set_xlabel("时刻 / h")
    ax.set_ylabel("功率 / kW")
    ax.set_title("紧急购电与弃光的功率分布")
    ax.set_xlim(0, 24)
    ax.legend(fontsize=9)
    panel_label(ax, "(d)")
    save(fig, f"dispatch_{day_label.replace('-', '')}")
def main() -> None:
    fig_q2_attribution()
    fig_q3_forecast_value()
    fig_q4_price_value()
    fig_sensitivity()
    for day in ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21"):
        try:
            fig_dispatch_overview(day)
        except ValueError as exc:
            print("[warn]", exc)
    print("[fig] 结果层配图完成 →", FIGS)
if __name__ == "__main__":
    main()
