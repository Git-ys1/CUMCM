#!/usr/bin/env bash
# 安装 TeX Live（含 XeLaTeX / latexmk / bibtex）到 F:\AcademicHub\texlive，使用清华 TUNA 镜像。
# 不写系统 PATH，全部通过绝对路径调用；如失败请查看本脚本的 stderr。
set -euo pipefail

MIRROR="https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/tlnet"
ROOT="/f/AcademicHub/texlive"
TEXDIR="F:/AcademicHub/texlive/2026"
DL="$ROOT/_installer"

mkdir -p "$DL"
cd "$DL"

echo "==> 下载 install-tl.zip (TUNA)"
curl -fL --retry 3 --retry-delay 5 -o install-tl.zip "$MIRROR/install-tl.zip"
ls -la install-tl.zip

echo "==> 解压"
rm -rf install-tl-*
unzip -q install-tl.zip

cat > tl.profile <<EOF
selected_scheme scheme-full
TEXDIR $TEXDIR
TEXMFLOCAL F:/AcademicHub/texlive/texmf-local
TEXMFSYSCONFIG F:/AcademicHub/texlive/2026/texmf-config
TEXMFSYSVAR F:/AcademicHub/texlive/2026/texmf-var
TEXMFVAR F:/AcademicHub/texlive/2026/texmf-var
TEXMFHOME F:/AcademicHub/texlive/texmf-home
instopt_adjustpath 0
instopt_adjustrepo 1
instopt_letter 0
instopt_portable 0
instopt_write18_restricted 1
tlpdbopt_autobackup 0
tlpdbopt_install_docfiles 0
tlpdbopt_install_srcfiles 0
EOF

echo "==> 安装 (scheme-full, 不装 doc/src)"
./install-tl-20260910/install-tl-windows.bat -no-gui -profile tl.profile -repository "$MIRROR" || \
  ./install-tl-20260910/install-tl.bat -no-gui -profile tl.profile -repository "$MIRROR"

echo "==> 复检"
"$ROOT/2026/bin/windows/xelatex.exe" --version | head -2
"$ROOT/2026/bin/windows/latexmk.exe" --version | head -2
"$ROOT/2026/bin/windows/bibtex.exe" --version | head -2
echo "TEXLIVE_INSTALL_DONE"
