$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$cache = Get-CacheRoot
$exe = Join-Path $cache 'runtime/norwegian-py312-v1/Scripts/python.exe'
$database = Join-Path $cache 'lexical/bokmaal/dictionary.sqlite3'
if (!(Test-Path $exe)) { throw 'Run Setup-Once.cmd first.' }
if (!(Test-Path $database)) { throw 'Build the local dictionary index with tools/import_bokmaal.py first. See README.' }
& $exe "$PSScriptRoot/server.py" --dictionary
exit $LASTEXITCODE
