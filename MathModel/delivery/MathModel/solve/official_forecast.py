from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .io_data import DT_HOURS

QUANTILES=(0.80,0.85,0.90,0.95)

@dataclass(frozen=True)
class CalibrationDecision:
    issue_index:int; quantile:float; margin_kw:float; history_days_used:int
    raw_forecast_kw:np.ndarray; forecast_kw:np.ndarray; candidates:dict[float,np.ndarray]
    historical_score:float|None

class OnlineForecastBiasCalibrator:
    """Issue-specific causal bias correction for official 24 h PV forecasts."""
    def __init__(self,residual_window:int=30,score_window:int=30):
        self.residual_window=residual_window; self.score_window=score_window
        self.residual_days=[[] for _ in range(4)]
        self.score_days=[{q:[] for q in QUANTILES} for _ in range(4)]
    def calibrate(self,issue_index:int,raw_forecast_kw:np.ndarray)->CalibrationDecision:
        raw=np.asarray(raw_forecast_kw,dtype=float)
        days=self.residual_days[issue_index][-self.residual_window:]
        residual=np.concatenate(days) if days else np.array([])
        margins={q:(max(0.0,float(np.quantile(residual,q))) if residual.size else 0.0) for q in QUANTILES}
        candidates={q:np.clip(raw-margins[q],0.0,None) for q in QUANTILES}
        history_count=len(self.residual_days[issue_index])
        if history_count<7: q=0.80; hist=None
        else:
            scores={x:float(np.mean(self.score_days[issue_index][x][-self.score_window:])) for x in QUANTILES}
            q=min(scores,key=lambda x:(scores[x],x)); hist=scores[q]
        return CalibrationDecision(issue_index,q,margins[q],history_count,raw.copy(),candidates[q],candidates,hist)
    def observe(self,decision:CalibrationDecision,actual_block_kw:np.ndarray,price_block:np.ndarray)->None:
        actual=np.asarray(actual_block_kw,dtype=float); price=np.asarray(price_block,dtype=float)
        if actual.shape!=(36,) or price.shape!=(36,): raise ValueError("calibration block must contain 36 slots")
        issue=decision.issue_index
        if decision.history_days_used!=len(self.residual_days[issue]): raise ValueError("stale calibration decision")
        for q,forecast in decision.candidates.items():
            error=forecast[:36]-actual
            score=float(np.sum(price*(4*np.maximum(error,0)+np.maximum(-error,0)))*DT_HOURS)
            self.score_days[issue][q].append(score)
        raw_error=decision.raw_forecast_kw[:36]-actual
        mask=(decision.raw_forecast_kw[:36]>1e-9)|(actual>1e-9)
        self.residual_days[issue].append(raw_error[mask].copy())
