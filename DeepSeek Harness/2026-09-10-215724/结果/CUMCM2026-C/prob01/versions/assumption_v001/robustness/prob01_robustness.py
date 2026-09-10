"""prob01 robustness 情景扫描、汇总与敏感性图生成（assumption_v001 / formulation_v001）。

预注册方案：同目录 `plan.md`（运行前写定，运行后不得改写）。本脚本：

1. 复用**已接受实现** `code/prob01_solver.py` 的 `solve_model`（求解配置逐项一致）与
   `build_model` / `evaluate_solution`（用于 I1 等价性校验）；
2. 用语义等价的广义构造器支持非对称功率上限（asm-05 电池侧计量）与反送上限（asm-03
   允许零收益反送），并用 I1 情景在对称口径下与已接受构造器逐项比对；
3. 执行 `plan.md` §4 的预注册情景矩阵（含 200 次蒙特卡洛输入不确定性探针），输出
   `raw/`、`summary.json`、`summary.csv`、`ci.json`、`figures/`、`run_manifest.json`；
4. 只读附件 1，不修改任何上游产物；**不**在 worker 内登记 figure manifest
   （由 robustness 聚合动作以 `--register-figures` 调用本脚本完成登记）。

用法：
    .venv/Scripts/python.exe prob01_robustness.py --data data/附件1.xlsx \
        --output problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness
    .venv/Scripts/python.exe prob01_robustness.py --probe
    .venv/Scripts/python.exe prob01_robustness.py --register-figures --output <同上>
"""

from __future__ import annotations

# ruff: noqa: E402 -- matplotlib 后端与 MPLCONFIGDIR 必须先于 pyplot 导入设置
import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

PROBLEM = "CUMCM2026-C"
QUESTION = "prob01"
ASSUMPTION = "assumption_v001"
FORMULATION = "formulation_v001"
BASELINE_TASK_ID = "13bf04ee604e54581fa2"
BASELINE_COST_DAY = 35126.94858928963
BASELINE_Q_DAY = 59482.69899835391
ANCHOR_TOL = 1.0e-6
DT = 1.0 / 6.0

ACCEPTED_SOLVER_REL = "problems/CUMCM2026-C/prob01/versions/assumption_v001/code/prob01_solver.py"
RESULT_DIR_REL = "problems/CUMCM2026-C/prob01/versions/assumption_v001/results/prob01_m1_formulation_v001"

BASE_PARAMS = {
    "Emin": 1200.0,
    "Emax": 10800.0,
    "Pmax": 5000.0,
    "eta_ch": 0.90,
    "eta_dis": 0.90,
    "E0": 6000.0,
}

MC_DRAWS = 200
MC_NOISE = 0.05
MC_SEED = 20260101

BALANCE_TOLERANCE = 1.0e-6
SOC_TOLERANCE = 1.0e-6
COMPLEMENTARITY_TOLERANCE = 1.0e-9
M1_M2_GAP_TOLERANCE = 1.0e-7

STABILITY = {
    "C2_assumption_envelope": 0.10,
    "C3_parameter_envelope": 0.25,
    "C4a_no_curtail_share": 0.90,
    "C6_ci_width": 0.15,
    "C6_mean_bias": 0.05,
}

C2_SCENARIOS = [
    "A3_meter_battery_side",
    "A4_allow_zero_revenue_export",
    "B1_E0_4800",
    "B2_E0_7200",
    "C1_roundtrip_0.90",
]


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file():
            return parent
    return Path(__file__).resolve().parents[6]


ROOT = project_root()
ACCEPTED_SOLVER = ROOT / ACCEPTED_SOLVER_REL
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "runtime" / "tmp" / "mplconfig"))


def resolve_out_root(output: str | Path) -> Path:
    """把 `--output` 统一解析为项目根下的绝对路径（语义同 `automm.common.resolve_project_path`）。

    worker 的 cwd 是项目根，但任务命令传入的是相对路径；run_manifest 与 figure 登记
    必须写**项目相对**路径，因此先绝对化再 `relative_to(ROOT)`。attempt-001（task
    cd463874338e3f8a7f16）正是在此处用相对路径调用 `relative_to(ROOT)` 而抛
    `ValueError`，导致 43 情景扫描全部完成后 `run_manifest.json` 未写出。
    """
    candidate = Path(output)
    resolved = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise ValueError(f"输出目录必须位于项目根内：{output}")
    return resolved


def output_rel(out_root: Path) -> str:
    """输出目录的项目相对路径（正斜杠），供 run_manifest 与 figure 登记使用。"""
    return out_root.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_accepted_module() -> Any:
    spec = importlib.util.spec_from_file_location("prob01_solver_accepted", ACCEPTED_SOLVER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载已接受实现：{ACCEPTED_SOLVER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------------------
# 预注册情景矩阵（plan.md §4；运行前固定）
# --------------------------------------------------------------------------------------


def _scale_scenario(sid: str, axis: str, factor: float) -> dict[str, Any]:
    direction = "up" if factor > 1 else "down"
    if axis == "pv":
        direction = "down" if factor > 1 else "up"
    return {
        "id": sid,
        "group": "E_data_perturbation",
        "kind": "parameter_perturbation",
        "covers": ["asm-01", "asm-07"],
        "description": f"{axis} 整体 ×{factor:.2f}",
        "scale": {axis: factor},
        "expect": direction,
    }


def scenario_matrix() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = [
        {
            "id": "A1_baseline",
            "group": "A_structure",
            "kind": "baseline",
            "covers": ["asm-01", "asm-02", "asm-03", "asm-04", "asm-05", "asm-06"],
            "description": "接受版本基线（锚定 Cost_day=35126.94858928963）",
            "expect": "same",
            "expect_tol": ANCHOR_TOL,
            "is_baseline": True,
        },
        {
            "id": "A2_no_storage",
            "group": "A_structure",
            "kind": "no_storage_reference",
            "covers": ["asm-02", "asm-03"],
            "description": "无储能参照（Pmax=0），用于 K3 节省量",
            "params": {"Pmax": 0.0},
            "expect": "up",
        },
        {
            "id": "A3_meter_battery_side",
            "group": "A_structure",
            "kind": "metering_side",
            "covers": ["asm-05"],
            "description": "电池侧计量：充电上限 Pmax*dt/eta_ch，放电上限 Pmax*dt*eta_dis",
            "metering": "battery",
            "expect": "up",
        },
        {
            "id": "A4_allow_zero_revenue_export",
            "group": "A_structure",
            "kind": "curtail_export",
            "covers": ["asm-03"],
            "description": "允许零收益反送：反送上限放宽为 pv*dt + Pmax*dt",
            "allow_export": True,
            "expect": "same",
            "expect_tol": ANCHOR_TOL,
        },
        {
            "id": "A5_lp_relaxation",
            "group": "A_structure",
            "kind": "lp_lower_bound",
            "covers": ["asm-06", "I1"],
            "description": "基线 + M2 真 LP 松弛（下界与退化诊断，K4/I1）",
            "expect": "same",
            "expect_tol": ANCHOR_TOL,
        },
        {
            "id": "B1_E0_4800",
            "group": "B_terminal_bounds",
            "kind": "terminal_endpoint",
            "covers": ["asm-02"],
            "description": "E_0 = E_144 = 4800 kWh",
            "params": {"E0": 4800.0},
            "expect": "up",
        },
        {
            "id": "B2_E0_7200",
            "group": "B_terminal_bounds",
            "kind": "terminal_endpoint",
            "covers": ["asm-02"],
            "description": "E_0 = E_144 = 7200 kWh",
            "params": {"E0": 7200.0},
            "expect": "down",
        },
        {
            "id": "B3_Emax_9600",
            "group": "B_terminal_bounds",
            "kind": "energy_upper_bound",
            "covers": ["asm-08"],
            "description": "E_max = 9600 kWh（收紧运行上界）",
            "params": {"Emax": 9600.0},
            "expect": "not_up",
        },
        {
            "id": "B4_Emax_12000",
            "group": "B_terminal_bounds",
            "kind": "energy_upper_bound",
            "covers": ["asm-08"],
            "description": "E_max = 12000 kWh（= E_cap，非运行上界，仅量化误用方向）",
            "params": {"Emax": 12000.0},
            "expect": "not_up",
        },
        {
            "id": "B5_Emin_1800",
            "group": "B_terminal_bounds",
            "kind": "energy_lower_bound",
            "covers": ["asm-08"],
            "description": "E_min = 1800 kWh（收紧运行下界）",
            "params": {"Emin": 1800.0},
            "expect": "not_down",
        },
        {
            "id": "C1_roundtrip_0.90",
            "group": "C_efficiency",
            "kind": "efficiency_metering",
            "covers": ["asm-04", "alt-01"],
            "description": "往返效率 0.9：单向 eta = sqrt(0.9) = 0.9486833",
            "params": {"eta_ch": math.sqrt(0.9), "eta_dis": math.sqrt(0.9)},
            "expect": "down",
        },
        {
            "id": "C2_eta_0.855",
            "group": "C_efficiency",
            "kind": "efficiency",
            "covers": ["asm-04"],
            "description": "单向效率 -5%：eta = 0.855",
            "params": {"eta_ch": 0.855, "eta_dis": 0.855},
            "expect": "up",
        },
        {
            "id": "C3_eta_0.945",
            "group": "C_efficiency",
            "kind": "efficiency",
            "covers": ["asm-04"],
            "description": "单向效率 +5%：eta = 0.945",
            "params": {"eta_ch": 0.945, "eta_dis": 0.945},
            "expect": "down",
        },
        {
            "id": "C4_eta_0.81",
            "group": "C_efficiency",
            "kind": "efficiency",
            "covers": ["asm-04"],
            "description": "单向效率 -10%：eta = 0.81",
            "params": {"eta_ch": 0.81, "eta_dis": 0.81},
            "expect": "up",
        },
        {
            "id": "C5_eta_0.99",
            "group": "C_efficiency",
            "kind": "efficiency",
            "covers": ["asm-04"],
            "description": "单向效率 +10%：eta = 0.99",
            "params": {"eta_ch": 0.99, "eta_dis": 0.99},
            "expect": "down",
        },
        {
            "id": "D1_Pmax_-10pct",
            "group": "D_power_cap",
            "kind": "power_cap",
            "covers": ["asm-05"],
            "description": "Pmax ×0.90 = 4500 kW",
            "params": {"Pmax": 4500.0},
            "expect": "not_down",
        },
        {
            "id": "D2_Pmax_-20pct",
            "group": "D_power_cap",
            "kind": "power_cap",
            "covers": ["asm-05"],
            "description": "Pmax ×0.80 = 4000 kW",
            "params": {"Pmax": 4000.0},
            "expect": "not_down",
        },
        {
            "id": "D3_Pmax_+10pct",
            "group": "D_power_cap",
            "kind": "power_cap",
            "covers": ["asm-05"],
            "description": "Pmax ×1.10 = 5500 kW",
            "params": {"Pmax": 5500.0},
            "expect": "not_up",
        },
        {
            "id": "D4_Pmax_+20pct",
            "group": "D_power_cap",
            "kind": "power_cap",
            "covers": ["asm-05"],
            "description": "Pmax ×1.20 = 6000 kW",
            "params": {"Pmax": 6000.0},
            "expect": "not_up",
        },
    ]
    factors = (
        (0.95, "-5pct"),
        (0.90, "-10pct"),
        (0.80, "-20pct"),
        (1.05, "+5pct"),
        (1.10, "+10pct"),
        (1.20, "+20pct"),
    )
    for axis, tag in (("price", "price"), ("load", "load"), ("pv", "pv")):
        for factor, suffix in factors:
            sid = f"E_{tag}_{suffix}"
            scenarios.append(_scale_scenario(sid, axis, factor))
    scenarios.extend(
        [
            {
                "id": "F1_price+20_load+20",
                "group": "F_stress_combinations",
                "kind": "combined_stress",
                "covers": ["asm-01", "asm-07"],
                "description": "price ×1.20 且 load ×1.20",
                "scale": {"price": 1.20, "load": 1.20},
                "expect": "up",
            },
            {
                "id": "F2_price-20_load+20",
                "group": "F_stress_combinations",
                "kind": "combined_stress",
                "covers": ["asm-01", "asm-07"],
                "description": "price ×0.80 且 load ×1.20",
                "scale": {"price": 0.80, "load": 1.20},
                "expect": "any",
            },
            {
                "id": "F3_pv-20_load+20",
                "group": "F_stress_combinations",
                "kind": "combined_stress",
                "covers": ["asm-01", "asm-07"],
                "description": "pv ×0.80 且 load ×1.20（供给最紧）",
                "scale": {"pv": 0.80, "load": 1.20},
                "expect": "up",
            },
            {
                "id": "F4_pv+20_load-20",
                "group": "F_stress_combinations",
                "kind": "combined_stress",
                "covers": ["asm-01", "asm-07", "asm-03"],
                "description": "pv ×1.20 且 load ×0.80（余电最多）",
                "scale": {"pv": 1.20, "load": 0.80},
                "expect": "down",
            },
            {
                "id": "F5_price+20_pv+20_load-20",
                "group": "F_stress_combinations",
                "kind": "combined_stress",
                "covers": ["asm-01", "asm-07"],
                "description": "price ×1.20、pv ×1.20、load ×0.80",
                "scale": {"price": 1.20, "pv": 1.20, "load": 0.80},
                "expect": "any",
            },
            {
                "id": "G1_cyclic_shift_1",
                "group": "G_time_label",
                "kind": "time_label_shift",
                "covers": ["asm-12"],
                "description": "price/load/pv 三条曲线整体循环移位 1 个时段（10 分钟）",
                "cyclic_shift": 1,
                "expect": "any",
            },
        ]
    )
    return scenarios


# --------------------------------------------------------------------------------------
# 广义模型构造与回代（与已接受实现语义一致，另支持非对称功率上限与反送上限）
# --------------------------------------------------------------------------------------


def scale_series(
    series: dict[str, np.ndarray],
    scale: dict[str, float] | None,
    shift: int = 0,
) -> dict[str, np.ndarray]:
    result = {}
    for key in ("price", "load", "pv"):
        values = np.asarray(series[key], dtype=float)
        factor = float((scale or {}).get(key, 1.0))
        values = values * factor
        if shift:
            values = np.roll(values, int(shift))
        result[key] = values
    return result


def caps_for(params: dict[str, float], metering: str) -> tuple[float, float]:
    pbar = float(params["Pmax"]) * DT
    if metering == "battery":
        return pbar / float(params["eta_ch"]), pbar * float(params["eta_dis"])
    return pbar, pbar


def curtail_upper_for(series: dict[str, np.ndarray], cap_discharge: float, allow_export: bool) -> np.ndarray:
    upper = np.asarray(series["pv"], dtype=float) * DT
    if allow_export:
        return upper + float(cap_discharge)
    return upper


def build_general(
    series: dict[str, np.ndarray],
    params: dict[str, float],
    *,
    cap_charge: float,
    cap_discharge: float,
    curtail_upper: np.ndarray,
    relaxation: bool,
) -> dict[str, Any]:
    """广义构造器：与已接受 build_model 同语义，另支持非对称功率上限与反送上限。"""
    from scipy.optimize import Bounds, LinearConstraint
    from scipy.sparse import csr_matrix

    price = np.asarray(series["price"], dtype=float)
    load = np.asarray(series["load"], dtype=float)
    periods = len(price)
    eta_ch = float(params["eta_ch"])
    eta_dis = float(params["eta_dis"])
    e0 = float(params["E0"])
    pbar_c = float(cap_charge)
    pbar_d = float(cap_discharge)
    curtail_up = np.asarray(curtail_upper, dtype=float)

    blocks = ["q", "C", "D", "E", "curtail"] if relaxation else ["q", "C", "D", "E", "curtail", "y"]
    size = periods * len(blocks)
    offset = {name: index * periods for index, name in enumerate(blocks)}

    lower = np.full(size, -np.inf)
    upper = np.full(size, np.inf)
    lower[offset["q"] : offset["q"] + periods] = 0.0
    lower[offset["C"] : offset["C"] + periods] = 0.0
    upper[offset["C"] : offset["C"] + periods] = pbar_c
    lower[offset["D"] : offset["D"] + periods] = 0.0
    upper[offset["D"] : offset["D"] + periods] = pbar_d
    lower[offset["E"] : offset["E"] + periods] = float(params["Emin"])
    upper[offset["E"] : offset["E"] + periods] = float(params["Emax"])
    lower[offset["curtail"] : offset["curtail"] + periods] = 0.0
    upper[offset["curtail"] : offset["curtail"] + periods] = curtail_up
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
            load[t] * DT - float(series["pv"][t]) * DT,
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
            ub_data.extend([1.0, -pbar_c])
            ub_upper.append(0.0)
        for t in range(periods):
            row = len(ub_upper)
            ub_rows.extend([row, row])
            ub_cols.extend([offset["D"] + t, offset["y"] + t])
            ub_data.extend([1.0, pbar_d])
            ub_upper.append(pbar_d)
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
        "pbar_charge": pbar_c,
        "pbar_discharge": pbar_d,
        "curtail_upper": curtail_up,
        "dt": DT,
    }


def evaluate_general(
    solution: np.ndarray,
    model: dict[str, Any],
    series: dict[str, np.ndarray],
    params: dict[str, float],
) -> dict[str, Any]:
    """回代硬门禁；与已接受 evaluate_solution 同语义，另含非对称上限与反送上限校验。"""
    periods = int(model["periods"])
    offset = model["offset"]
    pbar_c = float(model["pbar_charge"])
    pbar_d = float(model["pbar_discharge"])
    curtail_up = np.asarray(model["curtail_upper"], dtype=float)
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

    balance = q + pv * DT + discharge - charge - curtail - load * DT
    soc_prev = np.concatenate([[e0], energy[:-1]])
    soc_residual = energy - (soc_prev + eta_ch * charge - discharge / eta_dis)
    complementarity = np.minimum(charge, discharge)
    all_values = np.concatenate([q, charge, discharge, energy, curtail])
    nan_inf = int(np.count_nonzero(~np.isfinite(all_values)))

    metrics = {
        "periods": int(periods),
        "dt_hours": DT,
        "cost_day": float(np.dot(price, q)),
        "q_day": float(np.sum(q)),
        "curtail_total": float(np.sum(curtail)),
        "charge_total": float(np.sum(charge)),
        "discharge_total": float(np.sum(discharge)),
        "E_0": e0,
        "E_144": float(energy[-1]),
        "E_min_seen": float(np.min(energy)),
        "E_max_seen": float(np.max(energy)),
        "curtail_periods": [int(index + 1) for index in np.nonzero(curtail > 1e-9)[0]],
        "charge_bound_binding_periods": int(np.count_nonzero(charge >= pbar_c - 1e-6)),
        "discharge_bound_binding_periods": int(np.count_nonzero(discharge >= pbar_d - 1e-6)),
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
        "power_upper_violation": float(max(0.0, float(np.max(charge)) - pbar_c, float(np.max(discharge)) - pbar_d)),
        "curtail_upper_violation": float(max(0.0, float(np.max(curtail - curtail_up)))),
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
        "curtail_upper": residuals["curtail_upper_violation"] <= SOC_TOLERANCE,
        "complementarity": residuals["complementarity_max_min"] <= COMPLEMENTARITY_TOLERANCE,
        "nonnegativity": residuals["nonnegativity_violation"] <= SOC_TOLERANCE,
        "finite": nan_inf == 0,
    }
    gates["all_pass"] = all(gates.values())
    return {
        "metrics": metrics,
        "residuals": residuals,
        "gates": gates,
        "series": {"q": q, "C": charge, "D": discharge, "E": energy, "curtail": curtail, "y": mutual},
    }


def model_entry(run: dict[str, Any], evaluation: dict[str, Any] | None) -> dict[str, Any]:
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


def solve_scenario(
    scenario: dict[str, Any],
    loaded: dict[str, Any],
    accepted: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    series = scale_series(loaded["series"], scenario.get("scale"), int(scenario.get("cyclic_shift", 0) or 0))
    params = {**BASE_PARAMS, **scenario.get("params", {})}
    metering = str(scenario.get("metering", "grid"))
    cap_charge, cap_discharge = caps_for(params, metering)
    curtail_upper = curtail_upper_for(series, cap_discharge, bool(scenario.get("allow_export")))

    record: dict[str, Any] = {
        "scenario_id": scenario["id"],
        "group": scenario["group"],
        "kind": scenario["kind"],
        "covers": scenario.get("covers", []),
        "description": scenario["description"],
        "scale": scenario.get("scale", {}),
        "params": {key: float(value) for key, value in params.items()},
        "metering": metering,
        "allow_export": bool(scenario.get("allow_export")),
        "cyclic_shift": int(scenario.get("cyclic_shift", 0) or 0),
        "cap_charge_kwh": cap_charge,
        "cap_discharge_kwh": cap_discharge,
        "expect": scenario.get("expect", "any"),
        "expect_tol": float(scenario.get("expect_tol", 1.0e-3)),
        "modes": {},
        "series_file": None,
    }
    evaluations: dict[str, dict[str, Any]] = {}
    for mode in ("milp", "lp"):
        model = build_general(
            series,
            params,
            cap_charge=cap_charge,
            cap_discharge=cap_discharge,
            curtail_upper=curtail_upper,
            relaxation=(mode == "lp"),
        )
        run = accepted.solve_model(model, mode=mode, time_limit=args.time_limit, mip_gap=args.mip_gap)
        evaluation = None if run["solution"] is None else evaluate_general(run["solution"], model, series, params)
        record["modes"][mode] = model_entry(run, evaluation)
        if mode == "milp" and evaluation is not None:
            record["metrics"] = evaluation["metrics"]
            record["residuals"] = evaluation["residuals"]
            record["gates"] = evaluation["gates"]
            if scenario.get("save_series"):
                record["_series"] = {
                    "price": series["price"].tolist(),
                    "load": series["load"].tolist(),
                    "pv": series["pv"].tolist(),
                    "q": evaluation["series"]["q"].tolist(),
                    "C": evaluation["series"]["C"].tolist(),
                    "D": evaluation["series"]["D"].tolist(),
                    "E": evaluation["series"]["E"].tolist(),
                    "curtail": evaluation["series"]["curtail"].tolist(),
                }
        if evaluation is not None:
            evaluations[mode] = evaluation
    if "milp" in evaluations and "lp" in evaluations:
        record["m1_m2"] = {
            "milp_objective": evaluations["milp"]["metrics"]["cost_day"],
            "lp_objective": evaluations["lp"]["metrics"]["cost_day"],
            "lp_le_milp": bool(
                evaluations["lp"]["metrics"]["cost_day"]
                <= evaluations["milp"]["metrics"]["cost_day"] + M1_M2_GAP_TOLERANCE
            ),
            "objective_gap": float(
                evaluations["milp"]["metrics"]["cost_day"] - evaluations["lp"]["metrics"]["cost_day"]
            ),
            "lp_max_min_charge_discharge": evaluations["lp"]["residuals"]["complementarity_max_min"],
        }
    return record


def equivalence_check(loaded: dict[str, Any], accepted: Any, args: argparse.Namespace) -> dict[str, Any]:
    """I1：广义构造器 vs 已接受 build_model/evaluate_solution 的逐项等价性校验（对称口径）。"""
    checks = []
    subset = [
        "A1_baseline",
        "B1_E0_4800",
        "C4_eta_0.81",
        "E_price_+20pct",
        "E_pv_-20pct",
    ]
    by_id = {item["id"]: item for item in scenario_matrix()}
    max_diff = 0.0
    for sid in subset:
        scenario = by_id[sid]
        series = scale_series(loaded["series"], scenario.get("scale"), int(scenario.get("cyclic_shift", 0) or 0))
        params = {**BASE_PARAMS, **scenario.get("params", {})}
        cap_charge, cap_discharge = caps_for(params, "grid")
        curtail_upper = curtail_upper_for(series, cap_discharge, False)

        accepted_model = accepted.build_model(series, params, dt=DT, relaxation=False)
        accepted_run = accepted.solve_model(
            accepted_model, mode="milp", time_limit=args.time_limit, mip_gap=args.mip_gap
        )
        accepted_eval = accepted.evaluate_solution(accepted_run["solution"], accepted_model, series, params)

        general_model = build_general(
            series,
            params,
            cap_charge=cap_charge,
            cap_discharge=cap_discharge,
            curtail_upper=curtail_upper,
            relaxation=False,
        )
        general_run = accepted.solve_model(general_model, mode="milp", time_limit=args.time_limit, mip_gap=args.mip_gap)
        general_eval = evaluate_general(general_run["solution"], general_model, series, params)

        diffs = {
            "cost_day": abs(accepted_eval["metrics"]["cost_day"] - general_eval["metrics"]["cost_day"]),
            "q_day": abs(accepted_eval["metrics"]["q_day"] - general_eval["metrics"]["q_day"]),
            "curtail_total": abs(accepted_eval["metrics"]["curtail_total"] - general_eval["metrics"]["curtail_total"]),
            "balance_residual": abs(
                accepted_eval["residuals"]["balance_max_abs"] - general_eval["residuals"]["balance_max_abs"]
            ),
            "soc_residual": abs(accepted_eval["residuals"]["soc_max_abs"] - general_eval["residuals"]["soc_max_abs"]),
            "complementarity": abs(
                accepted_eval["residuals"]["complementarity_max_min"]
                - general_eval["residuals"]["complementarity_max_min"]
            ),
        }
        worst = max(diffs.values())
        max_diff = max(max_diff, worst)
        checks.append({"scenario_id": sid, "diffs": diffs, "max_abs_diff": worst})
    return {
        "scenario_ids": subset,
        "checks": checks,
        "max_abs_diff": max_diff,
        "margin_keys_equal": bool(max_diff <= 1.0e-9),
    }


def run_monte_carlo(loaded: dict[str, Any], accepted: Any, args: argparse.Namespace) -> dict[str, Any]:
    rng = np.random.default_rng(MC_SEED)
    periods = len(loaded["series"]["price"])
    samples = []
    for draw in range(MC_DRAWS):
        scale = {
            "price": float(1.0 + rng.uniform(-MC_NOISE, MC_NOISE)),
            "load": float(1.0 + rng.uniform(-MC_NOISE, MC_NOISE)),
            "pv": float(1.0 + rng.uniform(-MC_NOISE, MC_NOISE)),
        }
        series = scale_series(loaded["series"], scale)
        params = dict(BASE_PARAMS)
        cap_charge, cap_discharge = caps_for(params, "grid")
        model = build_general(
            series,
            params,
            cap_charge=cap_charge,
            cap_discharge=cap_discharge,
            curtail_upper=curtail_upper_for(series, cap_discharge, False),
            relaxation=False,
        )
        run = accepted.solve_model(model, mode="milp", time_limit=args.time_limit, mip_gap=args.mip_gap)
        evaluation = None if run["solution"] is None else evaluate_general(run["solution"], model, series, params)
        samples.append(
            {
                "draw": draw + 1,
                "price_factor": scale["price"],
                "load_factor": scale["load"],
                "pv_factor": scale["pv"],
                "status": run["status"],
                "cost_day": None if evaluation is None else evaluation["metrics"]["cost_day"],
                "q_day": None if evaluation is None else evaluation["metrics"]["q_day"],
                "curtail_total": None if evaluation is None else evaluation["metrics"]["curtail_total"],
                "gates_all_pass": None if evaluation is None else evaluation["gates"]["all_pass"],
                "periods": periods,
            }
        )
    return {"draws": MC_DRAWS, "noise": MC_NOISE, "seed": MC_SEED, "samples": samples}


def bootstrap_ci(values: np.ndarray, *, seed: int = MC_SEED, resamples: int = 2000) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = np.array([float(np.mean(rng.choice(values, size=values.size, replace=True))) for _ in range(resamples)])
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def direction_of(delta: float, tol: float) -> str:
    if delta > tol:
        return "up"
    if delta < -tol:
        return "down"
    return "same"


def direction_matches(expect: str, observed: str) -> bool:
    if expect == "any":
        return True
    if expect == "same":
        return observed == "same"
    if expect == "not_up":
        return observed in {"down", "same"}
    if expect == "not_down":
        return observed in {"up", "same"}
    return expect == observed


def summarize(
    scenarios: list[dict[str, Any]],
    mc: dict[str, Any],
    equivalence: dict[str, Any],
) -> dict[str, Any]:
    baseline = next(item for item in scenarios if item["scenario_id"] == "A1_baseline")
    baseline_cost = float(baseline["modes"]["milp"]["cost_day"])
    anchor_ok = abs(baseline_cost - BASELINE_COST_DAY) <= ANCHOR_TOL
    no_storage = next(item for item in scenarios if item["scenario_id"] == "A2_no_storage")
    no_storage_cost = float(no_storage["modes"]["milp"]["cost_day"])

    rows = []
    for item in scenarios:
        cost = item["modes"]["milp"].get("cost_day")
        delta = None if cost is None else float(cost) - baseline_cost
        pct = None if delta is None else delta / baseline_cost
        observed = "n/a" if delta is None else direction_of(delta, float(item.get("expect_tol", 1.0e-3)))
        rows.append(
            {
                "scenario_id": item["scenario_id"],
                "group": item["group"],
                "kind": item["kind"],
                "description": item["description"],
                "cost_day": cost,
                "q_day": item["modes"]["milp"].get("q_day"),
                "curtail_total": item["metrics"]["curtail_total"] if "metrics" in item else None,
                "delta_cost": delta,
                "delta_pct": pct,
                "milp_status": item["modes"]["milp"]["status"],
                "milp_gap": item["modes"]["milp"]["mip_gap"],
                "lp_objective": item["modes"]["lp"].get("objective"),
                "gates_all_pass": item["gates"]["all_pass"] if "gates" in item else False,
                "expect": item["expect"],
                "observed_direction": observed,
                "direction_pass": direction_matches(str(item["expect"]), observed),
            }
        )

    c1_violations = [
        row["scenario_id"]
        for row in rows
        if not row["gates_all_pass"] or int(row["milp_status"]) != 0 or row["cost_day"] is None
    ]
    assumption_rows = [row for row in rows if row["scenario_id"] in C2_SCENARIOS]
    c2_limit = STABILITY["C2_assumption_envelope"]
    c2_violations = [
        row["scenario_id"]
        for row in assumption_rows
        if row["delta_pct"] is None or abs(row["delta_pct"]) > c2_limit
    ]
    envelope_groups = {"D_power_cap", "E_data_perturbation", "G_time_label"}
    envelope_rows = [row for row in rows if row["group"] in envelope_groups]
    c3_violations = [
        row["scenario_id"]
        for row in envelope_rows
        if row["delta_pct"] is None or abs(row["delta_pct"]) > STABILITY["C3_parameter_envelope"]
    ]
    no_curtail = [row for row in rows if row["curtail_total"] is not None and row["curtail_total"] <= 1.0e-9]
    c4a_share = len(no_curtail) / max(1, len(rows))
    c4b_violations = [
        row["scenario_id"]
        for row in rows
        if row["scenario_id"] != "A2_no_storage" and (row["cost_day"] is None or row["cost_day"] >= no_storage_cost)
    ]
    baseline_m1_m2 = baseline.get("m1_m2", {})
    c4c_gap = float(baseline_m1_m2.get("objective_gap", float("inf")))
    c4 = {
        "c4a_no_curtail_share": c4a_share,
        "c4a_pass": bool(c4a_share >= STABILITY["C4a_no_curtail_share"]),
        "c4b_all_below_no_storage": bool(not c4b_violations),
        "c4b_violations": c4b_violations,
        "c4c_baseline_m1_m2_gap": c4c_gap,
        "c4c_pass": bool(c4c_gap <= M1_M2_GAP_TOLERANCE),
    }
    c4_pass = bool(c4["c4a_pass"] and c4["c4b_all_below_no_storage"] and c4["c4c_pass"])

    shift_row = next(row for row in rows if row["scenario_id"] == "G1_cyclic_shift_1")
    c5 = {
        "delta_pct": shift_row["delta_pct"],
        "direction": shift_row["observed_direction"],
        "note": "asm-12 整体错位一个时段的影响，仅登记为交付风险，不作为失败判据",
    }

    costs = np.array(
        [sample["cost_day"] for sample in mc["samples"] if sample["cost_day"] is not None], dtype=float
    )
    mc_ok = bool(int(mc["draws"]) > 0 and costs.size == mc["draws"])
    if mc_ok:
        percentile_low = float(np.percentile(costs, 2.5))
        percentile_high = float(np.percentile(costs, 97.5))
    else:
        percentile_low, percentile_high = None, None
    boot_low, boot_high = bootstrap_ci(costs) if mc_ok else (None, None)
    ci_width = None if not mc_ok else (percentile_high - percentile_low) / baseline_cost
    mean_bias = None if not mc_ok else (float(np.mean(costs)) - baseline_cost) / baseline_cost
    c6 = {
        "draws": mc["draws"],
        "noise": mc["noise"],
        "seed": mc["seed"],
        "all_solved": bool(mc_ok),
        "mean_cost": None if not mc_ok else float(np.mean(costs)),
        "std_cost": None if not mc_ok else float(np.std(costs, ddof=1)),
        "percentile_2_5": percentile_low,
        "percentile_97_5": percentile_high,
        "bootstrap_ci_95_mean": [boot_low, boot_high],
        "ci_width_ratio": ci_width,
        "mean_bias_ratio": mean_bias,
        "curtail_positive_draws": int(sum(1 for sample in mc["samples"] if (sample["curtail_total"] or 0.0) > 1e-9)),
        "gate_failures": int(sum(1 for sample in mc["samples"] if sample["gates_all_pass"] is False)),
    }
    c6_pass = bool(
        mc_ok
        and ci_width is not None
        and ci_width <= STABILITY["C6_ci_width"]
        and mean_bias is not None
        and abs(mean_bias) <= STABILITY["C6_mean_bias"]
    )

    if c1_violations:
        verdict = "needs_revision"
        recommended = "mathematical_formulation"
    elif c2_violations or c3_violations:
        verdict = "fragile"
        recommended = "sanity_check"
    elif not c4_pass:
        verdict = "stable_with_caveats"
        recommended = "sanity_check"
    else:
        verdict = "stable"
        recommended = "sanity_check"

    return {
        "baseline": {
            "scenario_id": baseline["scenario_id"],
            "task_id": BASELINE_TASK_ID,
            "cost_day": baseline_cost,
            "expected_cost_day": BASELINE_COST_DAY,
            "anchor_abs_diff": abs(baseline_cost - BASELINE_COST_DAY),
            "anchor_ok": bool(anchor_ok),
            "q_day": baseline["modes"]["milp"]["q_day"],
            "expected_q_day": BASELINE_Q_DAY,
            "curtail_total": baseline["metrics"]["curtail_total"],
        },
        "no_storage_cost_day": no_storage_cost,
        "storage_saving_day": float(no_storage_cost - baseline_cost),
        "storage_saving_ratio": float((no_storage_cost - baseline_cost) / no_storage_cost),
        "rows": rows,
        "criteria": {
            "C1_violations": c1_violations,
            "C1_pass": bool(not c1_violations),
            "C2_threshold": STABILITY["C2_assumption_envelope"],
            "C2_violations": c2_violations,
            "C2_pass": bool(not c2_violations),
            "C3_threshold": STABILITY["C3_parameter_envelope"],
            "C3_violations": c3_violations,
            "C3_pass": bool(not c3_violations),
            "C4": c4,
            "C4_pass": c4_pass,
            "C5": c5,
            "C6": c6,
            "C6_pass": c6_pass,
        },
        "direction_checks": {
            "total": len(rows),
            "passed": int(sum(1 for row in rows if row["direction_pass"])),
            "failed": [row["scenario_id"] for row in rows if not row["direction_pass"]],
        },
        "equivalence": equivalence,
        "verdict": verdict,
        "recommended_next_stage": recommended,
    }


def _pyplot() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    style = yaml.safe_load((ROOT / "config" / "visualization.yaml").read_text(encoding="utf-8"))
    available = {font.name for font in font_manager.fontManager.ttflist}
    chosen = None
    for candidate in [style.get("preferred_font"), *style.get("fallback_fonts", [])]:
        if candidate and candidate in available:
            chosen = candidate
            break
    if chosen is None:
        raise RuntimeError("配置中的中文字体均不可用，禁止生成含中文标签的敏感性图")
    plt.rcParams.update(
        {
            "font.family": chosen,
            "font.size": style.get("font_size", 11),
            "axes.titlesize": style.get("title_size", 14),
            "axes.unicode_minus": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "figure.facecolor": style.get("background", "white"),
            "savefig.facecolor": style.get("background", "white"),
        }
    )
    return plt, style, chosen


def _barh(plt: Any, rows: list[dict[str, Any]], title: str, path: Path, dpi: int, width: float, height: float) -> None:
    labels = [row["scenario_id"] for row in rows]
    values = [100.0 * float(row["delta_pct"]) for row in rows]
    colors = ["#C00000" if value > 0 else "#1F4E79" for value in values]
    figure, axis = plt.subplots(figsize=(width, max(3.5, 0.32 * len(rows))), dpi=dpi)
    axis.barh(labels, values, color=colors, alpha=0.85)
    axis.axvline(0.0, color="#7F8C8D", linewidth=1.0)
    axis.set_xlabel("相对基线的 Cost_day 变化（%）")
    axis.set_title(title)
    for index, value in enumerate(values):
        axis.text(value, index, f" {value:+.2f}%", va="center", ha="left" if value >= 0 else "right", fontsize=8)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def generate_figures(summary: dict[str, Any], mc: dict[str, Any], out_root: Path) -> dict[str, Any]:
    plt, style, font = _pyplot()
    dpi = int(style.get("dpi", 180))
    width = float(style.get("figure_width", 10))
    height = float(style.get("figure_height", 6))
    palette = style.get("palette", {})
    figures_dir = out_root / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    rows = summary["rows"]
    index: list[dict[str, Any]] = []
    errors: list[str] = []
    out_rel = output_rel(out_root)
    summary_rel = f"{out_rel}/summary.json"
    figure_rel_dir = f"{out_rel}/figures"

    def add(file_name: str, kind: str, title: str, caption: str, source: str, y: list[str]) -> None:
        index.append(
            {
                "file": file_name,
                "path": f"{figure_rel_dir}/{file_name}",
                "kind": kind,
                "title": title,
                "caption": caption,
                "source_data": source,
                "y": y,
            }
        )

    try:
        selected = [
            row for row in rows if row["scenario_id"] != "A1_baseline" and row["group"] != "F_stress_combinations"
        ]
        selected = sorted(selected, key=lambda row: float(row["delta_pct"] or 0.0))
        _barh(
            plt,
            selected,
            "prob01 参数与口径扰动的购电费变化（相对基线）",
            figures_dir / "robustness_tornado.png",
            dpi,
            width,
            max(4.0, 0.3 * len(selected)),
        )
        add(
            "robustness_tornado.png",
            "sensitivity_tornado",
            "prob01 参数与口径扰动的购电费变化（相对基线）",
            "每个情景相对接受版本基线的 Cost_day 变化百分比；红色为费用上升、蓝色为下降，0 线为基线。"
            "区间情景覆盖 asm-02 端点、asm-04 效率、asm-05 计量/功率、asm-03 反送与 ±5/10/20% 数据扰动。",
            f"{summary_rel}",
            ["Cost_day 变化率"],
        )
    except Exception as exc:  # noqa: BLE001 - 非关键图表失败降级记录，不阻断扫描
        errors.append(f"robustness_tornado.png: {exc}")

    try:
        if not mc["samples"]:
            raise RuntimeError("探针模式无蒙特卡洛样本，跳过分布图")
        costs = np.array(
            [sample["cost_day"] for sample in mc["samples"] if sample["cost_day"] is not None], dtype=float
        )
        figure, axis = plt.subplots(figsize=(width, height * 0.8), dpi=dpi)
        axis.hist(costs, bins=24, color=palette.get("primary", "#1F4E79"), alpha=0.8, edgecolor="white")
        baseline = float(summary["baseline"]["cost_day"])
        c6_ci = summary["criteria"]["C6"]
        accent = palette.get("accent", "#ED7D31")
        axis.axvline(baseline, color=palette.get("warning", "#C00000"), linewidth=1.6, label="基线 Cost_day")
        axis.axvline(float(c6_ci["percentile_2_5"]), color=accent, linestyle="--", label="2.5% 分位")
        axis.axvline(float(c6_ci["percentile_97_5"]), color=accent, linestyle="--", label="97.5% 分位")
        axis.set_xlabel("Cost_day（元）")
        axis.set_ylabel("样本数")
        axis.set_title(f"输入 ±{100 * mc['noise']:.0f}% 均匀噪声下的 Cost_day 分布（{mc['draws']} 次）")
        axis.legend()
        figure.tight_layout()
        figure.savefig(figures_dir / "robustness_mc_hist.png")
        plt.close(figure)
        add(
            "robustness_mc_hist.png",
            "monte_carlo_histogram",
            f"输入 ±{100 * mc['noise']:.0f}% 均匀噪声下的 Cost_day 分布（{mc['draws']} 次）",
            "price/load/pv 独立 ±5% 均匀乘性噪声下 200 次独立求解的 Cost_day 直方图；"
            "虚线为 2.5%/97.5% 分位，实线为接受版本基线。该探针超出 asm-01 的确定性口径，仅用于给出区间。",
            f"{summary_rel}",
            ["Cost_day 频数"],
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robustness_mc_hist.png: {exc}")

    try:
        endpoint = [row for row in rows if row["group"] == "B_terminal_bounds"]
        figure, axis = plt.subplots(figsize=(width, height * 0.8), dpi=dpi)
        labels = [row["scenario_id"] for row in endpoint]
        values = [100.0 * float(row["delta_pct"]) for row in endpoint]
        axis.bar(labels, values, color=palette.get("secondary", "#70AD47"))
        axis.axhline(0.0, color="#7F8C8D", linewidth=1.0)
        axis.set_ylabel("Cost_day 变化（%）")
        axis.set_title("储电量端点与运行边界敏感性（asm-02 / asm-08）")
        for index_value, value in enumerate(values):
            vertical = "bottom" if value >= 0 else "top"
            axis.text(index_value, value, f"{value:+.2f}%", ha="center", va=vertical, fontsize=9)
        figure.tight_layout()
        figure.savefig(figures_dir / "robustness_endpoint_sensitivity.png")
        plt.close(figure)
        add(
            "robustness_endpoint_sensitivity.png",
            "endpoint_sensitivity",
            "储电量端点与运行边界敏感性（asm-02 / asm-08）",
            "E_0=E_144 ∈ {4800, 6000, 7200}、E_max ∈ {9600, 10800, 12000} 与 E_min=1800 下 Cost_day 相对变化；"
            "基线最优解贴运行上下界，贴界不等于设备余量。",
            f"{summary_rel}",
            ["Cost_day 变化率"],
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robustness_endpoint_sensitivity.png: {exc}")

    try:
        wanted = {
            "A3_meter_battery_side",
            "A4_allow_zero_revenue_export",
            "C1_roundtrip_0.90",
            "C2_eta_0.855",
            "C3_eta_0.945",
            "C4_eta_0.81",
            "C5_eta_0.99",
        }
        selected = [row for row in rows if row["scenario_id"] in wanted]
        figure, axis = plt.subplots(figsize=(width, height * 0.8), dpi=dpi)
        labels = [row["scenario_id"] for row in selected]
        values = [100.0 * float(row["delta_pct"]) for row in selected]
        axis.bar(labels, values, color=palette.get("accent", "#ED7D31"))
        axis.axhline(0.0, color="#7F8C8D", linewidth=1.0)
        axis.set_ylabel("Cost_day 变化（%）")
        axis.set_title("效率口径与计量侧对照（asm-04 / asm-05 / asm-03）")
        for index_value, value in enumerate(values):
            vertical = "bottom" if value >= 0 else "top"
            axis.text(index_value, value, f"{value:+.2f}%", ha="center", va=vertical, fontsize=9)
        figure.tight_layout()
        figure.savefig(figures_dir / "robustness_efficiency_metering.png")
        plt.close(figure)
        add(
            "robustness_efficiency_metering.png",
            "efficiency_metering",
            "效率口径与计量侧对照（asm-04 / asm-05 / asm-03）",
            "往返效率 0.9（单侧 0.9487）、单向效率 ±5%/±10%、电池侧计量与允许零收益反送对 Cost_day 的影响；"
            "零收益反送应与基线完全一致（差值 ≤1e-6 元）。",
            f"{summary_rel}",
            ["Cost_day 变化率"],
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robustness_efficiency_metering.png: {exc}")

    try:
        combos = [
            row for row in rows if row["group"] == "F_stress_combinations" or row["scenario_id"] == "A2_no_storage"
        ]
        figure, axis = plt.subplots(figsize=(width, height * 0.8), dpi=dpi)
        labels = [row["scenario_id"] for row in combos]
        values = [float(row["cost_day"]) for row in combos]
        axis.bar(labels, values, color=palette.get("primary", "#1F4E79"))
        warning = palette.get("warning", "#C00000")
        neutral = palette.get("neutral", "#7F8C8D")
        axis.axhline(float(summary["baseline"]["cost_day"]), color=warning, linestyle="--", label="基线 Cost_day")
        axis.axhline(float(summary["no_storage_cost_day"]), color=neutral, linestyle=":", label="无储能 Cost_day")
        axis.set_ylabel("Cost_day（元）")
        axis.set_title("组合压力情景与储能节省量（K3）")
        axis.legend()
        figure.tight_layout()
        figure.savefig(figures_dir / "robustness_stress_combos.png")
        plt.close(figure)
        add(
            "robustness_stress_combos.png",
            "stress_combinations",
            "组合压力情景与储能节省量（K3）",
            "多参数同向/反向压力情景的 Cost_day 与基线、无储能参照线对比；所有情景均应严格低于无储能费用（C4b）。",
            f"{summary_rel}",
            ["Cost_day"],
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robustness_stress_combos.png: {exc}")

    try:
        series_files = sorted((out_root / "raw" / "series").glob("*.json"))
        if series_files:
            figure, axis = plt.subplots(figsize=(width, height * 0.8), dpi=dpi)
            for path in series_files:
                payload = json.loads(path.read_text(encoding="utf-8"))
                energy = np.asarray(payload["E"], dtype=float)
                axis.plot(np.arange(1, energy.size + 1) / 6.0, energy, label=str(payload["scenario_id"]))
            warning = palette.get("warning", "#C00000")
            axis.axhline(10800.0, color=warning, linestyle="--", linewidth=1.0, label="E_max=10800")
            axis.axhline(1200.0, color=warning, linestyle=":", linewidth=1.0, label="E_min=1200")
            axis.set_xlabel("时刻（小时）")
            axis.set_ylabel("储电量 E_t（kWh）")
            axis.set_title("终端储电量端点情景的储电量轨迹（asm-02）")
            axis.legend(fontsize=8)
            figure.tight_layout()
            figure.savefig(figures_dir / "robustness_dispatch_endpoint.png")
            plt.close(figure)
            add(
                "robustness_dispatch_endpoint.png",
                "dispatch_endpoint_compare",
                "终端储电量端点情景的储电量轨迹（asm-02）",
                "E_0=E_144 ∈ {4800, 6000, 7200} 三种终端取值下的最优储电量轨迹与运行上下界；"
                "轨迹贴界处说明最优解受边界强约束，不得解读为设备余量。",
                f"{summary_rel}",
                ["储电量 E_t"],
            )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"robustness_dispatch_endpoint.png: {exc}")

    payload = {"font": font, "dpi": dpi, "figures": index, "errors": errors}
    (figures_dir / "figure_index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_raw(
    out_root: Path,
    scenarios: list[dict[str, Any]],
    mc: dict[str, Any],
    equivalence: dict[str, Any],
) -> None:
    """原始逐情景记录与逐次蒙特卡洛样本，必须先于汇总与出图落盘。"""
    raw_dir = out_root / "raw"
    series_dir = raw_dir / "series"
    series_dir.mkdir(parents=True, exist_ok=True)
    with (raw_dir / "scenarios.jsonl").open("w", encoding="utf-8") as handle:
        for record in scenarios:
            payload = dict(record)
            series_payload = payload.pop("_series", None)
            if series_payload is not None:
                path = series_dir / f"{record['scenario_id']}.json"
                path.write_text(
                    json.dumps({"scenario_id": record["scenario_id"], **series_payload}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                payload["series_file"] = f"raw/series/{record['scenario_id']}.json"
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    if mc["samples"]:
        pd.DataFrame(mc["samples"]).to_csv(raw_dir / "monte_carlo_samples.csv", index=False, encoding="utf-8-sig")
    (raw_dir / "equivalence_check.json").write_text(
        json.dumps(equivalence, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_outputs(
    out_root: Path,
    loaded: dict[str, Any],
    scenarios: list[dict[str, Any]],
    mc: dict[str, Any],
    equivalence: dict[str, Any],
    summary: dict[str, Any],
    figures: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    crit = summary["criteria"]
    base = summary["baseline"]
    checks = summary["direction_checks"]
    (out_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_rows = pd.DataFrame(
        [
            {
                "scenario_id": row["scenario_id"],
                "group": row["group"],
                "description": row["description"],
                "cost_day": row["cost_day"],
                "delta_cost": row["delta_cost"],
                "delta_pct": row["delta_pct"],
                "curtail_total": row["curtail_total"],
                "milp_status": row["milp_status"],
                "gates_all_pass": row["gates_all_pass"],
                "expect": row["expect"],
                "observed_direction": row["observed_direction"],
                "direction_pass": row["direction_pass"],
            }
            for row in summary["rows"]
        ]
    )
    summary_rows.to_csv(out_root / "summary.csv", index=False, encoding="utf-8-sig")

    envelope_groups = {"D_power_cap", "E_data_perturbation", "G_time_label"}
    envelope_rows = [row for row in summary["rows"] if row["group"] in envelope_groups]
    envelope_pcts = [float(row["delta_pct"]) for row in envelope_rows if row["delta_pct"] is not None]
    ci_payload = {
        "baseline_cost_day": summary["baseline"]["cost_day"],
        "anchor_ok": summary["baseline"]["anchor_ok"],
        "groups": {
            row["scenario_id"]: {"delta_pct": row["delta_pct"]}
            for row in summary["rows"]
        },
        "c2_envelope": {
            "threshold": STABILITY["C2_assumption_envelope"],
            "scenarios": [row for row in summary["rows"] if row["scenario_id"] in C2_SCENARIOS],
        },
        "c3_envelope": {
            "threshold": STABILITY["C3_parameter_envelope"],
            "min_delta_pct": min(envelope_pcts) if envelope_pcts else None,
            "max_delta_pct": max(envelope_pcts) if envelope_pcts else None,
        },
        "monte_carlo": summary["criteria"]["C6"],
        "storage_saving_day": summary["storage_saving_day"],
        "storage_saving_ratio": summary["storage_saving_ratio"],
    }
    (out_root / "ci.json").write_text(json.dumps(ci_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    gaps = [
        float(item["modes"]["milp"]["mip_gap"])
        for item in scenarios
        if item["modes"]["milp"].get("mip_gap") is not None
    ]
    solver_status = {
        "solver": "scipy.optimize.milp/HiGHS",
        "stage": "robustness",
        "scenario_count": len(scenarios),
        "milp_optimal_count": int(
            sum(1 for item in scenarios if int(item["modes"]["milp"]["status"]) == 0)
        ),
        "gate_failure_scenarios": list(crit["C1_violations"]),
        "max_mip_gap": max(gaps) if gaps else None,
        "verdict": summary["verdict"],
        "anchor_ok": bool(base["anchor_ok"]),
        "feasible_incumbent": bool(crit["C1_pass"] and base["anchor_ok"]),
        "incumbent_found": True,
        "seed": MC_SEED,
    }
    (out_root / "solver_status.json").write_text(
        json.dumps(solver_status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    def pct_text(value: object, digits: int = 3) -> str:
        return "n/a" if value is None else f"{100 * float(value):+.{digits}f}%"

    crit = summary["criteria"]
    base = summary["baseline"]
    checks = summary["direction_checks"]
    c5 = crit["C5"]
    c6 = crit["C6"]
    c4_info = crit["C4"]
    lines = [
        "# prob01 鲁棒性扫描汇总（预注册方案：plan.md）",
        "",
        f"- 基线 Cost_day = {base['cost_day']:.6f} 元"
        f"（锚定偏差 {base['anchor_abs_diff']:.3e}，通过={base['anchor_ok']}）",
        f"- 无储能参照 Cost_day = {summary['no_storage_cost_day']:.6f} 元；"
        f"储能节省 {summary['storage_saving_day']:.6f} 元（{100 * summary['storage_saving_ratio']:.2f}%）",
        f"- 情景数（含基线）= {len(summary['rows'])}；蒙特卡洛 {mc['draws']} 次；判定 = **{summary['verdict']}**",
        "",
        "## 判据结果",
        "",
        f"- C1 数值合法性：通过={crit['C1_pass']}，违反={crit['C1_violations'] or '无'}",
        f"- C2 假设口径 ≤{100 * STABILITY['C2_assumption_envelope']:.0f}%："
        f"通过={crit['C2_pass']}，违反={crit['C2_violations'] or '无'}",
        f"- C3 参数包络 ≤{100 * STABILITY['C3_parameter_envelope']:.0f}%："
        f"通过={crit['C3_pass']}，违反={crit['C3_violations'] or '无'}",
        f"- C4 结构结论：通过={crit['C4_pass']}，"
        f"无弃光占比={100 * c4_info['c4a_no_curtail_share']:.1f}%，"
        f"M1-M2 差={c4_info['c4c_baseline_m1_m2_gap']:.3e}",
        f"- C5 时间标签错位：Δ={pct_text(c5['delta_pct'])}（方向 {c5['direction']}，仅登记）",
        f"- C6 蒙特卡洛：95% 区间宽度="
        f"{pct_text(c6['ci_width_ratio']) if c6['ci_width_ratio'] is not None else 'n/a'}，"
        f"均值偏差={pct_text(c6['mean_bias_ratio']) if c6['mean_bias_ratio'] is not None else 'n/a'}，"
        f"通过={crit['C6_pass']}",
        f"- 方向核验：{checks['passed']}/{checks['total']} 通过；失败={checks['failed'] or '无'}",
        f"- 广义构造器等价性：max|Δ|={equivalence['max_abs_diff']:.3e}"
        f"（keys_equal={equivalence['margin_keys_equal']}）",
        f"- 敏感性图错误：{figures['errors'] or '无'}",
        "",
        "## 情景表",
        "",
        "| 情景 | 组 | Cost_day | Δ% | 弃光 | 期望方向 | 实测 | 通过 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in summary["rows"]:
        cost_text = "n/a" if row["cost_day"] is None else format(float(row["cost_day"]), ".6f")
        curtail_text = "n/a" if row["curtail_total"] is None else format(float(row["curtail_total"]), ".6f")
        lines.append(
            f"| {row['scenario_id']} | {row['group']} | {cost_text} | {pct_text(row['delta_pct'])} | "
            f"{curtail_text} | {row['expect']} | {row['observed_direction']} | {row['direction_pass']} |"
        )
    lines.extend(
        [
            "",
            "## 后续（聚合动作按 plan.md §6 执行）",
            "",
            "1. 复核 summary.json 的 C1–C6 与基线锚定；",
            "2. 运行 `--register-figures` 登记敏感性图到题目 figure manifest；",
            "3. 写 `stability_conclusion.md` 并经 commands 记录 `record_figure_review` 与 `record_optional_stage`。",
            "",
        ]
    )
    (out_root / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "problem_id": PROBLEM,
        "question_id": QUESTION,
        "stage": "robustness",
        "assumption_version": ASSUMPTION,
        "formulation_version": FORMULATION,
        "baseline_task_id": BASELINE_TASK_ID,
        "scan_task_id": os.environ.get("AUTOMM_TASK_ID"),
        "plan_path": "problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness/plan.md",
        "code_path": "problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness/prob01_robustness.py",
        "code_sha256": sha256_file(Path(__file__)),
        "accepted_solver_path": ACCEPTED_SOLVER_REL,
        "accepted_solver_sha256": sha256_file(ACCEPTED_SOLVER),
        "data_path": "data/附件1.xlsx",
        "data_sha256": hashlib.sha256(Path(args.data).read_bytes()).hexdigest(),
        "scenario_count": len(scenarios),
        "monte_carlo_draws": mc["draws"],
        "monte_carlo_noise": mc["noise"],
        "monte_carlo_seed": mc["seed"],
        "solver": "scipy.optimize.milp/HiGHS",
        "time_limit_seconds": args.time_limit,
        "mip_gap": args.mip_gap,
        "output_directory": output_rel(out_root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    (out_root / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_data(path: Path, accepted: Any) -> dict[str, Any]:
    raw = accepted.load_problem_data(path)
    series = {"price": raw["series"]["price"], "load": raw["series"]["load"], "pv": raw["series"]["pv"]}
    return {"series": series, "labels": raw["labels"], "periods": raw["periods"]}


def run_sweep(args: argparse.Namespace, *, probe: bool) -> int:
    if not args.output and not probe:
        print("正式扫描必须提供 --output（须与 task spec 的 output_directory 一致）")
        return 2
    accepted = load_accepted_module()
    loaded = load_data(Path(args.data), accepted)
    matrix = scenario_matrix()
    for scenario in matrix:
        if scenario["id"] in {"A1_baseline", "B1_E0_4800", "B2_E0_7200"}:
            scenario["save_series"] = True
    if probe:
        subset = {"A1_baseline", "A2_no_storage", "B1_E0_4800", "C4_eta_0.81", "G1_cyclic_shift_1"}
        matrix = [scenario for scenario in matrix if scenario["id"] in subset]
    started = time.perf_counter()
    scenarios = [solve_scenario(scenario, loaded, accepted, args) for scenario in matrix]
    equivalence = equivalence_check(loaded, accepted, args)
    mc = (
        {"draws": 0, "noise": MC_NOISE, "seed": MC_SEED, "samples": []}
        if probe
        else run_monte_carlo(loaded, accepted, args)
    )
    empty_mc = {"draws": 0, "noise": MC_NOISE, "seed": MC_SEED, "samples": []}
    summary = summarize(scenarios, mc if mc["samples"] else empty_mc, equivalence)
    runtime = time.perf_counter() - started
    summary["runtime_seconds"] = runtime
    summary["scenario_count"] = len(scenarios)
    summary["equivalence_max_abs_diff"] = equivalence["max_abs_diff"]
    summary["probe"] = bool(probe)

    if probe:
        out = ROOT / "runtime" / "tmp" / "prob01_robustness_probe.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        probe_root = ROOT / "runtime" / "tmp" / "prob01_robustness_probe"
        write_raw(probe_root, scenarios, mc, equivalence)
        figures = generate_figures(summary, mc, probe_root)
        write_outputs(probe_root, loaded, scenarios, mc, equivalence, summary, figures, args)
        print(
            json.dumps(
                {
                    "probe": True,
                    "output": str(out),
                    "baseline": summary["baseline"],
                    "criteria": summary["criteria"],
                    "verdict": summary["verdict"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if summary["baseline"]["anchor_ok"] and summary["criteria"]["C1_pass"] else 3

    out_root = resolve_out_root(args.output)
    out_root.mkdir(parents=True, exist_ok=True)
    write_raw(out_root, scenarios, mc, equivalence)
    figures = generate_figures(summary, mc, out_root)
    write_outputs(out_root, loaded, scenarios, mc, equivalence, summary, figures, args)
    print(
        json.dumps(
            {
                "scenario_count": len(scenarios),
                "monte_carlo_draws": mc["draws"],
                "verdict": summary["verdict"],
                "criteria": summary["criteria"],
                "baseline": summary["baseline"],
                "no_storage_cost_day": summary["no_storage_cost_day"],
                "storage_saving_day": summary["storage_saving_day"],
                "runtime_seconds": runtime,
                "figures": [item["path"] for item in figures["figures"]],
                "figure_errors": figures["errors"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if summary["baseline"]["anchor_ok"] and summary["criteria"]["C1_pass"] else 3


def register_figures(args: argparse.Namespace) -> int:
    sys.path.insert(0, str(ROOT / "scripts"))
    from automm.common import config_section, hash_path, utc_now
    from automm.visualization import inspect_png, register_figure, stable_figure_id

    out_root = resolve_out_root(args.output)
    index_path = out_root / "figures" / "figure_index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    style = config_section("visualization", PROBLEM, QUESTION)
    registered = []
    for item in payload.get("figures", []):
        png = ROOT / item["path"]
        quality = inspect_png(png, PROBLEM, QUESTION)
        source_path = ROOT / item["source_data"]
        stable_id = stable_figure_id(
            problem_id=PROBLEM,
            question_id=QUESTION,
            kind=item["kind"],
            title=item["title"],
            source_hash=hash_path(source_path),
            x="scenario",
            y=item["y"],
            style={"palette": style.get("palette", {}), "dpi": style.get("dpi", 180)},
        )
        source_hashes = {source_path.name: hash_path(source_path)}
        series_dir = out_root / "raw" / "series"
        series_file = None
        if item["kind"] == "dispatch_endpoint_compare" and series_dir.is_dir():
            series_file = series_dir
            for path in sorted(series_dir.glob("*.json")):
                source_hashes[path.name] = hash_path(path)
        entry = {
            "stable_id": stable_id,
            "problem_id": PROBLEM,
            "question_id": QUESTION,
            "assumption_version": ASSUMPTION,
            "formulation_version": FORMULATION,
            "task_id": args.scan_task_id or BASELINE_TASK_ID,
            "title": item["title"],
            "caption": item["caption"],
            "kind": item["kind"],
            "stage": "robustness",
            "path": item["path"],
            "source_data": item["source_data"],
            "source_hashes": source_hashes,
            "script": "problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness/prob01_robustness.py",
            "font": payload.get("font"),
            "dpi": payload.get("dpi"),
            "formats": ["png"],
            "generated_at": utc_now(),
            "included_in_summary": True,
            "included_in_paper": False,
            "quality_report": item["path"] + ".quality.json",
            "quality_status": quality["status"],
            "visual_audit": {
                "method": "programmatic_quality_check",
                "status": quality["status"],
                "warnings": quality["warnings"],
            },
            "series_file": None if series_file is None else str(series_file.relative_to(ROOT)).replace("\\", "/"),
        }
        register_figure(PROBLEM, entry)
        registered.append(
            {
                "stable_id": stable_id,
                "path": item["path"],
                "quality_status": quality["status"],
                "quality_warnings": quality["warnings"],
            }
        )
    print(json.dumps({"registered": registered}, ensure_ascii=False, indent=2))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="prob01 robustness 情景扫描与稳定性判定（plan.md 预注册方案）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--data", default="data/附件1.xlsx", help="附件 1 输入文件路径（只读）")
    parser.add_argument("--output", help="输出目录；正式扫描必须与 task spec 的 output_directory 一致")
    parser.add_argument("--time-limit", type=float, default=300.0, help="单次求解时限（秒）")
    parser.add_argument("--mip-gap", type=float, default=1.0e-4, help="MILP 相对 gap 目标")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="只跑 3 个代表情景 + 等价性校验，写入 runtime/tmp，不产出正式结果",
    )
    parser.add_argument(
        "--register-figures",
        action="store_true",
        help="登记 figures/figure_index.json 中的敏感性图（聚合动作调用）",
    )
    parser.add_argument(
        "--scan-task-id",
        default=None,
        help="鲁棒性扫描的隔离 task id（写入 figure manifest，可省略）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.register_figures:
        if not args.output:
            print("--register-figures 必须提供 --output")
            return 2
        return register_figures(args)
    return run_sweep(args, probe=bool(args.probe))


if __name__ == "__main__":
    raise SystemExit(main())
