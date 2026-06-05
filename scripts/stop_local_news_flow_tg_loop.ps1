# stop_local_news_flow_tg_loop.ps1
# Stop the local news flow TG loop.

$ErrorActionPreference = "SilentlyContinue"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$PidFile = Join-Path $ProjectRoot "runtime\local_news_flow_tg_loop.pid"
$LogFile = Join-Path $ProjectRoot "logs\local_news_flow_tg_loop.log"

if (-not (Test-Path $PidFile)) {
    Write-Output "PID file not found. Loop may not be running."
    Write-Output "To find orphaned: Get-Process powershell* | Select Id,StartTime"
    exit 0
}

$pidText = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
if (-not $pidText) { Write-Output "PID file empty."; Remove-Item $PidFile -Force; exit 0 }

$pid = [int]$pidText
$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if (-not $proc) { Write-Output "Process $pid not running."; Remove-Item $PidFile -Force; exit 0 }

if ($proc.ProcessName -notin @("powershell","pwsh")) {
    Write-Output "WARNING: PID $pid is '$($proc.ProcessName)', not powershell. Not stopping."
    exit 1
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "[$ts] STOP requested by stop_local_news_flow_tg_loop.ps1"

# Stop child processes first
Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $pid } | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Stop-Process -Id $pid -Force
Start-Sleep -Seconds 2

$proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
if ($proc) { Write-Output "WARNING: Process $pid still running."; exit 1 }

Remove-Item $PidFile -Force
Write-Output "Stopped (PID=$pid)."
Add-Content -Path $LogFile -Value "[$ts] STOP complete."
