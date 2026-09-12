from __future__ import annotations
import json
import unittest
from pathlib import Path
from ..solve.io_data import read_attachment4
from ..solve.q1 import run_q1
from ..solve.q2 import run_q2
from ..solve.q3 import run_q3
FIXTURE = Path(__file__).with_name("legacy_metrics.json")
LEGACY = json.loads(FIXTURE.read_text(encoding="utf-8"))
ABS_TOL = 1e-3
REL_TOL = 1e-9
def _close(test: unittest.TestCase, label: str, new: float, old: float, abs_tol: float = ABS_TOL) -> None:
    tolerance = max(abs_tol, REL_TOL * abs(old))
    test.assertLess(
        abs(new - old),
        tolerance,
        f"{label} 未复现 legacy 数值：new={new!r} legacy={old!r} diff={new - old!r}",
    )
class LegacyRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = read_attachment4().price
    def test_q1_unchanged(self):
        metrics = run_q1()["metrics"]
        _close(self, "Q1 费用", metrics["cost_yuan"], LEGACY["q1"]["cost_yuan"])
        _close(self, "Q1 购电量", metrics["grid_energy_kwh"], LEGACY["q1"]["grid_energy_kwh"])
        _close(self, "Q1 充电量", metrics["charge_energy_kwh"], LEGACY["q1"]["charge_energy_kwh"])
    def test_q2_legacy_benchmark(self):
        metrics = run_q2(
            max_days=365,
            write_outputs=False,
            load_mode="perfect",
            pv_risk_mode="asymmetric",
            realtime_feedback=True,
            price_mode="perfect",
            terminal_policy="daily_cycle",
            use_typical_prior=False,
        )["metrics"]
        _close(self, "Q2 总费用", metrics["total_cost_yuan"], LEGACY["q2"]["total_cost_yuan"])
        _close(self, "Q2 计划费用", metrics["plan_purchase_cost_yuan"], LEGACY["q2"]["plan_purchase_cost_yuan"])
        _close(self, "Q2 紧急电量", metrics["emergency_energy_kwh"], LEGACY["q2"]["emergency_energy_kwh"])
        _close(self, "Q2 弃光量", metrics["curtailment_energy_kwh"], LEGACY["q2"]["curtailment_energy_kwh"])
    def test_q3_legacy_benchmark(self):
        metrics = run_q3(
            max_days=365,
            write_outputs=False,
            downscale="linear",
            calibrate=True,
            update_nodes=(0, 36, 72, 108),
            settlement_mode="replacement",
            load_mode="perfect",
            price_mode="perfect",
            realtime_feedback=True,
            terminal_policy="daily_cycle",
            use_typical_prior=False,
        )["metrics"]
        _close(self, "Q3 总费用", metrics["total_cost_yuan"], LEGACY["q3"]["total_cost_yuan"])
        _close(self, "Q3 基准计划费用", metrics["baseline_purchase_cost_yuan"], LEGACY["q3"]["baseline_purchase_cost_yuan"])
        _close(self, "Q3 紧急电量", metrics["emergency_energy_kwh"], LEGACY["q3"]["emergency_energy_kwh"])
        _close(self, "Q3 弃光量", metrics["curtailment_energy_kwh"], LEGACY["q3"]["curtailment_energy_kwh"], abs_tol=1e-2)
    def test_q4_legacy_benchmark(self):
        metrics2 = run_q2(
            max_days=365,
            write_outputs=False,
            price_matrix=self.prices,
            load_mode="perfect",
            pv_risk_mode="asymmetric",
            realtime_feedback=True,
            price_mode="perfect",
            use_typical_prior=False,
        )["metrics"]
        _close(self, "Q4-2 总费用", metrics2["total_cost_yuan"], LEGACY["q4-2"]["total_cost_yuan"])
        metrics3 = run_q3(
            max_days=365,
            write_outputs=False,
            price_matrix=self.prices,
            update_nodes=(0, 36, 72, 108),
            settlement_mode="replacement",
            load_mode="perfect",
            price_mode="perfect",
            realtime_feedback=True,
            use_typical_prior=False,
        )["metrics"]
        _close(self, "Q4-3 总费用", metrics3["total_cost_yuan"], LEGACY["q4-3"]["total_cost_yuan"])
if __name__ == "__main__":
    unittest.main()
