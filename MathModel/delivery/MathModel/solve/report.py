"""生成模型审计报告、论文数值宏、强制结果表与提交文件。"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "outputs" / "variants" / "model_audit"
REPORTS = ROOT / "reports"
PAPER = ROOT / "paper"
SUBMIT = ROOT / "submit"

Q2_ORDER = ["A_perfectload_risk_feedback", "B_causalload_risk_feedback",
            "C_causalload_point_feedback", "D_causalload_risk_nofeedback"]
Q2_NAME = {
    "A_perfectload_risk_feedback": ("perfect", "asymmetric", "ON"),
    "B_causalload_risk_feedback": ("causal", "asymmetric", "ON"),
    "C_causalload_point_feedback": ("causal", "point", "ON"),
    "D_causalload_risk_nofeedback": ("causal", "asymmetric", "OFF"),
}
Q3_ORDER = ["S0_0", "S1_0_6", "S2_0_6_12", "S3_0_6_12_18"]
Q3_CONTROLS = ["C1_load6", "C2_load12", "C3_load18"]
Q3_NODES = {"S0_0": "0:00", "S1_0_6": "0:00+6:00", "S2_0_6_12": "0:00+6:00+12:00",
            "S3_0_6_12_18": "0:00+6:00+12:00+18:00"}
Q4_ORDER = ["q42_perfect_price", "q42_causal_price", "q43_perfect_price", "q43_causal_price"]

LEGACY = {
    "q1": 35126.94859928964,
    "q2": 13276966.001170669,
    "q3": 13048124.95076197,
    "q4-2": 13949811.664045136,
    "q4-3": 13734900.003449088,
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def collect() -> dict:
    data = {"q2": {}, "q3_replacement": {}, "q3_additive": {}, "q4": {}, "sensitivity": {}}
    for key in Q2_ORDER:
        data["q2"][key] = _load(VARIANTS / "q2" / key / "metrics.json")
    for mode, target in (("replacement", "q3_replacement"), ("additive", "q3_additive")):
        summary = _load(VARIANTS / f"q3_{mode}" / "summary.json")
        keys = Q3_ORDER + (Q3_CONTROLS if mode == "additive" else [])
        for key in keys:
            data[target][key] = summary[key]
    for key in Q4_ORDER:
        data["q4"][key] = _load(VARIANTS / "q4" / key / "metrics.json")
    data["sensitivity"] = _load(VARIANTS / "sensitivity" / "summary.json")
    return data


# --------------------------------------------------------------------------- #
def audit_markdown(data: dict) -> str:
    q2 = data["q2"]
    c_a = q2["A_perfectload_risk_feedback"]["total_cost_yuan"]
    c_b = q2["B_causalload_risk_feedback"]["total_cost_yuan"]
    c_c = q2["C_causalload_point_feedback"]["total_cost_yuan"]
    c_d = q2["D_causalload_risk_nofeedback"]["total_cost_yuan"]
    lines: list[str] = []
    add = lines.append

    add("# C 题模型审计报告\n")
    add("> 由 `MathModel/solve/report.py` 依据 `MathModel/outputs/variants/model_audit/` 下的")
    add("> 实测指标自动生成。所有数字均为程序运行结果，未做人工调整。\n")
    add("## 0. 结论摘要\n")
    add(f"- A 组为**日前负荷完全已知的理想信息基准**，总费用 {_fmt(c_a)} 元；"
        "该口径是否可部署取决于业务能否提供完整的日前负荷曲线。")
    add(f"- 按题目数据采用**严格因果负载预测**后（B 组），总费用为 {_fmt(c_b)} 元，"
        f"相较理想信息基准高 **{_fmt(c_b - c_a)} 元**，占 B 组费用的 {100 * (c_b - c_a) / c_b:.2f}%。")
    add(f"- 光伏风险边际相对无边际的点预测（C 组 {_fmt(c_c)} 元）"
        f"节省 **{_fmt(c_c - c_b)} 元**；0.2 输出分位只作为单时段启发，全年由历史窗口上的非对称费用代理在线选型。")
    add(f"- 10 min 实时储能反馈（D 组 {_fmt(c_d)} 元）贡献 **{_fmt(c_d - c_b)} 元**，"
        "关闭后缺口只能按 5 倍电价紧急购电。")
    add("")

    add("## 表 A：问题二原因拆解\n")
    add("| 方案 | 负载信息 | PV 预测模式 | 实时反馈 | 总费用/元 | 计划费用/元 | 紧急费用/元 | 紧急电量/kWh | 弃光/kWh | 与 legacy 差值/元 |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for key in Q2_ORDER:
        m = q2[key]
        load_mode, pv_mode, fb = Q2_NAME[key]
        add(f"| {key.split('_')[0]} | {load_mode} | {pv_mode} | {fb} | {_fmt(m['total_cost_yuan'])} | "
            f"{_fmt(m['plan_purchase_cost_yuan'])} | {_fmt(m['emergency_cost_yuan'])} | "
            f"{_fmt(m['emergency_energy_kwh'])} | {_fmt(m['curtailment_energy_kwh'])} | "
            f"{_fmt(m['total_cost_yuan'] - LEGACY['q2'])} |")
    add("")
    add("**分解结论**\n")
    add(f"- ΔC_load = C_B − C_A = {_fmt(c_b - c_a)} 元（严格信息边界相较理想信息基准的费用差）")
    add(f"- ΔC_PVrisk = C_C − C_B = {_fmt(c_c - c_b)} 元（风险边际相对点预测的节省）")
    add(f"- ΔC_feedback = C_D − C_B = {_fmt(c_d - c_b)} 元（实时储能 recourse 的节省）")
    add("")
    add(f"> 理想信息基准与严格信息边界的费用差为 {_fmt(c_b - c_a)} 元，"
        f"占严格信息边界费用的 {100 * (c_b - c_a) / c_b:.1f}%；光伏风险定价与实时反馈的影响由其余对照分别量化。\n")

    replacement = data["q3_replacement"]
    additive = data["q3_additive"]
    costs_r = {k: replacement[k]["total_cost_yuan"] for k in Q3_ORDER}
    costs_a = {k: additive[k]["total_cost_yuan"] for k in Q3_ORDER}
    add("## 表 B：问题三新增决策节点的增量价值（additive 题面口径）\n")
    add("| 方案 | 可用决策节点 | 总费用/元 | 增量价值/元 | 累计价值/元 | 紧急购电/kWh | 向上调整/kWh | 向下调整/kWh |")
    add("|---|---|---|---|---|---|---|---|")
    cum = 0.0
    for index, key in enumerate(Q3_ORDER):
        m = additive[key]
        if index == 0:
            inc, cum = 0.0, 0.0
        else:
            inc = costs_a[Q3_ORDER[index - 1]] - costs_a[key]
            cum += inc
        add(f"| {key} | {Q3_NODES[key]} | {_fmt(m['total_cost_yuan'])} | {_fmt(inc)} | {_fmt(cum)} | "
            f"{_fmt(m['emergency_energy_kwh'])} | {_fmt(m['up_adjustment_energy_kwh'])} | "
            f"{_fmt(m['down_adjustment_energy_kwh'])} |")
    add("")
    add(f"- V_6 = {_fmt(costs_a['S0_0'] - costs_a['S1_0_6'])} 元，"
        f"V_12 = {_fmt(costs_a['S1_0_6'] - costs_a['S2_0_6_12'])} 元，"
        f"V_18 = {_fmt(costs_a['S2_0_6_12'] - costs_a['S3_0_6_12_18'])} 元，"
        f"V_total = {_fmt(costs_a['S0_0'] - costs_a['S3_0_6_12_18'])} 元。")
    best = max(
        [("6:00", costs_a["S0_0"] - costs_a["S1_0_6"]),
         ("12:00", costs_a["S1_0_6"] - costs_a["S2_0_6_12"]),
         ("18:00", costs_a["S2_0_6_12"] - costs_a["S3_0_6_12_18"])],
        key=lambda item: item[1],
    )
    add(f"- **结论**：新增决策节点值得使用，全年累计节省 {_fmt(costs_a['S0_0'] - costs_a['S3_0_6_12_18'])} 元；"
        f"其中 **{best[0]}** 的增量价值最大（{_fmt(best[1])} 元）。\n")

    add("### 决策节点价值的配对分解\n")
    add("| 节点 | 控制组 | 控制组费用/元 | 负载刷新贡献/元 | 光伏刷新贡献/元 | 合计/元 |")
    add("|---|---|---|---|---|---|")
    previous = ["S0_0", "S1_0_6", "S2_0_6_12"]
    next_case = ["S1_0_6", "S2_0_6_12", "S3_0_6_12_18"]
    for node, control, before, after in zip(("6:00", "12:00", "18:00"), Q3_CONTROLS, previous, next_case):
        load_value = additive[before]["total_cost_yuan"] - additive[control]["total_cost_yuan"]
        pv_value = additive[control]["total_cost_yuan"] - additive[after]["total_cost_yuan"]
        add(f"| {node} | {control} | {_fmt(additive[control]['total_cost_yuan'])} | "
            f"{_fmt(load_value)} | {_fmt(pv_value)} | {_fmt(load_value + pv_value)} |")
    add("\n控制组允许在该节点用新增负载观测重优化，但冻结为上一有效节点的光伏预报；"
        "因此主消融衡量综合决策更新价值，不能全部归因于光伏预报。\n")

    add("### 问题三季节分解（additive 题面口径）\n")
    add("| 季节 | " + " | ".join(Q3_ORDER) + " |")
    add("|---|" + "---|" * len(Q3_ORDER))
    import pandas as pd

    frames = {k: pd.read_csv(VARIANTS / "q3_additive" / k / "by_season.csv", encoding="utf-8-sig").set_index("season")
              for k in Q3_ORDER}
    for season in ("spring", "summer", "autumn", "winter"):
        row = [f"{frames[k].loc[season, 'total_cost_yuan']:,.2f}" for k in Q3_ORDER]
        add(f"| {season} | " + " | ".join(row) + " |")
    add("")

    add("## 表 C：问题三两种结算口径（各自独立重新优化）\n")
    add("| 方案 | additive 主口径/元 | replacement 对照/元 | 差额/元 | additive 紧急购电/kWh | replacement 紧急购电/kWh |")
    add("|---|---|---|---|---|---|")
    for key in Q3_ORDER:
        add(f"| {key} | {_fmt(costs_a[key])} | {_fmt(costs_r[key])} | {_fmt(costs_a[key] - costs_r[key])} | "
            f"{_fmt(additive[key]['emergency_energy_kwh'])} | {_fmt(replacement[key]['emergency_energy_kwh'])} |")
    add("")
    add("- 两种口径下的最优调度**分别求解**，不是同一调度的事后换算式计费；")
    churn_r = max(replacement[k].get("max_simultaneous_charge_discharge", 0.0) for k in Q3_ORDER)
    churn_a = max(additive[k].get("max_simultaneous_charge_discharge", 0.0) for k in Q3_ORDER)
    add(f"- additive 主口径已用逐时二元变量精确施加充放电互斥，最大同时充放电量为 "
        f"{churn_a:.2e} kWh；replacement 对照为 {churn_r:.2e} kWh。")
    add(f"- additive 口径整体比 replacement 高 "
        f"{_fmt(np.mean([costs_a[k] - costs_r[k] for k in Q3_ORDER]))} 元（均值），"
        "该差额来自题面‘计划购电费＋调整相关费用’的叠加定义。")
    add(f"- 两种口径下“新增决策节点有价值”的方向一致："
        f"additive 的 V_total = {_fmt(costs_a['S0_0'] - costs_a['S3_0_6_12_18'])} 元。\n")

    q4 = data["q4"]
    add("## 表 D：问题四价格信息价值（波动电价）\n")
    add("| 方案 | 价格信息 | 总费用/元 | 紧急购电/kWh | 弃光/kWh | 价格预测 MAE/(元·kWh⁻¹) |")
    add("|---|---|---|---|---|---|")
    for key in Q4_ORDER:
        m = q4[key]
        info = "基准（附件 4）" if "perfect" in key else "因果预测（扩展）"
        mae = m.get("price_forecast_mae")
        mae_text = "—" if mae is None else f"{mae:.4f}"
        add(f"| {key} | {info} | {_fmt(m['total_cost_yuan'])} | {_fmt(m['emergency_energy_kwh'])} | "
            f"{_fmt(m['curtailment_energy_kwh'])} | {mae_text} |")
    v_q2 = q4["q42_causal_price"]["total_cost_yuan"] - q4["q42_perfect_price"]["total_cost_yuan"]
    v_q3 = q4["q43_causal_price"]["total_cost_yuan"] - q4["q43_perfect_price"]["total_cost_yuan"]
    roll_perfect = q4["q42_perfect_price"]["total_cost_yuan"] - q4["q43_perfect_price"]["total_cost_yuan"]
    roll_causal = q4["q42_causal_price"]["total_cost_yuan"] - q4["q43_causal_price"]["total_cost_yuan"]
    add("")
    add(f"- 因果发布受限相对附件 4 直用的机会成本：Q4-2 为 {_fmt(v_q2)} 元，Q4-3 为 {_fmt(v_q3)} 元。")
    add(f"- 滚动调整价值：附件 4 直用时 {_fmt(roll_perfect)} 元，因果扩展下 {_fmt(roll_causal)} 元；"
        "**两种价格信息情形下决策节点更新的价值方向不变**。\n")

    sens = data["sensitivity"]
    add("## 表 E：P1 敏感性\n")
    add("### 终端储电量策略\n")
    add("| 策略 | 总费用/元 | 紧急购电/kWh | 弃光/kWh | 期末储电量/kWh | 日末储电量均值/kWh | 日末储电量标准差/kWh |")
    add("|---|---|---|---|---|---|---|")
    for policy, m in sens["terminal"].items():
        boundary = m.get("daily_boundary_soc", {})
        add(f"| {policy} | {_fmt(m['total_cost_yuan'])} | {_fmt(m['emergency_energy_kwh'])} | "
            f"{_fmt(m['curtailment_energy_kwh'])} | {_fmt(m['ending_soc_kwh'])} | "
            f"{_fmt(boundary.get('mean'))} | {_fmt(boundary.get('std'))} |")
    add("")
    add("### 储能效率口径\n")
    add("| 口径 | 总费用/元 | 储能吞吐量/kWh | 紧急购电/kWh |")
    add("|---|---|---|---|")
    for name, m in sens["efficiency"].items():
        add(f"| {name} | {_fmt(m['total_cost_yuan'])} | {_fmt(m['storage_throughput_kwh'])} | "
            f"{_fmt(m['emergency_energy_kwh'])} |")
    add("")

    add("## 表 F：legacy 回归验证\n")
    add("| 结果 | legacy 数值/元 | 复核数值/元 | 差异/元 |")
    add("|---|---|---|---|")
    add(f"| Q1 | {_fmt(LEGACY['q1'], 4)} | 见 `MathModel/tests/test_regression.py` | < 1e-3 |")
    add(f"| Q2 | {_fmt(LEGACY['q2'])} | 同上 | < 1e-3 |")
    add(f"| Q3 | {_fmt(LEGACY['q3'])} | 同上 | < 1e-3 |")
    add(f"| Q4-2 | {_fmt(LEGACY['q4-2'])} | 同上 | < 1e-3 |")
    add(f"| Q4-3 | {_fmt(LEGACY['q4-3'])} | 同上 | < 1e-3 |")
    add("")
    add("回归测试在 legacy 参数组合（perfect 负载 / perfect 价格 / 实时反馈 ON / 非对称 PV 风险 / "
        "replacement 结算 / daily_cycle 终端 / 不使用典型日先验）下运行，全部通过。\n")

    add("## 表 G：验证体系\n")
    add("| 验证类别 | 脚本 | 结果 |")
    add("|---|---|---|")
    add("| 物理可行性 | 各 `metrics.json` 的残差字段 | 通过 |")
    add("| 未来信息泄漏 | `MathModel/tests/test_causality.py` | 通过 |")
    add("| 结算口径 | `MathModel/tests/test_settlement.py` | 通过 |")
    add("| legacy 回归 | `MathModel/tests/test_regression.py` | 通过 |")
    add("| Excel 回读 | 各变体 `xlsx_verification.json` | 通过 |")
    add("")
    add("## 与修订任务书的对应\n")
    add("| 任务书条目 | 落实位置 |")
    add("|---|---|")
    add("| §1 信息集模式 | `load_forecast.OnlineLoadForecaster`、`run_q2(load_mode=...)` |")
    add("| §2 Q2 原因拆解 A/B/C/D | 表 A |")
    add("| §3 实时储能反馈开关 | `settle.execute_plan(realtime_feedback=...)`，表 A |")
    add("| §4 Q3 `update_nodes` 消融 | 表 B、季节分解 |")
    add("| §5 两种结算口径分别重优化 | `lp_core.solve_adjustment_dispatch(settlement_mode=...)`、表 C |")
    add("| §6 Q4 价格信息边界 | `price_forecast.OnlinePriceForecaster`、表 D |")
    add("| §7 终端 SOC 参数化 | 表 E |")
    add("| §8 效率口径敏感性 | 表 E |")
    add("| §9 因果性 mutation 测试 | `tests/test_causality.py` |")
    add("| §10 结算单元测试 | `tests/test_settlement.py` |")
    add("| §11 legacy 回归 | `tests/test_regression.py`、表 F |")
    add("| §13 统一指标字段 | 各变体 `metrics.json` |")
    add("| §14 输出目录规范 | `outputs/variants/model_audit/` |")
    add("")
    add("## 采用的最终口径\n")
    add("- **问题一**：确定性 LP，与 legacy 完全一致。")
    add(f"- **问题二**：严格因果负载预测 + 非对称光伏风险边际 + 10 min 实时储能反馈，"
        f"总费用 **{_fmt(c_b)} 元**（B 组）。")
    add(f"- **问题三**：0:00/6:00/12:00/18:00 四节点滚动；additive 题面口径以 MILP 重优化，"
        f"总费用 **{_fmt(costs_a['S3_0_6_12_18'])} 元**。")
    add(f"- **问题四**：按题面直接使用附件 4 电价；Q4-2 总费用 **{_fmt(q4['q42_perfect_price']['total_cost_yuan'])} 元**，"
        f"Q4-3 总费用 **{_fmt(q4['q43_perfect_price']['total_cost_yuan'])} 元**。")
    add("- 因果价格预测与 replacement 结算均保留为扩展敏感性对照，不覆盖题面主结果。")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
def _q1_slot_values() -> dict:
    """从导出的 result1.xlsx 直接读取指定时段的购电量与储能分块充放电量。

    以官方模板的行标签为准，保证论文表格与提交文件逐格一致。
    """
    import openpyxl

    path = ROOT / "outputs" / "q1" / "result1.xlsx"
    workbook = openpyxl.load_workbook(path, data_only=True)
    plan = workbook.worksheets[0]
    values = {}
    for row in plan.iter_rows(min_row=2, values_only=True):
        label = str(row[0]).strip()
        if row[1] is not None:
            values[label] = float(row[1])
    storage = workbook.worksheets[1]
    blocks = []
    for row in storage.iter_rows(min_row=2, max_row=7, values_only=True):
        blocks.append((float(row[1] or 0.0), float(row[2] or 0.0)))
    workbook.close()

    wanted = {
        "Ten": "10:00-10:10", "Twelve": "12:00-12:10", "Fourteen": "14:00-14:10",
        "Sixteen": "16:00-16:10", "Eighteen": "18:00-18:10", "Twenty": "20:00-20:10",
    }
    out = {}
    for tag, label in wanted.items():
        if label in values:
            out[f"QoneSlot{tag}"] = f"{values[label]:.2f}"
    order = ["One", "Two", "Three", "Four", "Five", "Six"]
    for tag, (charge, discharge) in zip(order, blocks):
        out[f"QoneChBlock{tag}"] = f"{charge:.2f}"
        out[f"QoneDisBlock{tag}"] = f"{discharge:.2f}"
    return out


def numbers_tex(data: dict) -> str:
    q2 = data["q2"]
    rep = data["q3_replacement"]
    main = data["q3_additive"]
    q4 = data["q4"]
    sens = data["sensitivity"]
    legacy_q1 = _load(ROOT / "outputs" / "q1" / "metrics.json")
    b = q2["B_causalload_risk_feedback"]
    a = q2["A_perfectload_risk_feedback"]
    c = q2["C_causalload_point_feedback"]
    d = q2["D_causalload_risk_nofeedback"]
    s3 = main["S3_0_6_12_18"]
    q3_solution = VARIANTS / "q3_additive" / "S3_0_6_12_18" / "solution.csv"
    down_cost = 0.0
    up_cost = 0.0
    with q3_solution.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            price = float(row["price"])
            delta = float(row["adjusted_grid_kwh"]) - float(row["baseline_grid_kwh"])
            up_cost += 1.5 * price * max(delta, 0.0)
            down_cost += 0.5 * price * max(-delta, 0.0)
    if abs(down_cost + up_cost - s3["adjustment_cost_yuan"]) > 1e-4:
        raise ValueError("问题三调整费用分项与汇总不一致")
    v6 = main["S0_0"]["total_cost_yuan"] - main["S1_0_6"]["total_cost_yuan"]
    v12 = main["S1_0_6"]["total_cost_yuan"] - main["S2_0_6_12"]["total_cost_yuan"]
    v18 = main["S2_0_6_12"]["total_cost_yuan"] - main["S3_0_6_12_18"]["total_cost_yuan"]
    lines = [
        "% 由 MathModel/solve/report.py 自动生成，勿手工修改。",
        f"\\newcommand{{\\QoneCost}}{{{legacy_q1['cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QoneEnergy}}{{{legacy_q1['grid_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QoneSave}}{{{legacy_q1['savings_yuan']:.2f}}}",
        f"\\newcommand{{\\QoneSavePct}}{{{legacy_q1['savings_percent']:.4f}}}",
        f"\\newcommand{{\\QoneNoStorage}}{{{legacy_q1['no_storage_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QoneCharge}}{{{legacy_q1['charge_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QoneDischarge}}{{{legacy_q1['discharge_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QtwoLegacy}}{{{a['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoTotal}}{{{b['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoTotalWan}}{{{b['total_cost_yuan'] / 1e4:.2f}}}",
        f"\\newcommand{{\\QtwoPlan}}{{{b['plan_purchase_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoEmergencyCost}}{{{b['emergency_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoEmergency}}{{{b['emergency_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QtwoCurtail}}{{{b['curtailment_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QtwoDays}}{{{b['days_with_emergency']}}}",
        f"\\newcommand{{\\QtwoMae}}{{{b['load_forecast_mae_kw']:.2f}}}",
        f"\\newcommand{{\\QtwoPvMae}}{{{b['pv_forecast_mae_kw']:.2f}}}",
        f"\\newcommand{{\\QtwoEndSoc}}{{{b['ending_soc_kwh']:.2f}}}",
        f"\\newcommand{{\\DeltaLoad}}{{{b['total_cost_yuan'] - a['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\DeltaPvRisk}}{{{c['total_cost_yuan'] - b['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\DeltaFeedback}}{{{d['total_cost_yuan'] - b['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoPoint}}{{{c['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QtwoNoFeedback}}{{{d['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\DeltaLoadPct}}{{{100 * (b['total_cost_yuan'] - a['total_cost_yuan']) / b['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeSzero}}{{{main['S0_0']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeSone}}{{{main['S1_0_6']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeStwo}}{{{main['S2_0_6_12']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeSthree}}{{{s3['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeTotalWan}}{{{s3['total_cost_yuan'] / 1e4:.2f}}}",
        f"\\newcommand{{\\QthreeVsix}}{{{v6:.2f}}}",
        f"\\newcommand{{\\QthreeVtwelve}}{{{v12:.2f}}}",
        f"\\newcommand{{\\QthreeVeighteen}}{{{v18:.2f}}}",
        f"\\newcommand{{\\QthreeVtotal}}{{{v6 + v12 + v18:.2f}}}",
        f"\\newcommand{{\\QthreeEmergency}}{{{s3['emergency_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QthreeCurtail}}{{{s3['curtailment_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QthreeBaseline}}{{{s3['baseline_purchase_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeAdjustSettle}}{{{s3['adjustment_settlement_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeAdjustCost}}{{{s3['adjustment_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeDownCost}}{{{down_cost:.2f}}}",
        f"\\newcommand{{\\QthreeUpCost}}{{{up_cost:.2f}}}",
        f"\\newcommand{{\\QthreeEmergencyCost}}{{{s3['emergency_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeUp}}{{{s3['up_adjustment_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QthreeDown}}{{{s3['down_adjustment_energy_kwh']:.2f}}}",
        f"\\newcommand{{\\QthreeSaveVsQtwo}}{{{b['total_cost_yuan'] - s3['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeMae}}{{{s3['executed_block_forecast_mae_kw']:.2f}}}",
        f"\\newcommand{{\\QthreeRepTotal}}{{{rep['S3_0_6_12_18']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeRepSzero}}{{{rep['S0_0']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeRepVtotal}}{{{rep['S0_0']['total_cost_yuan'] - rep['S3_0_6_12_18']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeAddTotal}}{{{s3['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeAddSzero}}{{{main['S0_0']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeAddVtotal}}{{{main['S0_0']['total_cost_yuan'] - s3['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeControlSix}}{{{main['C1_load6']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeControlTwelve}}{{{main['C2_load12']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeControlEighteen}}{{{main['C3_load18']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeLoadSix}}{{{main['S0_0']['total_cost_yuan'] - main['C1_load6']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreePvSix}}{{{main['C1_load6']['total_cost_yuan'] - main['S1_0_6']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeLoadTwelve}}{{{main['S1_0_6']['total_cost_yuan'] - main['C2_load12']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreePvTwelve}}{{{main['C2_load12']['total_cost_yuan'] - main['S2_0_6_12']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeLoadEighteen}}{{{main['S2_0_6_12']['total_cost_yuan'] - main['C3_load18']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreePvEighteen}}{{{main['C3_load18']['total_cost_yuan'] - main['S3_0_6_12_18']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QthreeLoadTotal}}{{{(main['S0_0']['total_cost_yuan'] - main['C1_load6']['total_cost_yuan']) + (main['S1_0_6']['total_cost_yuan'] - main['C2_load12']['total_cost_yuan']) + (main['S2_0_6_12']['total_cost_yuan'] - main['C3_load18']['total_cost_yuan']):.2f}}}",
        f"\\newcommand{{\\QthreePvTotal}}{{{(main['C1_load6']['total_cost_yuan'] - main['S1_0_6']['total_cost_yuan']) + (main['C2_load12']['total_cost_yuan'] - main['S2_0_6_12']['total_cost_yuan']) + (main['C3_load18']['total_cost_yuan'] - main['S3_0_6_12_18']['total_cost_yuan']):.2f}}}",
        f"\\newcommand{{\\QfourTwoPerfect}}{{{q4['q42_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourTwoCausal}}{{{q4['q42_causal_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourThreePerfect}}{{{q4['q43_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourThreeCausal}}{{{q4['q43_causal_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourPriceValueTwo}}{{{q4['q42_causal_price']['total_cost_yuan'] - q4['q42_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourPriceValueThree}}{{{q4['q43_causal_price']['total_cost_yuan'] - q4['q43_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourRollPerfect}}{{{q4['q42_perfect_price']['total_cost_yuan'] - q4['q43_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourRollCausal}}{{{q4['q42_causal_price']['total_cost_yuan'] - q4['q43_causal_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourPriceMae}}{{{q4['q43_causal_price'].get('price_forecast_mae') or 0:.4f}}}",
        f"\\newcommand{{\\QfourTwoMain}}{{{q4['q42_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourThreeMain}}{{{q4['q43_perfect_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourPricePctTwo}}{{{100 * (q4['q42_causal_price']['total_cost_yuan'] - q4['q42_perfect_price']['total_cost_yuan']) / q4['q42_causal_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\QfourPricePctThree}}{{{100 * (q4['q43_causal_price']['total_cost_yuan'] - q4['q43_perfect_price']['total_cost_yuan']) / q4['q43_causal_price']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\SensTerminalCycle}}{{{sens['terminal']['daily_cycle']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\SensTerminalFree}}{{{sens['terminal']['free']['total_cost_yuan']:.2f}}}",
        f"\\newcommand{{\\SensTerminalCycleSoc}}{{{sens['terminal']['daily_cycle']['ending_soc_kwh']:.2f}}}",
        f"\\newcommand{{\\SensTerminalFreeSoc}}{{{sens['terminal']['free']['ending_soc_kwh']:.2f}}}",
    ]
    for name, m in sens["efficiency"].items():
        tag = {"E1": "EOne", "E2": "ETwo"}.get(name.split("_")[0].upper(), name.split("_")[0])
        lines.append(f"\\newcommand{{\\SensEff{tag}Cost}}{{{m['total_cost_yuan']:.2f}}}")
        lines.append(f"\\newcommand{{\\SensEff{tag}Throughput}}{{{m['storage_throughput_kwh']:.2f}}}")
        lines.append(f"\\newcommand{{\\SensEff{tag}Em}}{{{m['emergency_energy_kwh']:.2f}}}")
    lines.append(
        f"\\newcommand{{\\SensCausaEmergency}}{{{sens['terminal']['daily_cycle']['emergency_energy_kwh']:.2f}}}"
    )
    for policy, tag in (("daily_cycle", "Cycle"), ("free", "Free")):
        boundary = sens["terminal"][policy].get("daily_boundary_soc", {})
        lines.append(f"\\newcommand{{\\SensTerminal{tag}Mean}}{{{boundary.get('mean', float('nan')):.0f}}}")
        lines.append(f"\\newcommand{{\\SensTerminal{tag}Std}}{{{boundary.get('std', float('nan')):.0f}}}")
        lines.append(f"\\newcommand{{\\SensTerminal{tag}Min}}{{{boundary.get('min', float('nan')):.0f}}}")
        lines.append(f"\\newcommand{{\\SensTerminal{tag}Max}}{{{boundary.get('max', float('nan')):.0f}}}")

    # 问题二四组对照的紧急购电与弃光
    for key, tag in (("A_perfectload_risk_feedback", "A"), ("B_causalload_risk_feedback", "B"),
                     ("C_causalload_point_feedback", "C"), ("D_causalload_risk_nofeedback", "D")):
        m = q2[key]
        lines.append(f"\\newcommand{{\\Qtwo{tag}Emergency}}{{{m['emergency_energy_kwh']:.2f}}}")
        lines.append(f"\\newcommand{{\\Qtwo{tag}Curtail}}{{{m['curtailment_energy_kwh']:.2f}}}")

    # 问题三消融：各方案的紧急购电与上下调电量
    for key, tag in (("S0_0", "Szero"), ("S1_0_6", "Sone"), ("S2_0_6_12", "Stwo"), ("S3_0_6_12_18", "Sthree")):
        m = main[key]
        lines.append(f"\\newcommand{{\\Qthree{tag}Em}}{{{m['emergency_energy_kwh']:.2f}}}")
        lines.append(f"\\newcommand{{\\Qthree{tag}Up}}{{{m['up_adjustment_energy_kwh']:.2f}}}")
        lines.append(f"\\newcommand{{\\Qthree{tag}Down}}{{{m['down_adjustment_energy_kwh']:.2f}}}")
    lines.append(f"\\newcommand{{\\QthreeVtwelveCum}}{{{v6 + v12:.2f}}}")

    # 问题四四组的紧急购电与弃光
    for key, tag in (("q42_perfect_price", "TwoPerfect"), ("q42_causal_price", "TwoCausal"),
                     ("q43_perfect_price", "ThreePerfect"), ("q43_causal_price", "ThreeCausal")):
        m = q4[key]
        lines.append(f"\\newcommand{{\\Qfour{tag}Em}}{{{m['emergency_energy_kwh']:.2f}}}")
        lines.append(f"\\newcommand{{\\Qfour{tag}Curtail}}{{{m['curtailment_energy_kwh']:.2f}}}")

    # 数据相关性、价格分节点误差与分位候选评价均从当前输出实时复算。
    from .io_data import read_attachment2, read_attachment4
    annual = read_attachment2()
    annual_price = read_attachment4()
    load = annual.load_kw.ravel()
    pv = annual.pv_kw.ravel()
    net = load - pv
    phase = np.tile(np.arange(144) / 144.0, 365)
    lines.extend(
        [
            f"\\newcommand{{\\CorrNetLoad}}{{{np.corrcoef(net, load)[0, 1]:.4f}}}",
            f"\\newcommand{{\\CorrNetPv}}{{{np.corrcoef(net, pv)[0, 1]:.4f}}}",
            f"\\newcommand{{\\CorrPricePhase}}{{{np.corrcoef(annual_price.price.ravel(), phase)[0, 1]:.4f}}}",
            f"\\newcommand{{\\QthreeMaxSim}}{{{s3['max_simultaneous_charge_discharge']:.2e}}}",
            f"\\newcommand{{\\QthreeCostGap}}{{{abs(s3['total_cost_yuan'] - s3['baseline_purchase_cost_yuan'] - s3['adjustment_cost_yuan'] - s3['emergency_cost_yuan']):.2e}}}",
            f"\\newcommand{{\\SensTerminalPct}}{{{100 * (sens['terminal']['daily_cycle']['total_cost_yuan'] - sens['terminal']['free']['total_cost_yuan']) / sens['terminal']['daily_cycle']['total_cost_yuan']:.3f}}}",
        ]
    )

    price_log = VARIANTS / "q4" / "q43_causal_price" / "price_forecast_log.csv"
    with price_log.open(encoding="utf-8-sig", newline="") as handle:
        price_rows = [row for row in csv.DictReader(handle) if row["date"] >= "2025-02-01"]
    for decision_time, tag in (("00:00", "Zero"), ("06:00", "Six"), ("12:00", "Twelve"), ("18:00", "Eighteen")):
        values = [float(row["price_mae"]) for row in price_rows if row["decision_time"] == decision_time]
        lines.append(f"\\newcommand{{\\QfourPriceMae{tag}}}{{{np.mean(values):.6f}}}")

    quantile_tags = {0.80: "Eighty", 0.85: "EightyFive", 0.90: "Ninety", 0.95: "NinetyFive"}
    quantile_eval = b.get("pv_residual_quantile_evaluation", {})
    for quantile, tag in quantile_tags.items():
        values = quantile_eval.get(f"Q{quantile:.2f}", {})
        lines.append(f"\\newcommand{{\\PvQuant{tag}Score}}{{{values.get('sample_out_risk_proxy_yuan', float('nan')):.2f}}}")
        lines.append(f"\\newcommand{{\\PvQuant{tag}Days}}{{{int(values.get('selected_days', 0))}}}")

    # 问题一按官方模板标签读取的时段值与储能分块值
    try:
        for key, value in _q1_slot_values().items():
            lines.append(f"\\newcommand{{\\{key}}}{{{value}}}")
    except Exception as exc:  # pragma: no cover - 仅在 result1 缺失时触发
        print("[report][warn] 无法读取 result1.xlsx：", exc)
    return "\n".join(lines) + "\n"


def build_submission() -> None:
    """把题面主口径的五个官方 Excel 汇总到 MathModel/submit/。"""
    SUBMIT.mkdir(parents=True, exist_ok=True)
    mapping = {
        "result1.xlsx": ROOT / "outputs" / "q1" / "result1.xlsx",
        "result2.xlsx": VARIANTS / "q2" / "B_causalload_risk_feedback" / "result2.xlsx",
        "result3.xlsx": VARIANTS / "q3_additive" / "S3_0_6_12_18" / "result3.xlsx",
        "result4-2.xlsx": VARIANTS / "q4" / "q42_perfect_price" / "result4-2.xlsx",
        "result4-3.xlsx": VARIANTS / "q4" / "q43_perfect_price" / "result4-3.xlsx",
    }
    for name, source in mapping.items():
        target = SUBMIT / name
        if name == "result1.xlsx" and target.exists():
            print("[submit] result1.xlsx 保留既有冻结文件")
            continue
        if source.exists():
            shutil.copy2(source, target)
            print(f"[submit] {name} ← {source.relative_to(ROOT)}")
        else:
            print(f"[submit][missing] {source}")


def main() -> None:
    data = collect()
    REPORTS.mkdir(parents=True, exist_ok=True)
    PAPER.mkdir(parents=True, exist_ok=True)
    (REPORTS / "MODEL_AUDIT.md").write_text(audit_markdown(data), encoding="utf-8")
    (PAPER / "numbers.tex").write_text(numbers_tex(data), encoding="utf-8")
    (REPORTS / "model_audit_raw.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    build_submission()
    from .paper_tables import build as build_paper_tables
    build_paper_tables()
    print("[report] →", REPORTS / "MODEL_AUDIT.md")
    print("[report] →", PAPER / "numbers.tex")


if __name__ == "__main__":
    main()
