<#
.SYNOPSIS
  One-time setup: a Python 3.12/3.13 virtual environment in .venv and the Python packages.
  Kokoro (retired, D-39) and Remotion are no longer set up here; see docs/AUDIO_SYSTEM.md.

.EXAMPLE
  .\setup.ps1
#>
[CmdletBinding()]
param([string]$PythonExe = "")

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if ($PythonExe -eq "") {
  foreach ($v in "3.13", "3.12") {
    $found = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $found) { $PythonExe = $found.Trim(); break }
  }
  if ($PythonExe -eq "") {
    $uv = Get-ChildItem "$env:APPDATA\uv\python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
          Where-Object { $_.FullName -match "cpython-3\.1[23]" } | Select-Object -First 1
    if ($uv) { $PythonExe = $uv.FullName }
  }
  if ($PythonExe -eq "") { throw "Python 3.12-3.13 not found (the pinned packages are tested on 3.12/3.13). Install 3.13 (python.org or 'uv python install 3.13') and re-run." }
}

$venv = Join-Path $root ".venv"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
  Write-Host "==> Creating .venv with $PythonExe" -ForegroundColor Cyan
  & $PythonExe -m venv $venv
}
$py = Join-Path $venv "Scripts\python.exe"
Write-Host "==> Installing packages" -ForegroundColor Cyan
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r (Join-Path $root "requirements.txt")
Write-Host "Done. Run the tests: .venv\Scripts\python -m pytest -q" -ForegroundColor Green
