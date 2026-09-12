from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from .io_data import DT_HOURS
from .params import DEFAULT_STORAGE, ENERGY_LIMIT, StorageParams
ETA_CH = DEFAULT_STORAGE.eta_ch
ETA_DIS = DEFAULT_STORAGE.eta_dis
SOC_MIN = DEFAULT_STORAGE.soc_min
SOC_MAX = DEFAULT_STORAGE.soc_max
POWER_LIMIT_KW = DEFAULT_STORAGE.power_limit_kw
@dataclass
class DispatchResult:
    grid: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    curtail: np.ndarray
    objective: float
    primary_objective: float
    curtail_total: float
    throughput_total: float
    status: int
    message: str
    nit: int
    solve_seconds: float
    equality_marginals: np.ndarray
def _slices(t: int):
    return slice(0, t), slice(t, 2 * t), slice(2 * t, 3 * t), slice(3 * t, 4 * t), slice(4 * t, 5 * t)
def _solve(c, a_eq, b_eq, bounds, a_ub=None, b_ub=None):
    return linprog(
        c,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
        options={"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    )
def _solve_milp(c, a_eq, b_eq, bounds, integrality, a_ub=None, b_ub=None):
    lower = np.asarray([(-np.inf if lo is None else lo) for lo, _ in bounds], dtype=float)
    upper = np.asarray([(np.inf if hi is None else hi) for _, hi in bounds], dtype=float)
    constraints = [LinearConstraint(np.asarray(a_eq), np.asarray(b_eq), np.asarray(b_eq))]
    if a_ub is not None and len(a_ub):
        constraints.append(
            LinearConstraint(
                np.asarray(a_ub, dtype=float),
                np.full(len(b_ub), -np.inf, dtype=float),
                np.asarray(b_ub, dtype=float),
            )
        )
    return milp(
        np.asarray(c, dtype=float),
        integrality=np.asarray(integrality, dtype=int),
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={"presolve": True, "mip_rel_gap": 1e-10},
    )
SLACK_ABS = 1e-5
SLACK_REL = 1e-10
def _lexicographic_slack(value: float, factor: float = 1.0) -> float:
    return factor * max(SLACK_ABS, SLACK_REL * max(1.0, abs(value)))
def _lexicographic(objectives, a_eq, b_eq, bounds, extra_rows=None, extra_rhs=None, slack_factor=1.0):
    base_rows = [np.asarray(r, dtype=float) for r in (extra_rows or [])]
    base_rhs = [float(v) for v in (extra_rhs or [])]
    rows = list(base_rows)
    rhs = list(base_rhs)
    x = None
    result = None
    degraded = False
    values: list[float] = []
    for index, c in enumerate(objectives):
        solution = None
        for factor, keep in ((1.0, None), (100.0, None), (1.0, 1)):
            if keep is None:
                sel_rows, sel_rhs = rows, rhs
            else:
                sel_rows, sel_rhs = rows[-keep:], rhs[-keep:]
            a_ub = np.asarray(sel_rows) if sel_rows else None
            b_ub = np.asarray(sel_rhs) if sel_rhs else None
            solution = _solve(c, a_eq, b_eq, bounds, a_ub, b_ub)
            if solution.success:
                if factor != 1.0 or (keep is not None and len(rows) > keep):
                    degraded = True
                break
        if solution is None or not solution.success:
            if x is None:
                raise RuntimeError(f"lexicographic LP stage {index} failed: {solution.message}")
            degraded = True
            break
        x = solution.x
        result = solution
        value = float(solution.fun)
        values.append(value)
        rows.append(np.asarray(c, dtype=float))
        rhs.append(value + _lexicographic_slack(value, slack_factor))
    return x, result, degraded, values
def _milp_lexicographic(objectives, a_eq, b_eq, bounds, integrality, extra_rows=None, extra_rhs=None):
    rows = [np.asarray(r, dtype=float) for r in (extra_rows or [])]
    rhs = [float(v) for v in (extra_rhs or [])]
    values: list[float] = []
    result = None
    for index, objective in enumerate(objectives):
        result = _solve_milp(
            objective,
            a_eq,
            b_eq,
            bounds,
            integrality,
            np.asarray(rows) if rows else None,
            np.asarray(rhs) if rhs else None,
        )
        if not result.success:
            raise RuntimeError(f"lexicographic MILP stage {index} failed: {result.message}")
        value = float(np.dot(objective, result.x))
        values.append(value)
        rows.append(np.asarray(objective, dtype=float))
        rhs.append(value + _lexicographic_slack(value, 10.0))
    return result.x, result, values
def _validate(load_kw, pv_kw, price, storage: StorageParams, soc_initial, soc_terminal):
    load_kw = np.asarray(load_kw, dtype=float)
    pv_kw = np.asarray(pv_kw, dtype=float)
    price = np.asarray(price, dtype=float)
    if not (load_kw.shape == pv_kw.shape == price.shape):
        raise ValueError("load/pv/price shape mismatch")
    t = len(price)
    if t == 0 or not np.isfinite(np.r_[load_kw, pv_kw, price]).all():
        raise ValueError("invalid input")
    if (load_kw < 0).any() or (pv_kw < 0).any() or (price <= 0).any():
        raise ValueError("physical bounds violated")
    if not storage.soc_min <= soc_initial <= storage.soc_max:
        raise ValueError("initial SOC invalid")
    if soc_terminal is not None and not storage.soc_min <= soc_terminal <= storage.soc_max:
        raise ValueError("terminal SOC invalid")
    return load_kw, pv_kw, price, t
def _energy_balance_rows(a_eq, b_eq, t, load_kw, pv_kw, storage: StorageParams, soc_initial):
    g, ch, dis, soc, spill = _slices(t)
    for i in range(t):
        a_eq[i, g.start + i] = 1
        a_eq[i, ch.start + i] = -1
        a_eq[i, dis.start + i] = 1
        a_eq[i, spill.start + i] = -1
        b_eq[i] = (load_kw[i] - pv_kw[i]) * DT_HOURS
        row = t + i
        a_eq[row, soc.start + i] = 1
        a_eq[row, ch.start + i] = -storage.eta_ch
        a_eq[row, dis.start + i] = 1.0 / storage.eta_dis
        if i == 0:
            b_eq[row] = soc_initial
        else:
            a_eq[row, soc.start + i - 1] = -1
def solve_dispatch(
    load_kw: np.ndarray,
    pv_kw: np.ndarray,
    price: np.ndarray,
    *,
    soc_initial: float,
    soc_terminal: float | None,
    storage: StorageParams = DEFAULT_STORAGE,
) -> DispatchResult:
    load_kw, pv_kw, price, t = _validate(load_kw, pv_kw, price, storage, soc_initial, soc_terminal)
    g, ch, dis, soc, spill = _slices(t)
    n = 5 * t
    a_eq = np.zeros((2 * t + (soc_terminal is not None), n))
    b_eq = np.zeros(a_eq.shape[0])
    _energy_balance_rows(a_eq, b_eq, t, load_kw, pv_kw, storage, soc_initial)
    if soc_terminal is not None:
        a_eq[-1, soc.stop - 1] = 1
        b_eq[-1] = soc_terminal
    limit = storage.energy_limit
    bounds = (
        [(0, None)] * t
        + [(0, limit)] * t
        + [(0, limit)] * t
        + [(storage.soc_min, storage.soc_max)] * t
        + [(0, float(x) * DT_HOURS) for x in pv_kw]
    )
    primary_c = np.zeros(n)
    primary_c[g] = price
    throughput_c = np.zeros(n)
    throughput_c[ch] = 1
    throughput_c[dis] = 1
    spill_c = np.zeros(n)
    spill_c[spill] = 1
    started = perf_counter()
    x, tertiary, fell_back, values = _lexicographic(
        [primary_c, throughput_c, spill_c], a_eq, b_eq, bounds
    )
    primary_value = values[0]
    return DispatchResult(
        x[g].copy(),
        x[ch].copy(),
        x[dis].copy(),
        x[soc].copy(),
        x[spill].copy(),
        float(np.dot(price, x[g])),
        primary_value,
        float(x[spill].sum()),
        float(x[ch].sum() + x[dis].sum()),
        int(tertiary.status),
        str(tertiary.message),
        int(getattr(tertiary, "nit", -1)),
        perf_counter() - started,
        np.asarray(tertiary.eqlin.marginals, dtype=float),
    )
@dataclass
class AdjustmentDispatchResult:
    dispatch: DispatchResult
    increase: np.ndarray
    decrease: np.ndarray
    settlement_objective: float
    variable_objective: float
    adjustment_mask: np.ndarray
    settlement_mode: str
    plan_purchase_constant: float
    lexicographic_fallback: bool = False
    throughput_objective: float = 0.0
def settlement_cost(plan_grid: np.ndarray, adjusted_grid: np.ndarray, price: np.ndarray, mode: str) -> float:
    plan = np.asarray(plan_grid, dtype=float)
    adjusted = np.asarray(adjusted_grid, dtype=float)
    p = np.asarray(price, dtype=float)
    increase = np.maximum(adjusted - plan, 0.0)
    decrease = np.maximum(plan - adjusted, 0.0)
    if mode == "replacement":
        return float(np.dot(p, np.minimum(plan, adjusted) + 0.5 * decrease + 1.5 * increase))
    if mode == "additive":
        return float(np.dot(p, plan) + np.dot(p, 0.5 * decrease + 1.5 * increase))
    raise ValueError(f"unknown settlement mode: {mode}")
def solve_adjustment_dispatch(
    load_kw: np.ndarray,
    pv_kw: np.ndarray,
    price: np.ndarray,
    baseline_grid: np.ndarray,
    adjustment_mask: np.ndarray,
    *,
    soc_initial: float,
    soc_terminal: float | None,
    settlement_mode: str = "replacement",
    storage: StorageParams = DEFAULT_STORAGE,
) -> AdjustmentDispatchResult:
    if settlement_mode not in ("replacement", "additive"):
        raise ValueError(f"unknown settlement mode: {settlement_mode}")
    load_kw, pv_kw, price, t = _validate(load_kw, pv_kw, price, storage, soc_initial, soc_terminal)
    baseline = np.asarray(baseline_grid, dtype=float)
    mask = np.asarray(adjustment_mask, dtype=bool)
    if not (baseline.shape == mask.shape == (t,)):
        raise ValueError("adjustment shape mismatch")
    g, ch, dis, soc, spill = _slices(t)
    inc = slice(5 * t, 6 * t)
    dec = slice(6 * t, 7 * t)
    use_milp = True
    z = slice(7 * t, 8 * t)
    n = 8 * t
    masked = np.flatnonzero(mask)
    a_eq = np.zeros((2 * t + (soc_terminal is not None) + len(masked), n))
    b_eq = np.zeros(a_eq.shape[0])
    _energy_balance_rows(a_eq, b_eq, t, load_kw, pv_kw, storage, soc_initial)
    if soc_terminal is not None:
        last = a_eq.shape[0] - 1 - len(masked)
        a_eq[last, soc.stop - 1] = 1
        b_eq[last] = soc_terminal
    limit = storage.energy_limit
    bounds = (
        [(0, None)] * t
        + [(0, limit)] * t
        + [(0, limit)] * t
        + [(storage.soc_min, storage.soc_max)] * t
        + [(0, float(x) * DT_HOURS) for x in pv_kw]
        + [((0, None) if flag else (0, 0)) for flag in mask]
        + [((0, None) if flag else (0, 0)) for flag in mask]
        + ([(0, 1)] * t if use_milp else [])
    )
    for k, i in enumerate(masked):
        row = 2 * t + (1 if soc_terminal is not None else 0) + k
        a_eq[row, g.start + i] = 1.0
        a_eq[row, inc.start + i] = -1.0
        a_eq[row, dec.start + i] = 1.0
        b_eq[row] = baseline[i]
    adjustment_rows: list[np.ndarray] = []
    adjustment_rhs: list[float] = []
    primary_c = np.zeros(n)
    if settlement_mode == "replacement":
        primary_c[g] = price
        primary_c[inc] = np.where(mask, 0.5 * price, 0.0)
        primary_c[dec] = np.where(mask, 0.5 * price, 0.0)
        constant = 0.0
    else:
        primary_c[inc] = np.where(mask, 1.5 * price, 0.0)
        primary_c[dec] = np.where(mask, 0.5 * price, 0.0)
        constant = float(np.sum(price[mask] * baseline[mask]))
    throughput_c = np.zeros(n)
    throughput_c[ch] = 1
    throughput_c[dis] = 1
    throughput_c[inc] = 1
    throughput_c[dec] = 1
    spill_c = np.zeros(n)
    spill_c[spill] = 1
    started = perf_counter()
    if use_milp:
        mutual_rows = np.zeros((2 * t, n))
        mutual_rhs = np.zeros(2 * t)
        for i in range(t):
            mutual_rows[2 * i, ch.start + i] = 1.0
            mutual_rows[2 * i, z.start + i] = -limit
            mutual_rows[2 * i + 1, dis.start + i] = 1.0
            mutual_rows[2 * i + 1, z.start + i] = limit
            mutual_rhs[2 * i + 1] = limit
        integrality = np.zeros(n, dtype=int)
        integrality[z] = 1
        tertiary = _solve_milp(
            primary_c,
            a_eq,
            b_eq,
            bounds,
            integrality,
            mutual_rows,
            mutual_rhs,
        )
        if not tertiary.success:
            raise RuntimeError(f"adjustment MILP failed: {tertiary.message}")
        x = tertiary.x
        values = [
            float(np.dot(primary_c, x)),
            float(np.dot(throughput_c, x)),
            float(np.dot(spill_c, x)),
        ]
        fell_back = False
    else:
        x, tertiary, fell_back, values = _lexicographic(
            [primary_c, throughput_c, spill_c],
            a_eq,
            b_eq,
            bounds,
            adjustment_rows,
            adjustment_rhs,
        )
    primary_value = values[0]
    adjusted = x[g].copy()
    increase_vec = x[inc].copy()
    decrease_vec = x[dec].copy()
    if settlement_mode == "replacement":
        settlement = float(np.dot(primary_c, x))
    else:
        settlement = constant + float(np.dot(primary_c, x))
    dispatch = DispatchResult(
        adjusted,
        x[ch].copy(),
        x[dis].copy(),
        x[soc].copy(),
        x[spill].copy(),
        settlement,
        float(primary_value + constant),
        float(x[spill].sum()),
        float(x[ch].sum() + x[dis].sum()),
        int(tertiary.status),
        str(tertiary.message),
        int(getattr(tertiary, "nit", getattr(tertiary, "mip_node_count", -1)) or 0),
        perf_counter() - started,
        (
            np.zeros(a_eq.shape[0], dtype=float)
            if use_milp
            else np.asarray(tertiary.eqlin.marginals, dtype=float)
        ),
    )
    return AdjustmentDispatchResult(
        dispatch,
        increase_vec,
        decrease_vec,
        settlement,
        float(np.dot(primary_c, x)),
        mask.copy(),
        settlement_mode,
        constant,
        bool(fell_back),
        float(values[1]) if len(values) > 1 else float("nan"),
    )
