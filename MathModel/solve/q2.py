from __future__ import annotations

import csv
import json
import platform
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import scipy

from .export import export_result2
from .forecast import OnlinePVForecaster
from .io_data import DEFAULT_DATA_ROOT, DT_HOURS, read_attachment1, read_attachment2, template_path
from .load_forecast import OnlineLoadForecaster
from .lp_core import solve_dispatch
from .params import DEFAULT_STORAGE, StorageParams
from .price_forecast import OnlinePriceForecaster
from .settle import execute_plan

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "q2"


def _verify_day(record: dict, storage: StorageParams) -> dict:
    execution = record["execution"]
    load = record["load_kw"]
    pv = record["actual_pv_kw"]
    balance = (
        execution.grid
        + pv * DT_HOURS
        + execution.discharge
        + execution.emergency
        - load * DT_HOURS
        - execution.charge
        - execution.curtail
    )
    previous = np.r_[record["soc_initial"], execution.soc[:-1]]
    soc_residual = execution.soc - (previous + storage.eta_ch * execution.charge - execution.discharge / storage.eta_dis)
    return {
        "max_balance_residual": float(np.max(np.abs(balance))),
        "max_soc_residual": float(np.max(np.abs(soc_residual))),
        "min_soc": float(execution.soc.min()),
        "max_soc": float(execution.soc.max()),
        "max_simultaneous": float(np.max(np.minimum(execution.charge, execution.discharge))),
    }


def _emergency_intervals(emergency: np.ndarray, threshold: float = 1e-7) -> int:
    """统计紧急购电的连续时段块数（相邻时段合并为一个时间段）。"""
    active = emergency > threshold
    if not active.any():
        return 0
    return int(np.sum(active[1:] & ~active[:-1]) + (1 if active[0] else 0))


def run_q2(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    max_days: int = 365,
    price_matrix: np.ndarray | None = None,
    output_dir: Path | None = None,
    template_name: str = "result2.xlsx",
    write_outputs: bool = True,
    load_mode: str = "causal",
    pv_risk_mode: str = "asymmetric",
    realtime_feedback: bool = True,
    terminal_policy: str = "daily_cycle",
    price_mode: str = "perfect",
    storage: StorageParams = DEFAULT_STORAGE,
    use_typical_prior: bool = True,
    tag: str = "",
) -> dict:
    """问题二（及问题四对应问题二）日滚动调度。

    信息集说明：
      load_mode  = "perfect" 计划使用当日真实负载（旧基准，含未来信息）
                 = "causal"  计划使用 OnlineLoadForecaster 的因果预测
      price_mode = "perfect" 计划使用当日附件 4 真实电价
                 = "causal"  计划使用 OnlinePriceForecaster 的因果预测
      pv_risk_mode 见 forecast.OnlinePVForecaster
      realtime_feedback 见 settle.execute_plan
      terminal_policy = "daily_cycle" 计划层 S_144 = 当日实际 S_0；"free" 不约束
    """
    if load_mode not in ("perfect", "causal"):
        raise ValueError(f"unknown load_mode: {load_mode}")
    if price_mode not in ("perfect", "causal"):
        raise ValueError(f"unknown price_mode: {price_mode}")
    if terminal_policy not in ("daily_cycle", "free"):
        raise ValueError(f"unknown terminal_policy: {terminal_policy}")

    day1 = read_attachment1(data_root)
    annual = read_attachment2(data_root)
    if max_days < 1 or max_days > 365:
        raise ValueError("max_days must be 1..365")
    prices = np.tile(day1.price, (365, 1)) if price_matrix is None else np.asarray(price_matrix, dtype=float)
    if prices.shape != (365, 144):
        raise ValueError("price matrix must have shape (365,144)")
    out_dir = OUTPUT if output_dir is None else Path(output_dir)

    # 附件 1 的典型日曲线作为 2025-01-01 之前的先验（在论文假设中显式声明）；
    # use_typical_prior=False 用于复现不含先验的 legacy 基准结果。
    prior_pv = day1.pv_kw if use_typical_prior else None
    prior_load = day1.load_kw if use_typical_prior else None
    prior_price = day1.price if use_typical_prior else None
    selector = OnlinePVForecaster(day1.price, risk_mode=pv_risk_mode, prior_pv=prior_pv)
    load_forecaster = OnlineLoadForecaster(prior_kw=prior_load)
    price_forecaster = OnlinePriceForecaster(prior_price=prior_price)

    state = 6000.0
    records: list[dict] = []
    forecast_rows: list[dict] = []
    load_rows: list[dict] = []
    price_rows: list[dict] = []
    verify_rows: list[dict] = []

    for d in range(max_days):
        initial = state

        # ---- 决策时刻 0:00 可用信息 --------------------------------------
        load_decision = load_forecaster.predict(d, 0, 144)
        pv_decision = selector.predict()
        if pv_decision.history_days_used != d:
            raise RuntimeError("PV forecast causality counter mismatch")
        price_decision = price_forecaster.predict_horizon(d, 0, 144) if price_mode == "causal" else None

        load_plan = annual.load_kw[d] if load_mode == "perfect" else load_decision.forecast_kw
        price_plan = prices[d] if price_mode == "perfect" else price_decision.forecast_price
        soc_terminal = initial if terminal_policy == "daily_cycle" else None

        # ---- 日前计划优化（只使用上面确定的信息） -------------------------
        plan = solve_dispatch(
            load_plan,
            pv_decision.forecast_kw,
            price_plan,
            soc_initial=initial,
            soc_terminal=soc_terminal,
            storage=storage,
        )

        # ---- 真实执行（真实负载 / 真实光伏，实时储能反馈可开关） ----------
        execution = execute_plan(
            plan,
            annual.load_kw[d],
            annual.pv_kw[d],
            soc_initial=initial,
            realtime_feedback=realtime_feedback,
            storage=storage,
        )

        # ---- 用真实电价结算 ----------------------------------------------
        plan_cost = float(np.dot(prices[d], plan.grid))
        emergency_cost = float(np.dot(5.0 * prices[d], execution.emergency))
        state = float(execution.soc[-1])

        record = {
            "day_index": d,
            "date": annual.dates[d],
            "soc_initial": initial,
            "plan": plan,
            "execution": execution,
            "load_kw": annual.load_kw[d],
            "actual_pv_kw": annual.pv_kw[d],
            "load_plan_kw": np.asarray(load_plan, dtype=float),
            "pv_plan_kw": pv_decision.forecast_kw,
            "price_plan": np.asarray(price_plan, dtype=float),
            "plan_cost": plan_cost,
            "emergency_cost": emergency_cost,
            "total_cost": plan_cost + emergency_cost,
            "load_decision": load_decision,
            "pv_decision": pv_decision,
            "adjusted_grid": execution.grid,
        }
        records.append(record)
        verify_rows.append(_verify_day(record, storage))

        # ---- 日志留痕 -----------------------------------------------------
        forecast_rows.append(
            {
                "day_index": d,
                "date": annual.dates[d].isoformat(),
                "history_days_used": pv_decision.history_days_used,
                "candidate": pv_decision.name,
                "method": pv_decision.method,
                "quantile": pv_decision.quantile,
                "margin_kw": pv_decision.margin_kw,
                "historical_score": pv_decision.historical_score,
                "pv_forecast_mae_kw": float(np.mean(np.abs(pv_decision.forecast_kw - annual.pv_kw[d]))),
                "pv_forecast_rmse_kw": float(np.sqrt(np.mean((pv_decision.forecast_kw - annual.pv_kw[d]) ** 2))),
                "pv_daily_energy_error_kwh": float(np.sum(pv_decision.forecast_kw - annual.pv_kw[d]) * DT_HOURS),
            }
        )
        load_rows.append(load_forecaster.log_row(load_decision, annual.load_kw[d], annual.dates[d].isoformat()))
        if price_decision is not None:
            price_rows.append(
                price_forecaster.log_row(price_decision, prices[d], annual.dates[d].isoformat())
            )

        # ---- 观测回填（严格在决策之后） -----------------------------------
        selector.observe(pv_decision, annual.pv_kw[d], price=np.asarray(price_plan, dtype=float))
        load_forecaster.observe_block(load_decision, annual.load_kw[d])
        load_forecaster.commit_day(annual.load_kw[d], d)
        if price_decision is not None:
            price_forecaster.observe_block(price_decision, prices[d])
        price_forecaster.commit_day(prices[d], d)

    delivery = records[31:] if max_days == 365 else []
    min_soc = min(r["min_soc"] for r in verify_rows)
    max_soc = max(r["max_soc"] for r in verify_rows)
    max_balance = max(r["max_balance_residual"] for r in verify_rows)
    max_soc_res = max(r["max_soc_residual"] for r in verify_rows)
    max_sim = max(r["max_simultaneous"] for r in verify_rows)
    continuity = (
        max(abs(records[i]["soc_initial"] - records[i - 1]["execution"].soc[-1]) for i in range(1, len(records)))
        if len(records) > 1
        else 0.0
    )

    metrics = {
        "case_tag": tag,
        "days_simulated": max_days,
        "warmup_days": 31 if max_days == 365 else None,
        "delivery_days": len(delivery),
        "load_mode": load_mode,
        "pv_risk_mode": pv_risk_mode,
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
            "Causal forecast from days strictly before d, "
            + ("historical residual quantile safety margin" if pv_risk_mode == "asymmetric" else "no safety margin (point)")
        ),
        "price_information": (
            "Attachment 4 same-day true price curve (perfect-information benchmark)"
            if price_mode == "perfect"
            else "Online causal forecast from days strictly before d"
        ),
        "realtime_storage_feedback": bool(realtime_feedback),
        "terminal_policy_definition": (
            "planned S_144 equals actual S_0 of the same day" if terminal_policy == "daily_cycle" else "no terminal SOC constraint"
        ),
        "max_balance_residual": max_balance,
        "max_soc_residual": max_soc_res,
        "max_day_boundary_soc_gap": continuity,
        "min_soc_kwh": min_soc,
        "max_soc_kwh": max_soc,
        "max_simultaneous_charge_discharge": max_sim,
        "forecast_selection_counts": dict(Counter(row["candidate"] for row in forecast_rows)),
        "load_selection_counts": dict(Counter(row["candidate"] for row in load_rows)),
        "price_selection_counts": dict(Counter(row["method"] for row in price_rows)) if price_rows else None,
    }
    if delivery:
        metrics.update(
            {
                "total_cost_yuan": float(sum(r["total_cost"] for r in delivery)),
                "plan_purchase_cost_yuan": float(sum(r["plan_cost"] for r in delivery)),
                "adjustment_cost_yuan": 0.0,
                "emergency_cost_yuan": float(sum(r["emergency_cost"] for r in delivery)),
                "plan_purchase_energy_kwh": float(sum(r["plan"].grid.sum() for r in delivery)),
                "adjusted_purchase_energy_kwh": float(sum(r["adjusted_grid"].sum() for r in delivery)),
                "emergency_energy_kwh": float(sum(r["execution"].emergency.sum() for r in delivery)),
                "curtailment_energy_kwh": float(sum(r["execution"].curtail.sum() for r in delivery)),
                "days_with_emergency": int(sum(r["execution"].emergency.sum() > 1e-7 for r in delivery)),
                "emergency_interval_count": int(
                    sum(_emergency_intervals(r["execution"].emergency) for r in delivery)
                ),
                "storage_charge_energy_kwh": float(sum(r["execution"].charge.sum() for r in delivery)),
                "storage_discharge_energy_kwh": float(sum(r["execution"].discharge.sum() for r in delivery)),
                "storage_throughput_kwh": float(
                    sum(r["execution"].charge.sum() + r["execution"].discharge.sum() for r in delivery)
                ),
                "ending_soc_kwh": float(delivery[-1]["execution"].soc[-1]),
                "load_forecast_mae_kw": float(np.mean([row["mae_kw"] for row in load_rows[31:]])),
                "load_forecast_rmse_kw": float(np.mean([row["rmse_kw"] for row in load_rows[31:]])),
                "pv_forecast_mae_kw": float(np.mean([row["pv_forecast_mae_kw"] for row in forecast_rows[31:]])),
                "pv_forecast_rmse_kw": float(np.mean([row["pv_forecast_rmse_kw"] for row in forecast_rows[31:]])),
                "price_forecast_mae": float(np.mean([row["price_mae"] for row in price_rows[31:]])) if price_rows else None,
                "price_forecast_rmse": float(np.mean([row["price_rmse"] for row in price_rows[31:]])) if price_rows else None,
                "runtime_seconds": float(sum(r["plan"].solve_seconds for r in delivery)),
            }
        )
    # 阈值说明：能量残差用 1e-7 kWh，同时充放电量用 1e-5 kWh。后者是数值噪声
    # （约 1e-6 kWh）与真实的线性松弛退化（80~824 kWh）之间的分界，两者相差 7 个
    # 数量级，因此该阈值既能滤掉浮点噪声、又不会放过真正的"边充边放"伪解。
    # （统一为与 q3.py 相同的阈值，避免同一份代码里出现两套判据。）
    metrics["passed"] = bool(
        max_balance < 1e-7
        and max_soc_res < 1e-7
        and continuity < 1e-9
        and min_soc >= storage.soc_min - 1e-7
        and max_soc <= storage.soc_max + 1e-7
        and max_sim < 1e-5
    )

    if write_outputs:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_csv(out_dir / "forecast_log.csv", forecast_rows)
        _write_csv(out_dir / "load_forecast_log.csv", load_rows)
        if price_rows:
            _write_csv(out_dir / "price_forecast_log.csv", price_rows)
        if delivery:
            fields = [
                "date", "slot", "load_kw", "actual_pv_kw", "load_plan_kw", "pv_plan_kw", "price",
                "grid_plan_kwh", "grid_actual_kwh", "charge_actual_kwh", "discharge_actual_kwh",
                "soc_actual_kwh", "curtail_actual_kwh", "emergency_kwh",
            ]
            with (out_dir / "solution.csv").open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                for r in delivery:
                    for t in range(144):
                        writer.writerow(
                            {
                                "date": r["date"].isoformat(),
                                "slot": t + 1,
                                "load_kw": r["load_kw"][t],
                                "actual_pv_kw": r["actual_pv_kw"][t],
                                "load_plan_kw": r["load_plan_kw"][t],
                                "pv_plan_kw": r["pv_plan_kw"][t],
                                "price": prices[r["day_index"], t],
                                "grid_plan_kwh": r["plan"].grid[t],
                                "grid_actual_kwh": r["adjusted_grid"][t],
                                "charge_actual_kwh": r["execution"].charge[t],
                                "discharge_actual_kwh": r["execution"].discharge[t],
                                "soc_actual_kwh": r["execution"].soc[t],
                                "curtail_actual_kwh": r["execution"].curtail[t],
                                "emergency_kwh": r["execution"].emergency[t],
                            }
                        )
            daily_fields = [
                "date", "soc_initial", "soc_terminal", "plan_cost", "emergency_cost", "total_cost",
                "plan_energy", "emergency_energy", "curtailment_energy",
            ]
            _write_csv(
                out_dir / "daily_metrics.csv",
                [
                    {
                        "date": r["date"].isoformat(),
                        "soc_initial": r["soc_initial"],
                        "soc_terminal": r["execution"].soc[-1],
                        "plan_cost": r["plan_cost"],
                        "emergency_cost": r["emergency_cost"],
                        "total_cost": r["total_cost"],
                        "plan_energy": r["plan"].grid.sum(),
                        "emergency_energy": r["execution"].emergency.sum(),
                        "curtailment_energy": r["execution"].curtail.sum(),
                    }
                    for r in delivery
                ],
                daily_fields,
            )
            check = export_result2(template_path(template_name, data_root), out_dir / template_name, delivery)
            (out_dir / "xlsx_verification.json").write_text(
                json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            metrics["xlsx_passed"] = check["passed"]
            (out_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "algorithm": "scipy.optimize.linprog(method=highs), lexicographic 3-pass LP",
        "case_tag": tag,
    }
    if write_outputs:
        (out_dir / "environment.json").write_text(json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"metrics": metrics, "records": records, "forecast_rows": forecast_rows, "load_rows": load_rows}


def _write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows:
        return
    fieldnames = fields if fields is not None else list(rows[0])
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    print(json.dumps(run_q2()["metrics"], ensure_ascii=False, indent=2))
