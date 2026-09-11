from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from scipy.optimize import linprog
from .io_data import DT_HOURS

ETA_CH=0.9; ETA_DIS=0.9; SOC_MIN=1200.0; SOC_MAX=10800.0
POWER_LIMIT_KW=5000.0; ENERGY_LIMIT=POWER_LIMIT_KW*DT_HOURS

@dataclass
class DispatchResult:
    grid:np.ndarray; charge:np.ndarray; discharge:np.ndarray; soc:np.ndarray; curtail:np.ndarray
    objective:float; primary_objective:float; curtail_total:float; throughput_total:float
    status:int; message:str; nit:int; solve_seconds:float; equality_marginals:np.ndarray

def _slices(t:int):
    return slice(0,t),slice(t,2*t),slice(2*t,3*t),slice(3*t,4*t),slice(4*t,5*t)

def _solve(c,a_eq,b_eq,bounds,a_ub=None,b_ub=None):
    return linprog(c,A_ub=a_ub,b_ub=b_ub,A_eq=a_eq,b_eq=b_eq,bounds=bounds,method="highs",
                   options={"primal_feasibility_tolerance":1e-9,"dual_feasibility_tolerance":1e-9})

def solve_dispatch(load_kw:np.ndarray,pv_kw:np.ndarray,price:np.ndarray,*,soc_initial:float,soc_terminal:float|None)->DispatchResult:
    load_kw=np.asarray(load_kw,dtype=float); pv_kw=np.asarray(pv_kw,dtype=float); price=np.asarray(price,dtype=float)
    if not (load_kw.shape==pv_kw.shape==price.shape): raise ValueError("load/pv/price shape mismatch")
    t=len(price)
    if t==0 or not np.isfinite(np.r_[load_kw,pv_kw,price]).all(): raise ValueError("invalid input")
    if (load_kw<0).any() or (pv_kw<0).any() or (price<=0).any(): raise ValueError("physical bounds violated")
    if not SOC_MIN<=soc_initial<=SOC_MAX: raise ValueError("initial SOC invalid")
    if soc_terminal is not None and not SOC_MIN<=soc_terminal<=SOC_MAX: raise ValueError("terminal SOC invalid")
    g,ch,dis,soc,spill=_slices(t); n=5*t
    a_eq=np.zeros((2*t+(soc_terminal is not None),n)); b_eq=np.zeros(a_eq.shape[0])
    for i in range(t):
        a_eq[i,g.start+i]=1; a_eq[i,ch.start+i]=-1; a_eq[i,dis.start+i]=1; a_eq[i,spill.start+i]=-1
        b_eq[i]=(load_kw[i]-pv_kw[i])*DT_HOURS
        row=t+i; a_eq[row,soc.start+i]=1; a_eq[row,ch.start+i]=-ETA_CH; a_eq[row,dis.start+i]=1/ETA_DIS
        if i==0: b_eq[row]=soc_initial
        else: a_eq[row,soc.start+i-1]=-1
    if soc_terminal is not None: a_eq[-1,soc.stop-1]=1; b_eq[-1]=soc_terminal
    bounds=([(0,None)]*t+[(0,ENERGY_LIMIT)]*t+[(0,ENERGY_LIMIT)]*t+
            [(SOC_MIN,SOC_MAX)]*t+[(0,float(x)*DT_HOURS) for x in pv_kw])
    primary_c=np.zeros(n); primary_c[g]=price
    started=perf_counter(); primary=_solve(primary_c,a_eq,b_eq,bounds)
    if not primary.success: raise RuntimeError(f"primary LP failed: {primary.message}")
    primary_value=float(primary.fun); objective_tol=max(1e-5,1e-10*max(1.0,abs(primary_value)))
    throughput_c=np.zeros(n); throughput_c[ch]=1; throughput_c[dis]=1
    secondary=_solve(throughput_c,a_eq,b_eq,bounds,primary_c.reshape(1,-1),np.array([primary_value+objective_tol]))
    if not secondary.success: raise RuntimeError(f"throughput LP failed: {secondary.message}")
    throughput_value=float(secondary.fun); throughput_tol=max(1e-5,1e-10*max(1.0,abs(throughput_value)))
    spill_c=np.zeros(n); spill_c[spill]=1
    tertiary=_solve(spill_c,a_eq,b_eq,bounds,np.vstack([primary_c,throughput_c]),
                    np.array([primary_value+objective_tol,throughput_value+throughput_tol]))
    if not tertiary.success: raise RuntimeError(f"curtailment LP failed: {tertiary.message}")
    x=tertiary.x
    return DispatchResult(x[g].copy(),x[ch].copy(),x[dis].copy(),x[soc].copy(),x[spill].copy(),
                          float(np.dot(price,x[g])),primary_value,float(x[spill].sum()),
                          float(x[ch].sum()+x[dis].sum()),int(tertiary.status),str(tertiary.message),
                          int(getattr(tertiary,"nit",-1)),perf_counter()-started,
                          np.asarray(tertiary.eqlin.marginals,dtype=float))


@dataclass
class AdjustmentDispatchResult:
    dispatch:DispatchResult
    increase:np.ndarray
    settlement_objective:float
    variable_objective:float
    adjustment_mask:np.ndarray

def solve_adjustment_dispatch(load_kw:np.ndarray,pv_kw:np.ndarray,price:np.ndarray,baseline_grid:np.ndarray,
                              adjustment_mask:np.ndarray,*,soc_initial:float,soc_terminal:float|None)->AdjustmentDispatchResult:
    """Jointly optimize adjusted purchases and storage under the replacement settlement."""
    load_kw=np.asarray(load_kw,dtype=float); pv_kw=np.asarray(pv_kw,dtype=float); price=np.asarray(price,dtype=float)
    baseline=np.asarray(baseline_grid,dtype=float); mask=np.asarray(adjustment_mask,dtype=bool)
    if not (load_kw.shape==pv_kw.shape==price.shape==baseline.shape==mask.shape): raise ValueError("adjustment shape mismatch")
    t=len(price); g=slice(0,t); ch=slice(t,2*t); dis=slice(2*t,3*t); soc=slice(3*t,4*t); spill=slice(4*t,5*t); inc=slice(5*t,6*t); n=6*t
    a_eq=np.zeros((2*t+(soc_terminal is not None),n)); b_eq=np.zeros(a_eq.shape[0])
    for i in range(t):
        a_eq[i,g.start+i]=1; a_eq[i,ch.start+i]=-1; a_eq[i,dis.start+i]=1; a_eq[i,spill.start+i]=-1
        b_eq[i]=(load_kw[i]-pv_kw[i])*DT_HOURS
        row=t+i; a_eq[row,soc.start+i]=1; a_eq[row,ch.start+i]=-ETA_CH; a_eq[row,dis.start+i]=1/ETA_DIS
        if i==0: b_eq[row]=soc_initial
        else: a_eq[row,soc.start+i-1]=-1
    if soc_terminal is not None: a_eq[-1,soc.stop-1]=1; b_eq[-1]=soc_terminal
    bounds=([(0,None)]*t+[(0,ENERGY_LIMIT)]*t+[(0,ENERGY_LIMIT)]*t+[(SOC_MIN,SOC_MAX)]*t+
            [(0,float(x)*DT_HOURS) for x in pv_kw]+[(0,None) if flag else (0,0) for flag in mask])
    rows=[]; rhs=[]
    for i,flag in enumerate(mask):
        if flag:
            row=np.zeros(n); row[g.start+i]=1; row[inc.start+i]=-1
            rows.append(row); rhs.append(baseline[i])
    adjustment_a=np.asarray(rows) if rows else None; adjustment_b=np.asarray(rhs) if rhs else None
    primary_c=np.zeros(n)
    primary_c[g]=np.where(mask,0.5*price,price)
    primary_c[inc]=np.where(mask,price,0.0)
    constant=float(np.sum(0.5*price[mask]*baseline[mask]))
    started=perf_counter(); primary=_solve(primary_c,a_eq,b_eq,bounds,adjustment_a,adjustment_b)
    if not primary.success: raise RuntimeError(f"adjustment primary LP failed: {primary.message}")
    primary_value=float(primary.fun); tol=max(1e-5,1e-10*max(1.0,abs(primary_value)))
    throughput_c=np.zeros(n); throughput_c[ch]=1; throughput_c[dis]=1
    a2=np.vstack([adjustment_a,primary_c]) if adjustment_a is not None else primary_c.reshape(1,-1)
    b2=np.r_[adjustment_b,primary_value+tol] if adjustment_b is not None else np.array([primary_value+tol])
    secondary=_solve(throughput_c,a_eq,b_eq,bounds,a2,b2)
    if not secondary.success: raise RuntimeError(f"adjustment throughput LP failed: {secondary.message}")
    throughput_value=float(secondary.fun); ttol=max(1e-5,1e-10*max(1.0,abs(throughput_value)))
    spill_c=np.zeros(n); spill_c[spill]=1
    a3=np.vstack([a2,throughput_c]); b3=np.r_[b2,throughput_value+ttol]
    tertiary=_solve(spill_c,a_eq,b_eq,bounds,a3,b3)
    if not tertiary.success: raise RuntimeError(f"adjustment curtailment LP failed: {tertiary.message}")
    x=tertiary.x; settlement=float(np.dot(primary_c,x)+constant)
    dispatch=DispatchResult(x[g].copy(),x[ch].copy(),x[dis].copy(),x[soc].copy(),x[spill].copy(),
                            settlement,float(primary.fun+constant),float(x[spill].sum()),
                            float(x[ch].sum()+x[dis].sum()),int(tertiary.status),str(tertiary.message),
                            int(getattr(tertiary,"nit",-1)),perf_counter()-started,
                            np.asarray(tertiary.eqlin.marginals,dtype=float))
    return AdjustmentDispatchResult(dispatch,x[inc].copy(),settlement,float(np.dot(primary_c,x)),mask.copy())
