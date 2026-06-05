# run_local_news_flow_once.ps1
# Single-run: sync remote tweets → import to event candidates → generate preview.
#
# Usage:
#   .\scripts\run_local_news_flow_once.ps1                    # dry-run sync + full import
#   .\scripts\run_local_news_flow_once.ps1 -LiveSync          # real sync (updates state)
#   .\scripts\run_local_news_flow_once.ps1 -Limit 50 -LookbackMinutes 60

param(
    [switch] $LiveSync,
    [int]    $Limit = 100,
    [int]    $LookbackMinutes = 120
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptRoot
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "local_news_flow_once.log"
$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Load secrets (for SSH key agent if needed)
$SecretsFile = Join-Path $ProjectRoot "config\local_secrets.ps1"
if (Test-Path $SecretsFile) {
    . $SecretsFile
    Write-Output "[OK] Loaded config/local_secrets.ps1"
} else {
    Write-Output "[WARN] config/local_secrets.ps1 not found — SSH may fail without key agent"
}

$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python" }

$sep = "=" * 60
$banner = @"
$sep
Local News Flow - Single Run
  Start time     : $StartTime
  LiveSync       : $($LiveSync.IsPresent)
  Limit          : $Limit
  LookbackMinutes: $LookbackMinutes
  Log file       : $LogFile
$sep
"@
Write-Output $banner
Add-Content -Path $LogFile -Value $banner

# ── Step 1: Sync remote tweets ──────────────────────────────
$syncArgs = @(
    "scripts/sync_remote_tweets_incremental.py",
    "--limit", $Limit,
    "--lookback-minutes", $LookbackMinutes
)
if (-not $LiveSync.IsPresent) {
    $syncArgs += "--dry-run"
}

Write-Output "[STEP 1/2] Syncing remote tweets..."
$syncCmd = "$PythonExe $($syncArgs -join ' ')"
Write-Output "[CMD] $syncCmd"
Add-Content -Path $LogFile -Value "[STEP 1/2] $syncCmd"

$syncExit = 0
$syncOutput = ""
try {
    $syncResult = & $PythonExe $syncArgs 2>&1
    $syncExit = $LASTEXITCODE
    $syncOutput = ($syncResult | Out-String).Trim()
    Write-Output $syncOutput
    Add-Content -Path $LogFile -Value $syncOutput
} catch {
    $syncExit = 1
    $errMsg = "Sync error: $_"
    Write-Output $errMsg
    Add-Content -Path $LogFile -Value "[ERROR] $errMsg"
}

if ($syncExit -ne 0) {
    $msg = "Sync failed (exit=$syncExit). Check SSH connectivity and remote host."
    Write-Output $msg
    Add-Content -Path $LogFile -Value "[ERROR] $msg"
    Write-Output ""
    Write-Output "Troubleshooting:"
    Write-Output "  - Is SSH key agent running? (ssh-add -l)"
    Write-Output "  - Can you reach the server? (ssh root@43.98.174.247 echo ok)"
    Write-Output "  - Run with -LiveSync only after SSH is confirmed working."
    exit 1
}

# ── Step 2: Import to event candidates ──────────────────────
$incrementalCsv = Join-Path $ProjectRoot "data\raw_news_live_incremental.csv"
if (-not (Test-Path $incrementalCsv)) {
    if ($LiveSync.IsPresent) {
        Write-Output "[WARN] No new tweets synced (0 rows). Skipping import."
    } else {
        Write-Output "[DRY-RUN] No CSV written (dry-run mode). Skipping import."
    }
    exit 0
}

$candidatesCsv = Join-Path $ProjectRoot "data\event_candidates_live_incremental_review.csv"
$importArgs = @(
    "scripts/import_raw_news_to_event_candidates.py",
    "--input", $incrementalCsv,
    "--output", $candidatesCsv
)

Write-Output ""
Write-Output "[STEP 2/2] Importing to event candidates..."
$importCmd = "$PythonExe $($importArgs -join ' ')"
Write-Output "[CMD] $importCmd"
Add-Content -Path $LogFile -Value "[STEP 2/2] $importCmd"

$importExit = 0
try {
    $importResult = & $PythonExe $importArgs 2>&1
    $importExit = $LASTEXITCODE
    Write-Output ($importResult | Out-String).Trim()
    Add-Content -Path $LogFile -Value ($importResult | Out-String).Trim()
} catch {
    $importExit = 1
    $errMsg = "Import error: $_"
    Write-Output $errMsg
    Add-Content -Path $LogFile -Value "[ERROR] $errMsg"
}

if ($importExit -ne 0) {
    Write-Output "Import failed (exit=$importExit)."
    exit 1
}

# ── Build preview ────────────────────────────────────────────
Write-Output ""
Write-Output "Building preview..."
$previewPath = Join-Path $ProjectRoot "results\local_news_flow_preview.md"
$previewDir = Split-Path -Parent $previewPath
New-Item -ItemType Directory -Force -Path $previewDir | Out-Null

$previewContent = @"
# 本地快讯流预览

生成时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC+8')
数据来源：远程 tweets.db → 本地增量同步

---

## 同步摘要

- 同步新快讯数：待统计
- 输入文件：data/raw_news_live_incremental.csv
- 候选文件：data/event_candidates_live_incremental_review.csv

---

## 候选事件预览（最多 10 条）

"@

# Try to read candidates CSV and extract preview
if (Test-Path $candidatesCsv) {
    $candidatePreview = & $PythonExe -c @"
import csv
rows = list(csv.DictReader(open(r'$candidatesCsv', encoding='utf-8-sig')))
print(f'候选事件总数: {len(rows)}')
print()
if rows:
    cols = ['title','source','published_at_china','candidate_asset_symbol','candidate_event_type','candidate_importance','review_decision']
    available = [c for c in cols if c in rows[0]]
    print(f'字段: {available}')
    print()
    for i, r in enumerate(rows[:10]):
        print(f'### {i+1}. {r.get(\"title\",\"?\")[:100]}')
        print(f'- 来源: {r.get(\"source\",\"?\")}')
        print(f'- 时间: {r.get(\"published_at_china\",\"?\")}')
        print(f'- 资产: {r.get(\"candidate_asset_symbol\",\"?\")}')
        print(f'- 类型: {r.get(\"candidate_event_type\",\"?\")}')
        print(f'- 重要度: {r.get(\"candidate_importance\",\"?\")}')
        print(f'- 决策: {r.get(\"review_decision\",\"?\")}')
        print()
"@ 2>&1
    $previewContent += $candidatePreview
} else {
    $previewContent += "`n(候选文件未生成，请检查 import 步骤)`n"
}

$previewContent += @"

---

> ⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。

"@

$previewContent | Out-File -FilePath $previewPath -Encoding utf8
Write-Output "Preview written: $previewPath"

$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$summary = @"

--- Run Complete ---
  End time : $EndTime
  Exit code: 0
  Preview  : $previewPath
"@
Write-Output $summary
Add-Content -Path $LogFile -Value $summary
