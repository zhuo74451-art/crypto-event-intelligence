# status_local_news_flow_tg_loop.ps1
# Check status of the local news flow TG loop.

$ErrorActionPreference = "SilentlyContinue"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$PidFile = Join-Path $ProjectRoot "runtime\local_news_flow_tg_loop.pid"
$LogFile = Join-Path $ProjectRoot "logs\local_news_flow_tg_loop.log"

Write-Output "================================================================"
Write-Output " Local News Flow TG Loop - Status"
Write-Output "================================================================"

if (-not (Test-Path $PidFile)) {
    Write-Output "PID file  : NOT FOUND"
    Write-Output "Status    : NOT RUNNING"
    Write-Output "Start with: .\scripts\start_local_news_flow_tg_loop.ps1"
    exit 0
}

$pt = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
if (-not $pt) { Write-Output "Status: NOT RUNNING (empty PID)"; Remove-Item $PidFile -Force; exit 0 }

$pid = [int]$pt
$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Output "Status    : NOT RUNNING (process $pid gone)"
    Remove-Item $PidFile -Force
    exit 0
}

Write-Output "PID       : $pid"
Write-Output "Status    : RUNNING"
Write-Output "Process   : $($proc.ProcessName)"
Write-Output "Started   : $($proc.StartTime.ToString('yyyy-MM-dd HH:mm:ss'))"
Write-Output ""

if (Test-Path $LogFile) {
    $lines = (Get-Content $LogFile).Count
    Write-Output "Log file  : $LogFile ($lines lines)"
    Write-Output ""
    Write-Output "--- Last 30 log lines ---"
    Get-Content $LogFile -Tail 30 | ForEach-Object { Write-Output "  $_" }
}
Write-Output ""
Write-Output "Commands:  Stop = .\scripts\stop_local_news_flow_tg_loop.ps1"
