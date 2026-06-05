# stop_local_market_radar_loop.ps1
# Stop the running local market radar loop.
#
# Usage:
#   .\scripts\stop_local_market_radar_loop.ps1

$ErrorActionPreference = "SilentlyContinue"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$PidFile = Join-Path $ProjectRoot "runtime\local_market_radar_loop.pid"
$LogFile = Join-Path $ProjectRoot "logs\local_market_radar_loop.log"

if (-not (Test-Path $PidFile)) {
    Write-Output "PID file not found: $PidFile"
    Write-Output ""
    Write-Output "The loop may not be running, or was started differently."
    Write-Output ""
    Write-Output "To find orphaned processes:"
    Write-Output '  Get-Process powershell* | Where-Object { $_.Id }'
    Write-Output '  Get-Process python* | Where-Object { $_.Id }'
    exit 0
}

$pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
if (-not $pidText) {
    Write-Output "PID file is empty: $PidFile"
    Remove-Item $PidFile -Force
    exit 0
}

$processId = [int]$pidText
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue

if (-not $process) {
    Write-Output "Process PID=$processId is not running."
    Remove-Item $PidFile -Force
    exit 0
}

# Verify it's a PowerShell process (our loop wrapper)
if ($process.ProcessName -ne "powershell" -and $process.ProcessName -ne "pwsh") {
    Write-Output "WARNING: PID $processId is '$($process.ProcessName)', not powershell."
    Write-Output "This PID may not be the market radar loop."
    Write-Output "Review manually before killing: Get-Process -Id $processId"
    exit 1
}

# Stop the process tree (the PS wrapper + any child python)
$stopTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Output "Stopping local market radar loop (PID=$processId)..."
Add-Content -Path $LogFile -Value "[$stopTime] STOP requested by stop_local_market_radar_loop.ps1"

# First, try to stop child processes (python scripts)
$childProcesses = Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $processId }
foreach ($child in $childProcesses) {
    try {
        Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
    } catch { }
}

# Then stop the parent PowerShell process
Stop-Process -Id $processId -Force
Start-Sleep -Seconds 2

# Verify
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue
if ($process) {
    Write-Output "WARNING: Process PID=$processId still running after Stop-Process."
    Write-Output "You may need to kill it manually: Stop-Process -Id $processId -Force"
    exit 1
}

Remove-Item $PidFile -Force
$msg = "[$stopTime] STOP complete — process killed, PID file removed."
Write-Output $msg
Add-Content -Path $LogFile -Value $msg
