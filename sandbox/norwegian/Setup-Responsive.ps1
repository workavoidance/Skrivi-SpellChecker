param([string]$Python)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$cache = Get-CacheRoot
$venv = Join-Path $cache 'runtime/norwegian-py312-v1'
$exe = Join-Path $venv 'Scripts/python.exe'
if (!(Test-Path $exe)) {
    if (!$Python) {
        $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($candidate -and $candidate.Source -notlike '*WindowsApps*') { $Python = $candidate.Source }
        elseif (Test-Path "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe") {
            $Python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
        } else { throw 'Install Python 3.12 x64 first, or pass -Python C:\path\python.exe.' }
    }
    & $Python -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 1)"
    if ($LASTEXITCODE) { throw 'Python 3.12 x64 is required.' }
    & $Python -m venv $venv
    if ($LASTEXITCODE) { throw 'Could not create the cached runtime.' }
}
$env:PIP_CACHE_DIR = Join-Path $cache 'runtime/pip-cache'
& $exe -m pip install --disable-pip-version-check 'torch==2.8.0' --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE) { throw 'CPU runtime setup failed.' }
& $exe -m pip install --disable-pip-version-check 'transformers==4.51.3' 'rapidfuzz==3.14.1'
if ($LASTEXITCODE) { throw 'Dependency setup failed.' }
& $exe "$PSScriptRoot/setup_assets.py"
if ($LASTEXITCODE) { throw 'Norwegian assets setup failed.' }
& $exe "$PSScriptRoot/setup_nuspell.py"
if ($LASTEXITCODE) { throw 'Nuspell setup failed.' }
Write-Host 'Ready. Close this window and double-click Start-Skrivi.cmd.'
