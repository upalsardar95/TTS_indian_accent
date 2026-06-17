<#
.SYNOPSIS
    One-shot environment setup for the Indian-accent Hinglish TTS engine.

.DESCRIPTION
    Creates a Python 3.11 virtual-env in .venv, installs all dependencies
    (the CUDA build of torch pinned in requirements.txt, for local GPU/CPU use),
    installs the `indian-tts` package, and runs a quick environment check.

    Run this on any fresh machine after cloning the repo — it reproduces the
    exact environment from the committed dependency files. Re-run any time after
    deleting .venv to rebuild from scratch.

    For a CPU-only server / container instead, use the Dockerfile + DEPLOY.md
    (those use requirements-cpu.txt and the CPU torch wheels).

.PARAMETER PythonLauncher
    How to invoke Python 3.11 to create the venv. Defaults to "py -3.11".
    Pass a full path if `py` isn't available, e.g.:
      .\scripts\setup.ps1 -PythonLauncher "C:\Python311\python.exe"

.EXAMPLE
    .\scripts\setup.ps1
#>
param(
    [string]$PythonLauncher = "py -3.11"
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment in .venv (using: $PythonLauncher) ..." -ForegroundColor Cyan
    Invoke-Expression "$PythonLauncher -m venv `"$(Join-Path $root '.venv')`""
} else {
    Write-Host ".venv already exists — installing into it." -ForegroundColor Yellow
}

Write-Host "Upgrading pip ..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "Installing dependencies from requirements.txt (torch cu118 + kokoro + ...) ..." -ForegroundColor Cyan
& $venvPython -m pip install -r (Join-Path $root 'requirements.txt')

Write-Host "Installing the indian-tts package (editable) ..." -ForegroundColor Cyan
& $venvPython -m pip install -e $root

Write-Host "Verifying environment ..." -ForegroundColor Cyan
& $venvPython (Join-Path $root 'scripts\check_env.py')

Write-Host "`nSetup complete. The Kokoro model (~330 MB) downloads on first synthesis." -ForegroundColor Green
Write-Host "Try it:   .\run.ps1 voices" -ForegroundColor Green
