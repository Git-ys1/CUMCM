from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .io_data import DT_HOURS
from .lp_core import DispatchResult
from .params import DEFAULT_STORAGE, StorageParams

TOL = 1e-10


@dataclass(frozen=True)
class ExecutionResult:
    grid: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    curtail: np.ndarray
    emergency: np.ndarray


def execute_with_realtime_storage_feedback(
    plan: DispatchResult,
    load_kw: np.ndarray,
    actual_pv_kw: np.ndarray,
    *,
    soc_initial: float,
    storage: StorageParams = DEFAULT_STORAGE,
) -> ExecutionResult:
    """实时储能反馈（realtime_feedback = ON）。

    真实光伏低于计划时：先取消充电 → 再增加放电 → 最后紧急购电；
    真实光伏高于计划时：先减少放电 → 再增加充电 → 最后弃光。
    每步只使用当前时刻已发生的真实光伏与当前 SOC，不使用任何未来信息。
    """
    load = np.asarray(load_kw, dtype=float)
    pv = np.asarray(actual_pv_kw, dtype=float)
    n = len(load)
    if pv.shape != load.shape or len(plan.grid) != n:
        raise ValueError("execution shape mismatch")
    limit = storage.energy_limit
    c_out = np.zeros(n)
    h_out = np.zeros(n)
    soc = np.zeros(n)
    spill = np.zeros(n)
    emergency = np.zeros(n)
    state = float(soc_initial)
    for t in range(n):
        c = min(float(plan.charge[t]), limit, max(0.0, (storage.soc_max - state) / storage.eta_ch))
        h = min(float(plan.discharge[t]), limit, max(0.0, (state - storage.soc_min) * storage.eta_dis))
        net = float(plan.grid[t] + pv[t] * DT_HOURS + h - load[t] * DT_HOURS - c)
        if net < -TOL:
            deficit = -net
            reduce = min(c, deficit)
            c -= reduce
            deficit -= reduce
            max_h = max(0.0, (state + storage.eta_ch * c - storage.soc_min) * storage.eta_dis)
            add = min(deficit, limit - h, max(0.0, max_h - h))
            h += add
            deficit -= add
            emergency[t] = max(0.0, deficit)
        elif net > TOL:
            surplus = net
            reduce = min(h, surplus)
            h -= reduce
            surplus -= reduce
            max_c = max(0.0, (storage.soc_max - (state - h / storage.eta_dis)) / storage.eta_ch)
            add = min(surplus, limit - c, max(0.0, max_c - c))
            c += add
            surplus -= add
            spill[t] = max(0.0, surplus)
        state = state + storage.eta_ch * c - h / storage.eta_dis
        if not storage.soc_min - 1e-6 <= state <= storage.soc_max + 1e-6:
            raise RuntimeError(f"SOC invalid at {t}: {state}")
        c_out[t] = c
        h_out[t] = h
        soc[t] = min(storage.soc_max, max(storage.soc_min, state))
    return ExecutionResult(plan.grid.copy(), c_out, h_out, soc, spill, emergency)


def execute_fixed_storage_plan(
    plan: DispatchResult,
    load_kw: np.ndarray,
    actual_pv_kw: np.ndarray,
    *,
    soc_initial: float,
    storage: StorageParams = DEFAULT_STORAGE,
) -> ExecutionResult:
    """固定储能计划执行（realtime_feedback = OFF）。

    储能充放电严格等于计划值，只保留 SOC 物理边界的被动钳位：
    真实不足部分全部进入 5 倍电价紧急购电，真实富余部分全部弃光。
    该口径用于度量 10 min 实时储能 recourse 对总费用的贡献。
    """
    load = np.asarray(load_kw, dtype=float)
    pv = np.asarray(actual_pv_kw, dtype=float)
    n = len(load)
    if pv.shape != load.shape or len(plan.grid) != n:
        raise ValueError("execution shape mismatch")
    limit = storage.energy_limit
    c_out = np.zeros(n)
    h_out = np.zeros(n)
    soc = np.zeros(n)
    spill = np.zeros(n)
    emergency = np.zeros(n)
    state = float(soc_initial)
    for t in range(n):
        # 被动钳位：计划值超出当前 SOC 可达范围时按边界截断（不主动做能量补偿）
        c = min(float(plan.charge[t]), limit, max(0.0, (storage.soc_max - state) / storage.eta_ch))
        h = min(float(plan.discharge[t]), limit, max(0.0, (state - storage.soc_min) * storage.eta_dis))
        net = float(plan.grid[t] + pv[t] * DT_HOURS + h - load[t] * DT_HOURS - c)
        if net < 0:
            emergency[t] = -net
        elif net > 0:
            spill[t] = net
        state = state + storage.eta_ch * c - h / storage.eta_dis
        if not storage.soc_min - 1e-6 <= state <= storage.soc_max + 1e-6:
            raise RuntimeError(f"SOC invalid at {t}: {state}")
        c_out[t] = c
        h_out[t] = h
        soc[t] = min(storage.soc_max, max(storage.soc_min, state))
    return ExecutionResult(plan.grid.copy(), c_out, h_out, soc, spill, emergency)


def execute_plan(
    plan: DispatchResult,
    load_kw: np.ndarray,
    actual_pv_kw: np.ndarray,
    *,
    soc_initial: float,
    realtime_feedback: bool = True,
    storage: StorageParams = DEFAULT_STORAGE,
) -> ExecutionResult:
    if realtime_feedback:
        return execute_with_realtime_storage_feedback(
            plan, load_kw, actual_pv_kw, soc_initial=soc_initial, storage=storage
        )
    return execute_fixed_storage_plan(plan, load_kw, actual_pv_kw, soc_initial=soc_initial, storage=storage)
