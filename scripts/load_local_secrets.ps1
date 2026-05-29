param(
  [string]$Path = "config/local_secrets.ps1"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path)) {
  Write-Host "Local secret file not found: $Path"
  Write-Host "Create it from config/secrets.example.ps1, then fill local values."
  exit 1
}

. $Path

$required = @("ETHERSCAN_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
$missing = @()
foreach ($name in $required) {
  $value = [Environment]::GetEnvironmentVariable($name, "Process")
  if ([string]::IsNullOrWhiteSpace($value) -or $value.StartsWith("replace_with_")) {
    $missing += $name
  }
}

if ($missing.Count -gt 0) {
  Write-Host "Loaded local secret file, but these values are missing or placeholders:"
  foreach ($name in $missing) {
    Write-Host " - $name"
  }
  exit 2
}

Write-Host "Loaded local secrets into current PowerShell process:"
Write-Host " - ETHERSCAN_API_KEY"
Write-Host " - TELEGRAM_BOT_TOKEN"
Write-Host " - TELEGRAM_CHAT_ID"
