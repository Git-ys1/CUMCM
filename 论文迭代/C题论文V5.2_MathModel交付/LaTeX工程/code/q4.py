from __future__ import annotations
import json
from pathlib import Path
from .io_data import DEFAULT_DATA_ROOT, read_attachment4
from .q2 import run_q2
from .q3 import run_q3
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
def run_q4(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    max_days: int = 365,
    price_mode_q2: str = "perfect",
    price_mode_q3: str = "perfect",
    load_mode: str = "causal",
    settlement_mode: str = "replacement",
    update_nodes: tuple[int, ...] = (0, 36, 72, 108),
    realtime_feedback: bool = True,
    write_outputs: bool = True,
    tag_prefix: str = "",
) -> dict:
    annual_price = read_attachment4(data_root)
    prices = annual_price.price
    suffix = f"-{tag_prefix}" if tag_prefix else ""
    out2 = OUTPUT / f"q4-2{suffix}"
    out3 = OUTPUT / f"q4-3{suffix}"
    q4_2 = run_q2(
        data_root=data_root,
        max_days=max_days,
        price_matrix=prices,
        output_dir=out2,
        template_name="result4-2.xlsx",
        write_outputs=write_outputs,
        load_mode=load_mode,
        price_mode=price_mode_q2,
        realtime_feedback=realtime_feedback,
        tag=f"q4-2 {tag_prefix}".strip(),
    )
    q4_3 = run_q3(
        data_root=data_root,
        max_days=max_days,
        price_matrix=prices,
        output_dir=out3,
        template_name="result4-3.xlsx",
        write_outputs=write_outputs,
        load_mode=load_mode,
        price_mode=price_mode_q3,
        settlement_mode=settlement_mode,
        update_nodes=update_nodes,
        realtime_feedback=realtime_feedback,
        tag=f"q4-3 {tag_prefix}".strip(),
    )
    c2 = q4_2["metrics"].get("total_cost_yuan")
    c3 = q4_3["metrics"].get("total_cost_yuan")
    comparison = {
        "q4_2_total_cost_yuan": c2,
        "q4_3_total_cost_yuan": c3,
        "rolling_saving_yuan": None if (c2 is None or c3 is None) else c2 - c3,
        "rolling_saving_percent": None if (c2 is None or c3 is None) else 100 * (c2 - c3) / c2,
        "q4_2_emergency_energy_kwh": q4_2["metrics"].get("emergency_energy_kwh"),
        "q4_3_emergency_energy_kwh": q4_3["metrics"].get("emergency_energy_kwh"),
        "q4_2_price_mode": price_mode_q2,
        "q4_3_price_mode": price_mode_q3,
        "q4_2_price_mae": q4_2["metrics"].get("price_forecast_mae"),
        "q4_3_price_mae": q4_3["metrics"].get("price_forecast_mae"),
        "q4_2_passed": bool(q4_2["metrics"]["passed"]),
        "q4_3_passed": bool(q4_3["metrics"]["passed"]),
    }
    comparison["passed"] = comparison["q4_2_passed"] and comparison["q4_3_passed"]
    if write_outputs:
        out2.mkdir(parents=True, exist_ok=True)
        (out2 / "q4_comparison.json").write_text(
            json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return {"q4_2": q4_2, "q4_3": q4_3, "comparison": comparison}
if __name__ == "__main__":
    print(json.dumps(run_q4()["comparison"], ensure_ascii=False, indent=2))
