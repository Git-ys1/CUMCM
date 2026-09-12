"""未来信息泄漏自动测试（任务书 §9）。

核心判据：在 causal 信息集模式下，人为篡改**决策时刻之后**才会发生的
真实负载 / 真实光伏 / 真实电价，决策时刻的优化输入必须完全不变。
"""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ..solve.io_data import read_attachment4
from ..solve.q2 import run_q2
from ..solve.q3 import run_q3
from .mutate import (
    make_root,
    mutate_attachment2_load,
    mutate_attachment2_pv,
    mutate_attachment4_price,
)

TARGET_DAY = 35
DAYS = 36
TOL = 1e-10


class CausalityTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.mkdtemp(prefix="mathmodel_causal_")
        cls.tmp = Path(cls._tmpdir)
        cls.base = make_root(cls.tmp / "base")
        cls.mut_load = make_root(cls.tmp / "mut_load")
        mutate_attachment2_load(cls.mut_load, TARGET_DAY, 0, 10.0)
        cls.mut_pv = make_root(cls.tmp / "mut_pv")
        mutate_attachment2_pv(cls.mut_pv, TARGET_DAY, 0, 10.0)
        cls.mut_both_after_6 = make_root(cls.tmp / "mut_both_after6")
        mutate_attachment2_load(cls.mut_both_after_6, TARGET_DAY, 36, 10.0)
        mutate_attachment2_pv(cls.mut_both_after_6, TARGET_DAY, 36, 10.0)
        cls.mut_price_after_6 = make_root(cls.tmp / "mut_price_after6")
        mutate_attachment4_price(cls.mut_price_after_6, TARGET_DAY, 36, 10.0)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    @staticmethod
    def _run_q2(root: Path, **kwargs):
        return run_q2(data_root=root, max_days=DAYS, write_outputs=False, load_mode="causal", **kwargs)

    @staticmethod
    def _run_q3(root: Path, **kwargs):
        kwargs.setdefault("settlement_mode", "replacement")
        return run_q3(data_root=root, max_days=DAYS, write_outputs=False, load_mode="causal", **kwargs)


class Q2LoadCausalityTest(CausalityTestBase):
    def test_future_load_cannot_change_plan(self):
        base = self._run_q2(self.base)
        mutated = self._run_q2(self.mut_load)
        b = base["records"][TARGET_DAY]["load_plan_kw"]
        m = mutated["records"][TARGET_DAY]["load_plan_kw"]
        self.assertLess(float(np.max(np.abs(b - m))), TOL, "第 d 天真实负载被篡改后 0:00 计划输入发生变化")

    def test_future_load_changes_execution_only(self):
        """篡改真实负载应当改变紧急购电，说明该数据确实通过执行通道发挥作用。"""
        base = self._run_q2(self.base)
        mutated = self._run_q2(self.mut_load)
        b = base["records"][TARGET_DAY]["execution"].emergency.sum()
        m = mutated["records"][TARGET_DAY]["execution"].emergency.sum()
        self.assertNotAlmostEqual(b, m, places=3)


class Q2PVCausalityTest(CausalityTestBase):
    def test_future_pv_cannot_change_plan(self):
        base = self._run_q2(self.base)
        mutated = self._run_q2(self.mut_pv)
        b = base["records"][TARGET_DAY]["pv_plan_kw"]
        m = mutated["records"][TARGET_DAY]["pv_plan_kw"]
        self.assertLess(float(np.max(np.abs(b - m))), TOL, "第 d 天真实光伏被篡改后 0:00 计划输入发生变化")


class Q3NodeCausalityTest(CausalityTestBase):
    def test_node_inputs_do_not_see_future_load_or_pv(self):
        base = self._run_q3(self.base)
        mutated = self._run_q3(self.mut_both_after_6)
        for day in (TARGET_DAY,):
            # 只冻结 6:00 这一次决策的输入；12:00/18:00 的预测可以合法使用 6:00-12:00
            # 已经执行完的观测（这正是滚动在线预测的应有之义）。
            b_load = base["records"][day]["load_plan_kw"][36:72]
            m_load = mutated["records"][day]["load_plan_kw"][36:72]
            self.assertLess(float(np.max(np.abs(b_load - m_load))), TOL, "6:00 负载预测输入受到未来真实负载影响")
            b_block = base["records"][day]["adjusted_grid"][36:72]
            m_block = mutated["records"][day]["adjusted_grid"][36:72]
            self.assertLess(float(np.max(np.abs(b_block - m_block))), TOL, "6:00 优化结果受到未来真实负载/光伏影响")
            b_base = base["records"][day]["baseline_plan"].grid
            m_base = mutated["records"][day]["baseline_plan"].grid
            self.assertLess(float(np.max(np.abs(b_base - m_base))), TOL, "0:00 基准计划受到未来真实负载/光伏影响")


class Q4PriceCausalityTest(CausalityTestBase):
    def test_causal_price_ignores_future_realized_price(self):
        prices = read_attachment4(self.base).price
        base = self._run_q3(self.base, price_matrix=prices, price_mode="causal")
        mutated = self._run_q3(self.mut_price_after_6, price_matrix=prices, price_mode="causal")
        b = base["records"][TARGET_DAY]["adjusted_grid"][36:72]
        m = mutated["records"][TARGET_DAY]["adjusted_grid"][36:72]
        self.assertLess(float(np.max(np.abs(b - m))), TOL, "causal 电价模式下提前看到未来真实电价")

    def test_perfect_price_does_see_future_realized_price(self):
        """反证：perfect 模式下同一篡改确实会改变结果（说明测试本身有鉴别力）。"""
        base = self._run_q3(self.base, price_matrix=read_attachment4(self.base).price, price_mode="perfect")
        mutated = self._run_q3(
            self.mut_price_after_6,
            price_matrix=read_attachment4(self.mut_price_after_6).price,
            price_mode="perfect",
        )
        b = base["records"][TARGET_DAY]["adjusted_grid"][36:72]
        m = mutated["records"][TARGET_DAY]["adjusted_grid"][36:72]
        self.assertGreater(float(np.max(np.abs(b - m))), 1e-6)


if __name__ == "__main__":
    unittest.main()
