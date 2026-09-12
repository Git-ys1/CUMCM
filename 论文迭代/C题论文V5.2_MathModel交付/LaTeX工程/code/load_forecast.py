from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .io_data import DT_HOURS, SLOTS_PER_DAY
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
NODE_SLOTS = (0, 36, 72, 108)
@dataclass(frozen=True)
class LoadForecastDecision:
    day_index: int
    node: int
    name: str
    method: str
    corrected: bool
    offset_kw: float
    historical_score: float | None
    history_days_used: int
    horizon: int
    forecast_kw: np.ndarray
    candidates: dict[str, np.ndarray]
    weekday_of_target: int
def _daily_window_shape(history: list[np.ndarray], method: str, weekday: int) -> np.ndarray:
    if not history:
        return np.zeros(SLOTS_PER_DAY, dtype=float)
    if method == "weekday_mean":
        same = [h for h, w in history if w == weekday]
        if len(same) >= 2:
            recent = np.stack(same[-4:])
            return recent.mean(axis=0)
        method = "mean7"
    n = min(METHOD_WINDOWS[method], len(history))
    recent = np.stack([h for h, _ in history[-n:]])
    if method == "persistence":
        return recent[-1].copy()
    if method.startswith("weighted"):
        weights = np.arange(1, n + 1, dtype=float)
        return np.average(recent, axis=0, weights=weights)
    return recent.mean(axis=0)
class OnlineLoadForecaster:
    def __init__(self, score_window: int = 30, prior_kw: np.ndarray | None = None) -> None:
        self.score_window = score_window
        self.history: list[tuple[np.ndarray, int]] = []
        self.prior_days = 0
        if prior_kw is not None:
            prior = np.asarray(prior_kw, dtype=float)
            if prior.shape != (SLOTS_PER_DAY,):
                raise ValueError("prior load must have 144 slots")
            self.history.append((prior.copy(), -1))
            self.prior_days = 1
        self.partial: np.ndarray = np.zeros(SLOTS_PER_DAY, dtype=float)
        self.partial_len: int = 0
        self.score_days: dict[tuple[int, str], list[float]] = {}
    @property
    def observed_days(self) -> int:
        return len(self.history) - self.prior_days
    def _target_weekday(self, day_index: int, day_offset: int) -> int:
        return (day_index + day_offset) % 7
    def _base_horizon(self, method: str, day_index: int, node: int, horizon: int) -> np.ndarray:
        wd_today = self._target_weekday(day_index, 0)
        shape_today = _daily_window_shape(self.history, method, wd_today)
        head = shape_today[node:]
        if len(head) >= horizon:
            return head[:horizon].copy()
        wd_next = self._target_weekday(day_index, 1)
        shape_next = _daily_window_shape(self.history, method, wd_next)
        tail = horizon - len(head)
        while len(shape_next) < tail:
            shape_next = np.concatenate([shape_next, shape_next])
        return np.concatenate([head, shape_next[:tail]])
    def _offset(self, method: str, day_index: int, node: int) -> float:
        if node <= 0 or self.partial_len <= 0:
            return 0.0
        k = min(36, node, self.partial_len)
        if k < 6:
            return 0.0
        observed = self.partial[node - k : node]
        base = _daily_window_shape(self.history, method, self._target_weekday(day_index, 0))[node - k : node]
        return float(np.mean(observed - base))
    def _candidate_names(self, node: int) -> tuple[str, ...]:
        if node == 0:
            return BASE_METHODS
        return tuple(f"{m}_{suffix}" for m in BASE_METHODS for suffix in ("raw", "offset"))
    def _build(self, name: str, day_index: int, node: int, horizon: int) -> tuple[np.ndarray, str, bool, float]:
        if name.endswith("_offset"):
            method, corrected = name[: -len("_offset")], True
        elif name.endswith("_raw"):
            method, corrected = name[: -len("_raw")], False
        else:
            method, corrected = name, False
        base = self._base_horizon(method, day_index, node, horizon)
        offset = self._offset(method, day_index, node) if corrected else 0.0
        return np.clip(base + offset, 0.0, None), method, corrected, offset
    def predict(self, day_index: int, node: int = 0, horizon: int = SLOTS_PER_DAY) -> LoadForecastDecision:
        if node not in NODE_SLOTS:
            raise ValueError(f"node must be one of {NODE_SLOTS}")
        names = self._candidate_names(node)
        candidates: dict[str, np.ndarray] = {}
        meta: dict[str, tuple[str, bool, float]] = {}
        for name in names:
            forecast, method, corrected, offset = self._build(name, day_index, node, horizon)
            candidates[name] = forecast
            meta[name] = (method, corrected, offset)
        eligible = [n for n in names if self.score_days.get((node, n))]
        history_days = self._score_history_days(node)
        default = "persistence" if node == 0 else "persistence_raw"
        if history_days < 7 or not eligible:
            selected, hist = default, None
        else:
            scores = {
                n: float(np.mean(self.score_days[(node, n)][-self.score_window :])) for n in eligible
            }
            selected = min(scores, key=lambda n: (scores[n], n))
            hist = scores[selected]
        method, corrected, offset = meta[selected]
        return LoadForecastDecision(
            day_index=day_index,
            node=node,
            name=selected,
            method=method,
            corrected=corrected,
            offset_kw=offset,
            historical_score=hist,
            history_days_used=self.observed_days,
            horizon=horizon,
            forecast_kw=candidates[selected].copy(),
            candidates=candidates,
            weekday_of_target=self._target_weekday(day_index, 0),
        )
    def _score_history_days(self, node: int) -> int:
        return max((len(v) for (n, _), v in self.score_days.items() if n == node), default=0)
    def observe_block(self, decision: LoadForecastDecision, actual_block_kw: np.ndarray) -> dict[str, float]:
        actual = np.asarray(actual_block_kw, dtype=float)
        if actual.ndim != 1:
            raise ValueError("actual block must be 1-D")
        out: dict[str, float] = {}
        for name, forecast in decision.candidates.items():
            segment = forecast[: len(actual)]
            mae = float(np.mean(np.abs(segment - actual)))
            self.score_days.setdefault((decision.node, name), []).append(mae)
            out[name] = mae
        return out
    def observe_partial(self, node: int, actual_slots: np.ndarray) -> None:
        if actual_slots.shape != (node,) and node != 0:
            raise ValueError("partial block shape mismatch")
        self.partial[:node] = actual_slots
        self.partial_len = node
    def commit_day(self, actual_full_day_kw: np.ndarray, day_index: int) -> None:
        actual = np.asarray(actual_full_day_kw, dtype=float)
        if actual.shape != (SLOTS_PER_DAY,):
            raise ValueError("daily load must have 144 slots")
        self.history.append((actual.copy(), self._target_weekday(day_index, 0)))
        self.partial = np.zeros(SLOTS_PER_DAY, dtype=float)
        self.partial_len = 0
    def log_row(self, decision: LoadForecastDecision, actual_block_kw: np.ndarray, date_text: str) -> dict:
        actual = np.asarray(actual_block_kw, dtype=float)
        forecast = decision.forecast_kw[: len(actual)]
        error = forecast - actual
        slot = int(decision.node * 10) // 60
        minute = (decision.node * 10) % 60
        label = f"{slot:02d}:{minute:02d}"
        return {
            "date": date_text,
            "decision_time": label,
            "history_days_used": decision.history_days_used,
            "candidate": decision.name,
            "method": decision.method,
            "offset_corrected": decision.corrected,
            "offset_kw": decision.offset_kw,
            "mae_kw": float(np.mean(np.abs(error))),
            "rmse_kw": float(np.sqrt(np.mean(error**2))),
            "daily_energy_error_kwh": float(np.sum(error) * DT_HOURS),
            "block_energy_error_kwh": float(np.sum(error) * DT_HOURS),
            "historical_score": decision.historical_score,
        }
