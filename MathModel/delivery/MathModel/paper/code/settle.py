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
