$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$exe = Join-Path (Get-CacheRoot) 'runtime/norwegian-py312-v1/Scripts/python.exe'
if (!(Test-Path $exe)) { throw 'Run Setup.cmd first.' }
& $exe "$PSScriptRoot/server.py" --responsive
exit $LASTEXITCODE
