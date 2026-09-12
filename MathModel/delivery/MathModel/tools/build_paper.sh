#!/usr/bin/env bash
# 编译论文：同步代码 -> 生成数值宏 -> 检查宏 -> xelatex/bibtex 多轮 -> 输出 PDF。
set -uo pipefail

ROOT="/f/AcademicHub/000资料相关/数模/26国赛"
MM="$ROOT/MathModel"
TEXBIN="/f/AcademicHub/texlive/2026/bin/windows"
PAPER="$MM/paper"

PY="$ROOT/AutoMM/.venv/Scripts/python.exe"

echo "==> 1/5 同步源码到 paper/code"
"$PY" "$MM/tools/sync_code.py" || exit 1

echo "==> 2/5 生成数值宏 numbers.tex"
cd "$ROOT" && "$PY" -m MathModel.solve.report || exit 1

echo "==> 3/5 检查宏定义完整性"
"$PY" "$MM/tools/check_macros.py" || echo "[warn] 宏检查未通过，仍继续编译"

echo "==> 4/5 编译"
cd "$PAPER" || exit 1
export PATH="$TEXBIN:$PATH"
rm -f document.aux document.bbl document.blg document.log document.out document.toc
xelatex -interaction=nonstopmode -halt-on-error document.tex > /dev/null 2>&1
bibtex document
xelatex -interaction=nonstopmode document.tex > /dev/null 2>&1
xelatex -interaction=nonstopmode document.tex > /tmp/paper_build.log 2>&1

echo "==> 5/5 结果"
if [ -f document.pdf ]; then
  ls -la document.pdf
  grep -c "^!" /tmp/paper_build.log 2>/dev/null | sed 's/^/  错误行数: /'
  grep "^!" /tmp/paper_build.log 2>/dev/null | head -20
else
  echo "  [FAIL] 未生成 PDF"
  grep "^!" /tmp/paper_build.log 2>/dev/null | head -30
  tail -40 /tmp/paper_build.log
fi
