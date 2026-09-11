#!/usr/bin/env bash
set -uo pipefail
ROOT="/f/AcademicHub/000资料相关/数模/26国赛"
LOG="$ROOT/MathModel/tools/texlive_install.log"
for i in $(seq 1 60); do
  if grep -q "TEXLIVE_INSTALL_DONE" "$LOG" 2>/dev/null; then echo "==> 安装完成"; break; fi
  sleep 30
done
tail -3 "$LOG"
FMT=$(find /f/AcademicHub/texlive/2026 -name "xelatex.fmt" 2>/dev/null | head -1)
echo "fmt: ${FMT:-none}"
bash "$ROOT/MathModel/tools/build_paper.sh"
echo "WATCH2_DONE"
