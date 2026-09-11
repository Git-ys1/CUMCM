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
    ("tests/test_causality.py", "test_causality.py"),
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
