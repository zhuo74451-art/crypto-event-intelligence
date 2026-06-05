# start_local_tg_publisher.ps1
# Start the local TG publisher in background.
# Default: DRY_RUN=true (preview only, no real TG send).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$PidFile = Join-Path $Root "runtime\local_tg_publisher.pid"
$LogDir  = Join-Path $Root "logs"
$RuntimeDir = Join-Path $Root "runtime"

# Ensure directories exist
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

# Check if already running
if (Test-Path $PidFile) {
    $ExistingPid = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
    if ($ExistingPid) {
        $Proc = Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue
        if ($Proc) {
            Write-Output "Publisher already running (PID=$ExistingPid). Stop it first:"
            Write-Output "  .\scripts\stop_local_tg_publisher.ps1"
            exit 1
        }
    }
    Remove-Item $PidFile -Force
}

# Build Python command
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    $PythonExe = "python"
}

$PublisherScript = Join-Path $Root "scripts\run_local_tg_publisher.py"

Write-Output "=== Local TG Publisher ==="
Write-Output "Root:       $Root"
Write-Output "Script:     $PublisherScript"
Write-Output "PID file:   $PidFile"
Write-Output "Log:        $LogDir\local_tg_publisher.log"
Write-Output ""

# Check if we have an env file
$EnvFile = Join-Path $Root "config\local_tg_publisher.env"
if (-not (Test-Path $EnvFile)) {
    Write-Output "WARNING: No config/local_tg_publisher.env found."
    Write-Output "  Create one from config/local_tg_publisher.env.example"
    Write-Output "  Without it, only DRY_RUN=true will work (no real TG send)."
    Write-Output ""
}

# Start the publisher in background
Write-Output "Starting publisher (DRY_RUN=check .env)..."
$Process = Start-Process -FilePath $PythonExe `
    -ArgumentList "`"$PublisherScript`"" `
    -WindowStyle Hidden `
    -PassThru

$Process.Id | Out-File -FilePath $PidFile -Encoding utf8
Write-Output "Publisher started (PID=$($Process.Id))"
Write-Output ""
Write-Output "Commands:"
Write-Output "  Check log:     Get-Content $LogDir\local_tg_publisher.log -Tail 20"
Write-Output "  Stop:          .\scripts\stop_local_tg_publisher.ps1"
Write-Output "  Check process: Get-Process -Id $($Process.Id)"
