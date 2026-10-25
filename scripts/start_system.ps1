# ==============================================================================
# AI Machine Health Monitor — System Startup Script
# ==============================================================================
# Starts both required system services in separate terminal windows:
# 1. FastAPI REST Telemetry Gateway (port 8000)
# 2. Streamlit Web Analytics Dashboard (port 8501)
# ==============================================================================

[CmdletBinding()]
param()

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not (Test-Path "app.py") -or -not (Test-Path "api\main.py")) {
    Write-Error "Error: Must be run from the MachineHealth project root directory."
    exit 1
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Warning "Virtual environment (.venv) not found. Attempting to run setup..."
    & (Join-Path $PSScriptRoot "setup_windows.ps1")
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting AI Machine Health Monitor System" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Detect local LAN IPv4 address for ESP32 configuration
$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { 
    $_.InterfaceAlias -notmatch "Loopback|vEthernet|VirtualBox|VMware" -and $_.IPAddress -notmatch "^169\.254\."
} | Select-Object -ExpandProperty IPAddress -First 1)

if (-not $LocalIP) {
    $LocalIP = "192.168.1.X (run ipconfig to verify)"
}

Write-Host "Local Host Information:" -ForegroundColor White
Write-Host "  LAN IP Address : " -NoNewline; Write-Host "$LocalIP" -ForegroundColor Yellow
Write-Host "  API Endpoint   : " -NoNewline; Write-Host "http://$LocalIP:8000/api/readings" -ForegroundColor Yellow
Write-Host "  Web Dashboard  : " -NoNewline; Write-Host "http://localhost:8501" -ForegroundColor Yellow
Write-Host "  API Docs       : " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------" -ForegroundColor Gray

# Start Terminal 1: FastAPI Gateway
Write-Host "[1/2] Launching FastAPI Ingestion Gateway (Port 8000)..." -ForegroundColor Green
$ApiCommand = "cd '$ProjectRoot'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $ApiCommand -WindowStyle Normal

Start-Sleep -Seconds 2

# Start Terminal 2: Streamlit Dashboard
Write-Host "[2/2] Launching Streamlit Analytical Dashboard (Port 8501)..." -ForegroundColor Green
$DashboardCommand = "cd '$ProjectRoot'; if (Test-Path '.\.venv\Scripts\Activate.ps1') { .\.venv\Scripts\Activate.ps1 }; streamlit run app.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $DashboardCommand -WindowStyle Normal

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Both services launched in separate windows!" -ForegroundColor Green
Write-Host "Keep both terminal windows open while running." -ForegroundColor White
Write-Host "To safely stop the system, run:" -ForegroundColor White
Write-Host "  .\scripts\stop_system.ps1" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
