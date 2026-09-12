from __future__ import annotations
import csv,json,platform,sys
from pathlib import Path
import numpy as np
import scipy
import openpyxl
from .export import export_result1
from .io_data import DEFAULT_DATA_ROOT,DT_HOURS,read_attachment1,template_path
from .lp_core import ETA_CH,ETA_DIS,SOC_MAX,SOC_MIN,solve_dispatch

ROOT=Path(__file__).resolve().parents[1]; OUTPUT=ROOT/"outputs"/"q1"

def run_q1(*,data_root:Path=DEFAULT_DATA_ROOT)->dict:
    data=read_attachment1(data_root)
    result=solve_dispatch(data.load_kw,data.pv_kw,data.price,soc_initial=6000,soc_terminal=6000)
    balance=result.grid+data.pv_kw*DT_HOURS+result.discharge-data.load_kw*DT_HOURS-result.charge-result.curtail
    previous=np.r_[6000.0,result.soc[:-1]]
    soc_res=result.soc-(previous+ETA_CH*result.charge-result.discharge/ETA_DIS)
    no_storage_grid=np.maximum((data.load_kw-data.pv_kw)*DT_HOURS,0)
    metrics={"cost_yuan":result.objective,"primary_cost_yuan":result.primary_objective,
        "primary_cost_gap_yuan":result.objective-result.primary_objective,
        "grid_energy_kwh":float(result.grid.sum()),"charge_energy_kwh":float(result.charge.sum()),
        "discharge_energy_kwh":float(result.discharge.sum()),"curtailment_energy_kwh":float(result.curtail.sum()),
        "no_storage_cost_yuan":float(np.dot(data.price,no_storage_grid)),
        "savings_yuan":float(np.dot(data.price,no_storage_grid)-result.objective),
        "savings_percent":float(100*(np.dot(data.price,no_storage_grid)-result.objective)/np.dot(data.price,no_storage_grid)),
        "initial_soc_kwh":6000.0,"terminal_soc_kwh":float(result.soc[-1]),
        "min_soc_kwh":float(result.soc.min()),"max_soc_kwh":float(result.soc.max()),
        "max_balance_residual":float(np.max(np.abs(balance))),"max_soc_residual":float(np.max(np.abs(soc_res))),
        "max_simultaneous_charge_discharge":float(np.max(np.minimum(result.charge,result.discharge))),
        "solver_status":result.status,"solver_message":result.message,"iterations":result.nit,
        "solve_seconds":result.solve_seconds}
    metrics["passed"]=bool(metrics["max_balance_residual"]<1e-7 and metrics["max_soc_residual"]<1e-7 and
        abs(result.soc[-1]-6000)<1e-7 and metrics["min_soc_kwh"]>=SOC_MIN-1e-7 and
        metrics["max_soc_kwh"]<=SOC_MAX+1e-7 and metrics["max_simultaneous_charge_discharge"]<1e-5)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with (OUTPUT/"solution.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["slot","label","price","load_kw","pv_kw","grid_kwh","charge_kwh","discharge_kwh","soc_kwh","curtail_kwh"]
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for t in range(144):
            writer.writerow({"slot":t+1,"label":data.labels[t],"price":data.price[t],"load_kw":data.load_kw[t],
                "pv_kw":data.pv_kw[t],"grid_kwh":result.grid[t],"charge_kwh":result.charge[t],
                "discharge_kwh":result.discharge[t],"soc_kwh":result.soc[t],"curtail_kwh":result.curtail[t]})
    check=export_result1(template_path("result1.xlsx",data_root),OUTPUT/"result1.xlsx",result)
    metrics["xlsx_passed"]=check["passed"]
    (OUTPUT/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUTPUT/"xlsx_verification.json").write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding="utf-8")
    env={"python":sys.version,"platform":platform.platform(),"numpy":np.__version__,"scipy":scipy.__version__,
         "openpyxl":openpyxl.__version__,"algorithm":"HiGHS lexicographic LP"}
    (OUTPUT/"environment.json").write_text(json.dumps(env,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"metrics":metrics,"result":result}

if __name__=="__main__": print(json.dumps(run_q1()["metrics"],ensure_ascii=False,indent=2))
