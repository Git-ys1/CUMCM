"""prob01 计划购电策略求解器（formulation_v001 / assumption_v001）。

主模型 M1：确定性单日日前 MILP（并网点侧计量口径）
    min  Cost_day = sum_t price_t * q_t
    s.t. (C1) q_t + pv_t*dt + D_t - C_t - curtail_t = load_t*dt
         (C2) E_t = E_{t-1} + eta_ch*C_t - D_t/eta_dis
         (C3) Emin <= E_t <= Emax
         (C4) E_144 = E_0 = 6000
         (C5) 0 <= C_t, D_t <= Pbar = Pmax*dt
         (C6) C_t <= Pbar*y_t, D_t <= Pbar*(1-y_t), y_t in {0,1}
         (C7) q_t >= 0
         (C8) 0 <= curtail_t <= pv_t*dt

辅助模型 M2：去掉 (C6) 与 y 的 LP 松弛，仅用于下界与退化诊断（不得作为交付解）。

阶段边界：本脚本只应由 computation 阶段的隔离 task（supervised worker）以完整实例调用；
implementation 阶段只允许 `--smoke` 的小规模合成实例接口探针，不读取附件 1、不运行竞赛实例。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

DATA_COLUMNS = ["时间", "电价", "小区负载", "光伏发电预测功率"]

DEFAULT_PARAMS = {
    "Ecap": 12000.0,
    "Emin": 1200.0,
    "Emax": 10800.0,
    "Pmax": 5000.0,
    "eta_ch": 0.90,
    "eta_dis": 0.90,
    "E0": 6000.0,
}

# formulation_v001 §8 在查看结果前固定的比较标准。
COST_DAY_LOWER_BOUND = 20622.7344
COST_DAY_FEASIBLE_UPPER_BOUND = 48052.0466
BALANCE_TOLERANCE = 1.0e-6
SOC_TOLERANCE = 1.0e-6
COMPLEMENTARITY_TOLERANCE = 1.0e-9
LP_STRICT_BETTER_EPS = 1.0e-7

PAPER_TABLE1_PERIODS = {
    "10:00-10:10": 61,
    "12:00-12:10": 73,
    "14:00-14:10": 85,
    "16:00-16:10": 97,
    "18:00-18:10": 109,
    "20:00-20:10": 121,
}
RULE_TABLE2_BLOCKS = [
    ("0:00-4:00", 1, 24),
    ("4:00-8:00", 25, 48),
    ("8:00-12:00", 49, 72),
    ("12:00-16:00", 73, 96),
    ("16:00-20:00", 97, 120),
    ("20:00-24:00", 121, 144),
]


def project_root() -> Path:
    """从脚本位置向上寻找项目根（含 AGENTS.md），避免个人绝对路径进入产物。"""
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file():
            return parent
    return Path(__file__).resolve().parents[6]


def relative_path(path: Path) -> str:
    root = project_root()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def format_clock(minutes: int) -> str:
    if minutes >= 24 * 60:
        return "24:00"
    return f"{minutes // 60}:{minutes % 60:02d}"


def period_label(t: int) -> str:
    """第 t 个 10 分钟时段的物理区间标签 ((t-1)/6, t/6]，t=1..144。"""
    return f"{format_clock(10 * (t - 1))}-{format_clock(10 * t)}"


def label_minutes(value: object) -> int | None:
    """把附件 1 的时间标签解析为「距 0:00 的分钟数」（右端点口径）。"""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if "0:00+1" in text or text.startswith("24:"):
            return 24 * 60
        parts = text.split(":")
        if len(parts) < 2:
            return None
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return int(value.hour) * 60 + int(value.minute)
    return None


def load_problem_data(path: Path) -> dict:
    """只读读取附件 1 并校验结构、取值与时间标签口径。"""
    if not path.is_file():
        raise FileNotFoundError(f"输入数据不存在：{path}")
    frame = pd.read_excel(path, sheet_name=0)
    missing = [name for name in DATA_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"附件 1 缺少列：{missing}；实际列={list(frame.columns)}")
    frame = frame[DATA_COLUMNS]
    periods = int(len(frame))
    if periods != 144:
        raise ValueError(f"附件 1 期望 144 行时段，实际 {periods} 行")
    price = frame["电价"].to_numpy(dtype=float)
    load = frame["小区负载"].to_numpy(dtype=float)
    pv = frame["光伏发电预测功率"].to_numpy(dtype=float)
    if not np.all(np.isfinite(np.concatenate([price, load, pv]))):
        raise ValueError("附件 1 存在 NaN/Inf")
    if float(np.min(price)) < 0 or float(np.min(load)) < 0 or float(np.min(pv)) < 0:
        raise ValueError("附件 1 存在负的电价/负载/光伏功率")
    raw_labels = frame["时间"].tolist()
    for index, raw in enumerate(raw_labels, start=1):
        minutes = label_minutes(raw)
        if minutes is None:
            raise ValueError(f"无法解析附件 1 第 {index} 行时间标签：{raw!r}")
        if minutes != 10 * index:
            raise ValueError(f"附件 1 第 {index} 行时间标签与右端点口径不符：{raw!r}")
    return {
        "series": {"price": price, "load": load, "pv": pv},
        "labels": [str(item) for item in raw_labels],
        "periods": periods,
        "columns": list(frame.columns),
    }


def build_model(series: dict, params: dict, *, dt: float, relaxation: bool) -> dict:
    """构造 M1（relaxation=False）或 M2（relaxation=True，去掉 (C6) 与 y）。"""
    price = np.asarray(series["price"], dtype=float)
    load = np.asarray(series["load"], dtype=float)
    pv = np.asarray(series["pv"], dtype=float)
    periods = len(price)
    pbar = float(params["Pmax"]) * dt
    eta_ch = float(params["eta_ch"])
    eta_dis = float(params["eta_dis"])
    e0 = float(params["E0"])

    blocks = ["q", "C", "D", "E", "curtail"] if relaxation else ["q", "C", "D", "E", "curtail", "y"]
    size = periods * len(blocks)
    offset = {name: index * periods for index, name in enumerate(blocks)}

    lower = np.full(size, -np.inf)
    upper = np.full(size, np.inf)
    lower[offset["q"] : offset["q"] + periods] = 0.0
    lower[offset["C"] : offset["C"] + periods] = 0.0
    upper[offset["C"] : offset["C"] + periods] = pbar
    lower[offset["D"] : offset["D"] + periods] = 0.0
    upper[offset["D"] : offset["D"] + periods] = pbar
    lower[offset["E"] : offset["E"] + periods] = float(params["Emin"])
    upper[offset["E"] : offset["E"] + periods] = float(params["Emax"])
    lower[offset["curtail"] : offset["curtail"] + periods] = 0.0
    upper[offset["curtail"] : offset["curtail"] + periods] = pv * dt
    if not relaxation:
        lower[offset["y"] : offset["y"] + periods] = 0.0
        upper[offset["y"] : offset["y"] + periods] = 1.0

    objective = np.zeros(size)
    objective[offset["q"] : offset["q"] + periods] = price
    integrality = np.zeros(size, dtype=int)
    if not relaxation:
        integrality[offset["y"] : offset["y"] + periods] = 1

    eq_rows: list[int] = []
    eq_cols: list[int] = []
    eq_data: list[float] = []
    eq_lower: list[float] = []
    eq_upper: list[float] = []

    def add_eq(entries: list[tuple[int, float]], value: float) -> None:
        row = len(eq_lower)
        for column, coefficient in entries:
            if coefficient == 0.0:
                continue
            eq_rows.append(row)
            eq_cols.append(int(column))
            eq_data.append(float(coefficient))
        eq_lower.append(float(value))
        eq_upper.append(float(value))

    for t in range(periods):
        add_eq(
            [
                (offset["q"] + t, 1.0),
                (offset["D"] + t, 1.0),
                (offset["C"] + t, -1.0),
                (offset["curtail"] + t, -1.0),
            ],
            load[t] * dt - pv[t] * dt,
        )
    for t in range(periods):
        entries = [
            (offset["E"] + t, 1.0),
            (offset["C"] + t, -eta_ch),
            (offset["D"] + t, 1.0 / eta_dis),
        ]
        if t > 0:
            entries.append((offset["E"] + t - 1, -1.0))
        add_eq(entries, e0 if t == 0 else 0.0)
    add_eq([(offset["E"] + periods - 1, 1.0)], e0)

    matrix_eq = csr_matrix((eq_data, (eq_rows, eq_cols)), shape=(len(eq_lower), size))
    constraints = [LinearConstraint(matrix_eq, np.array(eq_lower), np.array(eq_upper))]

    ub_rows: list[int] = []
    ub_cols: list[int] = []
    ub_data: list[float] = []
    ub_upper: list[float] = []
    if not relaxation:
        for t in range(periods):
            row = len(ub_upper)
            ub_rows.extend([row, row])
            ub_cols.extend([offset["C"] + t, offset["y"] + t])
            ub_data.extend([1.0, -pbar])
            ub_upper.append(0.0)
        for t in range(periods):
            row = len(ub_upper)
            ub_rows.extend([row, row])
            ub_cols.extend([offset["D"] + t, offset["y"] + t])
            ub_data.extend([1.0, pbar])
            ub_upper.append(pbar)
    if ub_upper:
        matrix_ub = csr_matrix((ub_data, (ub_rows, ub_cols)), shape=(len(ub_upper), size))
        constraints.append(LinearConstraint(matrix_ub, np.full(len(ub_upper), -np.inf), np.array(ub_upper)))

    return {
        "objective": objective,
        "integrality": integrality,
        "bounds": Bounds(lower, upper),
        "constraints": constraints,
        "blocks": blocks,
        "offset": offset,
        "periods": periods,
        "size": size,
        "num_equalities": len(eq_lower),
        "num_inequalities": len(ub_upper),
        "pbar": pbar,
        "dt": dt,
    }


def solve_model(model: dict, *, mode: str, time_limit: float | None, mip_gap: float) -> dict:
    options: dict = {"disp": False, "presolve": True}
    if time_limit:
        options["time_limit"] = float(time_limit)
    if mode == "milp":
        options["mip_rel_gap"] = float(mip_gap)
    started = time.perf_counter()
    result = milp(
        c=model["objective"],
        integrality=model["integrality"] if mode == "milp" else None,
        bounds=model["bounds"],
        constraints=model["constraints"],
        options=options,
    )
    runtime = time.perf_counter() - started
    return {
        "mode": mode,
        "status": int(result.status),
        "success": bool(result.success),
        "message": str(result.message),
        "objective": None if result.fun is None else float(result.fun),
        "best_bound": optional_float(getattr(result, "mip_dual_bound", None)),
        "mip_gap": optional_float(getattr(result, "mip_gap", None)),
        "node_count": optional_float(getattr(result, "mip_node_count", None)),
        "runtime_seconds": runtime,
        "solution": None if result.x is None else np.asarray(result.x, dtype=float),
        "num_variables": int(model["size"]),
        "num_equalities": int(model["num_equalities"]),
        "num_inequalities": int(model["num_inequalities"]),
    }


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def evaluate_solution(solution: np.ndarray, model: dict, series: dict, params: dict) -> dict:
    """回代硬约束并计算交付指标，输出原始数值与门禁判定。"""
    periods = model["periods"]
    offset = model["offset"]
    dt = model["dt"]
    pbar = model["pbar"]
    e0 = float(params["E0"])
    eta_ch = float(params["eta_ch"])
    eta_dis = float(params["eta_dis"])
    price = np.asarray(series["price"], dtype=float)
    load = np.asarray(series["load"], dtype=float)
    pv = np.asarray(series["pv"], dtype=float)

    q = solution[offset["q"] : offset["q"] + periods]
    charge = solution[offset["C"] : offset["C"] + periods]
    discharge = solution[offset["D"] : offset["D"] + periods]
    energy = solution[offset["E"] : offset["E"] + periods]
    curtail = solution[offset["curtail"] : offset["curtail"] + periods]
    mutual = solution[offset["y"] : offset["y"] + periods] if "y" in offset else None

    balance = q + pv * dt + discharge - charge - curtail - load * dt
    soc_prev = np.concatenate([[e0], energy[:-1]])
    soc_residual = energy - (soc_prev + eta_ch * charge - discharge / eta_dis)
    complementarity = np.minimum(charge, discharge)
    all_values = np.concatenate([q, charge, discharge, energy, curtail])
    nan_inf = int(np.count_nonzero(~np.isfinite(all_values)))

    metrics = {
        "periods": int(periods),
        "dt_hours": dt,
        "cost_day": float(np.dot(price, q)),
        "q_day": float(np.sum(q)),
        "curtail_total": float(np.sum(curtail)),
        "charge_total": float(np.sum(charge)),
        "discharge_total": float(np.sum(discharge)),
        "E_0": e0,
        "E_144": float(energy[-1]),
        "table1_q": {name: float(q[t - 1]) for name, t in PAPER_TABLE1_PERIODS.items() if t <= periods},
        "table2_blocks": [
            {
                "label": label,
                "charge": float(np.sum(charge[start - 1 : min(end, periods)])),
                "discharge": float(np.sum(discharge[start - 1 : min(end, periods)])),
            }
            for label, start, end in RULE_TABLE2_BLOCKS
            if start <= periods
        ],
        "curtail_periods": [int(index + 1) for index in np.nonzero(curtail > 1e-9)[0]],
        "cost_lower_bound": COST_DAY_LOWER_BOUND,
        "cost_feasible_upper_bound": COST_DAY_FEASIBLE_UPPER_BOUND,
    }
    residuals = {
        "balance_max_abs": float(np.max(np.abs(balance))),
        "soc_max_abs": float(np.max(np.abs(soc_residual))),
        "energy_bound_violation": float(
            max(
                0.0,
                float(params["Emin"]) - float(np.min(energy)),
                float(np.max(energy)) - float(params["Emax"]),
            )
        ),
        "terminal_residual": float(abs(energy[-1] - e0)),
        "power_upper_violation": float(max(0.0, float(np.max(charge)) - pbar, float(np.max(discharge)) - pbar)),
        "complementarity_max_min": float(np.max(complementarity)),
        "nonnegativity_violation": float(max(0.0, -float(np.min(q)), -float(np.min(curtail)))),
        "nan_inf_count": nan_inf,
    }
    gates = {
        "balance": residuals["balance_max_abs"] <= BALANCE_TOLERANCE,
        "soc": residuals["soc_max_abs"] <= SOC_TOLERANCE,
        "energy_bounds": residuals["energy_bound_violation"] <= SOC_TOLERANCE,
        "terminal": residuals["terminal_residual"] <= SOC_TOLERANCE,
        "power_upper": residuals["power_upper_violation"] <= SOC_TOLERANCE,
        "complementarity": residuals["complementarity_max_min"] <= COMPLEMENTARITY_TOLERANCE,
        "nonnegativity": residuals["nonnegativity_violation"] <= SOC_TOLERANCE,
        "finite": nan_inf == 0,
    }
    gates["all_pass"] = all(gates.values())
    metrics["cost_in_bounds"] = bool(COST_DAY_LOWER_BOUND <= metrics["cost_day"] <= COST_DAY_FEASIBLE_UPPER_BOUND)
    return {
        "metrics": metrics,
        "residuals": residuals,
        "gates": gates,
        "series": {"q": q, "C": charge, "D": discharge, "E": energy, "curtail": curtail, "y": mutual},
    }


def write_solution_csv(path: Path, evaluation: dict, series: dict, labels: list[str], periods: int) -> None:
    frame = pd.DataFrame(
        {
            "t": np.arange(1, periods + 1),
            "time_label": [period_label(t) for t in range(1, periods + 1)],
            "source_label": labels,
            "price": series["price"],
            "load_kw": series["load"],
            "pv_kw": series["pv"],
            "q_kwh": evaluation["series"]["q"],
            "charge_kwh": evaluation["series"]["C"],
            "discharge_kwh": evaluation["series"]["D"],
            "E_kwh": evaluation["series"]["E"],
            "curtail_kwh": evaluation["series"]["curtail"],
        }
    )
    if evaluation["series"]["y"] is not None:
        frame["y_binary"] = evaluation["series"]["y"]
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_result_workbook(path: Path, evaluation: dict) -> None:
    """按 asm-12（歧义 A9）的行序对应规则写 result1.xlsx，并重写为物理区间标签。"""
    from openpyxl import Workbook

    periods = int(evaluation["metrics"]["periods"])
    workbook = Workbook()
    plan = workbook.active
    plan.title = "计划购电量"
    plan.append(["时间段", "购电量"])
    for t in range(1, periods + 1):
        plan.append([period_label(t), float(evaluation["series"]["q"][t - 1])])

    storage = workbook.create_sheet("充放电量")
    storage.append(["时间段", "充电量", "放电量", "时刻", "储电量"])
    storage_rows = []
    for index, block in enumerate(evaluation["metrics"]["table2_blocks"]):
        extras = ["", ""]
        if index == 0:
            extras = ["0:00", evaluation["metrics"]["E_0"]]
        elif index == 1:
            extras = ["24:00", evaluation["metrics"]["E_144"]]
        storage_rows.append([block["label"], block["charge"], block["discharge"], extras[0], extras[1]])
    if len(storage_rows) == 1:
        storage_rows.append(["", "", "", "24:00", evaluation["metrics"]["E_144"]])
    for row in storage_rows:
        storage.append(row)
    workbook.save(path)


def write_solution_artifacts(output_dir: Path, evaluation: dict, series: dict, labels: list[str], periods: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_solution_csv(output_dir / "solution.csv", evaluation, series, labels, periods)
    write_result_workbook(output_dir / "result1.xlsx", evaluation)
    with (output_dir / "solution.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "q_kwh": evaluation["series"]["q"].tolist(),
                "charge_kwh": evaluation["series"]["C"].tolist(),
                "discharge_kwh": evaluation["series"]["D"].tolist(),
                "E_kwh": evaluation["series"]["E"].tolist(),
                "curtail_kwh": evaluation["series"]["curtail"].tolist(),
                "y_binary": None if evaluation["series"]["y"] is None else evaluation["series"]["y"].tolist(),
                "time_labels": [period_label(t) for t in range(1, periods + 1)],
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {"metrics": evaluation["metrics"], "residuals": evaluation["residuals"], "gates": evaluation["gates"]},
            handle,
            ensure_ascii=False,
            indent=2,
        )


def run_summary(run: dict, evaluation: dict | None) -> dict:
    entry = {
        "status": run["status"],
        "success": run["success"],
        "message": run["message"],
        "objective": run["objective"],
        "best_bound": run["best_bound"],
        "mip_gap": run["mip_gap"],
        "node_count": run["node_count"],
        "runtime_seconds": run["runtime_seconds"],
        "num_variables": run["num_variables"],
        "num_equalities": run["num_equalities"],
        "num_inequalities": run["num_inequalities"],
        "incumbent_found": run["solution"] is not None,
    }
    if evaluation is not None:
        entry.update(
            {
                "cost_day": evaluation["metrics"]["cost_day"],
                "q_day": evaluation["metrics"]["q_day"],
                "curtail_total": evaluation["metrics"]["curtail_total"],
                "complementarity_max_min": evaluation["residuals"]["complementarity_max_min"],
                "gates_all_pass": evaluation["gates"]["all_pass"],
                "feasible_incumbent": evaluation["gates"]["all_pass"],
            }
        )
    return entry


def synthetic_smoke_instance() -> dict:
    """小规模合成实例（非竞赛数据），用于接口探针。"""
    return {
        "price": np.array([0.40, 0.90, 1.20, 0.50, 0.30, 0.80]),
        "load": np.array([40.0, 55.0, 70.0, 60.0, 45.0, 50.0]),
        "pv": np.array([0.0, 10.0, 90.0, 80.0, 5.0, 0.0]),
    }


def smoke_params() -> dict:
    params = dict(DEFAULT_PARAMS)
    params.update({"Ecap": 100.0, "Emin": 10.0, "Emax": 90.0, "Pmax": 120.0, "E0": 50.0})
    return params


def run_smoke(output_dir: Path, args: argparse.Namespace) -> int:
    series = synthetic_smoke_instance()
    labels = [format_clock(10 * (index + 1)) for index in range(len(series["price"]))]
    params = smoke_params()
    dt = 1.0 / 6.0
    report = {"mode": "smoke", "periods": len(series["price"]), "models": {}}
    healthy = True
    for mode in ("milp", "lp"):
        model = build_model(series, params, dt=dt, relaxation=(mode == "lp"))
        run = solve_model(model, mode=mode, time_limit=args.time_limit, mip_gap=args.mip_gap)
        evaluation = None if run["solution"] is None else evaluate_solution(run["solution"], model, series, params)
        report["models"][mode] = run_summary(run, evaluation)
        healthy = healthy and evaluation is not None and evaluation["gates"]["all_pass"] and run["status"] == 0
        if mode == "milp" and evaluation is not None:
            write_solution_artifacts(output_dir, evaluation, series, labels, model["periods"])
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "smoke_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if healthy else 4


def run_full(args: argparse.Namespace) -> int:
    if not args.output:
        print("完整实例必须提供 --output（须与 task spec 的 output_directory 一致）")
        return 2
    data_path = Path(args.data)
    output_dir = Path(args.output)
    loaded = load_problem_data(data_path)
    params = dict(DEFAULT_PARAMS)
    dt = 1.0 / 6.0
    modes = ("milp", "lp") if args.mode == "both" else (args.mode,)
    primary_mode = "milp" if "milp" in modes else modes[0]
    report: dict = {
        "problem_id": "CUMCM2026-C",
        "question_id": "prob01",
        "formulation_version": "formulation_v001",
        "assumption_version": "assumption_v001",
        "seed": args.seed,
        "modes": {},
    }
    models: dict = {}
    evaluations: dict = {}
    runs: dict = {}
    for mode in modes:
        model = build_model(loaded["series"], params, dt=dt, relaxation=(mode == "lp"))
        run = solve_model(model, mode=mode, time_limit=args.time_limit, mip_gap=args.mip_gap)
        evaluation = (
            None if run["solution"] is None else evaluate_solution(run["solution"], model, loaded["series"], params)
        )
        models[mode], runs[mode], evaluations[mode] = model, run, evaluation
        report["modes"][mode] = run_summary(run, evaluation)

    if primary_mode in evaluations and evaluations[primary_mode] is not None:
        primary_model = models[primary_mode]
        write_solution_artifacts(
            output_dir, evaluations[primary_mode], loaded["series"], loaded["labels"], primary_model["periods"]
        )
    else:
        primary_model = models[primary_mode]

    # M1 vs M2 比较指标（formulation_v001 §8）。
    comparison = {"milp": report["modes"].get("milp"), "lp": report["modes"].get("lp")}
    if "milp" in evaluations and "lp" in evaluations and evaluations["milp"] and evaluations["lp"]:
        milp_cost = evaluations["milp"]["metrics"]["cost_day"]
        lp_cost = evaluations["lp"]["metrics"]["cost_day"]
        comparison.update(
            {
                "lp_objective": lp_cost,
                "milp_objective": milp_cost,
                "lp_le_milp": bool(lp_cost <= milp_cost + LP_STRICT_BETTER_EPS),
                "lp_strictly_better": bool(lp_cost < milp_cost - LP_STRICT_BETTER_EPS),
                "lp_max_min_charge_discharge": evaluations["lp"]["residuals"]["complementarity_max_min"],
            }
        )
    report["comparison"] = comparison

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_run = runs[primary_mode]
    primary_eval = evaluations.get(primary_mode)
    status = {
        "solver": "scipy.optimize.milp/HiGHS",
        "mode": primary_mode,
        "status": primary_run["status"],
        "success": bool(primary_run["status"] == 0),
        "message": primary_run["message"],
        "objective": primary_run["objective"],
        "best_bound": primary_run["best_bound"],
        "mip_gap": primary_run["mip_gap"],
        "node_count": primary_run["node_count"],
        "runtime_seconds": primary_run["runtime_seconds"],
        "num_variables": primary_run["num_variables"],
        "num_equalities": primary_run["num_equalities"],
        "num_inequalities": primary_run["num_inequalities"],
        "pbar_kwh": primary_model["pbar"],
        "seed": args.seed,
        "feasible_incumbent": bool(primary_eval is not None and primary_eval["gates"]["all_pass"]),
        "incumbent_found": primary_run["solution"] is not None,
    }
    with (output_dir / "solver_status.json").open("w", encoding="utf-8") as handle:
        json.dump(status, handle, ensure_ascii=False, indent=2)
    with (output_dir / "run_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    manifest = {
        "problem_id": "CUMCM2026-C",
        "question_id": "prob01",
        "stage": "computation",
        "assumption_version": "assumption_v001",
        "formulation_version": "formulation_v001",
        "model_id": "M1_dayahead_milp" if primary_mode == "milp" else "M2_lp_relaxation",
        "data_path": relative_path(data_path),
        "code_path": relative_path(Path(__file__)),
        "code_sha256": sha256_file(Path(__file__)),
        "data_sha256": sha256_file(data_path),
        "seed": args.seed,
        "time_limit_seconds": args.time_limit,
        "mip_gap": args.mip_gap,
        "output_directory": relative_path(output_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
    }
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status["feasible_incumbent"] else 3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="prob01 计划购电策略求解器（M1 MILP + M2 LP 对照，formulation_v001）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data", default="data/附件1.xlsx", help="附件 1 输入文件路径")
    parser.add_argument("--output", help="输出目录；完整实例必须显式给出且与 task spec 一致")
    parser.add_argument("--mode", choices=("milp", "lp", "both"), default="both", help="求解模式")
    parser.add_argument("--seed", type=int, default=20260101, help="随机种子（本模型确定性，仅登记）")
    parser.add_argument("--time-limit", type=float, default=300.0, help="求解时限（秒），0 表示不限")
    parser.add_argument("--mip-gap", type=float, default=1.0e-4, help="MILP 相对 gap 目标")
    parser.add_argument("--smoke", action="store_true", help="只跑小规模合成实例接口探针，不读取附件 1")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.smoke:
        output_dir = Path(args.output) if args.output else Path("runtime/tmp/prob01_smoke")
        return run_smoke(output_dir, args)
    return run_full(args)


if __name__ == "__main__":
    raise SystemExit(main())
