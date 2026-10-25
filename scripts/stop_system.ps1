# ==============================================================================
# AI Machine Health Monitor — System Shutdown Script
# ==============================================================================
# Identifies and safely terminates the specific FastAPI and Streamlit processes
# listening on ports 8000 and 8501.
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$Force
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Stopping AI Machine Health Monitor Services" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$TargetPorts = @(8000, 8501)
$TerminatedCount = 0

foreach ($Port in $TargetPorts) {
    Write-Host "Checking port $Port..." -NoNewline
    $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

    if ($Connections) {
        foreach ($Conn in $Connections) {
            $PidToKill = $Conn.OwningProcess
            try {
                $Proc = Get-Process -Id $PidToKill -ErrorAction Stop
                $ProcName = $Proc.ProcessName
                
                # Verify that the process is python or uvicorn
                if ($ProcName -match "python|uvicorn|streamlit") {
                    Write-Host " Found $ProcName (PID: $PidToKill). Terminating..." -ForegroundColor Yellow
                    Stop-Process -Id $PidToKill -Force
                    $TerminatedCount++
                } else {
                    Write-Host " PID $PidToKill is $ProcName (not an app process; skipping)." -ForegroundColor Gray
                }
            } catch {
                Write-Host " Unable to inspect PID $PidToKill." -ForegroundColor Gray
            }
        }
    } else {
        Write-Host " Inactive (no active listener)." -ForegroundColor Green
    }
}

Write-Host "----------------------------------------------------------" -ForegroundColor Gray
if ($TerminatedCount -gt 0) {
    Write-Host "Successfully stopped $TerminatedCount MachineHealth service process(es)." -ForegroundColor Green
} else {
    Write-Host "No active MachineHealth processes were running on ports 8000 or 8501." -ForegroundColor White
}
Write-Host "==========================================================" -ForegroundColor Cyan
