from __future__ import annotations
import unittest
import numpy as np
from ..solve.lp_core import settlement_cost, solve_adjustment_dispatch
from ..solve.params import DEFAULT_STORAGE
class ReplacementFormulaTest(unittest.TestCase):
    def test_purchase_below_plan(self):
        value = settlement_cost(np.array([900.0]), np.array([700.0]), np.array([1.0]), "replacement")
        self.assertAlmostEqual(value, 800.0, places=9)
    def test_purchase_above_plan(self):
        value = settlement_cost(np.array([700.0]), np.array([900.0]), np.array([1.0]), "replacement")
        self.assertAlmostEqual(value, 1000.0, places=9)
    def test_unchanged(self):
        value = settlement_cost(np.array([800.0]), np.array([800.0]), np.array([1.0]), "replacement")
        self.assertAlmostEqual(value, 800.0, places=9)
class AdditiveFormulaTest(unittest.TestCase):
    def test_purchase_below_plan(self):
        value = settlement_cost(np.array([900.0]), np.array([700.0]), np.array([1.0]), "additive")
        self.assertAlmostEqual(value, 1000.0, places=9)
    def test_purchase_above_plan(self):
        value = settlement_cost(np.array([700.0]), np.array([900.0]), np.array([1.0]), "additive")
        self.assertAlmostEqual(value, 1000.0, places=9)
def _case(seed: int, t: int = 24, mask_all: bool = True):
    rng = np.random.default_rng(seed)
    load = 800.0 + 200.0 * rng.random(t)
    pv = 400.0 * rng.random(t)
    price = 0.3 + 0.7 * rng.random(t)
    baseline = np.maximum((load - pv) * (1 / 6), 0.0)
    mask = np.ones(t, dtype=bool) if mask_all else np.r_[np.ones(t - 6, dtype=bool), np.zeros(6, dtype=bool)]
    return load, pv, price, baseline, mask
def _model_objective(result, price, baseline, mode: str) -> float:
    mask = result.adjustment_mask
    p = price[mask]
    if mode == "replacement":
        return float(np.dot(p, result.dispatch.grid[mask] + 0.5 * result.increase[mask] + 0.5 * result.decrease[mask]))
    return float(np.dot(p, baseline[mask]) + np.dot(p, 0.5 * result.decrease[mask] + 1.5 * result.increase[mask]))
class LinearizationTest(unittest.TestCase):
    def _gap(self, mode: str, seed: int) -> float:
        load, pv, price, baseline, mask = _case(seed)
        result = solve_adjustment_dispatch(
            load, pv, price, baseline, mask,
            soc_initial=6000.0, soc_terminal=6000.0, settlement_mode=mode,
        )
        direct = settlement_cost(baseline, result.dispatch.grid, price, mode)
        return abs(direct - _model_objective(result, price, baseline, mode))
    def test_replacement_linearization(self):
        for seed in range(5):
            self.assertLess(self._gap("replacement", seed), 1e-7, f"seed={seed}")
    def test_additive_linearization(self):
        for seed in range(5):
            self.assertLess(self._gap("additive", seed), 1e-7, f"seed={seed}")
    def test_two_modes_are_reoptimized_not_revalued(self):
        for seed in range(5):
            load, pv, price, baseline, mask = _case(seed)
            kwargs = dict(soc_initial=6000.0, soc_terminal=6000.0)
            replacement = solve_adjustment_dispatch(
                load, pv, price, baseline, mask, settlement_mode="replacement", **kwargs
            )
            additive = solve_adjustment_dispatch(
                load, pv, price, baseline, mask, settlement_mode="additive", **kwargs
            )
            best_replacement = settlement_cost(baseline, replacement.dispatch.grid, price, "replacement")
            cross_replacement = settlement_cost(baseline, additive.dispatch.grid, price, "replacement")
            best_additive = settlement_cost(baseline, additive.dispatch.grid, price, "additive")
            cross_additive = settlement_cost(baseline, replacement.dispatch.grid, price, "additive")
            tol_r = 1e-6 * max(1.0, abs(best_replacement))
            tol_a = 1e-6 * max(1.0, abs(best_additive))
            self.assertLessEqual(best_replacement, cross_replacement + tol_r, f"seed={seed}")
            self.assertLessEqual(best_additive, cross_additive + tol_a, f"seed={seed}")
class StorageParamTest(unittest.TestCase):
    def test_energy_limit(self):
        self.assertAlmostEqual(DEFAULT_STORAGE.energy_limit, 5000.0 / 6.0, places=9)
if __name__ == "__main__":
    unittest.main()
