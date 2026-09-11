"""模型审计实验总控：Q2 原因拆解 / Q3 预报时点消融与结算口径 / Q4 价格信息边界 / P1 敏感性。

所有变体产物统一写入 MathModel/outputs/variants/model_audit_v2/，不覆盖任何既有结果。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from .io_data import DEFAULT_DATA_ROOT, read_attachment1, read_attachment4
from .params import DEFAULT_STORAGE, EFFICIENCY_VARIANTS
from .q2 import run_q2
from .q3 import run_q3

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "outputs" / "variants" / "model_audit_v2"

# Q2 原因拆解：只改变一个因素
Q2_CASES = {
    "A_perfectload_risk_feedback": dict(load_mode="perfect", pv_risk_mode="asymmetric", realtime_feedback=True),
    "B_causalload_risk_feedback": dict(load_mode="causal", pv_risk_mode="asymmetric", realtime_feedback=True),
    "C_causalload_point_feedback": dict(load_mode="causal", pv_risk_mode="point", realtime_feedback=True),
    "D_causalload_risk_nofeedback": dict(load_mode="causal", pv_risk_mode="asymmetric", realtime_feedback=False),
}

Q3_CASES = {
    "S0_0": dict(update_nodes=(0,)),
    "S1_0_6": dict(update_nodes=(0, 36)),
    "S2_0_6_12": dict(update_nodes=(0, 36, 72)),
    "S3_0_6_12_18": dict(update_nodes=(0, 36, 72, 108)),
}

Q4_CASES = {
    "q42_perfect_price": ("q2", dict(price_mode="perfect")),
    "q42_causal_price": ("q2", dict(price_mode="causal")),
    "q43_perfect_price": ("q3", dict(price_mode="perfect")),
    "q43_causal_price": ("q3", dict(price_mode="causal")),
}

SEASONS = {
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "autumn": (9, 10, 11),
    "winter": (12, 1, 2),
}


def _season(month: int) -> str:
    for name, months in SEASONS.items():
        if month in months:
            return name
    raise ValueError(month)


def run_q2_ablation(*, max_days: int = 365, data_root: Path = DEFAULT_DATA_ROOT) -> dict:
    out = VARIANTS / "q2"
    summary = {}
    for name, kwargs in Q2_CASES.items():
        started = time.perf_counter()
        result = run_q2(
            data_root=data_root,
            max_days=max_days,
            output_dir=out / name,
            template_name="result2.xlsx",
            write_outputs=True,
            tag=name,
            **kwargs,
        )
        metrics = result["metrics"]
        metrics["wall_seconds"] = time.perf_counter() - started
        (out / name / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[name] = metrics
        print(f"[Q2] {name}: total={metrics.get('total_cost_yuan')} emergency={metrics.get('emergency_energy_kwh')}")
    _dump(out / "summary.json", summary)
    return summary


def run_q3_ablation(
    *, max_days: int = 365, data_root: Path = DEFAULT_DATA_ROOT, settlement_mode: str = "replacement"
) -> dict:
    # 两种结算口径的输出必须分目录，否则后跑的一轮会覆盖前一轮的
    # metrics.json 与官方 result3.xlsx，导致论文与提交文件口径不一致。
    out = VARIANTS / f"q3_{settlement_mode}"
    summary = {}
    for name, kwargs in Q3_CASES.items():
        started = time.perf_counter()
        result = run_q3(
            data_root=data_root,
            max_days=max_days,
            output_dir=out / name,
            template_name="result3.xlsx",
            write_outputs=True,
            settlement_mode=settlement_mode,
            tag=name,
            **kwargs,
        )
        metrics = result["metrics"]
        metrics["wall_seconds"] = time.perf_counter() - started
        (out / name / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 季节分解
        (out / name / "by_season.csv").write_text(_season_table(result["records"]), encoding="utf-8-sig")
        summary[name] = metrics
        print(f"[Q3-{settlement_mode}] {name}: total={metrics.get('total_cost_yuan')}")
    _dump(out / "summary.json", summary)
    return summary


def _season_table(records: list[dict]) -> str:
    delivery = records[31:]
    rows = ["season,days,total_cost_yuan,baseline_cost_yuan,emergency_energy_kwh,up_energy_kwh,down_energy_kwh,curtailment_kwh"]
    for season in ("spring", "summer", "autumn", "winter"):
        subset = [r for r in delivery if _season(r["date"].month) == season]
        if not subset:
            continue
        rows.append(
            ",".join(
                str(x)
                for x in [
                    season,
                    len(subset),
                    round(sum(r["total_cost"] for r in subset), 4),
                    round(sum(r["baseline_cost"] for r in subset), 4),
                    round(sum(r["execution"].emergency.sum() for r in subset), 4),
                    round(sum(r["up_energy"] for r in subset), 4),
                    round(sum(r["down_energy"] for r in subset), 4),
                    round(sum(r["execution"].curtail.sum() for r in subset), 4),
                ]
            )
        )
    return "\n".join(rows) + "\n"


def run_q4_ablation(*, max_days: int = 365, data_root: Path = DEFAULT_DATA_ROOT) -> dict:
    out = VARIANTS / "q4"
    prices = read_attachment4(data_root).price
    summary = {}
    for name, (kind, kwargs) in Q4_CASES.items():
        started = time.perf_counter()
        if kind == "q2":
            result = run_q2(
                data_root=data_root,
                max_days=max_days,
                price_matrix=prices,
                output_dir=out / name,
                template_name="result4-2.xlsx",
                write_outputs=True,
                load_mode="causal",
                tag=name,
                **kwargs,
            )
        else:
            result = run_q3(
                data_root=data_root,
                max_days=max_days,
                price_matrix=prices,
                output_dir=out / name,
                template_name="result4-3.xlsx",
                write_outputs=True,
                load_mode="causal",
                settlement_mode="replacement",
                update_nodes=(0, 36, 72, 108),
                tag=name,
                **kwargs,
            )
        metrics = result["metrics"]
        metrics["wall_seconds"] = time.perf_counter() - started
        (out / name / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[name] = metrics
        print(f"[Q4] {name}: total={metrics.get('total_cost_yuan')} emergency={metrics.get('emergency_energy_kwh')}")
    _dump(out / "summary.json", summary)
    return summary


def run_sensitivity(*, max_days: int = 365, data_root: Path = DEFAULT_DATA_ROOT) -> dict:
    out = VARIANTS / "sensitivity"
    summary = {"terminal": {}, "efficiency": {}}
    for policy in ("daily_cycle", "free"):
        started = time.perf_counter()
        result = run_q2(
            data_root=data_root,
            max_days=max_days,
            output_dir=out / "terminal" / policy,
            template_name="result2.xlsx",
            write_outputs=True,
            load_mode="causal",
            pv_risk_mode="asymmetric",
            realtime_feedback=True,
            terminal_policy=policy,
            tag=f"terminal_{policy}",
        )
        metrics = result["metrics"]
        metrics["wall_seconds"] = time.perf_counter() - started
        daily_soc = [float(r["execution"].soc[-1]) for r in result["records"][31:]]
        metrics["daily_boundary_soc"] = {
            "min": float(np.min(daily_soc)),
            "max": float(np.max(daily_soc)),
            "mean": float(np.mean(daily_soc)),
            "std": float(np.std(daily_soc)),
        }
        (out / "terminal" / policy / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary["terminal"][policy] = metrics
        print(f"[P1-terminal] {policy}: total={metrics.get('total_cost_yuan')} endSOC={metrics.get('ending_soc_kwh')}")
    for name, storage in EFFICIENCY_VARIANTS.items():
        started = time.perf_counter()
        result = run_q2(
            data_root=data_root,
            max_days=max_days,
            output_dir=out / "efficiency" / name,
            template_name="result2.xlsx",
            write_outputs=True,
            load_mode="causal",
            pv_risk_mode="asymmetric",
            realtime_feedback=True,
            storage=storage,
            tag=f"efficiency_{name}",
        )
        metrics = result["metrics"]
        metrics["wall_seconds"] = time.perf_counter() - started
        (out / "efficiency" / name / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary["efficiency"][name] = metrics
        print(f"[P1-efficiency] {name}: total={metrics.get('total_cost_yuan')}")
    _dump(out / "summary.json", summary)
    return summary


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
