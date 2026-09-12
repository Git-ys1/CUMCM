"""从最终逐时输出自动生成题面指定日期的 LaTeX 表格。"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "outputs" / "variants" / "model_audit"
GENERATED = ROOT / "paper" / "generated"
TEMPLATE = ROOT.parent / "CUMCM2026Problems" / "C题" / "附件" / "附件5" / "result2.xlsx"
DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")
INTERVALS = ("10:00-10:10", "12:00-12:10", "14:00-14:10", "16:00-16:10", "18:00-18:10", "20:00-20:10")
PERIODS = ("0:00--4:00", "4:00--8:00", "8:00--12:00", "12:00--16:00", "16:00--20:00", "20:00--24:00")

SOURCES = {
    "q2": VARIANTS / "q2" / "B_causalload_risk_feedback",
    "q3": VARIANTS / "q3_additive" / "S3_0_6_12_18",
    "q42": VARIANTS / "q4" / "q42_perfect_price",
    "q43": VARIANTS / "q4" / "q43_perfect_price",
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _slot_indices() -> dict[str, int]:
    workbook = openpyxl.load_workbook(TEMPLATE, data_only=True, read_only=True)
    headers = list(next(workbook.worksheets[0].iter_rows(min_row=1, max_row=1, values_only=True)))
    workbook.close()
    # 官方模板第 2 列对应逐时数组下标 0；以模板表头定位，避免手工时标偏移。
    return {label: headers.index(label) - 1 for label in INTERVALS}


def emergency_segments(values: np.ndarray, tol: float = 1e-7) -> list[tuple[str, float]]:
    output: list[tuple[str, float]] = []
    start = None

    def stamp(slot: int) -> str:
        minutes = slot * 10
        return "24:00" if minutes == 1440 else f"{minutes // 60}:{minutes % 60:02d}"

    for index, active in enumerate(np.r_[np.asarray(values, dtype=float) > tol, False]):
        if active and start is None:
            start = index
        elif not active and start is not None:
            output.append((f"{stamp(start)}--{stamp(index)}", float(np.sum(values[start:index]))))
            start = None
    return output


def _dataset(key: str) -> tuple[dict[str, list[dict[str, str]]], dict[str, dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in _rows(SOURCES[key] / "solution.csv"):
        grouped[row["date"]].append(row)
    daily = {row["date"]: row for row in _rows(SOURCES[key] / "daily_metrics.csv")}
    missing = [date for date in DATES if date not in grouped or date not in daily]
    if missing:
        raise ValueError(f"{key} 缺少指定日期：{missing}")
    return grouped, daily


def _purchase_table(key: str, caption: str, label: str, adjusted: bool) -> str:
    grouped, daily = _dataset(key)
    indices = _slot_indices()
    lines = [
        r"\begin{table}[htbp]",
        r"\centering\zihao{-5}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\resizebox{\textwidth}{!}{%",
    ]
    if adjusted:
        lines += [
            r"\begin{tabular}{c c r r r r r r r r}",
            r"\toprule",
            r"日期 & 口径 & 10:00 & 12:00 & 14:00 & 16:00 & 18:00 & 20:00 & 全天/kWh & 费用/元 \\",
            r"\midrule",
        ]
    else:
        lines += [
            r"\begin{tabular}{c r r r r r r r r}",
            r"\toprule",
            r"日期 & 10:00 & 12:00 & 14:00 & 16:00 & 18:00 & 20:00 & 全天/kWh & 计划费/元 \\",
            r"\midrule",
        ]
    for date in DATES:
        day = grouped[date]
        drow = daily[date]
        if adjusted:
            for row_index, (name, column, cost_field) in enumerate(
                (("计划", "baseline_grid_kwh", "baseline_cost"), ("调整", "adjusted_grid_kwh", "settlement_cost"))
            ):
                values = [float(day[indices[item]][column]) for item in INTERVALS]
                total = sum(float(row[column]) for row in day)
                date_cell = rf"\multirow{{2}}{{*}}{{{date}}}" if row_index == 0 else ""
                lines.append(
                    f"{date_cell} & {name} & " + " & ".join(f"{value:.2f}" for value in values)
                    + f" & {total:.2f} & {float(drow[cost_field]):.2f} \\\\"
                )
        else:
            values = [float(day[indices[item]]["grid_plan_kwh"]) for item in INTERVALS]
            total = sum(float(row["grid_plan_kwh"]) for row in day)
            lines.append(
                f"{date} & " + " & ".join(f"{value:.2f}" for value in values)
                + f" & {total:.2f} & {float(drow['plan_cost']):.2f} \\\\"
            )
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    return "\n".join(lines)


def _storage_table(key: str, caption: str, label: str) -> str:
    grouped, daily = _dataset(key)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering\zihao{-5}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{c r r r r r r r r}",
        r"\toprule",
        r"日期 & \multicolumn{6}{c}{各 4 h 时段充电量/放电量（kWh）} & $S_{0:00}$ & $S_{24:00}$ \\",
        r"\cmidrule(lr){2-7}",
        "日期 & " + " & ".join(PERIODS) + r" & kWh & kWh \\",
        r"\midrule",
    ]
    for date in DATES:
        day = grouped[date]
        charge = np.asarray([float(row["charge_actual_kwh"]) for row in day])
        discharge = np.asarray([float(row["discharge_actual_kwh"]) for row in day])
        pairs = [f"{charge[i * 24:(i + 1) * 24].sum():.2f}/{discharge[i * 24:(i + 1) * 24].sum():.2f}" for i in range(6)]
        lines.append(
            f"{date} & " + " & ".join(pairs)
            + f" & {float(daily[date]['soc_initial']):.2f} & {float(daily[date]['soc_terminal']):.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}}", r"\end{table}"]
    return "\n".join(lines)


def _emergency_table(key: str, caption: str, label: str) -> str:
    grouped, daily = _dataset(key)
    lines = [
        r"\begin{table}[htbp]",
        r"\centering\zihao{-5}",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\begin{tabularx}{0.98\textwidth}{c >{\raggedright\arraybackslash}X r r}",
        r"\toprule",
        r"日期 & 紧急购电时段及对应电量/kWh & 合计/kWh & 当日总费用/元 \\",
        r"\midrule",
    ]
    for date in DATES:
        day = grouped[date]
        segments = emergency_segments(np.asarray([float(row["emergency_kwh"]) for row in day]))
        description = "无" if not segments else "；".join(f"{period}（{value:.2f}）" for period, value in segments)
        total = sum(value for _, value in segments)
        lines.append(f"{date} & {description} & {total:.2f} & {float(daily[date]['total_cost']):.2f} \\\\ ")
    lines += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    return "\n".join(lines)


def _bundle(key: str, title: str, prefix: str, adjusted: bool) -> str:
    return "\n\n".join(
        (
            _purchase_table(key, f"{title}指定日期购电结果", f"tab:{prefix}-purchase", adjusted),
            _storage_table(key, f"{title}指定日期储能结果", f"tab:{prefix}-storage"),
            _emergency_table(key, f"{title}指定日期紧急购电结果", f"tab:{prefix}-emergency"),
        )
    ) + "\n"


def build() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    outputs = {
        "q2_required_tables.tex": _bundle("q2", "问题二", "q2-required", False),
        "q3_required_tables.tex": _bundle("q3", "问题三", "q3-required", True),
        "q4_required_tables.tex": (
            _bundle("q42", "问题四对应问题二", "q42-required", False)
            + "\n"
            + _bundle("q43", "问题四对应问题三", "q43-required", True)
        ),
    }
    for name, content in outputs.items():
        path = GENERATED / name
        path.write_text("% 由 MathModel.solve.paper_tables 自动生成，勿手工修改。\n" + content, encoding="utf-8")
        print("[table]", path)


if __name__ == "__main__":
    build()
