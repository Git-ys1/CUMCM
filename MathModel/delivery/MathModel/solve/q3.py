from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

from .export import export_result3
from .io_data import (
    DEFAULT_DATA_ROOT,
    DT_HOURS,
    hourly_to_ten_min,
    read_attachment1,
    read_attachment2,
    read_attachment3,
    template_path,
)
from .load_forecast import OnlineLoadForecaster
from .lp_core import DispatchResult, settlement_cost, solve_adjustment_dispatch, solve_dispatch
from .official_forecast import OnlineForecastBiasCalibrator
from .params import DEFAULT_STORAGE, StorageParams
from .price_forecast import OnlinePriceForecaster
from .q2 import _emergency_intervals, _write_csv
from .settle import ExecutionResult, execute_plan

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "q3"
BLOCK = 36
ALL_NODES = (0, 36, 72, 108)


def _horizon(data: np.ndarray, day: int, start_slot: int, fallback: np.ndarray) -> np.ndarray:
    flat = data.reshape(-1)
    start = day * 144 + start_slot
    values = flat[start : min(start + 144, len(flat))]
    if len(values) < 144:
        pieces = [values]
        remaining = 144 - len(values)
        while remaining > 0:
            take = min(remaining, len(fallback))
            pieces.append(fallback[:take])
            remaining -= take
        values = np.concatenate(pieces)
    return np.asarray(values, dtype=float)


def _slice_dispatch(result: DispatchResult, start: int, stop: int) -> DispatchResult:
    return DispatchResult(
        result.grid[start:stop].copy(),
        result.charge[start:stop].copy(),
        result.discharge[start:stop].copy(),
        result.soc[start:stop].copy(),
        result.curtail[start:stop].copy(),
        result.objective,
        result.primary_objective,
        float(result.curtail[start:stop].sum()),
        float(result.charge[start:stop].sum() + result.discharge[start:stop].sum()),
        result.status,
        result.message,
        result.nit,
        result.solve_seconds,
        result.equality_marginals.copy(),
    )


def _replace_dispatch_tail(current: DispatchResult, horizon: DispatchResult, start: int) -> DispatchResult:
    """把 ``horizon`` 的首段写入当前日计划的 ``start:144``。

    该函数是节点消融的关键：若后续节点未启用，最近一次有效计划仍保留在
    ``current`` 中并继续执行，而不是回退到 0:00 基准计划。
    """
    count = 144 - start

    def merged(name: str) -> np.ndarray:
        values = np.asarray(getattr(current, name), dtype=float).copy()
        values[start:] = np.asarray(getattr(horizon, name), dtype=float)[:count]
        return values

    charge = merged("charge")
    discharge = merged("discharge")
    curtail = merged("curtail")
    return DispatchResult(
        merged("grid"),
        charge,
        discharge,
        merged("soc"),
        curtail,
        horizon.objective,
        horizon.primary_objective,
        float(curtail.sum()),
        float(charge.sum() + discharge.sum()),
        horizon.status,
        horizon.message,
        horizon.nit,
        horizon.solve_seconds,
        horizon.equality_marginals.copy(),
    )


def _reversal_count(revisions: np.ndarray) -> int:
    count = 0
    for slot in range(144):
        values = revisions[:, slot]
        values = values[np.isfinite(values)]
        signs = np.sign(np.diff(values))
        signs = signs[np.abs(signs) > 0]
        if len(signs) > 1 and np.any(signs[1:] * signs[:-1] < 0):
            count += 1
    return count


def _node_label(node: int) -> str:
    return f"{node // 6:02d}:00"


def run_q3(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    max_days: int = 365,
    downscale: str = "linear",
    calibrate: bool = True,
    update_nodes: tuple[int, ...] = ALL_NODES,
    pv_update_nodes: tuple[int, ...] | None = None,
    settlement_mode: str = "additive",
    load_mode: str = "causal",
    price_mode: str = "perfect",
    realtime_feedback: bool = True,
    terminal_policy: str = "daily_cycle",
    price_matrix: np.ndarray | None = None,
    storage: StorageParams = DEFAULT_STORAGE,
    output_dir: Path | None = None,
    template_name: str = "result3.xlsx",
    write_outputs: bool = True,
    use_typical_prior: bool = True,
    tag: str = "",
) -> dict:
    """问题三（及问题四对应问题三）多节点滚动调度。

    update_nodes 控制"允许在哪些时刻重新优化购电策略"；pv_update_nodes 控制这些
    决策时刻是否使用新发布的官方光伏预报。常规 S0--S3 令二者相同；负载刷新
    对照令 update_nodes=ALL_NODES、pv_update_nodes=(0,)，从而冻结 0:00 光伏预报：
        S0 = (0,)              仅 0:00 预报
        S1 = (0, 36)           +6:00
        S2 = (0, 36, 72)       +12:00
        S3 = (0, 36, 72, 108)  +18:00
    settlement_mode 决定 LP 目标函数本身：
        replacement  C = p[min(Gp,Ga) + 0.5(Gp-Ga)^+ + 1.5(Ga-Gp)^+]
        additive     C = p·Gp + 0.5p(Gp-Ga)^+ + 1.5p(Ga-Gp)^+
    两种口径**分别完整重新优化**，不是同一调度方案的事后换算式计费。
    """
    if settlement_mode not in ("replacement", "additive"):
        raise ValueError(f"unknown settlement_mode: {settlement_mode}")
    if load_mode not in ("perfect", "causal") or price_mode not in ("perfect", "causal"):
        raise ValueError("unknown information mode")
    nodes = tuple(sorted(int(n) for n in update_nodes))
    if not nodes or nodes[0] != 0 or any(n not in ALL_NODES for n in nodes):
        raise ValueError(f"update_nodes must be a prefix of {ALL_NODES}, got {update_nodes}")
    pv_nodes = nodes if pv_update_nodes is None else tuple(sorted(int(n) for n in pv_update_nodes))
    if not pv_nodes or pv_nodes[0] != 0 or any(n not in nodes for n in pv_nodes):
        raise ValueError(f"pv_update_nodes must contain 0 and be a subset of update_nodes, got {pv_nodes}")

    typical = read_attachment1(data_root)
    annual = read_attachment2(data_root)
    forecasts = read_attachment3(data_root)
    if annual.dates != forecasts.dates:
        raise ValueError("attachment2/3 dates do not align")
    if not 1 <= max_days <= 365:
        raise ValueError("max_days must be 1..365")
    prices = np.tile(typical.price, (365, 1)) if price_matrix is None else np.asarray(price_matrix, dtype=float)
    if prices.shape != (365, 144):
        raise ValueError("price matrix must have shape (365,144)")
    out_dir = OUTPUT if output_dir is None else Path(output_dir)

    state = 6000.0
    records: list[dict] = []
    verify: list[tuple] = []
    load_rows: list[dict] = []
    price_rows: list[dict] = []
    total_reversals = 0
    calibrator = OnlineForecastBiasCalibrator()
    load_forecaster = OnlineLoadForecaster(prior_kw=typical.load_kw if use_typical_prior else None)
    price_forecaster = OnlinePriceForecaster(prior_price=typical.price if use_typical_prior else None)

    for d in range(max_days):
        initial = state
        node_state = initial
        soc_terminal = initial if terminal_policy == "daily_cycle" else None

        # ---- 0:00 基准计划 -------------------------------------------------
        load_decision0 = load_forecaster.predict(d, 0, 144)
        price_decision0 = price_forecaster.predict_horizon(d, 0, 144) if price_mode == "causal" else None
        load0 = annual.load_kw[d] if load_mode == "perfect" else load_decision0.forecast_kw
        price0 = prices[d] if price_mode == "perfect" else price_decision0.forecast_price
        raw_base = hourly_to_ten_min(forecasts.hourly_kw[d, 0], downscale)
        calibration0 = calibrator.calibrate(0, raw_base)
        base_pv = calibration0.forecast_kw if calibrate else raw_base
        baseline = solve_dispatch(
            load0, base_pv, price0, soc_initial=initial, soc_terminal=soc_terminal, storage=storage
        )
        active_plan = baseline
        active_pv_day = np.asarray(base_pv, dtype=float).copy()
        active_source_node = 0

        adjusted = np.zeros(144)
        charge = np.zeros(144)
        discharge = np.zeros(144)
        soc = np.zeros(144)
        curtail = np.zeros(144)
        emergency = np.zeros(144)
        inc_acc = np.zeros(144)
        dec_acc = np.zeros(144)
        revisions = np.full((4, 144), np.nan)
        revisions[0] = baseline.grid
        plan_source_nodes = np.zeros(144, dtype=int)
        block_forecast_mae: list[float] = []
        calibration_margins: list[float] = []
        calibration_quantiles: list = []
        load_plan_day = np.asarray(load0, dtype=float).copy()

        load_rows.append(load_forecaster.log_row(load_decision0, annual.load_kw[d, :36], annual.dates[d].isoformat()))
        if price_decision0 is not None:
            price_rows.append(price_forecaster.log_row(price_decision0, prices[d, :36], annual.dates[d].isoformat()))
        node_load_decisions: dict[int, object] = {0: load_decision0}

        for node_index, node in enumerate(ALL_NODES):
            block_stop = node + BLOCK
            if node_index == 0:
                calibration = calibration0
                block_plan = _slice_dispatch(baseline, 0, BLOCK)
                block_forecast = base_pv[0:BLOCK]
                block_inc = np.zeros(BLOCK)
                block_dec = np.zeros(BLOCK)
            elif node in nodes:
                if node in pv_nodes:
                    raw_horizon = hourly_to_ten_min(forecasts.hourly_kw[d, node_index], downscale)
                    calibration = calibrator.calibrate(node_index, raw_horizon)
                    forecast_horizon = calibration.forecast_kw if calibrate else raw_horizon
                else:
                    # 负载刷新对照：允许重优化，但不引入该节点的新光伏预报。
                    # 当日剩余部分沿用最近一次可用预报，跨午夜部分用附件 1 典型日先验补齐。
                    calibration = None
                    forecast_horizon = np.r_[active_pv_day[node:], typical.pv_kw[:node]]
                if load_mode == "perfect":
                    load_horizon = _horizon(annual.load_kw, d, node, typical.load_kw)
                else:
                    load_decision = load_forecaster.predict(d, node, 144)
                    load_horizon = load_decision.forecast_kw
                    load_plan_day[node:] = load_horizon[: 144 - node]
                    node_load_decisions[node] = load_decision
                    load_rows.append(
                        load_forecaster.log_row(load_decision, annual.load_kw[d, node:block_stop], annual.dates[d].isoformat())
                    )
                if price_mode == "perfect":
                    price_horizon = _horizon(prices, d, node, typical.price)
                else:
                    price_decision = price_forecaster.predict_horizon(d, node, 144)
                    price_horizon = price_decision.forecast_price
                    price_rows.append(
                        price_forecaster.log_row(price_decision, prices[d, node:block_stop], annual.dates[d].isoformat())
                    )
                baseline_horizon = np.r_[baseline.grid[node:], np.zeros(node)]
                mask = np.r_[np.ones(144 - node, dtype=bool), np.zeros(node, dtype=bool)]
                rolling = solve_adjustment_dispatch(
                    load_horizon,
                    forecast_horizon,
                    price_horizon,
                    baseline_horizon,
                    mask,
                    soc_initial=node_state,
                    soc_terminal=None if terminal_policy == "free" else node_state,
                    settlement_mode=settlement_mode,
                    storage=storage,
                )
                horizon_plan = rolling.dispatch
                active_plan = _replace_dispatch_tail(active_plan, horizon_plan, node)
                active_pv_day[node:] = forecast_horizon[: 144 - node]
                active_source_node = node
                block_plan = _slice_dispatch(active_plan, node, block_stop)
                revisions[node_index, node:] = active_plan.grid[node:]
                block_forecast = active_pv_day[node:block_stop]
                base_block = baseline.grid[node:block_stop]
                block_inc = np.maximum(block_plan.grid - base_block, 0.0)
                block_dec = np.maximum(base_block - block_plan.grid, 0.0)
            else:
                # 没有新决策时，最近一次有效计划持续生效。
                calibration = None
                block_plan = _slice_dispatch(active_plan, node, block_stop)
                block_forecast = active_pv_day[node:block_stop]
                base_block = baseline.grid[node:block_stop]
                block_inc = np.maximum(block_plan.grid - base_block, 0.0)
                block_dec = np.maximum(base_block - block_plan.grid, 0.0)

            plan_source_nodes[node:block_stop] = active_source_node

            execution = execute_plan(
                block_plan,
                annual.load_kw[d, node:block_stop],
                annual.pv_kw[d, node:block_stop],
                soc_initial=node_state,
                realtime_feedback=realtime_feedback,
                storage=storage,
            )
            adjusted[node:block_stop] = execution.grid
            charge[node:block_stop] = execution.charge
            discharge[node:block_stop] = execution.discharge
            soc[node:block_stop] = execution.soc
            curtail[node:block_stop] = execution.curtail
            emergency[node:block_stop] = execution.emergency
            inc_acc[node:block_stop] = block_inc
            dec_acc[node:block_stop] = block_dec

            if calibration is not None:
                calibrator.observe(calibration, annual.pv_kw[d, node:block_stop], prices[d, node:block_stop])
                calibration_margins.append(calibration.margin_kw if calibrate else 0.0)
                calibration_quantiles.append(calibration.quantile if calibrate else None)
            block_forecast_mae.append(float(np.mean(np.abs(block_forecast - annual.pv_kw[d, node:block_stop]))))
            node_state = float(execution.soc[-1])

            # 供后续节点使用的已观测信息（严格在决策与执行之后）
            if load_mode == "causal" and node in node_load_decisions:
                load_forecaster.observe_block(node_load_decisions[node], annual.load_kw[d, node:block_stop])
            load_forecaster.observe_partial(block_stop, annual.load_kw[d, :block_stop])

        state = node_state
        actual = ExecutionResult(adjusted.copy(), charge, discharge, soc, curtail, emergency)

        gp = baseline.grid
        ga = adjusted
        increase = np.maximum(ga - gp, 0.0)
        decrease = np.maximum(gp - ga, 0.0)
        settlement = settlement_cost(gp, ga, prices[d], settlement_mode)
        if settlement_mode == "replacement":
            lp_side = float(np.dot(prices[d], ga + 0.5 * inc_acc + 0.5 * dec_acc))
        else:
            lp_side = float(np.dot(prices[d], gp) + np.dot(prices[d], 0.5 * dec_acc + 1.5 * inc_acc))
        emergency_cost = float(np.dot(5 * prices[d], emergency))
        reversals = _reversal_count(revisions)
        total_reversals += reversals

        record = {
            "day_index": d,
            "date": annual.dates[d],
            "soc_initial": initial,
            "baseline_plan": baseline,
            "adjusted_grid": adjusted,
            "execution": actual,
            "load_kw": annual.load_kw[d],
            "actual_pv_kw": annual.pv_kw[d],
            "load_plan_kw": load_plan_day,
            "revisions": revisions,
            "plan_source_nodes": plan_source_nodes.copy(),
            "baseline_cost": float(np.dot(prices[d], gp)),
            "settlement_cost": settlement,
            "emergency_cost": emergency_cost,
            "total_cost": settlement + emergency_cost,
            "adjustment_cost_yuan": settlement - float(np.dot(prices[d], gp)) if settlement_mode == "additive" else settlement - float(np.dot(prices[d], gp)),
            "linearization_gap": abs(settlement - lp_side),
            "up_energy": float(increase.sum()),
            "down_energy": float(decrease.sum()),
            "reversal_slots": reversals,
            "forecast_mae": float(np.mean(block_forecast_mae)),
            "calibration_margins": calibration_margins,
            "calibration_quantiles": calibration_quantiles,
        }
        records.append(record)

        balance = ga + annual.pv_kw[d] * DT_HOURS + discharge + emergency - annual.load_kw[d] * DT_HOURS - charge - curtail
        previous = np.r_[initial, soc[:-1]]
        soc_res = soc - (previous + storage.eta_ch * charge - discharge / storage.eta_dis)
        verify.append(
            (
                float(np.max(np.abs(balance))),
                float(np.max(np.abs(soc_res))),
                float(soc.min()),
                float(soc.max()),
                float(np.max(np.minimum(charge, discharge))),
            )
        )

        # ---- 日终观测回填 ---------------------------------------------------
        if load_mode == "causal":
            load_forecaster.commit_day(annual.load_kw[d], d)
        if price_mode == "causal":
            price_forecaster.commit_day(prices[d], d)
        else:
            price_forecaster.commit_day(prices[d], d)

    delivery = records[31:] if max_days == 365 else []
    metrics = {
        "case_tag": tag,
        "days_simulated": max_days,
        "warmup_days": 31 if max_days == 365 else None,
        "delivery_days": len(delivery),
        "downscale_method": downscale,
        "calibration_enabled": calibrate,
        "update_nodes": list(nodes),
        "update_nodes_label": "S" + str(len(nodes) - 1),
        "pv_update_nodes": list(pv_nodes),
        "settlement_mode": settlement_mode,
        "load_mode": load_mode,
        "price_mode": price_mode,
        "realtime_feedback": bool(realtime_feedback),
        "terminal_policy": terminal_policy,
        "storage": storage.as_dict(),
        "price_source": "attachment1" if price_matrix is None else "attachment4",
        "load_information": (
            "Attachment 2 same-day true load curve (perfect-information benchmark)"
            if load_mode == "perfect"
            else "Online causal forecast from days strictly before d"
        ),
        "pv_information": (
            "Attachment 3 rolling forecasts with causal issue-specific calibration"
            if calibrate
            else "raw Attachment 3 forecasts"
        )
        + f"; newly issued forecasts used at nodes {list(pv_nodes)}; actual PV used only after block execution",
        "price_information": (
            "Attachment 4 same-day true price curve (perfect-information benchmark)"
            if price_mode == "perfect"
            else "Online causal price forecast from days strictly before d"
        ),
        "max_balance_residual": max(v[0] for v in verify),
        "max_soc_residual": max(v[1] for v in verify),
        "min_soc_kwh": min(v[2] for v in verify),
        "max_soc_kwh": max(v[3] for v in verify),
        "max_simultaneous_charge_discharge": max(v[4] for v in verify),
        "replacement_settlement_formula": "min(Gp,Ga) + 0.5*(Gp-Ga)^+ + 1.5*(Ga-Gp)^+",
        "additive_settlement_formula": "Gp + 0.5*(Gp-Ga)^+ + 1.5*(Ga-Gp)^+",
        "cross_midnight": "24h optimize, execute current 6h block only; carry SOC only",
    }
    if delivery:
        metrics.update(
            {
                "total_cost_yuan": float(sum(r["total_cost"] for r in delivery)),
                "baseline_purchase_cost_yuan": float(sum(r["baseline_cost"] for r in delivery)),
                "adjustment_settlement_cost_yuan": float(sum(r["settlement_cost"] for r in delivery)),
                "adjustment_cost_yuan": float(sum(r["adjustment_cost_yuan"] for r in delivery)),
                "emergency_cost_yuan": float(sum(r["emergency_cost"] for r in delivery)),
                "plan_purchase_energy_kwh": float(sum(r["baseline_plan"].grid.sum() for r in delivery)),
                "adjusted_purchase_energy_kwh": float(sum(r["adjusted_grid"].sum() for r in delivery)),
                "emergency_energy_kwh": float(sum(r["execution"].emergency.sum() for r in delivery)),
                "curtailment_energy_kwh": float(sum(r["execution"].curtail.sum() for r in delivery)),
                "up_adjustment_energy_kwh": float(sum(r["up_energy"] for r in delivery)),
                "down_adjustment_energy_kwh": float(sum(r["down_energy"] for r in delivery)),
                "days_with_emergency": int(sum(r["execution"].emergency.sum() > 1e-7 for r in delivery)),
                "emergency_interval_count": int(sum(_emergency_intervals(r["execution"].emergency) for r in delivery)),
                "storage_charge_energy_kwh": float(sum(r["execution"].charge.sum() for r in delivery)),
                "storage_discharge_energy_kwh": float(sum(r["execution"].discharge.sum() for r in delivery)),
                "storage_throughput_kwh": float(
                    sum(r["execution"].charge.sum() + r["execution"].discharge.sum() for r in delivery)
                ),
                "ending_soc_kwh": float(delivery[-1]["execution"].soc[-1]),
                "direction_reversal_slots": int(sum(r["reversal_slots"] for r in delivery)),
                "max_linearization_gap": float(max(r["linearization_gap"] for r in delivery)),
                "executed_block_forecast_mae_kw": float(np.mean([r["forecast_mae"] for r in delivery])),
                "load_forecast_mae_kw": float(np.mean([row["mae_kw"] for row in load_rows[31:]])) if load_rows else None,
                "load_forecast_rmse_kw": float(np.mean([row["rmse_kw"] for row in load_rows[31:]])) if load_rows else None,
                "price_forecast_mae": float(np.mean([row["price_mae"] for row in price_rows[31:]])) if price_rows else None,
                "price_forecast_rmse": float(np.mean([row["price_rmse"] for row in price_rows[31:]])) if price_rows else None,
                "runtime_seconds": float(
                    sum(r["baseline_plan"].solve_seconds for r in delivery)
                ),
            }
        )
    metrics["passed"] = bool(
        metrics["max_balance_residual"] < 1e-7
        and metrics["max_soc_residual"] < 1e-7
        and metrics["min_soc_kwh"] >= storage.soc_min - 1e-7
        and metrics["max_soc_kwh"] <= storage.soc_max + 1e-7
        and metrics["max_simultaneous_charge_discharge"] < 1e-5
        and (not delivery or metrics["max_linearization_gap"] < 1e-6)
    )

    if write_outputs:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_csv(out_dir / "load_forecast_log.csv", load_rows)
        if price_rows:
            _write_csv(out_dir / "price_forecast_log.csv", price_rows)
        if delivery:
            fields = [
                "date", "slot", "load_kw", "actual_pv_kw", "load_plan_kw", "price", "baseline_grid_kwh",
                "adjusted_grid_kwh", "charge_actual_kwh", "discharge_actual_kwh", "soc_actual_kwh",
                "curtail_actual_kwh", "emergency_kwh", "revision_0", "revision_6", "revision_12", "revision_18",
            ]
            with (out_dir / "solution.csv").open("w", newline="", encoding="utf-8-sig") as f:
                import csv as _csv

                writer = _csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for r in delivery:
                    for t in range(144):
                        rev = r["revisions"][:, t]
                        writer.writerow(
                            {
                                "date": r["date"].isoformat(),
                                "slot": t + 1,
                                "load_kw": r["load_kw"][t],
                                "actual_pv_kw": r["actual_pv_kw"][t],
                                "load_plan_kw": r["load_plan_kw"][t],
                                "price": prices[r["day_index"], t],
                                "baseline_grid_kwh": r["baseline_plan"].grid[t],
                                "adjusted_grid_kwh": r["adjusted_grid"][t],
                                "charge_actual_kwh": r["execution"].charge[t],
                                "discharge_actual_kwh": r["execution"].discharge[t],
                                "soc_actual_kwh": r["execution"].soc[t],
                                "curtail_actual_kwh": r["execution"].curtail[t],
                                "emergency_kwh": r["execution"].emergency[t],
                                "revision_0": rev[0],
                                "revision_6": rev[1],
                                "revision_12": rev[2],
                                "revision_18": rev[3],
                            }
                        )
            fields_d = [
                "date", "soc_initial", "soc_terminal", "baseline_cost", "settlement_cost", "emergency_cost",
                "total_cost", "up_energy", "down_energy", "reversal_slots", "forecast_mae",
            ]
            _write_csv(
                out_dir / "daily_metrics.csv",
                [
                    {
                        "date": r["date"].isoformat(),
                        "soc_initial": r["soc_initial"],
                        "soc_terminal": r["execution"].soc[-1],
                        **{k: r[k] for k in fields_d[3:]},
                    }
                    for r in delivery
                ],
                fields_d,
            )
            check = export_result3(template_path(template_name, data_root), out_dir / template_name, delivery)
            (out_dir / "xlsx_verification.json").write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")
            metrics["xlsx_passed"] = check["passed"]
            (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        env = {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "algorithm": (
                "HiGHS MILP with binary charge/discharge exclusivity and explicit (inc, dec) split"
                if settlement_mode == "additive"
                else "HiGHS LP with explicit (inc, dec) split"
            ),
            "case_tag": tag,
        }
        (out_dir / "environment.json").write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"metrics": metrics, "records": records}


if __name__ == "__main__":
    print(json.dumps(run_q3()["metrics"], ensure_ascii=False, indent=2))
