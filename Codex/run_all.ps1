param([switch]$SkipSolve)
$ErrorActionPreference='Stop'
$Python=Join-Path $PSScriptRoot '..\AutoMM\.venv\Scripts\python.exe'
$Root=Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $Root
try {
    if(-not $SkipSolve){
        & $Python -m Codex.solve.q1
        & $Python -m Codex.solve.q2
        & $Python -m Codex.solve.q3
        & $Python -m Codex.solve.q4
    }
    & $Python -m unittest discover -s Codex\tests -v
    & $Python -m Codex.solve.validate_all
    $env:MPLBACKEND='Agg'
    & $Python -m Codex.solve.plot_results
    & $Python -m Codex.solve.paper_tables
    & $Python -m Codex.solve.build_manifest
} finally { Pop-Location }
