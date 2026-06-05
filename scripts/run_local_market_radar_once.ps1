# run_local_market_radar_once.ps1
# Single-run v09 market radar cycle - preview (default) or send to TG.
#
# Usage:
#   .\scripts\run_local_market_radar_once.ps1              # dry-run preview
#   .\scripts\run_local_market_radar_once.ps1 -Send         # real TG send
#   .\scripts\run_local_market_radar_once.ps1 -Hours 12 -LimitAlerts 50
#   .\scripts\run_local_market_radar_once.ps1 -Send -ChatIdEnv TELEGRAM_PUBLISH_CHAT_IDS
#
# Chat ID auto-detection:
#   Tries -ChatIdEnv value first, then TELEGRAM_PUBLISH_CHAT_IDS, then TELEGRAM_CHAT_ID.
#   Uses whichever has a non-empty value in the current process environment.

param(
    [switch] $Send,
    [int]    $Hours = 24,
    [int]    $LimitAlerts = 100,
    [string] $TokenEnv = "TELEGRAM_BOT_TOKEN",
    [string] $ChatIdEnv = "TELEGRAM_CHAT_ID"
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

# Ensure directories
$LogDir = Join-Path $ProjectRoot "logs"
$RuntimeDir = Join-Path $ProjectRoot "runtime"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$LogFile = Join-Path $LogDir "local_market_radar_once.log"
$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Load secrets
$SecretsFile = Join-Path $ProjectRoot "config\local_secrets.ps1"
if (-not (Test-Path $SecretsFile)) {
    Write-Output "ERROR: config\local_secrets.ps1 not found."
    Write-Output "  Copy from config\secrets.example.ps1 and fill in values."
    exit 1
}
. $SecretsFile

# Write start banner (NEVER print token value)
$sep = "=" * 60
$banner = @"
$sep
Local Market Radar - Single Run
  Start time : $StartTime
  Hours      : $Hours
  LimitAlerts: $LimitAlerts
  Send to TG : $($Send.IsPresent)
  Log file   : $LogFile
$sep
"@
Write-Output $banner
Add-Content -Path $LogFile -Value $banner

# Build command
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

$CmdArgs = @(
    "scripts/run_v09_market_radar_cycle.py",
    "--hours", $Hours,
    "--limit-alerts", $LimitAlerts,
    "--sample-if-no-key", "false"
)

if ($Send.IsPresent) {
    # Validate token (never print value)
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        $msg = "ERROR: TELEGRAM_BOT_TOKEN not set. Run `. .\config\local_secrets.ps1` first."
        Write-Output $msg
        Add-Content -Path $LogFile -Value "[ERROR] $msg"
        exit 1
    }

    # Auto-detect chat_id env var: try user-specified name, then common fallbacks
    $altNames = [System.Collections.ArrayList]::new()
    [void]$altNames.Add($ChatIdEnv)
    if ($ChatIdEnv -ne "TELEGRAM_PUBLISH_CHAT_IDS") { [void]$altNames.Add("TELEGRAM_PUBLISH_CHAT_IDS") }
    if ($ChatIdEnv -ne "TELEGRAM_CHAT_ID")       { [void]$altNames.Add("TELEGRAM_CHAT_ID") }

    $resolvedName = $null
    foreach ($name in $altNames) {
        $val = [Environment]::GetEnvironmentVariable($name, "Process")
        if ($val) {
            $resolvedName = $name
            break
        }
    }
    if (-not $resolvedName) {
        $msg = "ERROR: No chat_id env var set. Tried: $($altNames -join ', '). Run `. .\config\local_secrets.ps1` first."
        Write-Output $msg
        Add-Content -Path $LogFile -Value "[ERROR] $msg"
        exit 1
    }

    $CmdArgs += @(
        "--send-board",
        "--send-quality-summary",
        "--token-env", $TokenEnv,
        "--chat-id-env", $resolvedName
    )
    $modeLabel = "REAL SEND (chat_id=$resolvedName)"
} else {
    $modeLabel = "DRY RUN / PREVIEW"
}

$CmdLine = "$PythonExe $($CmdArgs -join ' ')"
Write-Output "[MODE] $modeLabel"
Write-Output "[CMD]  $CmdLine"
Add-Content -Path $LogFile -Value "[MODE] $modeLabel"
Add-Content -Path $LogFile -Value "[CMD]  $CmdLine"

# v1.5B-3: Delta snapshot step (before radar cycle)
try {
    Write-Output "[SNAPSHOT] Writing HL position snapshots..."
    Add-Content -Path $LogFile -Value "[SNAPSHOT] $PythonExe scripts/snapshot_hl_positions.py --check-delta"
    $snapProc = Start-Process -FilePath $PythonExe -ArgumentList @("scripts/snapshot_hl_positions.py", "--check-delta") `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "local_market_radar_once_snapshot_stdout.txt") `
        -RedirectStandardError (Join-Path $LogDir "local_market_radar_once_snapshot_stderr.txt")
    $snapExit = $snapProc.ExitCode
    Write-Output "[SNAPSHOT] Done (exit=$snapExit)"
    Add-Content -Path $LogFile -Value "[SNAPSHOT] Done (exit=$snapExit)"
} catch {
    Write-Output "[SNAPSHOT] WARNING: Snapshot step failed, continuing: $_"
    Add-Content -Path $LogFile -Value "[SNAPSHOT] WARNING: $_"
}

# Run
$ExitCode = 0
try {
    $proc = Start-Process -FilePath $PythonExe -ArgumentList $CmdArgs `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "local_market_radar_once_stdout.txt") `
        -RedirectStandardError (Join-Path $LogDir "local_market_radar_once_stderr.txt")
    $ExitCode = $proc.ExitCode
} catch {
    $ExitCode = 1
    $errMsg = "Process error: $_"
    Write-Output $errMsg
    Add-Content -Path $LogFile -Value "[ERROR] $errMsg"
}

$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$duration = [math]::Round(((Get-Date) - [datetime]::ParseExact($StartTime, "yyyy-MM-dd HH:mm:ss", $null)).TotalSeconds, 1)

# Show outputs
$summary = @"

--- Run Complete ---
  End time : $EndTime
  Duration : ${duration}s
  Exit code: $ExitCode
  Mode     : $modeLabel
"@
Write-Output $summary
Add-Content -Path $LogFile -Value $summary

# Show generated files
$GeneratedFiles = @(
    "results/v09_market_radar_cycle_summary.csv",
    "results/v09_tg_market_radar_board.md",
    "results/v09_tg_market_radar_board_summary.csv",
    "results/v09_tg_market_radar_send_summary.csv"
)
Write-Output "Generated outputs:"
foreach ($f in $GeneratedFiles) {
    $fullPath = Join-Path $ProjectRoot $f
    if (Test-Path $fullPath) {
        Write-Output "  [+] $f"
    } else {
        Write-Output "  [ ] $f (not generated)"
    }
}

if ($ExitCode -ne 0) {
    Write-Output ""
    Write-Output "Pipeline failed (exit=$ExitCode). Check:"
    Write-Output "  $LogFile"
    Write-Output "  logs/local_market_radar_once_stdout.txt"
    Write-Output "  logs/local_market_radar_once_stderr.txt"
}

exit $ExitCode
