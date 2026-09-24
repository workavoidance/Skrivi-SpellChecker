$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$python = Join-Path (Get-CacheRoot) 'runtime/norwegian-py312-v1/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run Setup.cmd first so the shared Python runtime is available.' }
& $python (Join-Path $PSScriptRoot 'setup_ordbank.py')
if ($LASTEXITCODE -ne 0) { throw "Ordbank setup failed with exit code $LASTEXITCODE" }
Read-Host 'Press Enter to close'

