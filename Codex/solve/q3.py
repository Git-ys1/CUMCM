from __future__ import annotations
import csv,json,platform,sys
from pathlib import Path
import numpy as np
import scipy
from .export import export_result3
from .io_data import DEFAULT_DATA_ROOT,DT_HOURS,hourly_to_ten_min,read_attachment1,read_attachment2,read_attachment3,template_path
from .lp_core import DispatchResult,ETA_CH,ETA_DIS,SOC_MAX,SOC_MIN,solve_adjustment_dispatch,solve_dispatch
from .official_forecast import OnlineForecastBiasCalibrator
from .settle import ExecutionResult,execute_with_realtime_storage_feedback

ROOT=Path(__file__).resolve().parents[1]; OUTPUT=ROOT/"outputs"/"q3"; BLOCK=36

def _horizon(data:np.ndarray,day:int,start_slot:int,fallback:np.ndarray)->np.ndarray:
    flat=data.reshape(-1); start=day*144+start_slot; values=flat[start:min(start+144,len(flat))]
    if len(values)<144:
        pieces=[values]; remaining=144-len(values)
        while remaining>0:
            take=min(remaining,len(fallback)); pieces.append(fallback[:take]); remaining-=take
        values=np.concatenate(pieces)
    return np.asarray(values,dtype=float)

def _slice_dispatch(result:DispatchResult,start:int,stop:int)->DispatchResult:
    return DispatchResult(result.grid[start:stop].copy(),result.charge[start:stop].copy(),
        result.discharge[start:stop].copy(),result.soc[start:stop].copy(),result.curtail[start:stop].copy(),
        result.objective,result.primary_objective,float(result.curtail[start:stop].sum()),
        float(result.charge[start:stop].sum()+result.discharge[start:stop].sum()),result.status,
        result.message,result.nit,result.solve_seconds,result.equality_marginals.copy())

def _reversal_count(revisions:np.ndarray)->int:
    count=0
    for slot in range(144):
        values=revisions[:,slot]; values=values[np.isfinite(values)]
        signs=np.sign(np.diff(values)); signs=signs[np.abs(signs)>0]
        if len(signs)>1 and np.any(signs[1:]*signs[:-1]<0): count+=1
    return count

def run_q3(*,data_root:Path=DEFAULT_DATA_ROOT,max_days:int=365,downscale:str="linear",calibrate:bool=True,price_matrix:np.ndarray|None=None,output_dir:Path|None=None,template_name:str="result3.xlsx",write_outputs:bool=True)->dict:
    typical=read_attachment1(data_root); annual=read_attachment2(data_root); forecasts=read_attachment3(data_root)
    if annual.dates!=forecasts.dates: raise ValueError("attachment2/3 dates do not align")
    if not 1<=max_days<=365: raise ValueError("max_days must be 1..365")
    prices=np.tile(typical.price,(365,1)) if price_matrix is None else np.asarray(price_matrix,dtype=float)
    if prices.shape!=(365,144): raise ValueError("price matrix must have shape (365,144)")
    out_dir=OUTPUT if output_dir is None else Path(output_dir)
    state=6000.0; records=[]; verify=[]; total_reversals=0
    calibrator=OnlineForecastBiasCalibrator()
    for d in range(max_days):
        initial=state; raw_base=hourly_to_ten_min(forecasts.hourly_kw[d,0],downscale)
        calibration0=calibrator.calibrate(0,raw_base); base_pv=calibration0.forecast_kw if calibrate else raw_base
        baseline=solve_dispatch(annual.load_kw[d],base_pv,prices[d],soc_initial=initial,soc_terminal=initial)
        adjusted=np.zeros(144); charge=np.zeros(144); discharge=np.zeros(144); soc=np.zeros(144)
        curtail=np.zeros(144); emergency=np.zeros(144); revisions=np.full((4,144),np.nan)
        revisions[0]=baseline.grid; block_forecast_mae=[]; node_state=initial
        calibration_margins=[]; calibration_quantiles=[]
        for node_index,node in enumerate((0,36,72,108)):
            block_stop=node+BLOCK
            if node==0:
                calibration=calibration0
                horizon_plan=baseline; block_plan=_slice_dispatch(horizon_plan,node,block_stop)
                block_forecast=base_pv[node:block_stop]
            else:
                raw_horizon=hourly_to_ten_min(forecasts.hourly_kw[d,node_index],downscale)
                calibration=calibrator.calibrate(node_index,raw_horizon)
                forecast_horizon=calibration.forecast_kw if calibrate else raw_horizon
                load_horizon=_horizon(annual.load_kw,d,node,typical.load_kw)
                price_horizon=_horizon(prices,d,node,typical.price)
                baseline_horizon=np.r_[baseline.grid[node:],np.zeros(node)]
                mask=np.r_[np.ones(144-node,dtype=bool),np.zeros(node,dtype=bool)]
                rolling=solve_adjustment_dispatch(load_horizon,forecast_horizon,price_horizon,baseline_horizon,mask,
                                                   soc_initial=node_state,soc_terminal=node_state)
                horizon_plan=rolling.dispatch; block_plan=_slice_dispatch(horizon_plan,0,BLOCK)
                revisions[node_index,node:]=horizon_plan.grid[:144-node]
                block_forecast=forecast_horizon[:BLOCK]
            execution=execute_with_realtime_storage_feedback(block_plan,annual.load_kw[d,node:block_stop],
                                                               annual.pv_kw[d,node:block_stop],soc_initial=node_state)
            adjusted[node:block_stop]=execution.grid; charge[node:block_stop]=execution.charge
            discharge[node:block_stop]=execution.discharge; soc[node:block_stop]=execution.soc
            curtail[node:block_stop]=execution.curtail; emergency[node:block_stop]=execution.emergency
            calibrator.observe(calibration,annual.pv_kw[d,node:block_stop],prices[d,node:block_stop])
            calibration_margins.append(calibration.margin_kw if calibrate else 0.0); calibration_quantiles.append(calibration.quantile if calibrate else None)
            node_state=float(execution.soc[-1])
            block_forecast_mae.append(float(np.mean(np.abs(block_forecast-annual.pv_kw[d,node:block_stop]))))
        state=node_state; actual=ExecutionResult(adjusted.copy(),charge,discharge,soc,curtail,emergency)
        gp=baseline.grid; ga=adjusted; increase=np.maximum(ga-gp,0); decrease=np.maximum(gp-ga,0)
        settlement=float(np.dot(prices[d],0.5*gp+0.5*ga+increase))
        direct=float(np.dot(prices[d],np.minimum(gp,ga)+0.5*decrease+1.5*increase))
        additive=float(np.dot(prices[d],gp+0.5*decrease+1.5*increase))
        emergency_cost=float(np.dot(5*prices[d],emergency)); reversals=_reversal_count(revisions)
        total_reversals+=reversals
        record={"day_index":d,"date":annual.dates[d],"soc_initial":initial,"baseline_plan":baseline,
                "adjusted_grid":adjusted,"execution":actual,"load_kw":annual.load_kw[d],
                "actual_pv_kw":annual.pv_kw[d],"revisions":revisions,
                "baseline_cost":float(np.dot(prices[d],gp)),"settlement_cost":settlement,
                "emergency_cost":emergency_cost,"total_cost":settlement+emergency_cost,
                "additive_cost":additive+emergency_cost,"linearization_gap":abs(settlement-direct),
                "up_energy":float(increase.sum()),"down_energy":float(decrease.sum()),
                "reversal_slots":reversals,"forecast_mae":float(np.mean(block_forecast_mae)),
                "calibration_margins":calibration_margins,"calibration_quantiles":calibration_quantiles}
        records.append(record)
        balance=ga+annual.pv_kw[d]*DT_HOURS+discharge+emergency-annual.load_kw[d]*DT_HOURS-charge-curtail
        previous=np.r_[initial,soc[:-1]]; soc_res=soc-(previous+ETA_CH*charge-discharge/ETA_DIS)
        verify.append((float(np.max(np.abs(balance))),float(np.max(np.abs(soc_res))),
                       float(soc.min()),float(soc.max()),float(np.max(np.minimum(charge,discharge)))))
    delivery=records[31:] if max_days==365 else []
    metrics={"days_simulated":max_days,"warmup_days":31 if max_days==365 else None,"delivery_days":len(delivery),
        "downscale_method":downscale,"calibration_enabled":calibrate,"price_source":"attachment1" if price_matrix is None else "attachment4","max_balance_residual":max(v[0] for v in verify),
        "max_soc_residual":max(v[1] for v in verify),"min_soc":min(v[2] for v in verify),
        "max_soc":max(v[3] for v in verify),"max_simultaneous_charge_discharge":max(v[4] for v in verify),
        "information_set":("Attachment 3 forecasts plus issue-specific calibration from earlier days" if calibrate else "raw Attachment 3 forecasts")+"; actual PV used only after block execution",
        "replacement_settlement":"0.5*Gp + 0.5*Ga + max(Ga-Gp,0)","cross_midnight":"24h optimize, execute current 6h block only; carry SOC only"}
    if delivery:
        metrics.update({"baseline_purchase_cost_yuan":float(sum(r["baseline_cost"] for r in delivery)),
            "adjusted_settlement_cost_yuan":float(sum(r["settlement_cost"] for r in delivery)),
            "emergency_cost_yuan":float(sum(r["emergency_cost"] for r in delivery)),
            "total_cost_yuan":float(sum(r["total_cost"] for r in delivery)),
            "additive_interpretation_total_yuan":float(sum(r["additive_cost"] for r in delivery)),
            "adjusted_purchase_energy_kwh":float(sum(r["adjusted_grid"].sum() for r in delivery)),
            "emergency_energy_kwh":float(sum(r["execution"].emergency.sum() for r in delivery)),
            "curtailment_energy_kwh":float(sum(r["execution"].curtail.sum() for r in delivery)),
            "up_adjustment_energy_kwh":float(sum(r["up_energy"] for r in delivery)),
            "down_adjustment_energy_kwh":float(sum(r["down_energy"] for r in delivery)),
            "direction_reversal_slots":int(sum(r["reversal_slots"] for r in delivery)),
            "max_linearization_gap":float(max(r["linearization_gap"] for r in delivery)),
            "executed_block_forecast_mae_kw":float(np.mean([r["forecast_mae"] for r in delivery])),
            "days_with_emergency":int(sum(r["execution"].emergency.sum()>1e-7 for r in delivery)),
            "ending_soc_kwh":float(delivery[-1]["execution"].soc[-1])})
    metrics["passed"]=bool(metrics["max_balance_residual"]<1e-7 and metrics["max_soc_residual"]<1e-7 and
        metrics["min_soc"]>=SOC_MIN-1e-7 and metrics["max_soc"]<=SOC_MAX+1e-7 and
        metrics["max_simultaneous_charge_discharge"]<1e-5 and (not delivery or metrics["max_linearization_gap"]<1e-7))
    if write_outputs:
        out_dir.mkdir(parents=True,exist_ok=True)
        (out_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
        if delivery:
            fields=["date","slot","load_kw","actual_pv_kw","price","baseline_grid_kwh","adjusted_grid_kwh",
                    "charge_actual_kwh","discharge_actual_kwh","soc_actual_kwh","curtail_actual_kwh","emergency_kwh",
                    "revision_0","revision_6","revision_12","revision_18"]
            with (out_dir/"solution.csv").open("w",newline="",encoding="utf-8-sig") as f:
                writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
                for r in delivery:
                    for t in range(144):
                        rev=r["revisions"][:,t]
                        writer.writerow({"date":r["date"].isoformat(),"slot":t+1,"load_kw":r["load_kw"][t],
                            "actual_pv_kw":r["actual_pv_kw"][t],"price":prices[r["day_index"],t],
                            "baseline_grid_kwh":r["baseline_plan"].grid[t],"adjusted_grid_kwh":r["adjusted_grid"][t],
                            "charge_actual_kwh":r["execution"].charge[t],"discharge_actual_kwh":r["execution"].discharge[t],
                            "soc_actual_kwh":r["execution"].soc[t],"curtail_actual_kwh":r["execution"].curtail[t],
                            "emergency_kwh":r["execution"].emergency[t],
                            "revision_0":rev[0],"revision_6":rev[1],"revision_12":rev[2],"revision_18":rev[3]})
            with (out_dir/"daily_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
                fields_d=["date","soc_initial","soc_terminal","baseline_cost","settlement_cost","emergency_cost",
                          "total_cost","additive_cost","up_energy","down_energy","reversal_slots","forecast_mae"]
                writer=csv.DictWriter(f,fieldnames=fields_d); writer.writeheader()
                for r in delivery:
                    writer.writerow({"date":r["date"].isoformat(),"soc_initial":r["soc_initial"],
                        "soc_terminal":r["execution"].soc[-1],**{k:r[k] for k in fields_d[3:]}})
            check=export_result3(template_path(template_name,data_root),out_dir/template_name,delivery)
            (out_dir/"xlsx_verification.json").write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding="utf-8")
            metrics["xlsx_passed"]=check["passed"]
            (out_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
        env={"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"scipy":scipy.__version__,
             "algorithm":"HiGHS LP, replacement settlement linearized by b>=Ga-Gp"}
        (out_dir/"environment.json").write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"metrics":metrics,"records":records}

if __name__=="__main__": print(json.dumps(run_q3()["metrics"],ensure_ascii=False,indent=2))
