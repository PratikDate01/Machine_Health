# ==============================================================================
# AI Machine Health Monitor — Windows Setup Script
# ==============================================================================
# This script configures a fresh Windows 10/11 system for the AI Machine Health Monitor.
# It creates a virtual environment, installs dependencies, initializes config, and tests.
# ==============================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AI Machine Health Monitor — Fresh Windows Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify working directory is project root
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Path "app.py") -or -not (Test-Path "requirements.txt")) {
    Write-Error "Error: Must be run from the MachineHealth project root directory."
    exit 1
}

Write-Host "[1/6] Verified project root: $ProjectRoot" -ForegroundColor Green

# 2. Check for Python installation
Write-Host "[2/6] Detecting Python installation..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Write-Error "Python was not found on PATH. Please install Python 3.10-3.13 from python.org and check 'Add Python to PATH'."
    exit 1
}

$PyVer = & $PythonCmd --version 2>&1
Write-Host "      Detected Python: $PyVer" -ForegroundColor Green

# 3. Create Virtual Environment (.venv)
Write-Host "[3/6] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    & $PythonCmd -m venv .venv
    Write-Host "      Created virtual environment in $ProjectRoot\.venv" -ForegroundColor Green
} else {
    Write-Host "      Existing virtual environment detected in .venv (preserving)." -ForegroundColor Green
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$VenvPip    = Join-Path $ProjectRoot ".venv\Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment python binary not found at $VenvPython"
    exit 1
}

# 4. Upgrade pip and install dependencies
Write-Host "[4/6] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r requirements.txt --quiet
Write-Host "      All dependencies installed successfully." -ForegroundColor Green

# 5. Environment configuration (.env)
Write-Host "[5/6] Verifying environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "      Created default .env from .env.example (preserving secrets)." -ForegroundColor Green
    }
} else {
    Write-Host "      Existing .env configuration preserved." -ForegroundColor Green
}

# 6. Verify installation with test suite
Write-Host "[6/6] Running diagnostic verification test suite..." -ForegroundColor Yellow
$VenvPytest = Join-Path $ProjectRoot ".venv\Scripts\pytest.exe"
if (Test-Path $VenvPytest) {
    & $VenvPytest -q
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      All diagnostic tests passed successfully!" -ForegroundColor Green
    } else {
        Write-Warning "      Some tests reported warnings/errors. Review terminal output."
    }
} else {
    & $VenvPython -m pytest -q
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete! To start the platform run:" -ForegroundColor Cyan
Write-Host "  .\scripts\start_system.ps1" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
