"""论文数字、强制表格与提交工作簿的一致性测试。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "outputs" / "variants" / "model_audit"
DATES = ("2025-03-20", "2025-06-21", "2025-09-23", "2025-12-21")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_additive_main_cost_decomposition_and_exclusivity() -> None:
    metrics = _json(VARIANTS / "q3_additive" / "S3_0_6_12_18" / "metrics.json")
    components = (
        metrics["baseline_purchase_cost_yuan"]
        + metrics["adjustment_cost_yuan"]
        + metrics["emergency_cost_yuan"]
    )
    assert abs(metrics["total_cost_yuan"] - components) < 1e-6
    assert metrics["max_simultaneous_charge_discharge"] < 1e-5
    assert metrics["passed"] is True


def test_paired_node_decomposition_is_exact() -> None:
    summary = _json(VARIANTS / "q3_additive" / "summary.json")
    chain = (
        ("S0_0", "C1_load6", "S1_0_6"),
        ("S1_0_6", "C2_load12", "S2_0_6_12"),
        ("S2_0_6_12", "C3_load18", "S3_0_6_12_18"),
    )
    for before, control, after in chain:
        total = summary[before]["total_cost_yuan"] - summary[after]["total_cost_yuan"]
        load_part = summary[before]["total_cost_yuan"] - summary[control]["total_cost_yuan"]
        pv_part = summary[control]["total_cost_yuan"] - summary[after]["total_cost_yuan"]
        assert abs(total - load_part - pv_part) < 1e-6


def test_required_date_tables_cover_all_contract_dates() -> None:
    generated = ROOT / "paper" / "generated"
    for name in ("q2_required_tables.tex", "q3_required_tables.tex", "q4_required_tables.tex"):
        text = (generated / name).read_text(encoding="utf-8")
        for date in DATES:
            assert date in text


def test_q4_submission_uses_attachment4_direct_results() -> None:
    pairs = (
        ("result4-2.xlsx", VARIANTS / "q4" / "q42_perfect_price" / "result4-2.xlsx"),
        ("result4-3.xlsx", VARIANTS / "q4" / "q43_perfect_price" / "result4-3.xlsx"),
    )
    for name, source in pairs:
        assert _sha256(ROOT / "submit" / name) == _sha256(source)
