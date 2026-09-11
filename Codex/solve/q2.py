from __future__ import annotations
import csv
import json
import platform
import sys
from collections import Counter
from pathlib import Path
import numpy as np
import scipy

from .export import export_result2
from .forecast import OnlinePVForecaster
from .io_data import DEFAULT_DATA_ROOT,DT_HOURS,read_attachment1,read_attachment2,template_path
from .lp_core import ETA_CH,ETA_DIS,SOC_MAX,SOC_MIN,solve_dispatch
from .settle import execute_with_realtime_storage_feedback

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"q2"

def _verify_day(record:dict)->dict:
    execution=record["execution"]; load=record["load_kw"]; pv=record["actual_pv_kw"]
    balance=execution.grid+pv*DT_HOURS+execution.discharge+execution.emergency-load*DT_HOURS-execution.charge-execution.curtail
    previous=np.r_[record["soc_initial"],execution.soc[:-1]]
    soc_residual=execution.soc-(previous+ETA_CH*execution.charge-execution.discharge/ETA_DIS)
    return {
        "max_balance_residual":float(np.max(np.abs(balance))),
        "max_soc_residual":float(np.max(np.abs(soc_residual))),
        "min_soc":float(execution.soc.min()),"max_soc":float(execution.soc.max()),
        "max_simultaneous":float(np.max(np.minimum(execution.charge,execution.discharge))),
    }

def run_q2(*,data_root:Path=DEFAULT_DATA_ROOT,max_days:int=365,price_matrix:np.ndarray|None=None,output_dir:Path|None=None,template_name:str="result2.xlsx",write_outputs:bool=True)->dict:
    day1=read_attachment1(data_root); annual=read_attachment2(data_root)
    if max_days<1 or max_days>365: raise ValueError("max_days must be 1..365")
    prices=np.tile(day1.price,(365,1)) if price_matrix is None else np.asarray(price_matrix,dtype=float)
    if prices.shape!=(365,144): raise ValueError("price matrix must have shape (365,144)")
    out_dir=OUTPUT if output_dir is None else Path(output_dir)
    selector=OnlinePVForecaster(prices[0])
    state=6000.0; records=[]; forecast_rows=[]; verify_rows=[]
    for d in range(max_days):
        decision=selector.predict()
        if decision.history_days_used!=d: raise RuntimeError("forecast causality counter mismatch")
        initial=state
        plan=solve_dispatch(annual.load_kw[d],decision.forecast_kw,prices[d],
                            soc_initial=initial,soc_terminal=initial)
        execution=execute_with_realtime_storage_feedback(plan,annual.load_kw[d],annual.pv_kw[d],soc_initial=initial)
        scores=selector.observe(decision,annual.pv_kw[d],price=prices[d])
        state=float(execution.soc[-1])
        plan_cost=float(np.dot(prices[d],plan.grid))
        emergency_cost=float(np.dot(5.0*prices[d],execution.emergency))
        record={"day_index":d,"date":annual.dates[d],"soc_initial":initial,"plan":plan,
                "execution":execution,"load_kw":annual.load_kw[d],"actual_pv_kw":annual.pv_kw[d],
                "forecast_kw":decision.forecast_kw,"plan_cost":plan_cost,
                "emergency_cost":emergency_cost,"total_cost":plan_cost+emergency_cost,
                "decision":decision}
        records.append(record); verify_rows.append(_verify_day(record))
        forecast_rows.append({
            "day_index":d,"date":annual.dates[d].isoformat(),"history_days_used":decision.history_days_used,
            "candidate":decision.name,"method":decision.method,"quantile":decision.quantile,
            "margin_kw":decision.margin_kw,"historical_score":decision.historical_score,
            "realized_candidate_score":scores[decision.name],
            "mae_kw":float(np.mean(np.abs(decision.forecast_kw-annual.pv_kw[d]))),
            "daily_energy_error_kwh":float(np.sum(decision.forecast_kw-annual.pv_kw[d])*DT_HOURS),
        })

    max_balance=max(r["max_balance_residual"] for r in verify_rows)
    max_soc=max(r["max_soc_residual"] for r in verify_rows)
    min_soc=min(r["min_soc"] for r in verify_rows); max_soc_value=max(r["max_soc"] for r in verify_rows)
    max_sim=max(r["max_simultaneous"] for r in verify_rows)
    continuity=max(abs(records[i]["soc_initial"]-records[i-1]["execution"].soc[-1]) for i in range(1,len(records))) if len(records)>1 else 0.0
    delivery=records[31:] if max_days==365 else []
    metrics={
        "days_simulated":max_days,"warmup_days":31 if max_days==365 else None,
        "delivery_days":len(delivery),"terminal_policy":"planned S_144 equals actual S_0 of the day",
        "max_balance_residual":max_balance,"max_soc_residual":max_soc,
        "max_day_boundary_soc_gap":continuity,"min_soc":min_soc,"max_soc":max_soc_value,
        "max_simultaneous_charge_discharge":max_sim,
        "information_set":("Attachment 1 price" if price_matrix is None else "Attachment 4 prices")+" + Attachment 2 prior/current observations; Attachment 3 unused",
        "price_source":"attachment1" if price_matrix is None else "attachment4",
        "forecast_selection_counts":dict(Counter(row["candidate"] for row in forecast_rows)),
    }
    if delivery:
        metrics.update({
            "plan_purchase_cost_yuan":float(sum(r["plan_cost"] for r in delivery)),
            "emergency_cost_yuan":float(sum(r["emergency_cost"] for r in delivery)),
            "total_cost_yuan":float(sum(r["total_cost"] for r in delivery)),
            "plan_purchase_energy_kwh":float(sum(r["plan"].grid.sum() for r in delivery)),
            "emergency_energy_kwh":float(sum(r["execution"].emergency.sum() for r in delivery)),
            "curtailment_energy_kwh":float(sum(r["execution"].curtail.sum() for r in delivery)),
            "forecast_mae_kw":float(np.mean([row["mae_kw"] for row in forecast_rows[31:]])),
            "days_with_emergency":int(sum(r["execution"].emergency.sum()>1e-7 for r in delivery)),
            "ending_soc_kwh":float(delivery[-1]["execution"].soc[-1]),
        })
    metrics["passed"]=bool(max_balance<1e-7 and max_soc<1e-7 and continuity<1e-9 and
                           min_soc>=SOC_MIN-1e-7 and max_soc_value<=SOC_MAX+1e-7 and max_sim<1e-7)

    if write_outputs:
        out_dir.mkdir(parents=True,exist_ok=True)
        (out_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
        with (out_dir/"forecast_log.csv").open("w",newline="",encoding="utf-8-sig") as f:
            writer=csv.DictWriter(f,fieldnames=list(forecast_rows[0])); writer.writeheader(); writer.writerows(forecast_rows)
        if delivery:
            with (out_dir/"solution.csv").open("w",newline="",encoding="utf-8-sig") as f:
                fields=["date","slot","load_kw","actual_pv_kw","forecast_pv_kw","price",
                        "grid_plan_kwh","charge_actual_kwh","discharge_actual_kwh","soc_actual_kwh",
                        "curtail_actual_kwh","emergency_kwh"]
                writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
                for r in delivery:
                    for t in range(144):
                        writer.writerow({"date":r["date"].isoformat(),"slot":t+1,"load_kw":r["load_kw"][t],
                            "actual_pv_kw":r["actual_pv_kw"][t],"forecast_pv_kw":r["forecast_kw"][t],
                            "price":prices[r["day_index"],t],"grid_plan_kwh":r["plan"].grid[t],
                            "charge_actual_kwh":r["execution"].charge[t],"discharge_actual_kwh":r["execution"].discharge[t],
                            "soc_actual_kwh":r["execution"].soc[t],"curtail_actual_kwh":r["execution"].curtail[t],
                            "emergency_kwh":r["execution"].emergency[t]})
            daily_fields=["date","soc_initial","soc_terminal","plan_cost","emergency_cost","total_cost",
                          "plan_energy","emergency_energy","curtailment_energy"]
            with (out_dir/"daily_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
                writer=csv.DictWriter(f,fieldnames=daily_fields); writer.writeheader()
                for r in delivery:
                    writer.writerow({"date":r["date"].isoformat(),"soc_initial":r["soc_initial"],
                        "soc_terminal":r["execution"].soc[-1],"plan_cost":r["plan_cost"],
                        "emergency_cost":r["emergency_cost"],"total_cost":r["total_cost"],
                        "plan_energy":r["plan"].grid.sum(),"emergency_energy":r["execution"].emergency.sum(),
                        "curtailment_energy":r["execution"].curtail.sum()})
            export_check=export_result2(template_path(template_name,data_root),out_dir/template_name,delivery)
            (out_dir/"xlsx_verification.json").write_text(json.dumps(export_check,ensure_ascii=False,indent=2),encoding="utf-8")
            metrics["xlsx_passed"]=export_check["passed"]
            (out_dir/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
        environment={"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,
                     "scipy":scipy.__version__,"algorithm":"scipy.optimize.linprog(method=highs), lexicographic 3-pass LP"}
        (out_dir/"environment.json").write_text(json.dumps(environment,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"metrics":metrics,"records":records,"forecast_rows":forecast_rows}

if __name__=="__main__":
    result=run_q2()
    print(json.dumps(result["metrics"],ensure_ascii=False,indent=2))
