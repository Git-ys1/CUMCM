param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$mathModelRoot = (Resolve-Path (Join-Path $projectRoot 'MathModel')).Path
$stageRoot = Join-Path $mathModelRoot 'delivery'
$packageRoot = Join-Path $stageRoot 'MathModel'
$archivePath = Join-Path $mathModelRoot '支撑材料.zip'

$resolvedStage = [IO.Path]::GetFullPath($stageRoot)
$expectedStage = [IO.Path]::GetFullPath((Join-Path $mathModelRoot 'delivery'))
if ($resolvedStage -ne $expectedStage -or (Split-Path $resolvedStage -Leaf) -ne 'delivery') {
    throw "拒绝清理非预期目录：$resolvedStage"
}
if (Test-Path -LiteralPath $resolvedStage) {
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}

$directories = @(
    'results', 'solve', 'tests', 'tools', 'paper', 'paper\texfile',
    'paper\generated', 'paper\figures', 'paper\code', 'reports'
)
foreach ($relative in $directories) {
    New-Item -ItemType Directory -Path (Join-Path $packageRoot $relative) -Force | Out-Null
}

Copy-Item -LiteralPath (Join-Path $mathModelRoot 'support_README.md') -Destination (Join-Path $packageRoot 'README.md')
Copy-Item -LiteralPath (Join-Path $mathModelRoot '__init__.py') -Destination (Join-Path $packageRoot '__init__.py')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'paper\AI工具使用详情.pdf') -Destination (Join-Path $packageRoot 'AI工具使用详情.pdf')

foreach ($name in @('result1.xlsx', 'result2.xlsx', 'result3.xlsx', 'result4-2.xlsx', 'result4-3.xlsx')) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "submit\$name") -Destination (Join-Path $packageRoot "results\$name")
}
Copy-Item -Path (Join-Path $mathModelRoot 'solve\*.py') -Destination (Join-Path $packageRoot 'solve')
Copy-Item -Path (Join-Path $mathModelRoot 'tests\*.py') -Destination (Join-Path $packageRoot 'tests')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'tests\legacy_metrics.json') -Destination (Join-Path $packageRoot 'tests\legacy_metrics.json')

foreach ($name in @('build_paper.ps1', 'build_paper.sh', 'sync_code.py', 'check_macros.py', 'lint_tex.py', 'build_support.ps1', 'finalize.ps1')) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "tools\$name") -Destination (Join-Path $packageRoot "tools\$name")
}

foreach ($name in @('document.tex', 'cumcmthesis.cls', 'book.bib', 'numbers.tex', 'AI工具使用详情.tex', 'AI工具使用详情.pdf')) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "paper\$name") -Destination (Join-Path $packageRoot "paper\$name")
}
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'paper\document.pdf') -Destination (Join-Path $packageRoot 'paper\论文.pdf')
Copy-Item -Path (Join-Path $mathModelRoot 'paper\texfile\*.tex') -Destination (Join-Path $packageRoot 'paper\texfile')
Copy-Item -Path (Join-Path $mathModelRoot 'paper\generated\*.tex') -Destination (Join-Path $packageRoot 'paper\generated')
Copy-Item -Path (Join-Path $mathModelRoot 'paper\code\*.py') -Destination (Join-Path $packageRoot 'paper\code')
foreach ($name in @(
    'data_overview.pdf', 'dispatch_20250621.pdf', 'forecast_diagnosis.pdf',
    'netload_season.pdf', 'q1_dispatch.pdf', 'q2_attribution.pdf',
    'q3_forecast_value.pdf', 'sensitivity.pdf'
)) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "paper\figures\$name") -Destination (Join-Path $packageRoot "paper\figures\$name")
}

foreach ($name in @('MODEL_AUDIT.md', 'model_audit_raw.json', 'REFERENCES.md')) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "reports\$name") -Destination (Join-Path $packageRoot "reports\$name")
}

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
Compress-Archive -LiteralPath $packageRoot -DestinationPath $archivePath -CompressionLevel Optimal
Write-Host "[support] $archivePath"
Get-Item -LiteralPath $archivePath | Select-Object FullName, Length, LastWriteTime
