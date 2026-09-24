$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$cache = Get-CacheRoot
$exe = Join-Path $cache 'runtime/norwegian-py312-v1/Scripts/python.exe'
$database = Join-Path $cache 'lexical/norsk-ordvev-1.1.2/wordnet-help.sqlite3'
if (!(Test-Path $exe)) { throw 'Run Setup-Once.cmd first.' }
if (!(Test-Path $database)) { throw 'Run Setup-Wordnet.cmd once first.' }
& $exe "$PSScriptRoot/server.py" --wordnet
exit $LASTEXITCODE

