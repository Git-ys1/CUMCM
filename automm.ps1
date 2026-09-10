param(
    [ValidateSet('check', 'monitor', 'once', 'daemon', 'configure-ai', 'pause', 'resume', 'stop')]
    [string]$Action = 'check'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Join-Path $PSScriptRoot 'AutoMM'
$projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'AutoMM virtual environment is missing.' }
$env:PATH = (Join-Path $projectRoot '.venv\Scripts') + ';' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:AUTOMM_ROOT = $projectRoot
Push-Location $projectRoot
try {
    switch ($Action) {
        'check' {
            & $projectPython -m pip check
            if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed.' }
            & $projectPython scripts\harness.py validate-config
            if ($LASTEXITCODE -ne 0) { throw 'Configuration check failed.' }
            & $projectPython -c "import sys; sys.path.insert(0, 'scripts'); from automm.llm.dsh import DshHeadlessProvider; print(DshHeadlessProvider({'executable':'dsh'}).probe())"
            if ($LASTEXITCODE -ne 0) { throw 'DSH CLI probe failed.' }
            Write-Host 'Local checks passed. This does not verify API credentials or a real modeling run.'
        }
        'monitor' { & $projectPython monitor\monitor.py }
        'configure-ai' { & dsh.cmd web }
        'once' { & $projectPython scripts\orchestrator_runner.py }
        'daemon' { & $projectPython scripts\orchestrator_daemon.py }
        'pause' { & $projectPython scripts\harness.py control PAUSE }
        'resume' { & $projectPython scripts\harness.py control RESUME }
        'stop' { & $projectPython scripts\harness.py control STOP }
    }
    if ($LASTEXITCODE -ne 0) { throw "AutoMM action failed: $Action (exit $LASTEXITCODE)" }
}
finally { Pop-Location }
