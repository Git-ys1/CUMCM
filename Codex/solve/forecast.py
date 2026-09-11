from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .io_data import DT_HOURS,SLOTS_PER_DAY

METHOD_WINDOWS={"persistence":1,"mean7":7,"mean14":14,"mean30":30,"weighted14":14,"weighted30":30}
QUANTILES=(0.80,0.85,0.90,0.95)

@dataclass(frozen=True)
class ForecastDecision:
    day_index:int; name:str; method:str; quantile:float; margin_kw:float
    historical_score:float|None; history_days_used:int; forecast_kw:np.ndarray
    candidates:dict[str,np.ndarray]; bases:dict[str,np.ndarray]; margins:dict[str,float]

class OnlinePVForecaster:
    """All forecasts and model choices for day d use only observations before d."""
    def __init__(self,price:np.ndarray,score_window:int=30,residual_window:int=30):
        self.price=np.asarray(price,dtype=float)
        if self.price.shape!=(SLOTS_PER_DAY,): raise ValueError("price must contain 144 slots")
        self.score_window=score_window; self.residual_window=residual_window
        self.actual_history:list[np.ndarray]=[]
        self.residual_days={m:[] for m in METHOD_WINDOWS}
        self.score_days={self._name(m,q):[] for m in METHOD_WINDOWS for q in QUANTILES}
    @staticmethod
    def _name(method:str,q:float)->str: return f"{method}_q{int(round(q*100)):02d}"
    def _base(self,method:str)->np.ndarray:
        if not self.actual_history: return np.zeros(SLOTS_PER_DAY)
        n=min(METHOD_WINDOWS[method],len(self.actual_history)); recent=np.stack(self.actual_history[-n:])
        if method=="persistence": return recent[-1].copy()
        if method.startswith("weighted"): return np.average(recent,axis=0,weights=np.arange(1,n+1,dtype=float))
        return recent.mean(axis=0)
    def _margin(self,method:str,q:float)->float:
        days=self.residual_days[method][-self.residual_window:]
        if not days: return 0.0
        residual=np.concatenate(days)
        return 0.0 if residual.size==0 else max(0.0,float(np.quantile(residual,q)))
    def predict(self)->ForecastDecision:
        d=len(self.actual_history); bases={m:self._base(m) for m in METHOD_WINDOWS}; candidates={}; margins={}
        for method,base in bases.items():
            for q in QUANTILES:
                name=self._name(method,q); margins[name]=self._margin(method,q)
                candidates[name]=np.clip(base-margins[name],0.0,None)
        default=self._name("persistence",0.80)
        eligible=[n for n,s in self.score_days.items() if s]
        if d<7 or not eligible: selected=default; hist=None
        else:
            scores={n:float(np.mean(self.score_days[n][-self.score_window:])) for n in eligible}
            selected=min(scores,key=lambda n:(scores[n],n)); hist=scores[selected]
        method,q_text=selected.rsplit("_q",1)
        return ForecastDecision(d,selected,method,int(q_text)/100.0,margins[selected],hist,d,
                                candidates[selected].copy(),candidates,bases,margins)
    def observe(self,decision:ForecastDecision,actual_kw:np.ndarray,price:np.ndarray|None=None)->dict[str,float]:
        actual=np.asarray(actual_kw,dtype=float)
        if actual.shape!=(144,) or decision.day_index!=len(self.actual_history):
            raise ValueError("forecast observation out of sequence")
        score_price=self.price if price is None else np.asarray(price,dtype=float)
        if score_price.shape!=(144,): raise ValueError("score price must contain 144 slots")
        result={}
        for name,forecast in decision.candidates.items():
            error=forecast-actual
            score=float(np.sum(score_price*(4*np.maximum(error,0)+np.maximum(-error,0)))*DT_HOURS)
            self.score_days[name].append(score); result[name]=score
        for method,base in decision.bases.items():
            mask=(actual>1e-9)|(base>1e-9)
            self.residual_days[method].append((base-actual)[mask].copy())
        self.actual_history.append(actual.copy())
        return result
