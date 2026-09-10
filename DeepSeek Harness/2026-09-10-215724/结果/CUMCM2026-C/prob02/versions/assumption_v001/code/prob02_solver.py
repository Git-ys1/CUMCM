"""prob02 两阶段「0:00 计划—实际补救」求解器（formulation_v001 / assumption_v001）。

主模型 M1（计划层 + 执行层闭式投影）
    计划层（每个交付日 d 独立求解一个 144 时段 MILP，0:00 预报口径）
        min  Cost_plan_d = sum_t price_t * q_dt
        s.t. (C1) q_dt + pvfc_dt*dt + D_dt - C_dt - kappa_dt = load_dt*dt
             (C2) E_dt = E_d,t-1 + eta_ch*C_dt - D_dt/eta_dis
             (C3) Emin <= E_dt <= Emax
             (C4) E_d,0 = E_d,144 = 6000
             (C5) 0 <= C_dt, D_dt <= Pbar = Pmax*dt
             (C6) C_dt <= Pbar*y_dt, D_dt <= Pbar*(1-y_dt), y_dt in {0,1}
             (C7) q_dt >= 0
             (C8) 0 <= kappa_dt <= pvfc_dt*dt
    执行层（无新决策，formulation.md 式 (R) 的唯一闭式投影）
        s_dt = kappa*_dt + (pv_dt - pvfc_dt)*dt
        u_dt = max(0, -s_dt)          # 紧急购电（5 倍电价）
        kappa_act_dt = max(0, s_dt)   # 实际弃光
        Cost_em_d = alpha_em * sum_t price_t * u_dt
        Cost_total_d = Cost_plan_d + Cost_em_d

辅助模型 M2：删除 (C6) 与 y 的**真 LP 松弛**，仅用于下界与退化诊断；
交付的 C_dt/D_dt 只能取自 M1 的解（formulation.md §3.4）。

阶段边界：本脚本只应由 computation 阶段的隔离 task（supervised worker）以完整实例调用；
implementation 阶段只允许 `--smoke` 的小规模合成实例接口探针，不读取附件、不运行竞赛实例。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix

PROBLEM_ID = "CUMCM2026-C"
QUESTION_ID = "prob02"
ASSUMPTION_VERSION = "assumption_v001"
FORMULATION_VERSION = "formulation_v001"

PRICE_SHEET = 0
PRICE_COLUMNS = ("时间", "电价")
LOAD_PV_SHEETS = ("小区负载", "光伏发电实际功率")
FORECAST_HOUR_COLUMNS = tuple(f"预报{k}小时" for k in range(1, 25))
FORECAST_HOUR = "0:00"

PERIODS = 144
DT = 1.0 / 6.0
DELIVERY_START = date(2025, 2, 1)
DELIVERY_END = date(2025, 12, 31)
EXPECTED_DAYS = 334

DEFAULT_PARAMS = {
    "Ecap": 12000.0,
    "Emin": 1200.0,
    "Emax": 10800.0,
    "Pmax": 5000.0,
    "eta_ch": 0.90,
    "eta_dis": 0.90,
    "E0": 6000.0,
    "alpha_em": 5.0,
}

# formulation_v001 §7/§8 在查看任何优化结果之前固定的解析界与门禁（不得事后修改）。
COST_PLAN_LOWER_BOUND = 6749147.6122
COST_PLAN_FEASIBLE_UPPER_BOUND = 16565407.2763
COST_EM_UPPER_BOUND = 5815010.6013
COST_TOTAL_LOWER_BOUND = 6660821.0595
Q_PLAN_LOWER_BOUND = 18177074.097

BALANCE_TOLERANCE = 1.0e-6
SOC_TOLERANCE = 1.0e-6
COMPLEMENTARITY_TOLERANCE = 1.0e-9
NONNEG_TOLERANCE = 1.0e-9
INTEGRALITY_TOLERANCE = 1.0e-9
EMERGENCY_ZERO_TOLERANCE = 1.0e-9
LP_STRICT_BETTER_EPS = 1.0e-7
BOUND_TOLERANCE = 1.0e-6

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
KEY_DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")
DELIVERY_ROUNDING = {"energy": 3, "cost": 2}


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


def interval_label(start: int, end: int) -> str:
    return f"{format_clock(10 * (start - 1))}-{format_clock(10 * end)}"


def parse_hhmm(text: str) -> int:
    parts = str(text).strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"无法解析时间标签：{text!r}")
    return int(parts[0]) * 60 + int(parts[1])


def parse_label_minutes(value: object) -> int:
    """把右端点口径的时间标签解析为「距 0:00 的分钟数」。"""
    text = str(value).strip()
    if "+1" in text:
        return parse_hhmm(text.replace("+1", "")) + 24 * 60
    return parse_hhmm(text)


def validate_period_labels(labels: list[str], expected: int) -> None:
    if len(labels) != expected:
        raise ValueError(f"时段标签数量期望 {expected}，实际 {len(labels)}")
    for index, label in enumerate(labels, start=1):
        if parse_label_minutes(label) != 10 * index:
            raise ValueError(f"第 {index} 个时段标签不符合右端点口径：{label!r}")


def load_price_curve(path: Path) -> np.ndarray:
    """只读读取附件 1 的 144 时段电价曲线并校验结构。"""
    if not path.is_file():
        raise FileNotFoundError(f"电价输入不存在：{path}")
    frame = pd.read_excel(path, sheet_name=PRICE_SHEET)
    missing = [name for name in PRICE_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"附件 1 缺少列：{missing}；实际列={list(frame.columns)}")
    if len(frame) != PERIODS:
        raise ValueError(f"附件 1 期望 {PERIODS} 行时段，实际 {len(frame)} 行")
    validate_period_labels([str(item) for item in frame["时间"].tolist()], PERIODS)
    price = frame["电价"].to_numpy(dtype=float)
    if not np.all(np.isfinite(price)):
        raise ValueError("附件 1 电价存在 NaN/Inf")
    if float(np.min(price)) < 0:
        raise ValueError("附件 1 电价存在负值")
    return price


def load_day_series(path: Path) -> dict[date, dict]:
    """只读读取附件 2 的两个工作表，返回 {日期: {load, pv}}（全 365 天）。"""
    if not path.is_file():
        raise FileNotFoundError(f"负载/光伏输入不存在：{path}")
    payload: dict[date, dict[str, np.ndarray]] = {}
    for sheet in LOAD_PV_SHEETS:
        frame = pd.read_excel(path, sheet_name=sheet)
        if frame.shape[1] != PERIODS + 1:
            raise ValueError(f"附件 2「{sheet}」期望 {PERIODS + 1} 列，实际 {frame.shape[1]}")
        date_column = frame.columns[0]
        validate_period_labels([str(item) for item in frame.columns[1:]], PERIODS)
        parsed = pd.to_datetime(frame[date_column], errors="raise").dt.date
        seen: set[date] = set()
        for row_index, day in enumerate(parsed):
            if day in seen:
                raise ValueError(f"附件 2「{sheet}」日期重复：{day}")
            seen.add(day)
            values = frame.iloc[row_index, 1:].to_numpy(dtype=float)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"附件 2「{sheet}」{day} 存在 NaN/Inf")
            if float(np.min(values)) < 0:
                raise ValueError(f"附件 2「{sheet}」{day} 存在负值")
            payload.setdefault(day, {})[sheet] = values
    days: dict[date, dict] = {}
    for day, item in payload.items():
        if set(item) != set(LOAD_PV_SHEETS):
            raise ValueError(f"附件 2 日期 {day} 缺少工作表数据：{sorted(item)}")
        days[day] = {"load": item[LOAD_PV_SHEETS[0]], "pv": item[LOAD_PV_SHEETS[1]]}
    return days


def delivery_dates(day_series: dict[date, dict]) -> list[date]:
    dates = sorted(day for day in day_series if DELIVERY_START <= day <= DELIVERY_END)
    if len(dates) != EXPECTED_DAYS:
        raise ValueError(f"交付窗口期望 {EXPECTED_DAYS} 天，实际 {len(dates)} 天")
    if dates[0] != DELIVERY_START or dates[-1] != DELIVERY_END:
        raise ValueError(f"交付窗口端点不符：{dates[0]} ~ {dates[-1]}")
    return dates


def expand_forecast(values_24h: np.ndarray) -> np.ndarray:
    """formulation.md 式 (E)：pvfc_dt = pvfc_{d,0,ceil(t/6)}，同一小时 6 个时段取同一值。"""
    values = np.asarray(values_24h, dtype=float)
    if values.shape != (24,):
        raise ValueError(f"整点预报期望 24 个小时值，实际 {values.shape}")
    return values[np.arange(PERIODS) // 6]


def load_forecast(path: Path, dates: list[date]) -> dict[date, np.ndarray]:
    """只读附件 3 的 0:00 报表并展开到 144 个 10 分钟时段。"""
    if not path.is_file():
        raise FileNotFoundError(f"光伏预报输入不存在：{path}")
    frame = pd.read_excel(path, sheet_name=0)
    for column in ("日期", "预报时刻", *FORECAST_HOUR_COLUMNS):
        if column not in frame.columns:
            raise ValueError(f"附件 3 缺少列：{column}；实际列={list(frame.columns)}")
    frame["日期"] = pd.to_datetime(frame["日期"].ffill(), errors="raise").dt.date
    subset = frame[frame["预报时刻"].astype(str).str.strip() == FORECAST_HOUR]
    wanted = set(dates)
    result: dict[date, np.ndarray] = {}
    for _, row in subset.iterrows():
        day = row["日期"]
        if day not in wanted:
            continue
        if day in result:
            raise ValueError(f"附件 3 的 {FORECAST_HOUR} 报表日期重复：{day}")
        values = row[list(FORECAST_HOUR_COLUMNS)].to_numpy(dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"附件 3 {day} {FORECAST_HOUR} 报表存在 NaN/Inf")
        if float(np.min(values)) < 0:
            raise ValueError(f"附件 3 {day} {FORECAST_HOUR} 报表存在负值")
        result[day] = expand_forecast(values)
    missing = [day.isoformat() for day in dates if day not in result]
    if missing:
        raise ValueError(f"附件 3 缺少 {FORECAST_HOUR} 报表的交付日期：{missing[:5]}（共 {len(missing)} 天）")
    return result


def validate_template(path: Path) -> dict:
    """只读核验附件 5 result2.xlsx 的三张工作表与计划表规模。"""
    if not path.is_file():
        raise FileNotFoundError(f"交付模板不存在：{path}")
    workbook = pd.ExcelFile(path)
    expected = ("计划购电量", "充放电量", "紧急购电量")
    missing = [name for name in expected if name not in workbook.sheet_names]
    if missing:
        raise ValueError(f"附件 5 缺少工作表：{missing}；实际={workbook.sheet_names}")
    plan = pd.read_excel(path, sheet_name="计划购电量")
    if plan.shape != (EXPECTED_DAYS, PERIODS + 3):
        raise ValueError(f"附件 5「计划购电量」期望 {EXPECTED_DAYS}×{PERIODS + 3}，实际 {plan.shape}")
    charge = pd.read_excel(path, sheet_name="充放电量")
    if list(charge.columns) != ["日期", "时间段", "充电量", "放电量", "时刻", "储电量"]:
        raise ValueError(f"附件 5「充放电量」列名不符：{list(charge.columns)}")
    emergency = pd.read_excel(path, sheet_name="紧急购电量")
    if list(emergency.columns) != ["日期", "购电时间段", "购电量"]:
        raise ValueError(f"附件 5「紧急购电量」列名不符：{list(emergency.columns)}")
    return {
        "sheets": list(workbook.sheet_names),
        "plan_shape": list(plan.shape),
        "charge_columns": [str(item) for item in charge.columns],
        "emergency_columns": [str(item) for item in emergency.columns],
    }


def build_daily_model(
    price: np.ndarray,
    load: np.ndarray,
    pvfc: np.ndarray,
    params: dict,
    *,
    dt: float,
    relaxation: bool,
) -> dict:
    """构造单日 M1（relaxation=False）或 M2（relaxation=True，去掉 (C6) 与 y）。"""
    periods = len(price)
    pbar = float(params["Pmax"]) * dt
    eta_ch = float(params["eta_ch"])
    eta_dis = float(params["eta_dis"])
    e0 = float(params["E0"])

    blocks = ["q", "C", "D", "E", "kappa"] if relaxation else ["q", "C", "D", "E", "kappa", "y"]
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
    lower[offset["kappa"] : offset["kappa"] + periods] = 0.0
    upper[offset["kappa"] : offset["kappa"] + periods] = pvfc * dt
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
                (offset["kappa"] + t, -1.0),
            ],
            load[t] * dt - pvfc[t] * dt,
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

    ineq_rows: list[int] = []
    ineq_cols: list[int] = []
    ineq_data: list[float] = []
    ineq_upper: list[float] = []
    if not relaxation:
        for t in range(periods):
            row = len(ineq_upper)
            ineq_rows.extend([row, row])
            ineq_cols.extend([offset["C"] + t, offset["y"] + t])
            ineq_data.extend([1.0, -pbar])
            ineq_upper.append(0.0)
        for t in range(periods):
            row = len(ineq_upper)
            ineq_rows.extend([row, row])
            ineq_cols.extend([offset["D"] + t, offset["y"] + t])
            ineq_data.extend([1.0, pbar])
            ineq_upper.append(pbar)
    if ineq_upper:
        matrix_ineq = csr_matrix((ineq_data, (ineq_rows, ineq_cols)), shape=(len(ineq_upper), size))
        constraints.append(LinearConstraint(matrix_ineq, np.full(len(ineq_upper), -np.inf), np.array(ineq_upper)))

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
        "num_inequalities": len(ineq_upper),
        "pbar": pbar,
        "dt": dt,
        "big_m": pbar,
    }


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


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


def clean_binary(values: np.ndarray) -> np.ndarray:
    """把求解器数值噪声（|y|<1e-9 或 |y-1|<1e-9）归零/归一，避免交付 -1.5e-15 类噪声。"""
    cleaned = np.array(values, dtype=float, copy=True)
    cleaned[np.abs(cleaned) < 1.0e-9] = 0.0
    cleaned[np.abs(cleaned - 1.0) < 1.0e-9] = 1.0
    return np.clip(cleaned, 0.0, 1.0)


def merge_emergency_segments(values: np.ndarray) -> list[dict]:
    """按 asm-17 合并同一日内连续的紧急购电时段。"""
    segments: list[dict] = []
    start: int | None = None
    total = 0.0
    for index, value in enumerate(values, start=1):
        if value > EMERGENCY_ZERO_TOLERANCE:
            if start is None:
                start = index
            total += float(value)
        elif start is not None:
            segments.append({"start": start, "end": index - 1, "energy": total})
            start = None
            total = 0.0
    if start is not None:
        segments.append({"start": start, "end": len(values), "energy": total})
    return segments


def evaluate_day(
    solution: np.ndarray,
    model: dict,
    run: dict,
    *,
    price: np.ndarray,
    load: np.ndarray,
    pv: np.ndarray,
    pvfc: np.ndarray,
    params: dict,
) -> dict:
    """回代计划层与执行层硬约束，计算单日指标与门禁。"""
    periods = model["periods"]
    offset = model["offset"]
    dt = model["dt"]
    pbar = model["pbar"]
    e0 = float(params["E0"])
    eta_ch = float(params["eta_ch"])
    eta_dis = float(params["eta_dis"])
    alpha_em = float(params["alpha_em"])

    q = solution[offset["q"] : offset["q"] + periods]
    charge = solution[offset["C"] : offset["C"] + periods]
    discharge = solution[offset["D"] : offset["D"] + periods]
    energy = solution[offset["E"] : offset["E"] + periods]
    kappa = solution[offset["kappa"] : offset["kappa"] + periods]
    binary = clean_binary(solution[offset["y"] : offset["y"] + periods]) if "y" in offset else None

    surplus = kappa + (pv - pvfc) * dt
    emergency = np.maximum(0.0, -surplus)
    emergency[emergency < EMERGENCY_ZERO_TOLERANCE] = 0.0
    kappa_act = np.maximum(0.0, surplus)
    kappa_act[kappa_act < EMERGENCY_ZERO_TOLERANCE] = 0.0

    balance_plan = q + pvfc * dt + discharge - charge - kappa - load * dt
    balance_exec = q + emergency + pv * dt + discharge - charge - kappa_act - load * dt
    soc_prev = np.concatenate([[e0], energy[:-1]])
    soc_residual = energy - (soc_prev + eta_ch * charge - discharge / eta_dis)
    integrality_violation = 0.0 if binary is None else float(np.max(np.abs(binary - np.round(binary))))

    all_values = np.concatenate([q, charge, discharge, energy, kappa, emergency, kappa_act])
    nan_inf = int(np.count_nonzero(~np.isfinite(all_values)))

    residuals = {
        "balance_plan_max_abs": float(np.max(np.abs(balance_plan))),
        "balance_exec_max_abs": float(np.max(np.abs(balance_exec))),
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
        "complementarity_max_min": float(np.max(np.minimum(charge, discharge))),
        "exec_complementarity_max": float(np.max(emergency * kappa_act)),
        "nonnegativity_violation": float(max(0.0, -float(np.min(all_values)))),
        "kappa_upper_violation": float(max(0.0, float(np.max(kappa - pvfc * dt)))),
        "kappa_act_upper_violation": float(max(0.0, float(np.max(kappa_act - pv * dt)))),
        "integrality_violation": integrality_violation,
        "nan_inf_count": nan_inf,
    }
    gates = {
        "plan_balance": residuals["balance_plan_max_abs"] <= BALANCE_TOLERANCE,
        "exec_balance": residuals["balance_exec_max_abs"] <= BALANCE_TOLERANCE,
        "soc": residuals["soc_max_abs"] <= SOC_TOLERANCE,
        "energy_bounds": residuals["energy_bound_violation"] <= BOUND_TOLERANCE,
        "terminal": residuals["terminal_residual"] <= SOC_TOLERANCE,
        "power_upper": residuals["power_upper_violation"] <= BOUND_TOLERANCE,
        "complementarity": residuals["complementarity_max_min"] <= COMPLEMENTARITY_TOLERANCE,
        "exec_complementarity": residuals["exec_complementarity_max"] <= COMPLEMENTARITY_TOLERANCE,
        "nonnegativity": residuals["nonnegativity_violation"] <= NONNEG_TOLERANCE,
        "kappa_upper": residuals["kappa_upper_violation"] <= BOUND_TOLERANCE,
        "kappa_act_upper": residuals["kappa_act_upper_violation"] <= BOUND_TOLERANCE,
        "integrality": residuals["integrality_violation"] <= INTEGRALITY_TOLERANCE,
        "finite": nan_inf == 0,
    }
    gates["all_pass"] = all(gates.values())

    segments = merge_emergency_segments(emergency)
    emergency_cost = 0.0
    for segment in segments:
        sl = slice(segment["start"] - 1, segment["end"])
        emergency_cost += alpha_em * float(np.dot(price[sl], emergency[sl]))

    metrics = {
        "periods": int(periods),
        "q_plan": float(np.sum(q)),
        "cost_plan": float(np.dot(price, q)),
        "cost_em": float(alpha_em * np.dot(price, emergency)),
        "emergency_energy": float(np.sum(emergency)),
        "emergency_cost_segments": float(emergency_cost),
        "emergency_periods": int(np.count_nonzero(emergency > EMERGENCY_ZERO_TOLERANCE)),
        "emergency_segments": segments,
        "charge_total": float(np.sum(charge)),
        "discharge_total": float(np.sum(discharge)),
        "curtail_plan_total": float(np.sum(kappa)),
        "curtail_act_total": float(np.sum(kappa_act)),
        "curtail_act_periods": [int(index + 1) for index in np.nonzero(kappa_act > EMERGENCY_ZERO_TOLERANCE)[0]],
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
    }
    metrics["cost_total"] = metrics["cost_plan"] + metrics["cost_em"]
    return {
        "run": run,
        "metrics": metrics,
        "residuals": residuals,
        "gates": gates,
        "series": {
            "q": q,
            "C": charge,
            "D": discharge,
            "E": energy,
            "kappa": kappa,
            "u": emergency,
            "kappa_act": kappa_act,
            "surplus": surplus,
            "y": binary,
        },
    }


def run_smoke_instance() -> tuple[np.ndarray, list[dict], dict, float]:
    """小规模合成实例（非竞赛数据），仅用于接口探针。"""
    dt = DT
    price = np.array([0.40, 0.40, 0.90, 0.90, 1.20, 1.20, 0.50, 0.50, 0.30, 0.30, 0.80, 0.80])
    base = np.array([40.0, 42.0, 45.0, 50.0, 55.0, 58.0, 60.0, 57.0, 52.0, 48.0, 44.0, 41.0])
    forecast = np.array([0.0, 0.0, 5.0, 20.0, 40.0, 60.0, 70.0, 55.0, 30.0, 10.0, 0.0, 0.0])
    deviation = np.array([0.0, 0.0, 2.0, -5.0, -10.0, 5.0, 15.0, -8.0, -4.0, 3.0, 0.0, 0.0])
    days = []
    for offset in range(3):
        days.append(
            {
                "date": date(2025, 1, 1) + timedelta(days=offset),
                "load": base + 2.0 * offset,
                "pv": np.maximum(0.0, forecast + deviation),
                "pvfc": forecast.copy(),
            }
        )
    params = dict(DEFAULT_PARAMS)
    params.update({"Ecap": 100.0, "Emin": 10.0, "Emax": 90.0, "Pmax": 120.0, "E0": 50.0})
    return price, days, params, dt


def run_pipeline(
    price: np.ndarray,
    days: list[dict],
    params: dict,
    *,
    dt: float,
    output_dir: Path,
    args: argparse.Namespace,
    modes: tuple[str, ...],
    enforce_analytic_bounds: bool = True,
) -> int:
    periods = len(price)
    pbar = float(params["Pmax"]) * dt
    dates = [day["date"] for day in days]
    deadline = time.perf_counter() + float(args.total_budget) if args.total_budget and args.total_budget > 0 else None
    primary_mode = "milp" if "milp" in modes else modes[0]

    records: list[dict] = []
    mode_runs: dict[str, list[dict]] = {mode: [] for mode in modes}
    failed_days: list[str] = []
    for day in days:
        day_runs: dict[str, dict] = {}
        day_models: dict[str, dict] = {}
        for mode in modes:
            model = build_daily_model(price, day["load"], day["pvfc"], params, dt=dt, relaxation=(mode == "lp"))
            time_limit = args.time_limit
            if deadline is not None:
                remaining = deadline - time.perf_counter()
                time_limit = max(2.0, min(float(args.time_limit), remaining)) if args.time_limit else remaining
            run = solve_model(model, mode=mode, time_limit=time_limit, mip_gap=args.mip_gap)
            day_models[mode], day_runs[mode] = model, run
            mode_runs[mode].append(run)
        primary_run = day_runs[primary_mode]
        if primary_run["solution"] is None:
            failed_days.append(day["date"].isoformat())
            records.append(
                {
                    "date": day["date"],
                    "load": day["load"],
                    "pv": day["pv"],
                    "pvfc": day["pvfc"],
                    "incumbent": False,
                    "run": primary_run,
                }
            )
            continue
        evaluation = evaluate_day(
            primary_run["solution"],
            day_models[primary_mode],
            primary_run,
            price=price,
            load=day["load"],
            pv=day["pv"],
            pvfc=day["pvfc"],
            params=params,
        )
        records.append(
            {
                "date": day["date"],
                "load": day["load"],
                "pv": day["pv"],
                "pvfc": day["pvfc"],
                "incumbent": True,
                "evaluation": evaluation,
                "lp": day_runs.get("lp"),
                "lp_max_min_charge_discharge": (
                    None
                    if day_runs.get("lp") is None or day_runs["lp"]["solution"] is None
                    else evaluate_day(
                        day_runs["lp"]["solution"],
                        day_models["lp"],
                        day_runs["lp"],
                        price=price,
                        load=day["load"],
                        pv=day["pv"],
                        pvfc=day["pvfc"],
                        params=params,
                    )["residuals"]["complementarity_max_min"]
                ),
            }
        )

    artifacts = build_artifacts(
        price=price,
        records=records,
        mode_runs=mode_runs,
        modes=modes,
        primary_mode=primary_mode,
        params=params,
        dt=dt,
        pbar=pbar,
        output_dir=output_dir,
        args=args,
        failed_days=failed_days,
        periods=periods,
        dates=dates,
        enforce_analytic_bounds=enforce_analytic_bounds,
    )
    write_artifacts(output_dir, artifacts)
    print(json.dumps(artifacts["report"], ensure_ascii=False, indent=2))
    if failed_days:
        return 3
    return 0 if artifacts["status"]["feasible_incumbent"] else 3


def build_artifacts(
    *,
    price: np.ndarray,
    records: list[dict],
    mode_runs: dict[str, list[dict]],
    modes: tuple[str, ...],
    primary_mode: str,
    params: dict,
    dt: float,
    pbar: float,
    output_dir: Path,
    args: argparse.Namespace,
    failed_days: list[str],
    periods: int,
    dates: list[date],
    enforce_analytic_bounds: bool,
) -> dict:
    good = [record for record in records if record.get("incumbent")]
    annual = {
        "days_total": len(records),
        "days_with_incumbent": len(good),
        "days_failed": len(failed_days),
        "failed_days": failed_days,
        "cost_plan": float(sum(record["evaluation"]["metrics"]["cost_plan"] for record in good)),
        "cost_em": float(sum(record["evaluation"]["metrics"]["cost_em"] for record in good)),
        "cost_total": float(sum(record["evaluation"]["metrics"]["cost_total"] for record in good)),
        "q_plan": float(sum(record["evaluation"]["metrics"]["q_plan"] for record in good)),
        "charge_total": float(sum(record["evaluation"]["metrics"]["charge_total"] for record in good)),
        "discharge_total": float(sum(record["evaluation"]["metrics"]["discharge_total"] for record in good)),
        "curtail_plan_total": float(sum(record["evaluation"]["metrics"]["curtail_plan_total"] for record in good)),
        "curtail_act_total": float(sum(record["evaluation"]["metrics"]["curtail_act_total"] for record in good)),
        "emergency_energy": float(sum(record["evaluation"]["metrics"]["emergency_energy"] for record in good)),
        "emergency_periods": int(sum(record["evaluation"]["metrics"]["emergency_periods"] for record in good)),
        "emergency_segments": int(sum(len(record["evaluation"]["metrics"]["emergency_segments"]) for record in good)),
        "days_with_zero_emergency": int(
            sum(1 for record in good if record["evaluation"]["metrics"]["emergency_energy"] <= EMERGENCY_ZERO_TOLERANCE)
        ),
        "curtail_act_period_count": int(
            sum(len(record["evaluation"]["metrics"]["curtail_act_periods"]) for record in good)
        ),
    }

    residual_keys = (
        "balance_plan_max_abs",
        "balance_exec_max_abs",
        "soc_max_abs",
        "energy_bound_violation",
        "terminal_residual",
        "power_upper_violation",
        "complementarity_max_min",
        "exec_complementarity_max",
        "nonnegativity_violation",
        "kappa_upper_violation",
        "kappa_act_upper_violation",
        "integrality_violation",
    )
    residuals = {key: 0.0 for key in residual_keys}
    residuals["nan_inf_count"] = 0
    for record in good:
        for key in residual_keys:
            residuals[key] = max(residuals[key], float(record["evaluation"]["residuals"][key]))
        residuals["nan_inf_count"] += int(record["evaluation"]["residuals"]["nan_inf_count"])

    all_pass = bool(good) and len(good) == len(records)
    for record in good:
        all_pass = all_pass and bool(record["evaluation"]["gates"]["all_pass"])
    gates = {
        "all_days_have_incumbent": len(good) == len(records) and len(records) > 0,
        "hard_constraints": all_pass,
        "cost_plan_in_bounds": bool(
            COST_PLAN_LOWER_BOUND - BOUND_TOLERANCE
            <= annual["cost_plan"]
            <= COST_PLAN_FEASIBLE_UPPER_BOUND + BOUND_TOLERANCE
        )
        if enforce_analytic_bounds
        else True,
        "cost_em_le_upper": bool(annual["cost_em"] <= COST_EM_UPPER_BOUND + BOUND_TOLERANCE)
        if enforce_analytic_bounds
        else True,
        "cost_total_ge_lower": bool(annual["cost_total"] >= COST_TOTAL_LOWER_BOUND - BOUND_TOLERANCE)
        if enforce_analytic_bounds
        else True,
        "q_plan_ge_lower": bool(annual["q_plan"] >= Q_PLAN_LOWER_BOUND - BOUND_TOLERANCE)
        if enforce_analytic_bounds
        else True,
        "terminal_daily_ok": bool(
            all(abs(record["evaluation"]["metrics"]["E_0"] - params["E0"]) <= SOC_TOLERANCE for record in good)
            and all(abs(record["evaluation"]["metrics"]["E_144"] - params["E0"]) <= SOC_TOLERANCE for record in good)
        ),
        "finite": residuals["nan_inf_count"] == 0,
    }
    gates["all_pass"] = all(gates.values())

    comparison: dict = {}
    if "milp" in mode_runs and "lp" in mode_runs:
        milp_runs = [record["evaluation"]["run"] for record in good]
        lp_runs = [record["lp"] for record in good if record.get("lp") is not None]
        milp_objectives = [run["objective"] for run in milp_runs if run["objective"] is not None]
        lp_objectives = [run["objective"] for run in lp_runs if run["objective"] is not None]
        comparable = bool(lp_objectives) and bool(milp_objectives) and len(lp_objectives) == len(milp_objectives)
        if comparable:
            differences = np.array(lp_objectives, dtype=float) - np.array(milp_objectives, dtype=float)
        else:
            differences = None
        lp_min_charge = [
            record["lp_max_min_charge_discharge"]
            for record in good
            if record.get("lp_max_min_charge_discharge") is not None
        ]
        comparison = {
            "milp_objective_total": float(np.sum(milp_objectives)) if milp_objectives else None,
            "lp_objective_total": float(np.sum(lp_objectives)) if lp_objectives else None,
            "lp_minus_milp_max": float(np.max(differences)) if comparable else None,
            "lp_le_milp": bool(np.all(differences <= LP_STRICT_BETTER_EPS)) if comparable else None,
            "lp_strictly_better_days": (
                int(np.count_nonzero(differences < -LP_STRICT_BETTER_EPS)) if comparable else None
            ),
            "lp_max_min_charge_discharge": float(max(lp_min_charge)) if lp_min_charge else None,
        }

    solver_status = {
        "solver": "scipy.optimize.milp/HiGHS",
        "model_id": "M1_twostage_plan_recourse_milp" if primary_mode == "milp" else "M2_lp_relaxation",
        "mode": args.mode,
        "status": 0 if gates["all_days_have_incumbent"] else 3,
        "days_total": len(records),
        "days_with_incumbent": len(good),
        "days_optimal": int(sum(1 for record in good if record["evaluation"]["run"]["status"] == 0)),
        "days_feasible_not_optimal": int(sum(1 for record in good if record["evaluation"]["run"]["status"] == 1)),
        "days_failed": len(failed_days),
        "max_mip_gap": max(
            (record["evaluation"]["run"]["mip_gap"] or 0.0 for record in good),
            default=None,
        ),
        "total_runtime_seconds": float(
            sum(run["runtime_seconds"] for runs in mode_runs.values() for run in runs)
        ),
        "num_variables_per_day": int(records[0]["evaluation"]["run"]["num_variables"]) if good else None,
        "num_equalities_per_day": int(records[0]["evaluation"]["run"]["num_equalities"]) if good else None,
        "num_inequalities_per_day": int(records[0]["evaluation"]["run"]["num_inequalities"]) if good else None,
        "pbar_kwh": pbar,
        "big_m": pbar,
        "seed": args.seed,
        "mip_rel_gap": args.mip_gap,
        "time_limit_seconds_per_day": args.time_limit,
        "total_budget_seconds": args.total_budget,
        "feasible_incumbent": bool(gates["all_days_have_incumbent"] and gates["hard_constraints"]),
        "incumbent_found": bool(gates["all_days_have_incumbent"]),
        "cost_plan": annual["cost_plan"],
        "cost_em": annual["cost_em"],
        "cost_total": annual["cost_total"],
    }

    key_dates: dict = {}
    record_by_date = {record["date"].isoformat(): record for record in records}
    for name in KEY_DATES:
        record = record_by_date.get(name)
        if record is None or not record.get("incumbent"):
            key_dates[name] = {"available": False}
            continue
        evaluation = record["evaluation"]
        key_dates[name] = {
            "available": True,
            "load_kwh": float(np.sum(record["load"]) * dt),
            "pv_actual_kwh": float(np.sum(record["pv"]) * dt),
            "pv_fc0_kwh": float(np.sum(record["pvfc"]) * dt),
            "forecast_shortfall_kwh": float(np.sum(np.maximum(0.0, record["pvfc"] - record["pv"])) * dt),
            "metrics": evaluation["metrics"],
        }

    metrics = {
        "annual": annual,
        "residuals": residuals,
        "gates": gates,
        "key_dates": key_dates,
        "lp_comparison": comparison,
        "analytic_bounds": {
            "applied": enforce_analytic_bounds,
            "cost_plan_lower": COST_PLAN_LOWER_BOUND,
            "cost_plan_feasible_upper": COST_PLAN_FEASIBLE_UPPER_BOUND,
            "cost_em_upper": COST_EM_UPPER_BOUND,
            "cost_total_lower": COST_TOTAL_LOWER_BOUND,
            "q_plan_lower": Q_PLAN_LOWER_BOUND,
        },
    }
    report = {
        "problem_id": PROBLEM_ID,
        "question_id": QUESTION_ID,
        "assumption_version": ASSUMPTION_VERSION,
        "formulation_version": FORMULATION_VERSION,
        "seed": args.seed,
        "modes": {
            mode: {
                "days": len(runs),
                "objective_total": float(np.sum([run["objective"] for run in runs if run["objective"] is not None]))
                if runs
                else None,
                "status_counts": {
                    str(code): int(sum(1 for run in runs if run["status"] == code))
                    for code in sorted({run["status"] for run in runs})
                }
                if runs
                else {},
                "max_mip_gap": max((run["mip_gap"] or 0.0 for run in runs), default=None) if runs else None,
                "runtime_seconds": float(sum(run["runtime_seconds"] for run in runs)) if runs else 0.0,
            }
            for mode, runs in mode_runs.items()
        },
        "comparison": comparison,
        "annual": annual,
        "gates": gates,
        "residuals": residuals,
        "pbar_kwh": pbar,
        "periods": periods,
        "days": len(records),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest = {
        "problem_id": PROBLEM_ID,
        "question_id": QUESTION_ID,
        "stage": "computation",
        "assumption_version": ASSUMPTION_VERSION,
        "formulation_version": FORMULATION_VERSION,
        "model_id": "M1_twostage_plan_recourse_milp" if primary_mode == "milp" else "M2_lp_relaxation",
        "code_path": relative_path(Path(__file__)),
        "code_sha256": sha256_file(Path(__file__)),
        "inputs": input_hashes(args),
        "seed": args.seed,
        "time_limit_seconds_per_day": args.time_limit,
        "total_budget_seconds": args.total_budget,
        "mip_gap": args.mip_gap,
        "output_directory": relative_path(output_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": _scipy_version(),
        "pandas": pd.__version__,
        "delivery_mapping": {
            "result_file": "result2.xlsx",
            "plan_sheet": "计划购电量（列序一一对应模板第 t 列 = 时段 t，标签重写为物理区间）",
            "charge_sheet": "充放电量（每日 7 行：6 个 4 小时块 + 0:00/24:00 储电量）",
            "emergency_sheet": "紧急购电量（按 asm-17 合并连续时段；u=0 的日期显式登记为 0）",
            "rounding": DELIVERY_ROUNDING,
        },
    }
    return {
        "records": records,
        "annual": annual,
        "residuals": residuals,
        "gates": gates,
        "comparison": comparison,
        "status": solver_status,
        "metrics": metrics,
        "report": report,
        "manifest": manifest,
        "key_dates": key_dates,
        "params": params,
        "dt": dt,
        "periods": periods,
        "dates": dates,
        "price": price,
    }


def _scipy_version() -> str:
    import scipy

    return scipy.__version__


def input_hashes(args: argparse.Namespace) -> dict:
    if getattr(args, "smoke", False):
        return {"mode": "smoke", "note": "小规模合成实例，不读取任何附件"}
    hashes: dict = {}
    for key, value in (
        ("price", getattr(args, "price", None)),
        ("load_pv", getattr(args, "load_pv", None)),
        ("forecast", getattr(args, "forecast", None)),
        ("template", getattr(args, "template", None)),
    ):
        if not value:
            continue
        path = Path(str(value))
        hashes[key] = {"path": relative_path(path), "sha256": sha256_file(path)} if path.is_file() else None
    return hashes


def write_artifacts(output_dir: Path, artifacts: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = artifacts["records"]
    periods = artifacts["periods"]

    daily_rows = []
    for record in records:
        if not record.get("incumbent"):
            daily_rows.append({"date": record["date"].isoformat(), "incumbent": False})
            continue
        evaluation = record["evaluation"]
        metrics = evaluation["metrics"]
        run = evaluation["run"]
        daily_rows.append(
            {
                "date": record["date"].isoformat(),
                "incumbent": True,
                "solver_status": run["status"],
                "solver_message": run["message"],
                "objective": run["objective"],
                "best_bound": run["best_bound"],
                "mip_gap": run["mip_gap"],
                "node_count": run["node_count"],
                "runtime_seconds": run["runtime_seconds"],
                "q_plan": metrics["q_plan"],
                "cost_plan": metrics["cost_plan"],
                "emergency_energy": metrics["emergency_energy"],
                "cost_em": metrics["cost_em"],
                "cost_total": metrics["cost_total"],
                "emergency_periods": metrics["emergency_periods"],
                "emergency_segments": len(metrics["emergency_segments"]),
                "charge_total": metrics["charge_total"],
                "discharge_total": metrics["discharge_total"],
                "curtail_plan_total": metrics["curtail_plan_total"],
                "curtail_act_total": metrics["curtail_act_total"],
                "E_0": metrics["E_0"],
                "E_144": metrics["E_144"],
                "gates_all_pass": evaluation["gates"]["all_pass"],
            }
        )
    pd.DataFrame(daily_rows).to_csv(output_dir / "daily_metrics.csv", index=False, encoding="utf-8-sig")

    good = [record for record in records if record.get("incumbent")]
    if good:
        frame = pd.DataFrame(
            {
                "date": np.repeat([record["date"].isoformat() for record in good], periods),
                "t": np.tile(np.arange(1, periods + 1), len(good)),
                "time_label": np.tile([period_label(t) for t in range(1, periods + 1)], len(good)),
                "price": np.tile(np.asarray(artifacts["price"], dtype=float), len(good)),
                "load_kw": np.concatenate([record["load"] for record in good]),
                "pv_kw": np.concatenate([record["pv"] for record in good]),
                "pvfc_kw": np.concatenate([record["pvfc"] for record in good]),
                "q_kwh": np.concatenate([record["evaluation"]["series"]["q"] for record in good]),
                "charge_kwh": np.concatenate([record["evaluation"]["series"]["C"] for record in good]),
                "discharge_kwh": np.concatenate([record["evaluation"]["series"]["D"] for record in good]),
                "E_kwh": np.concatenate([record["evaluation"]["series"]["E"] for record in good]),
                "kappa_plan_kwh": np.concatenate([record["evaluation"]["series"]["kappa"] for record in good]),
                "emergency_kwh": np.concatenate([record["evaluation"]["series"]["u"] for record in good]),
                "kappa_act_kwh": np.concatenate([record["evaluation"]["series"]["kappa_act"] for record in good]),
                "surplus_kwh": np.concatenate([record["evaluation"]["series"]["surplus"] for record in good]),
                "y_binary": np.concatenate([record["evaluation"]["series"]["y"] for record in good]),
            }
        )
        frame.to_csv(output_dir / "solution.csv", index=False, encoding="utf-8-sig", float_format="%.10g")

    segment_rows = []
    for record in good:
        for index, segment in enumerate(record["evaluation"]["metrics"]["emergency_segments"], start=1):
            segment_rows.append(
                {
                    "date": record["date"].isoformat(),
                    "segment_index": index,
                    "start_period": segment["start"],
                    "end_period": segment["end"],
                    "interval": interval_label(segment["start"], segment["end"]),
                    "energy_kwh": segment["energy"],
                }
            )
    if segment_rows:
        pd.DataFrame(segment_rows).to_csv(output_dir / "emergency_segments.csv", index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(
            columns=["date", "segment_index", "start_period", "end_period", "interval", "energy_kwh"]
        ).to_csv(output_dir / "emergency_segments.csv", index=False, encoding="utf-8-sig")

    write_result_workbook(output_dir / "result2.xlsx", records, periods)

    with (output_dir / "solver_status.json").open("w", encoding="utf-8") as handle:
        json.dump(artifacts["status"], handle, ensure_ascii=False, indent=2)
    with (output_dir / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(artifacts["metrics"], handle, ensure_ascii=False, indent=2)
    with (output_dir / "run_report.json").open("w", encoding="utf-8") as handle:
        json.dump(artifacts["report"], handle, ensure_ascii=False, indent=2)
    with (output_dir / "run_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(artifacts["manifest"], handle, ensure_ascii=False, indent=2)


def round_value(value: float, digits: int) -> float:
    return float(np.round(float(value), digits))


def write_result_workbook(path: Path, records: list[dict], periods: int) -> None:
    """按 asm-15/asm-17 的行序对应规则写 result2.xlsx（标签统一为物理区间）。"""
    from openpyxl import Workbook

    energy_digits = DELIVERY_ROUNDING["energy"]
    cost_digits = DELIVERY_ROUNDING["cost"]
    workbook = Workbook()

    plan = workbook.active
    plan.title = "计划购电量"
    plan.append(["日期\\时间", *[period_label(t) for t in range(1, periods + 1)], "全天购电量", "全天购电费"])
    for record in records:
        if not record.get("incumbent"):
            plan.append([record["date"].isoformat(), *[""] * periods, "", ""])
            continue
        metrics = record["evaluation"]["metrics"]
        q = record["evaluation"]["series"]["q"]
        plan.append(
            [
                record["date"].isoformat(),
                *[round_value(value, energy_digits) for value in q],
                round_value(metrics["q_plan"], energy_digits),
                round_value(metrics["cost_plan"], cost_digits),
            ]
        )

    storage = workbook.create_sheet("充放电量")
    storage.append(["日期", "时间段", "充电量", "放电量", "时刻", "储电量"])
    for record in records:
        if not record.get("incumbent"):
            storage.append([record["date"].isoformat(), "", "", "", "", ""])
            continue
        metrics = record["evaluation"]["metrics"]
        blocks = metrics["table2_blocks"]
        for index, block in enumerate(blocks):
            date_text = record["date"].isoformat() if index == 0 else ""
            if index == 0:
                moment, stored = "00:00", round_value(metrics["E_0"], energy_digits)
            elif index == 1:
                moment, stored = "24:00", round_value(metrics["E_144"], energy_digits)
            else:
                moment, stored = "", ""
            storage.append(
                [
                    date_text,
                    block["label"],
                    round_value(block["charge"], energy_digits),
                    round_value(block["discharge"], energy_digits),
                    moment,
                    stored,
                ]
            )
        if len(blocks) == 1:
            storage.append(["", "", "", "", "24:00", round_value(metrics["E_144"], energy_digits)])

    emergency = workbook.create_sheet("紧急购电量")
    emergency.append(["日期", "购电时间段", "购电量"])
    for record in records:
        if not record.get("incumbent"):
            emergency.append([record["date"].isoformat(), "", 0])
            continue
        metrics = record["evaluation"]["metrics"]
        segments = metrics["emergency_segments"]
        if not segments:
            emergency.append([record["date"].isoformat(), "无", 0.0])
            continue
        for index, segment in enumerate(segments):
            emergency.append(
                [
                    record["date"].isoformat() if index == 0 else "",
                    interval_label(segment["start"], segment["end"]),
                    round_value(segment["energy"], energy_digits),
                ]
            )

    workbook.save(path)


def run_full(args: argparse.Namespace) -> int:
    if not args.output:
        print("完整实例必须提供 --output（须与 task spec 的 output_directory 一致）")
        return 2
    price = load_price_curve(Path(args.price))
    day_series = load_day_series(Path(args.load_pv))
    template_info = validate_template(Path(args.template))
    dates = delivery_dates(day_series)
    forecast = load_forecast(Path(args.forecast), dates)
    days = [
        {"date": day, "load": day_series[day]["load"], "pv": day_series[day]["pv"], "pvfc": forecast[day]}
        for day in dates
    ]
    print(
        json.dumps(
            {
                "template": template_info,
                "days": len(days),
                "first_date": dates[0].isoformat(),
                "last_date": dates[-1].isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    modes = ("milp", "lp") if args.mode == "both" else (args.mode,)
    if args.mode == "lp":
        print("交付解只能取自 M1（milp），--mode lp 不能用于交付；请使用 both 或 milp")
        return 2
    return run_pipeline(
        price,
        days,
        dict(DEFAULT_PARAMS),
        dt=DT,
        output_dir=Path(args.output),
        args=args,
        modes=modes,
    )


def run_smoke(args: argparse.Namespace) -> int:
    price, days, params, dt = run_smoke_instance()
    output_dir = Path(args.output) if args.output else Path("runtime/tmp/prob02_smoke")
    code = run_pipeline(
        price,
        days,
        params,
        dt=dt,
        output_dir=output_dir,
        args=args,
        modes=("milp", "lp"),
        enforce_analytic_bounds=False,
    )
    report_path = output_dir / "run_report.json"
    healthy = code == 0 and report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    smoke = {
        "mode": "smoke",
        "periods": len(price),
        "days": len(days),
        "pbar_kwh": float(params["Pmax"]) * dt,
        "returncode": code,
        "healthy": healthy,
        "annual": payload.get("annual"),
        "gates": payload.get("gates"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "smoke_report.json").open("w", encoding="utf-8") as handle:
        json.dump(smoke, handle, ensure_ascii=False, indent=2)
    print(json.dumps(smoke, ensure_ascii=False, indent=2))
    return 0 if healthy else 4


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="prob02 两阶段计划—补救求解器（M1 逐日 MILP + 执行层投影，formulation_v001）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--price", default="data/附件1.xlsx", help="附件 1（电价曲线）路径")
    parser.add_argument("--load-pv", default="data/附件2.xlsx", help="附件 2（小区负载与光伏实际功率）路径")
    parser.add_argument("--forecast", default="data/附件3.xlsx", help="附件 3（光伏预报）路径")
    parser.add_argument("--template", default="data/附件5/result2.xlsx", help="附件 5 交付模板路径（只读核验）")
    parser.add_argument("--output", help="输出目录；完整实例必须显式给出且与 task spec 一致")
    parser.add_argument("--mode", choices=("milp", "lp", "both"), default="both", help="求解模式")
    parser.add_argument("--seed", type=int, default=20260102, help="随机种子（本模型确定性，仅登记）")
    parser.add_argument("--time-limit", type=float, default=120.0, help="单日求解时限（秒），0 表示不限")
    parser.add_argument("--total-budget", type=float, default=1500.0, help="全部日期求解的总预算（秒），0 表示不限")
    parser.add_argument("--mip-gap", type=float, default=1.0e-6, help="MILP 相对 gap 目标（显式设定）")
    parser.add_argument("--smoke", action="store_true", help="只跑小规模合成实例接口探针，不读取附件")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.smoke:
        return run_smoke(args)
    return run_full(args)


if __name__ == "__main__":
    raise SystemExit(main())
