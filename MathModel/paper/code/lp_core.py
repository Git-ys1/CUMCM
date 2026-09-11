from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.optimize import linprog

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


# 词典序层间松弛沿用 legacy 公式：绝对 1e-5 与相对 1e-10 取大者。
# 该公式使后序层只能在"同一个最优解"内部换一个顶点，不会移动日调度结果；
# 由于微网是带状态反馈的滚动系统，日调度的一丝变化会沿 334 天放大，
# 因此这里必须与 legacy 逐位一致，才能保证 §11 的回归复现验收。
SLACK_ABS = 1e-5
SLACK_REL = 1e-10


def _lexicographic_slack(value: float, factor: float = 1.0) -> float:
    return factor * max(SLACK_ABS, SLACK_REL * max(1.0, abs(value)))


def _lexicographic(objectives, a_eq, b_eq, bounds, extra_rows=None, extra_rhs=None, slack_factor=1.0):
    """依次求解 objectives；后一层在前一层最优值的容差带内继续优化。

    数值退化（大规模最优面上的容差冲突）会让后序层被过紧的界判为不可行。
    此时按三级逐级退让：① 原界 → ② 容差放大 100 倍 → ③ 只保留**最后一条**界。
    第 ③ 级是刻意这样设计的：最后一条界来自第二层（吞吐量）目标，而"消除同时
    充放"正是靠这一层实现的；若把它也丢掉，最优面上的退化解（C=H=大值，母线
    平衡不变但储电量缓慢下降）就会重新出现。

    返回 (x, 最后一层的求解结果, 是否发生退让, 各层目标值)。
    """
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
    """写入母线平衡与 SOC 递推两族等式约束。"""
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
    """白天/全天的确定性调度 LP：min Σ p·G，词典序消除退化最优解。"""
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
    """按题意直接回代，不含紧急购电费。

    replacement：C = p·[min(Gp,Ga) + 0.5·(Gp-Ga)^+ + 1.5·(Ga-Gp)^+]
    additive   ：C = p·Gp + 0.5·p·(Gp-Ga)^+ + 1.5·p·(Ga-Gp)^+
    """
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
    """在给定基准计划下联合优化调整购电量与储能。

    显式引入 inc = (Ga-Gp)^+ 与 dec = (Gp-Ga)^+，满足 Ga - Gp = inc - dec：
      replacement 目标：Σ p·(Ga + 0.5·inc + 0.5·dec)          （等价于 min(Gp,Ga)+0.5dec+1.5inc）
      additive    目标：Σ p·Gp + 0.5·p·dec + 1.5·p·inc        （p·Gp 为常数，最终报告时补回）
    """
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
    n = 7 * t

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
    )

    # 等式约束：Ga - inc + dec = Gp（仅对允许调整的时段生效）
    # 必须是等式：若写成不等式，当 Ga < Gp 时 LP 可取 inc=dec=0，从而漏付 0.5p(Gp-Ga)
    # 的违约费用，导致目标函数系统性低估向下调整成本、调度不再最优。
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
        # additive 口径下 Ga 不进目标，最优面维度较高；Ga 的实际取值由母线平衡与
        # inc/dec 的等式关系共同决定，退化解再由后续的吞吐量层消除，无需人工微扰。
        constant = float(np.sum(price[mask] * baseline[mask]))

    throughput_c = np.zeros(n)
    throughput_c[ch] = 1
    throughput_c[dis] = 1
    spill_c = np.zeros(n)
    spill_c[spill] = 1
    started = perf_counter()
    # additive 口径下 Ga 本身不进目标，最优面维度远高于 replacement 口径，
    # 因此给它更宽的层间容差，避免后序层被过紧的界判为不可行而触发退让。
    x, tertiary, fell_back, values = _lexicographic(
        [primary_c, throughput_c, spill_c],
        a_eq,
        b_eq,
        bounds,
        adjustment_rows,
        adjustment_rhs,
        slack_factor=1.0 if settlement_mode == "replacement" else 100.0,
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
        int(getattr(tertiary, "nit", -1)),
        perf_counter() - started,
        np.asarray(tertiary.eqlin.marginals, dtype=float),
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
