from __future__ import annotations
import json
from pathlib import Path
from .io_data import read_attachment4
from .q2 import run_q2
from .q3 import run_q3

ROOT=Path(__file__).resolve().parents[1]

def run_q4()->dict:
    prices=read_attachment4().price
    q42_dir=ROOT/"outputs"/"q4-2"; q43_dir=ROOT/"outputs"/"q4-3"
    q42=run_q2(price_matrix=prices,output_dir=q42_dir,template_name="result4-2.xlsx")["metrics"]
    q43=run_q3(price_matrix=prices,output_dir=q43_dir,template_name="result4-3.xlsx",
               downscale="linear",calibrate=True)["metrics"]
    q2_fixed=json.loads((ROOT/"outputs"/"q2"/"metrics.json").read_text(encoding="utf-8"))
    q3_fixed=json.loads((ROOT/"outputs"/"q3"/"metrics.json").read_text(encoding="utf-8"))
    comparison={
        "q4_2_total_cost_yuan":q42["total_cost_yuan"],
        "q4_3_total_cost_yuan":q43["total_cost_yuan"],
        "rolling_value_under_dynamic_price_yuan":q42["total_cost_yuan"]-q43["total_cost_yuan"],
        "rolling_value_under_dynamic_price_percent":100*(q42["total_cost_yuan"]-q43["total_cost_yuan"])/q42["total_cost_yuan"],
        "q2_fixed_price_total_yuan":q2_fixed["total_cost_yuan"],
        "q3_fixed_price_total_yuan":q3_fixed["total_cost_yuan"],
        "rolling_value_under_fixed_price_yuan":q2_fixed["total_cost_yuan"]-q3_fixed["total_cost_yuan"],
        "q4_2_emergency_energy_kwh":q42["emergency_energy_kwh"],
        "q4_3_emergency_energy_kwh":q43["emergency_energy_kwh"],
        "q4_2_passed":bool(q42["passed"] and q42.get("xlsx_passed",False)),
        "q4_3_passed":bool(q43["passed"] and q43.get("xlsx_passed",False)),
    }
    comparison["passed"]=comparison["q4_2_passed"] and comparison["q4_3_passed"]
    out=ROOT/"outputs"/"q4_comparison.json"
    out.write_text(json.dumps(comparison,ensure_ascii=False,indent=2),encoding="utf-8")
    return {"q4_2":q42,"q4_3":q43,"comparison":comparison}

if __name__=="__main__": print(json.dumps(run_q4(),ensure_ascii=False,indent=2))
