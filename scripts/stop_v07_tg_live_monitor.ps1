$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidFile = Join-Path $Root "results\v07_tg_live_monitor.pid"

if (-not (Test-Path $PidFile)) {
    Write-Output "pid_file_missing=$PidFile"
    exit 0
}

$PidText = Get-Content $PidFile -ErrorAction SilentlyContinue
if (-not $PidText) {
    Write-Output "pid_file_empty=$PidFile"
    exit 0
}

$ProcessId = [int](($PidText -replace "pid=", "").Trim())
$Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
if (-not $Process) {
    Write-Output "process_not_running=$ProcessId"
    exit 0
}

Stop-Process -Id $ProcessId -Force
Write-Output "stopped_pid=$ProcessId"
