param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$mathModelRoot = (Resolve-Path (Join-Path $projectRoot 'MathModel')).Path
$stageRoot = Join-Path $mathModelRoot 'delivery_v4'
$packageRoot = Join-Path $stageRoot 'MathModel'
$archivePath = Join-Path $mathModelRoot '支撑材料V4.zip'

# 删除范围固定为 MathModel/delivery_v4，先做绝对路径与目录名双重校验。
$resolvedStage = [IO.Path]::GetFullPath($stageRoot)
$expectedStage = [IO.Path]::GetFullPath((Join-Path $mathModelRoot 'delivery_v4'))
if ($resolvedStage -ne $expectedStage -or (Split-Path $resolvedStage -Leaf) -ne 'delivery_v4') {
    throw "拒绝清理非预期目录：$resolvedStage"
}
if (Test-Path -LiteralPath $resolvedStage) {
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}

foreach ($relative in @('results', 'solve', 'tests', 'reports')) {
    New-Item -ItemType Directory -Path (Join-Path $packageRoot $relative) -Force | Out-Null
}

Copy-Item -LiteralPath (Join-Path $mathModelRoot 'support_README_V4.md') -Destination (Join-Path $packageRoot 'README.md')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'paper\AI工具使用详情.pdf') -Destination (Join-Path $packageRoot 'AI工具使用详情.pdf')
Copy-Item -LiteralPath (Join-Path $mathModelRoot '__init__.py') -Destination (Join-Path $packageRoot '__init__.py')
Copy-Item -Path (Join-Path $mathModelRoot 'submit\*.xlsx') -Destination (Join-Path $packageRoot 'results')
Copy-Item -Path (Join-Path $mathModelRoot 'solve\*.py') -Destination (Join-Path $packageRoot 'solve')
Copy-Item -Path (Join-Path $mathModelRoot 'tests\*.py') -Destination (Join-Path $packageRoot 'tests')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'tests\legacy_metrics.json') -Destination (Join-Path $packageRoot 'tests\legacy_metrics.json')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'reports\MODEL_AUDIT_V4.md') -Destination (Join-Path $packageRoot 'reports\MODEL_AUDIT_V4.md')
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'reports\model_audit_v4_raw.json') -Destination (Join-Path $packageRoot 'reports\model_audit_v4_raw.json')

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
Compress-Archive -LiteralPath $packageRoot -DestinationPath $archivePath -CompressionLevel Optimal
Write-Host "[support] $archivePath"
Get-Item -LiteralPath $archivePath | Select-Object FullName, Length, LastWriteTime
