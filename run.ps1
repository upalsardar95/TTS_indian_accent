<#
.SYNOPSIS
    Launcher for the Indian-accent Hinglish TTS CLI.

.DESCRIPTION
    Finds the project's virtual-env Python and runs the `indian-tts` CLI with it,
    so you don't have to activate the venv first. All arguments are forwarded
    straight to the CLI.

    Note: there is deliberately no param() / [CmdletBinding()] block. Those add
    PowerShell "common parameters" (-OutVariable, -OutBuffer, ...), which would
    intercept short CLI flags like -o as ambiguous matches. Using the automatic
    $args variable lets every flag pass through to the CLI untouched.

.EXAMPLE
    .\run.ps1 serve
    .\run.ps1 say "नमस्ते! Hello world." -o outputs/hello.wav
    .\run.ps1 voices
#>

$ErrorActionPreference = 'Stop'

# Resolve paths relative to this script, so it works from any directory.
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "venv Python not found at $python. Create it first (python -3.11 -m venv .venv) and install the package."
    exit 1
}

# So the Windows console can print Devanagari without crashing.
$env:PYTHONUTF8 = '1'

# Run the CLI module with the venv interpreter; forward all args verbatim.
& $python -m indian_tts.cli.main @args
exit $LASTEXITCODE
