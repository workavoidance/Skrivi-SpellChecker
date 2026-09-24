param([string]$Python)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$cache = Get-CacheRoot
$exe = Join-Path $cache 'runtime/norwegian-py312-v1/Scripts/python.exe'
if (!(Test-Path $exe)) { throw 'Run Setup-Once.cmd first.' }
& $exe "$PSScriptRoot/setup_wordnet.py"
if ($LASTEXITCODE) { throw 'Norsk ordvev setup failed.' }
Write-Host 'Ready. Use Launch-Wordnet-Experiment.cmd.'

