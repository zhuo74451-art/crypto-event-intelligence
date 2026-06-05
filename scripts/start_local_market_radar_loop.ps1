# start_local_market_radar_loop.ps1
# Start the v09 market radar in a long-running background loop.
#
# Usage:
#   .\scripts\start_local_market_radar_loop.ps1                    # preview mode (no TG)
#   .\scripts\start_local_market_radar_loop.ps1 -Send               # real TG send
#   .\scripts\start_local_market_radar_loop.ps1 -Send -IntervalSeconds 1800
#   .\scripts\start_local_market_radar_loop.ps1 -Send -ChatIdEnv TELEGRAM_PUBLISH_CHAT_IDS
#   .\scripts\start_local_market_radar_loop.ps1 -Send -EnableDeltaSnapshot:$false  # emergency disable
#
# Chat ID auto-detection:
#   Tries -ChatIdEnv value first, then TELEGRAM_PUBLISH_CHAT_IDS, then TELEGRAM_CHAT_ID.
#   Uses whichever has a non-empty value in the current process environment.
# Delta snapshot: enabled by default. Runs snapshot_hl_positions.py --check-delta before each cycle.

param(
    [switch] $Send,
    [int]    $IntervalSeconds = 3600,
    [int]    $Hours = 24,
    [int]    $LimitAlerts = 100,
    [string] $TokenEnv = "TELEGRAM_BOT_TOKEN",
    [string] $ChatIdEnv = "TELEGRAM_CHAT_ID",
    [bool]   $EnableDeltaSnapshot = $true
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

$PidFile = Join-Path $RuntimeDir "local_market_radar_loop.pid"
$LogFile = Join-Path $LogDir "local_market_radar_loop.log"

# Check if already running
if (Test-Path $PidFile) {
    $existingPid = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
    if ($existingPid) {
        try {
            $existingProc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
            if ($existingProc) {
                Write-Output "ERROR: Publisher already running (PID=$existingPid)."
                Write-Output "  Stop it first: .\scripts\stop_local_market_radar_loop.ps1"
                Write-Output "  Check status:  .\scripts\status_local_market_radar_loop.ps1"
                exit 1
            }
        } catch { }
    }
    Remove-Item $PidFile -Force
}

# Load secrets
$SecretsFile = Join-Path $ProjectRoot "config\local_secrets.ps1"
if (-not (Test-Path $SecretsFile)) {
    Write-Output "WARNING: config\local_secrets.ps1 not found."
    Write-Output "  Without it, watchers may use sample data and TG send will fail."
} else {
    . $SecretsFile
}

# Validate TG send requirements
$resolvedChatIdEnv = $null
if ($Send.IsPresent) {
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        Write-Output "ERROR: -Send requires TELEGRAM_BOT_TOKEN in config/local_secrets.ps1"
        exit 1
    }

    # Auto-detect chat_id env var: try user-specified name, then common fallbacks
    $altNames = [System.Collections.ArrayList]::new()
    [void]$altNames.Add($ChatIdEnv)
    if ($ChatIdEnv -ne "TELEGRAM_PUBLISH_CHAT_IDS") { [void]$altNames.Add("TELEGRAM_PUBLISH_CHAT_IDS") }
    if ($ChatIdEnv -ne "TELEGRAM_CHAT_ID")       { [void]$altNames.Add("TELEGRAM_CHAT_ID") }

    foreach ($name in $altNames) {
        $val = [Environment]::GetEnvironmentVariable($name, "Process")
        if ($val) {
            $resolvedChatIdEnv = $name
            break
        }
    }
    if (-not $resolvedChatIdEnv) {
        Write-Output "ERROR: No chat_id env var set. Tried: $($altNames -join ', '). Check config/local_secrets.ps1."
        exit 1
    }

    $modeLabel = "REAL SEND (chat_id=$resolvedChatIdEnv)"
} else {
    $modeLabel = "PREVIEW ONLY (no TG send)"
}

# Look up python
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

# Write startup info to log (NEVER include token values)
$startTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$tokenSet = [bool]$env:TELEGRAM_BOT_TOKEN
$chatSet = $resolvedChatIdEnv -ne $null
$startup = @"
======================================================================
Local Market Radar Loop - STARTING
  Start time      : $startTime
  Interval         : ${IntervalSeconds}s
  Hours per cycle  : $Hours
  Limit alerts     : $LimitAlerts
  Mode             : $modeLabel
  Token configured : $tokenSet
  Chat ID env      : $resolvedChatIdEnv
  Delta snapshot   : $EnableDeltaSnapshot
  Python           : $PythonExe
  PID file         : $PidFile
  Log file         : $LogFile
======================================================================
"@
Write-Output $startup
Add-Content -Path $LogFile -Value $startup

# Build the cycle arguments
$cycleArgs = @(
    "scripts/run_v09_market_radar_cycle.py",
    "--hours", $Hours,
    "--limit-alerts", $LimitAlerts,
    "--sample-if-no-key", "false"
)
if ($Send.IsPresent -and $resolvedChatIdEnv) {
    $cycleArgs += @(
        "--send-board",
        "--send-quality-summary",
        "--token-env", $TokenEnv,
        "--chat-id-env", $resolvedChatIdEnv
    )
}

# The loop script block (runs inside the background PowerShell process)
$loopScript = {
    param($ProjectRoot, $PythonExe, $CycleArgs, $LogFile, $IntervalSeconds, $EnableDeltaSnapshot)
    Set-Location $ProjectRoot

    $cycleNum = 0
    while ($true) {
        $cycleNum++
        $cycleStart = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $msg = "[CYCLE $cycleNum] Starting at $cycleStart"
        Write-Output $msg
        Add-Content -Path $LogFile -Value $msg

        # v1.5B-3: Delta snapshot step (before radar cycle)
        if ($EnableDeltaSnapshot) {
            try {
                $snapMsg = "[SNAPSHOT] Writing HL position snapshots..."
                Write-Output $snapMsg
                Add-Content -Path $LogFile -Value $snapMsg
                & $PythonExe scripts/snapshot_hl_positions.py --check-delta 2>&1 | Out-File -Append $LogFile
            } catch {
                $snapErr = "[SNAPSHOT] ERROR: $_"
                Write-Output $snapErr
                Add-Content -Path $LogFile -Value $snapErr
            }
        }
        Add-Content -Path $LogFile -Value $msg

        try {
            $proc = Start-Process -FilePath $PythonExe -ArgumentList $CycleArgs `
                -NoNewWindow -Wait -PassThru
            $exitCode = $proc.ExitCode
        } catch {
            $exitCode = 1
            $errMsg = "[CYCLE $cycleNum] Process error: $_"
            Write-Output $errMsg
            Add-Content -Path $LogFile -Value $errMsg
        }

        $cycleEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $elapsed = [math]::Round(((Get-Date) - [datetime]::ParseExact($cycleStart, "yyyy-MM-dd HH:mm:ss", $null)).TotalSeconds, 1)
        $msg = "[CYCLE $cycleNum] Done at $cycleEnd (${elapsed}s, exit=$exitCode). Sleeping ${IntervalSeconds}s..."
        Write-Output $msg
        Add-Content -Path $LogFile -Value $msg

        Start-Sleep -Seconds $IntervalSeconds
    }
}

# Start the loop in a separate PowerShell process (hidden, no terminal hog)
$psArgs = @(
    "-NoProfile",
    "-NonInteractive",
    "-WindowStyle", "Hidden",
    "-Command",
    "& { $loopScript -ProjectRoot '$ProjectRoot' -PythonExe '$PythonExe' -CycleArgs (,$CycleArgs) -LogFile '$LogFile' -IntervalSeconds $IntervalSeconds -EnableDeltaSnapshot `$$EnableDeltaSnapshot }"
)

$process = Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs `
    -WindowStyle Hidden -PassThru

$process.Id | Out-File -FilePath $PidFile -Encoding utf8

$startupInfo = @"

======================================================================
  Publisher started successfully!
  PID       : $($process.Id)
  PID file  : $PidFile
  Log file  : $LogFile
  Mode      : $modeLabel
======================================================================

Commands:
  Check status : .\scripts\status_local_market_radar_loop.ps1
  View log     : Get-Content $LogFile -Tail 20
  Follow log   : Get-Content $LogFile -Wait -Tail 10
  Stop         : .\scripts\stop_local_market_radar_loop.ps1

"@
Write-Output $startupInfo
