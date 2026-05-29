param(
  [string]$PromptPath = "docs/CLAUDE_MANUAL_REDUCTION_PROMPT.md",
  [string]$OutputPath = "results/v06_claude_manual_reduction_response.md",
  [string]$Model = "anthropic/claude-sonnet-4.5",
  [int]$TimeoutSec = 120,
  [int]$MaxTokens = 3000
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) {
  Write-Error "OPENROUTER_API_KEY is missing in environment."
}

if (-not (Test-Path -LiteralPath $PromptPath)) {
  Write-Error "Prompt file not found: $PromptPath"
}

$prompt = Get-Content -LiteralPath $PromptPath -Raw -Encoding UTF8
$body = @{
  model = $Model
  temperature = 0.2
  max_tokens = $MaxTokens
  messages = @(
    @{
      role = "user"
      content = $prompt
    }
  )
} | ConvertTo-Json -Depth 10

$headers = @{
  "Authorization" = "Bearer $env:OPENROUTER_API_KEY"
  "Content-Type" = "application/json"
}

$response = Invoke-RestMethod `
  -Method Post `
  -Uri "https://openrouter.ai/api/v1/chat/completions" `
  -Headers $headers `
  -Body $body `
  -TimeoutSec $TimeoutSec

$content = $response.choices[0].message.content
$dir = Split-Path -Parent $OutputPath
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
  New-Item -ItemType Directory -Path $dir | Out-Null
}
$content | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "wrote Claude response to $OutputPath"
