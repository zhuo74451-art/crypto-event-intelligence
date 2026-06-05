# stop_local_tg_publisher.ps1
# Stop the local TG publisher gracefully.

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidFile = Join-Path $Root "runtime\local_tg_publisher.pid"

if (-not (Test-Path $PidFile)) {
    Write-Output "PID file not found: $PidFile"
    Write-Output "Publisher may not be running, or was started differently."
    Write-Output ""
    Write-Output "To find and stop manually:"
    Write-Output "  Get-Process python* | Where-Object { `$_.CommandLine -like '*run_local_tg_publisher*' }"
    Write-Output "  Stop-Process -Id <PID> -Force"
    exit 0
}

$PidText = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
if (-not $PidText) {
    Write-Output "PID file empty: $PidFile"
    Remove-Item $PidFile -Force
    exit 0
}

$ProcessId = [int]$PidText
$Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue

if (-not $Process) {
    Write-Output "Process not running (PID=$ProcessId). Cleaning up PID file."
    Remove-Item $PidFile -Force
    exit 0
}

# Verify this is actually our publisher process
if ($Process.ProcessName -ne "python" -and $Process.ProcessName -ne "python.exe" -and $Process.ProcessName -ne "pythonw") {
    Write-Output "WARNING: PID $ProcessId is $($Process.ProcessName), not python."
    Write-Output "Not stopping — PID file may be stale. Please check manually."
    exit 1
}

# Graceful stop (Ctrl+C equivalent via closing stdin, then force if needed)
Write-Output "Stopping publisher (PID=$ProcessId)..."
Stop-Process -Id $ProcessId -Force
Start-Sleep -Seconds 1

$Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
if ($Process) {
    Write-Output "Process still running after Stop-Process. Check manually."
    exit 1
}

Remove-Item $PidFile -Force
Write-Output "Publisher stopped (PID=$ProcessId). PID file removed."
