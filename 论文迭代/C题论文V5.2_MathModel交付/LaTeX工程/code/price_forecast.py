from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .io_data import DT_HOURS, SLOTS_PER_DAY
from .load_forecast import NODE_SLOTS
METHOD_WINDOWS: dict[str, int] = {
    "persistence": 1,
    "mean7": 7,
    "mean14": 14,
    "mean30": 30,
    "weighted14": 14,
    "weighted30": 30,
    "weekday_mean": 28,
}
BASE_METHODS = tuple(METHOD_WINDOWS)
@dataclass(frozen=True)
class PriceForecastDecision:
    day_index: int
    node: int
    name: str
    method: str
    historical_score: float | None
    history_days_used: int
    horizon: int
    forecast_price: np.ndarray
    candidates: dict[str, np.ndarray]
def _window_shape(history: list[tuple[np.ndarray, int]], method: str, weekday: int) -> np.ndarray:
    if not history:
        return np.full(SLOTS_PER_DAY, np.nan, dtype=float)
    if method == "weekday_mean":
        same = [h for h, w in history if w == weekday]
        if len(same) >= 2:
            return np.stack(same[-4:]).mean(axis=0)
        method = "mean7"
    n = min(METHOD_WINDOWS[method], len(history))
    recent = np.stack([h for h, _ in history[-n:]])
    if method == "persistence":
        return recent[-1].copy()
    if method.startswith("weighted"):
        weights = np.arange(1, n + 1, dtype=float)
        return np.average(recent, axis=0, weights=weights)
    return recent.mean(axis=0)
class OnlinePriceForecaster:
    def __init__(self, score_window: int = 30, prior_price: np.ndarray | None = None) -> None:
        self.score_window = score_window
        self.history: list[tuple[np.ndarray, int]] = []
        self.prior_days = 0
        if prior_price is not None:
            prior = np.asarray(prior_price, dtype=float)
            if prior.shape != (SLOTS_PER_DAY,):
                raise ValueError("prior price must have 144 slots")
            self.history.append((prior.copy(), -1))
            self.prior_days = 1
        self.partial_len: int = 0
        self.score_days: dict[tuple[int, str], list[float]] = {}
    @property
    def observed_days(self) -> int:
        return len(self.history) - self.prior_days
    def _weekday(self, day_index: int, offset: int) -> int:
        return (day_index + offset) % 7
    def _base_horizon(self, method: str, day_index: int, node: int, horizon: int) -> np.ndarray:
        head = _window_shape(self.history, method, self._weekday(day_index, 0))[node:]
        if len(head) >= horizon:
            return head[:horizon].copy()
        tail_len = horizon - len(head)
        tail = _window_shape(self.history, method, self._weekday(day_index, 1))
        while len(tail) < tail_len:
            tail = np.concatenate([tail, tail])
        return np.concatenate([head, tail[:tail_len]])
    def _fallback(self) -> np.ndarray:
        if not self.history:
            return np.full(SLOTS_PER_DAY, 0.5, dtype=float)
        return self.history[-1][0].copy()
    def predict_horizon(self, day_index: int, node: int = 0, horizon: int = SLOTS_PER_DAY) -> PriceForecastDecision:
        if node not in NODE_SLOTS:
            raise ValueError(f"node must be one of {NODE_SLOTS}")
        candidates: dict[str, np.ndarray] = {}
        for method in BASE_METHODS:
            horizon_values = self._base_horizon(method, day_index, node, horizon)
            if not np.isfinite(horizon_values).all():
                horizon_values = np.where(np.isfinite(horizon_values), horizon_values, self._fallback()[node % SLOTS_PER_DAY])
            candidates[method] = np.clip(horizon_values, 1e-6, None)
        eligible = [n for n in BASE_METHODS if self.score_days.get((node, n))]
        history_days = max((len(v) for (n, _), v in self.score_days.items() if n == node), default=0)
        if history_days < 7 or not eligible:
            selected, hist = "persistence", None
        else:
            scores = {n: float(np.mean(self.score_days[(node, n)][-self.score_window :])) for n in eligible}
            selected = min(scores, key=lambda n: (scores[n], n))
            hist = scores[selected]
        return PriceForecastDecision(
            day_index=day_index,
            node=node,
            name=selected,
            method=selected,
            historical_score=hist,
            history_days_used=self.observed_days,
            horizon=horizon,
            forecast_price=candidates[selected].copy(),
            candidates=candidates,
        )
    def observe_block(self, decision: PriceForecastDecision, actual_block: np.ndarray) -> dict[str, float]:
        actual = np.asarray(actual_block, dtype=float)
        out: dict[str, float] = {}
        for name, forecast in decision.candidates.items():
            segment = forecast[: len(actual)]
            mae = float(np.mean(np.abs(segment - actual)))
            self.score_days.setdefault((decision.node, name), []).append(mae)
            out[name] = mae
        return out
    def observe_partial(self, node: int) -> None:
        self.partial_len = node
    def commit_day(self, actual_full_day: np.ndarray, day_index: int) -> None:
        actual = np.asarray(actual_full_day, dtype=float)
        if actual.shape != (SLOTS_PER_DAY,):
            raise ValueError("daily price must have 144 slots")
        self.history.append((actual.copy(), self._weekday(day_index, 0)))
        self.partial_len = 0
    def log_row(self, decision: PriceForecastDecision, actual_block: np.ndarray, date_text: str) -> dict:
        actual = np.asarray(actual_block, dtype=float)
        forecast = decision.forecast_price[: len(actual)]
        error = forecast - actual
        slot = int(decision.node * 10) // 60
        minute = (decision.node * 10) % 60
        return {
            "date": date_text,
            "decision_time": f"{slot:02d}:{minute:02d}",
            "history_days_used": decision.history_days_used,
            "method": decision.method,
            "price_mae": float(np.mean(np.abs(error))),
            "price_rmse": float(np.sqrt(np.mean(error**2))),
            "price_energy_weighted_error": float(
                np.sum(np.abs(error) * actual) / max(np.sum(actual), 1e-9)
            ),
            "daily_price_energy_weighted_error": float(
                np.sum(np.abs(error) * actual) * DT_HOURS
            ),
            "historical_score": decision.historical_score,
        }
