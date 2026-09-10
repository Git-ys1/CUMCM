from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .io_data import DT_HOURS
from .lp_core import DispatchResult,ENERGY_LIMIT,ETA_CH,ETA_DIS,SOC_MAX,SOC_MIN

@dataclass(frozen=True)
class ExecutionResult:
    grid:np.ndarray; charge:np.ndarray; discharge:np.ndarray; soc:np.ndarray
    curtail:np.ndarray; emergency:np.ndarray

def execute_with_realtime_storage_feedback(plan:DispatchResult,load_kw:np.ndarray,actual_pv_kw:np.ndarray,*,soc_initial:float)->ExecutionResult:
    load=np.asarray(load_kw,dtype=float); pv=np.asarray(actual_pv_kw,dtype=float); n=len(load)
    if pv.shape!=load.shape or len(plan.grid)!=n: raise ValueError("execution shape mismatch")
    c_out=np.zeros(n); h_out=np.zeros(n); soc=np.zeros(n); spill=np.zeros(n); emergency=np.zeros(n)
    state=float(soc_initial)
    for t in range(n):
        c=min(float(plan.charge[t]),ENERGY_LIMIT,max(0.0,(SOC_MAX-state)/ETA_CH))
        h=min(float(plan.discharge[t]),ENERGY_LIMIT,max(0.0,(state-SOC_MIN)*ETA_DIS))
        net=float(plan.grid[t]+pv[t]*DT_HOURS+h-load[t]*DT_HOURS-c)
        if net < -1e-10:
            deficit=-net; reduce=min(c,deficit); c-=reduce; deficit-=reduce
            max_h=max(0.0,(state+ETA_CH*c-SOC_MIN)*ETA_DIS)
            add=min(deficit,ENERGY_LIMIT-h,max(0.0,max_h-h)); h+=add; deficit-=add
            emergency[t]=max(0.0,deficit)
        elif net > 1e-10:
            surplus=net; reduce=min(h,surplus); h-=reduce; surplus-=reduce
            max_c=max(0.0,(SOC_MAX-(state-h/ETA_DIS))/ETA_CH)
            add=min(surplus,ENERGY_LIMIT-c,max(0.0,max_c-c)); c+=add; surplus-=add
            spill[t]=max(0.0,surplus)
        state=state+ETA_CH*c-h/ETA_DIS
        if not SOC_MIN-1e-6<=state<=SOC_MAX+1e-6: raise RuntimeError(f"SOC invalid at {t}: {state}")
        c_out[t]=c; h_out[t]=h; soc[t]=min(SOC_MAX,max(SOC_MIN,state))
    return ExecutionResult(plan.grid.copy(),c_out,h_out,soc,spill,emergency)
