"""把求解源码复制到 MathModel/paper/code/，供 LaTeX 附录 \\lstinputlisting 引用。

同时生成 numbers.tex（论文数值宏），保证论文表格与程序输出一致。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVE = ROOT / "solve"
TESTS = ROOT / "tests"
TARGET = ROOT / "paper" / "code"

FILES = [
    ("solve/params.py", "params.py"),
    ("solve/io_data.py", "io_data.py"),
    ("solve/lp_core.py", "lp_core.py"),
    ("solve/forecast.py", "forecast.py"),
    ("solve/load_forecast.py", "load_forecast.py"),
    ("solve/price_forecast.py", "price_forecast.py"),
    ("solve/settle.py", "settle.py"),
    ("solve/q1.py", "q1.py"),
    ("solve/q2.py", "q2.py"),
    ("solve/q3.py", "q3.py"),
    ("solve/q4.py", "q4.py"),
    ("solve/export.py", "export.py"),
    ("solve/ablation.py", "ablation.py"),
    ("solve/official_forecast.py", "official_forecast.py"),
    ("solve/paper_tables.py", "paper_tables.py"),
    ("solve/report.py", "report.py"),
    ("solve/validate_q2.py", "validate_q2.py"),
    ("solve/validate_all.py", "validate_all.py"),
    ("solve/build_manifest.py", "build_manifest.py"),
    ("solve/plot_style.py", "plot_style.py"),
    ("solve/fig_data.py", "fig_data.py"),
    ("solve/fig_q1.py", "fig_q1.py"),
    ("solve/fig_results.py", "fig_results.py"),
    ("solve/fig_route.py", "fig_route.py"),
    ("solve/plot_results.py", "plot_results.py"),
    ("tests/mutate.py", "mutate.py"),
    ("tests/test_causality.py", "test_causality.py"),
    ("tests/test_q2_q3.py", "test_q2_q3.py"),
    ("tests/test_paper_consistency.py", "test_paper_consistency.py"),
    ("tests/test_settlement.py", "test_settlement.py"),
    ("tests/test_regression.py", "test_regression.py"),
]


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    missing = []
    for source, name in FILES:
        path = ROOT / source
        if not path.exists():
            missing.append(source)
            continue
        shutil.copy2(path, TARGET / name)
        print(f"[sync] {source} -> paper/code/{name}")
    if missing:
        print("[sync][missing]", missing)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
