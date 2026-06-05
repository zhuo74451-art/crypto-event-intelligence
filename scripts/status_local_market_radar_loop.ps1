# status_local_market_radar_loop.ps1
# Check the status of the local market radar loop.
#
# Usage:
#   .\scripts\status_local_market_radar_loop.ps1

$ErrorActionPreference = "SilentlyContinue"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$PidFile = Join-Path $ProjectRoot "runtime\local_market_radar_loop.pid"
$LogFile = Join-Path $ProjectRoot "logs\local_market_radar_loop.log"

Write-Output "================================================================"
Write-Output " Local Market Radar Loop — Status"
Write-Output "================================================================"
Write-Output ""

# Check PID file
if (-not (Test-Path $PidFile)) {
    Write-Output "PID file  : NOT FOUND ($PidFile)"
    Write-Output "Status    : NOT RUNNING (no PID file)"
    Write-Output ""
    Write-Output "Start with: .\scripts\start_local_market_radar_loop.ps1"
    exit 0
}

$pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
Write-Output "PID file  : $PidFile"
Write-Output "PID       : $pidText"

if (-not $pidText) {
    Write-Output "Status    : NOT RUNNING (empty PID file)"
    Remove-Item $PidFile -Force
    exit 0
}

# Check process
$processId = [int]$pidText
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue

if (-not $process) {
    Write-Output "Status    : NOT RUNNING (process not found)"
    Write-Output ""
    Write-Output "PID file is stale. Cleaning up..."
    Remove-Item $PidFile -Force
    Write-Output "Removed stale PID file."
    Write-Output ""
    Write-Output "Restart with: .\scripts\start_local_market_radar_loop.ps1"
    exit 0
}

# Process is running
$startTime = $process.StartTime.ToString("yyyy-MM-dd HH:mm:ss")
$cpuTime = $process.TotalProcessorTime
Write-Output "Status    : RUNNING"
Write-Output "Process   : $($process.ProcessName) (PID=$processId)"
Write-Output "Started   : $startTime"
Write-Output "CPU time  : $cpuTime"
Write-Output ""

# Check log file
if (Test-Path $LogFile) {
    $logSize = (Get-Item $LogFile).Length
    $logLines = (Get-Content $LogFile).Count
    Write-Output "Log file  : $LogFile"
    Write-Output "Log size  : $logSize bytes ($logLines lines)"
    Write-Output ""
    Write-Output "--- Last 30 log lines ---"
    Get-Content $LogFile -Tail 30 | ForEach-Object { Write-Output "  $_" }
} else {
    Write-Output "Log file  : NOT FOUND ($LogFile)"
}

Write-Output ""
Write-Output "================================================================"
Write-Output "Commands:"
Write-Output "  Stop     : .\scripts\stop_local_market_radar_loop.ps1"
Write-Output "  Full log : Get-Content $LogFile"
Write-Output "  Follow   : Get-Content $LogFile -Wait -Tail 10"
Write-Output "================================================================"
