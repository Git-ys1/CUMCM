param(
    [Parameter(Mandatory = $true)]
    [string]$PaperName,
    [Parameter(Mandatory = $true)]
    [string]$SubmissionFolder
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$mathModelRoot = Join-Path $projectRoot 'MathModel'
$paperDir = Join-Path $mathModelRoot 'paper'
$writingDir = Join-Path $projectRoot 'WorkBuddy\01_论文写作'
$submissionDir = Join-Path $projectRoot "提交文件\$SubmissionFolder"

New-Item -ItemType Directory -Path $writingDir -Force | Out-Null
New-Item -ItemType Directory -Path $submissionDir -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $paperDir 'document.pdf') -Destination (Join-Path $writingDir $PaperName) -Force
foreach ($name in @('result1.xlsx', 'result2.xlsx', 'result3.xlsx', 'result4-2.xlsx', 'result4-3.xlsx')) {
    Copy-Item -LiteralPath (Join-Path $mathModelRoot "submit\$name") -Destination (Join-Path $submissionDir $name) -Force
}
Copy-Item -LiteralPath (Join-Path $paperDir 'document.pdf') -Destination (Join-Path $submissionDir $PaperName) -Force
Copy-Item -LiteralPath (Join-Path $paperDir 'AI工具使用详情.pdf') -Destination (Join-Path $submissionDir 'AI工具使用详情.pdf') -Force
Copy-Item -LiteralPath (Join-Path $mathModelRoot '支撑材料.zip') -Destination (Join-Path $submissionDir '支撑材料.zip') -Force
Copy-Item -LiteralPath (Join-Path $mathModelRoot 'reports\MODEL_AUDIT.md') -Destination (Join-Path $submissionDir '模型审计报告.md') -Force

Write-Host "[finalize] paper -> $(Join-Path $writingDir $PaperName)"
Write-Host "[finalize] submission -> $submissionDir"
Get-ChildItem -LiteralPath $submissionDir | Select-Object Name, Length, LastWriteTime
