param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$mathModelRoot = Join-Path $projectRoot 'MathModel'
$paperRoot = Join-Path $mathModelRoot 'paper'
$python = (Resolve-Path (Join-Path $projectRoot 'AutoMM\.venv\Scripts\python.exe')).Path
$texBin = (Resolve-Path 'F:\AcademicHub\texlive\2026\bin\windows').Path
$xelatex = Join-Path $texBin 'xelatex.exe'
$bibtex = Join-Path $texBin 'bibtex.exe'

& $python (Join-Path $mathModelRoot 'tools\sync_code.py')
if ($LASTEXITCODE -ne 0) { throw "附录代码同步失败：$LASTEXITCODE" }
Push-Location $projectRoot
& $python -m MathModel.solve.report
if ($LASTEXITCODE -ne 0) { throw "报告与数值宏生成失败：$LASTEXITCODE" }
& $python (Join-Path $mathModelRoot 'tools\check_macros.py')
if ($LASTEXITCODE -ne 0) { throw "论文数值宏检查失败：$LASTEXITCODE" }
Pop-Location

foreach ($name in @('document.aux', 'document.bbl', 'document.blg', 'document.log', 'document.out', 'document.toc')) {
    $path = Join-Path $paperRoot $name
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

Push-Location $paperRoot
& $xelatex -interaction=nonstopmode -halt-on-error document.tex
if ($LASTEXITCODE -ne 0) { throw "XeLaTeX 首轮编译失败：$LASTEXITCODE" }
& $bibtex document
if ($LASTEXITCODE -ne 0) { throw "BibTeX 编译失败：$LASTEXITCODE" }
& $xelatex -interaction=nonstopmode -halt-on-error document.tex
if ($LASTEXITCODE -ne 0) { throw "XeLaTeX 第二轮编译失败：$LASTEXITCODE" }
& $xelatex -interaction=nonstopmode -halt-on-error document.tex
if ($LASTEXITCODE -ne 0) { throw "XeLaTeX 第三轮编译失败：$LASTEXITCODE" }
Pop-Location

Get-Item -LiteralPath (Join-Path $paperRoot 'document.pdf') | Select-Object FullName, Length, LastWriteTime
