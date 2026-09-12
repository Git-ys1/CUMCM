from __future__ import annotations
import hashlib,json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUTS=ROOT/"outputs"
VARIANTS={
    "q1":{"path":"q1","parameters":{"question":1}},
    "q2_fixed_online":{"path":"q2","parameters":{"question":2,"price":"attachment1","forecast":"strictly_online"}},
    "q3_main_linear_calibrated":{"path":"q3","parameters":{"question":3,"downscale":"linear","calibration":True,"price":"attachment1"}},
    "q3_raw_step":{"path":"q3/variants/raw_step","parameters":{"question":3,"downscale":"step","calibration":False,"price":"attachment1"}},
    "q3_calibrated_step":{"path":"q3/variants/calibrated_step","parameters":{"question":3,"downscale":"step","calibration":True,"price":"attachment1"}},
    "q4_2_dynamic":{"path":"q4-2","parameters":{"question":"4-2","price":"attachment4","forecast":"strictly_online"}},
    "q4_3_dynamic":{"path":"q4-3","parameters":{"question":"4-3","price":"attachment4","downscale":"linear","calibration":True}},
}

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def build()->dict:
    result={"generated_at":datetime.now().astimezone().isoformat(),"authority_root":str(ROOT),
            "main":{"q1":"q1","q2":"q2_fixed_online","q3":"q3_main_linear_calibrated",
                    "q4_2":"q4_2_dynamic","q4_3":"q4_3_dynamic"},"variants":{},"source_files":{}}
    for name,spec in VARIANTS.items():
        folder=OUTPUTS/spec["path"]; files={}
        for path in sorted(folder.glob("*")):
            if path.is_file():
                files[path.name]={"bytes":path.stat().st_size,"sha256":digest(path)}
        metrics_path=folder/"metrics.json"
        metrics=json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
        result["variants"][name]={"relative_path":spec["path"],"parameters":spec["parameters"],
                                  "metrics":metrics,"files":files}
    for path in sorted((ROOT/"solve").glob("*.py")):
        result["source_files"][str(path.relative_to(ROOT))]={"bytes":path.stat().st_size,"sha256":digest(path)}
    for pattern in ("reports/*.md","tests/*.py","README.md","requirements.txt","run_all.ps1"):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file(): result["source_files"][str(path.relative_to(ROOT))]={"bytes":path.stat().st_size,"sha256":digest(path)}
    result["figures"]={}
    for path in sorted((ROOT/"figures").rglob("*.pdf")):
        result["figures"][str(path.relative_to(ROOT))]={"bytes":path.stat().st_size,"sha256":digest(path)}
    result["governance_outputs"]={}
    for name in ("verification_summary.json","q4_comparison.json"):
        path=OUTPUTS/name
        if path.exists(): result["governance_outputs"][name]={"bytes":path.stat().st_size,"sha256":digest(path)}
    (OUTPUTS/"MANIFEST.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

if __name__=="__main__":
    manifest=build(); print(json.dumps({"variants":list(manifest["variants"]),
        "source_files":len(manifest["source_files"]),"manifest":str(OUTPUTS/"MANIFEST.json")},ensure_ascii=False,indent=2))
