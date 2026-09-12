from __future__ import annotations
import math
from dataclasses import dataclass
from .io_data import DT_HOURS, SLOTS_PER_DAY
POWER_LIMIT_KW = 5000.0
ENERGY_LIMIT = POWER_LIMIT_KW * DT_HOURS
@dataclass(frozen=True)
class StorageParams:
    eta_ch: float = 0.9
    eta_dis: float = 0.9
    soc_min: float = 1200.0
    soc_max: float = 10800.0
    power_limit_kw: float = POWER_LIMIT_KW
    @property
    def energy_limit(self) -> float:
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
TERMINAL_POLICIES = ("daily_cycle", "free")
LOAD_MODES = ("perfect", "causal")
PRICE_MODES = ("perfect", "causal")
PV_RISK_MODES = ("asymmetric", "point")
SETTLEMENT_MODES = ("replacement", "additive")
