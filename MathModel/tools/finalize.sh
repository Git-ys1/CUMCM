#!/usr/bin/env bash
# 把编译好的论文与官方结果文件汇总到交付位置。
#   论文：WorkBuddy/01_论文写作/论文V3.pdf （用户指定的论文位置）
#   结果：MathModel/submit/ 与根目录 提交文件/
set -uo pipefail

ROOT="/f/AcademicHub/000资料相关/数模/26国赛"
MM="$ROOT/MathModel"
PAPER="$MM/paper"
DEST="$ROOT/WorkBuddy/01_论文写作"
SUBMIT="$ROOT/提交文件"

mkdir -p "$SUBMIT"

if [ -f "$PAPER/document.pdf" ]; then
  cp "$PAPER/document.pdf" "$DEST/论文V3.pdf"
  cp "$PAPER/document.pdf" "$SUBMIT/论文V3.pdf"
  echo "[finalize] 论文 → $DEST/论文V3.pdf"
else
  echo "[finalize][FAIL] 未找到 $PAPER/document.pdf"
fi

for f in result1.xlsx result2.xlsx result3.xlsx result4-2.xlsx result4-3.xlsx; do
  if [ -f "$MM/submit/$f" ]; then
    cp "$MM/submit/$f" "$SUBMIT/$f"
    echo "[finalize] $f → $SUBMIT/$f"
  fi
done

cp "$MM/reports/MODEL_AUDIT_V2.md" "$SUBMIT/模型审计报告_MODEL_AUDIT_V2.md" 2>/dev/null && \
  echo "[finalize] 审计报告 → $SUBMIT/"

ls -la "$SUBMIT"
echo "FINALIZE_DONE"
