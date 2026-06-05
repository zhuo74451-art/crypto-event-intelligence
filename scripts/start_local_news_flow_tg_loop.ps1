# start_local_news_flow_tg_loop.ps1
# Start local news-flow -> TG long-running loop.
#
# Usage:
#   .\scripts\start_local_news_flow_tg_loop.ps1                          # dry-run loop (no TG)
#   .\scripts\start_local_news_flow_tg_loop.ps1 -Send                    # real TG send
#   .\scripts\start_local_news_flow_tg_loop.ps1 -Send -IntervalSeconds 300
#   .\scripts\start_local_news_flow_tg_loop.ps1 -Once -DryRun            # one-shot test

param(
    [switch] $Send,
    [switch] $Once,
    [switch] $DryRun,
    [int]    $IntervalSeconds = 300,
    [int]    $Limit = 20,
    [int]    $LookbackMinutes = 1440
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
$RuntimeDir = Join-Path $ProjectRoot "runtime"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

$PidFile = Join-Path $RuntimeDir "local_news_flow_tg_loop.pid"
$LogFile = Join-Path $LogDir "local_news_flow_tg_loop.log"

# Prevent duplicate start
if (Test-Path $PidFile) {
    $ep = (Get-Content $PidFile -ErrorAction SilentlyContinue).Trim()
    if ($ep) {
        try { $proc = Get-Process -Id ([int]$ep) -ErrorAction SilentlyContinue; if ($proc) {
            Write-Output "ERROR: Loop already running (PID=$ep). Stop first: .\scripts\stop_local_news_flow_tg_loop.ps1"; exit 1 } } catch {}
    }
    Remove-Item $PidFile -Force
}

# Load secrets
$SecretsFile = Join-Path $ProjectRoot "config\local_secrets.ps1"
if (Test-Path $SecretsFile) { . $SecretsFile } else { Write-Output "WARNING: config\local_secrets.ps1 not found" }

$tokenOk = [bool]$env:TELEGRAM_BOT_TOKEN
$chatOk  = [bool]($env:TELEGRAM_CHAT_ID -or $env:TELEGRAM_PUBLISH_CHAT_IDS)
$sendMode = if ($Send.IsPresent -and -not $DryRun.IsPresent) { "TG_ENABLED" } else { "DRY_RUN" }
$loopMode = if ($Once.IsPresent) { "ONCE" } else { "LOOP" }

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = "python" }

$startTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$banner = @"
======================================================================
Local News Flow TG Loop - STARTING
  Time            : $startTime
  Mode            : $sendMode
  Loop            : $loopMode
  Interval        : ${IntervalSeconds}s
  Limit           : $Limit
  Lookback        : ${LookbackMinutes}min
  Token configured: $tokenOk
  Chat configured : $chatOk
  PID file        : $PidFile
  Log file        : $LogFile
======================================================================
"@
Write-Output $banner
Add-Content -Path $LogFile -Value $banner

if ($Send.IsPresent -and -not $DryRun.IsPresent) {
    if (-not $tokenOk) { Write-Output "ERROR: TELEGRAM_BOT_TOKEN not set"; exit 1 }
    if (-not $chatOk)  { Write-Output "ERROR: No chat_id set (TELEGRAM_CHAT_ID or TELEGRAM_PUBLISH_CHAT_IDS)"; exit 1 }
}

# Build the cycle script block
$cycleBlock = {
    param($ProjectRoot, $python, $Limit, $LookbackMinutes, $sendMode, $LogFile)
    Set-Location $ProjectRoot
    $rawCsv = "data/raw_news_live_incremental.csv"
    $candCsv = "data/event_candidates_live_incremental_review.csv"
    $previewMd = "results/local_news_flow_preview.md"
    $n = 0
    while ($true) {
        $n++
        $cs = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $msg = "[CYCLE $n] Start $cs"
        Write-Output $msg; Add-Content -Path $LogFile -Value $msg
        try {
            # Step 1: sync
            & $python scripts/sync_remote_tweets_incremental.py --limit $Limit --lookback-minutes $LookbackMinutes --output $rawCsv 2>&1 | Out-File -Append $LogFile
            # Step 2: import
            & $python scripts/import_raw_news_to_event_candidates.py --input $rawCsv --output $candCsv --symbol-map data/symbol_map.csv --limit $Limit 2>&1 | Out-File -Append $LogFile
            # Step 3: preview
            & $python -c "
import csv; from pathlib import Path; from datetime import datetime, timedelta, timezone
ROOT=Path('.').resolve(); CN=timezone(timedelta(hours=8))
now=datetime.now(CN).strftime('%Y-%m-%d %H:%M:%S UTC+8')
raw_lines=len((ROOT/'$rawCsv').read_text(encoding='utf-8-sig').strip().splitlines())-1 if (ROOT/'$rawCsv').exists() else 0
rows=list(csv.DictReader(open(ROOT/'$candCsv',encoding='utf-8-sig'))) if (ROOT/'$candCsv').exists() else []
lines=['# 本地快讯流预览','',f'生成时间：{now}','数据来源：远程 tweets.db -> 本地增量同步','','---','',f'## 摘要','',f'- 本轮同步快讯：{raw_count} 条',f'- 候选事件：{len(rows)} 条','','---','','## 候选事件预览','']
for i,r in enumerate(rows[:10],1):
    lines.append(f'### {i}. {r.get(\"title\",\"?\")[:100]}')
    lines.append(f'- 来源: {r.get(\"source\",\"?\")}  |  时间: {r.get(\"published_at_china\",\"?\")}  |  资产: {r.get(\"candidate_asset_symbol\",\"?\")}  |  类型: {r.get(\"candidate_event_type\",\"?\")}  |  重要度: {r.get(\"candidate_importance\",\"?\")}  |  决策: {r.get(\"review_decision\",\"pending\")}')
    lines.append('')
lines.extend(['---','','> 仅作市场结构与链上情报观察，不构成任何交易建议。',''])
(ROOT/'$previewMd').write_text('\n'.join(lines),encoding='utf-8')
print(f'Preview: {len(rows)} candidates, {min(10,len(rows))} preview items')
" 2>&1 | Out-File -Append $LogFile
            # Step 4: TG send
            if ($sendMode -eq "TG_ENABLED") {
                & $python scripts/send_local_news_flow_preview_to_tg.py --send 2>&1 | Out-File -Append $LogFile
            }
        } catch {
            $err = "[CYCLE $n] ERROR: $_"
            Write-Output $err; Add-Content -Path $LogFile -Value $err
        }
        if ($n -eq 1) { break }  # $once is handled by caller via -Once
        $ce = Get-Date -Format "HH:mm:ss"
        Add-Content -Path $LogFile -Value "[CYCLE $n] Done $ce, sleeping ${IntervalSeconds}s"
        Start-Sleep -Seconds $IntervalSeconds
    }
}

if ($Once.IsPresent) {
    Write-Output "Running single cycle (--Once)..."
    & $cycleBlock -ProjectRoot $ProjectRoot -python $python -Limit $Limit -LookbackMinutes $LookbackMinutes -sendMode $sendMode -LogFile $LogFile
    Write-Output "One-shot complete."
    exit 0
}

# Background start
$psArgs = @("-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", "& { $cycleBlock }")
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList $psArgs -WindowStyle Hidden -PassThru
$proc.Id | Out-File -FilePath $PidFile -Encoding utf8

Write-Output ""
Write-Output "Loop started (PID=$($proc.Id))."
Write-Output "  Status : .\scripts\status_local_news_flow_tg_loop.ps1"
Write-Output "  Stop   : .\scripts\stop_local_news_flow_tg_loop.ps1"
Write-Output "  Log    : Get-Content $LogFile -Tail 20"
