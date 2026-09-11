#!/usr/bin/env bash
# 等待 TeX Live 安装完成，然后自动编译论文。
set -uo pipefail

ROOT="/f/AcademicHub/000资料相关/数模/26国赛"
LOG="$ROOT/MathModel/tools/texlive_install.log"

echo "==> 等待 TeX Live 安装完成（每 60 s 检查一次）"
for i in $(seq 1 180); do
  if grep -q "TEXLIVE_INSTALL_DONE" "$LOG" 2>/dev/null; then
    echo "==> TeX Live 安装完成（等待 $i 分钟）"
    break
  fi
  if [ -x "/f/AcademicHub/texlive/2026/bin/windows/xelatex.exe" ] && ! pgrep -f "install-tl" >/dev/null 2>&1; then
    echo "==> 安装进程已结束，xelatex 存在（等待 $i 分钟）"
    break
  fi
  sleep 60
done

ls -la /f/AcademicHub/texlive/2026/bin/windows/xelatex.exe || { echo "[FAIL] 未找到 xelatex"; exit 1; }

echo "==> 开始编译"
bash "$ROOT/MathModel/tools/build_paper.sh"
echo "WAIT_AND_BUILD_DONE"
