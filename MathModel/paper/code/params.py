"""储能物理参数与口径变体。

题目附录 1 只给出"充放电效率为 90%"，存在两种等价解释：
  E1  充电效率 = 放电效率 = 0.90      （往返效率 0.81）
  E2  往返总效率 = 0.90               （充电效率 = 放电效率 = sqrt(0.90)）
主模型采用 E1；E2 作为效率口径敏感性对照。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .io_data import DT_HOURS, SLOTS_PER_DAY

POWER_LIMIT_KW = 5000.0
ENERGY_LIMIT = POWER_LIMIT_KW * DT_HOURS  # 833.333... kWh / 10 min


@dataclass(frozen=True)
class StorageParams:
    """储能物理参数。充电量 C 为母线侧电量，放电量 H 为母线侧电量。"""

    eta_ch: float = 0.9
    eta_dis: float = 0.9
    soc_min: float = 1200.0
    soc_max: float = 10800.0
    power_limit_kw: float = POWER_LIMIT_KW

    @property
    def energy_limit(self) -> float:
        """单个 10 min 时段的最大充放电量（kWh）。"""
        return self.power_limit_kw * DT_HOURS

    @property
    def round_trip(self) -> float:
        return self.eta_ch * self.eta_dis

    def as_dict(self) -> dict:
        return {
            "eta_ch": self.eta_ch,
            "eta_dis": self.eta_dis,
            "round_trip_efficiency": self.round_trip,
            "soc_min": self.soc_min,
            "soc_max": self.soc_max,
            "power_limit_kw": self.power_limit_kw,
            "energy_limit_per_slot_kwh": self.energy_limit,
        }


DEFAULT_STORAGE = StorageParams()
SQRT_HALF = math.sqrt(0.9)
EFFICIENCY_VARIANTS: dict[str, StorageParams] = {
    "E1_eta_ch_0.90_eta_dis_0.90": StorageParams(0.9, 0.9),
    "E2_round_trip_0.90": StorageParams(SQRT_HALF, SQRT_HALF),
}

# 终端 SOC 策略
TERMINAL_POLICIES = ("daily_cycle", "free")
# 信息集口径
LOAD_MODES = ("perfect", "causal")
PRICE_MODES = ("perfect", "causal")
PV_RISK_MODES = ("asymmetric", "point")
SETTLEMENT_MODES = ("replacement", "additive")
