param([string]$Python)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/../Core.ps1"
$cache = Get-CacheRoot
if (!$Python) {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike '*WindowsApps*') { $Python = $cmd.Source }
    elseif (Test-Path "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe") {
        $Python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
    } else { throw 'Install Python 3.12 x64, or run Setup.ps1 -Python C:\path\python.exe.' }
}
$venv = Join-Path $cache 'runtime/norwegian-py312-v1'
if (!(Test-Path "$venv/Scripts/python.exe")) {
    & $Python -c "import sys,struct; sys.exit(0 if sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8 else 1)"
    if ($LASTEXITCODE) { throw 'This experiment requires Python 3.12 x64. Use Setup.ps1 -Python C:\path\python.exe.' }
    & $Python -m venv $venv
    if ($LASTEXITCODE) { throw 'Could not create the persistent Python environment.' }
}
$exe = "$venv/Scripts/python.exe"
$env:PIP_CACHE_DIR = Join-Path $cache 'runtime/pip-cache'
& $exe -m pip install --disable-pip-version-check 'torch==2.8.0' --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE) { throw 'CPU model runtime installation failed.' }
& $exe -m pip install --disable-pip-version-check 'transformers==4.51.3' 'rapidfuzz==3.14.1'
if ($LASTEXITCODE) { throw 'Model dependencies could not be installed.' }
& $exe "$PSScriptRoot/setup_assets.py"
if ($LASTEXITCODE) { throw 'Norwegian asset setup failed.' }
# Reuses the existing pinned Qwen and llama.cpp cache; does not replace it.
& "$PSScriptRoot/../Setup.ps1"
Write-Host 'Ready. Double-click Launch.cmd in the norwegian folder.'
