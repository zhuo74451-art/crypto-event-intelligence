param(
    [switch]$OpenCursor = $true
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

python scripts\generate_cursor_prompt.py --copy

if ($OpenCursor) {
    $cursor = Get-Command cursor -ErrorAction SilentlyContinue
    if ($cursor) {
        cursor $ProjectRoot
        Write-Host "Opened Cursor at $ProjectRoot"
    } else {
        Write-Host "Cursor CLI not found. Prompt is copied; open Cursor manually."
    }
}

Write-Host "Cursor prompt copied to clipboard."
Write-Host "Paste it into Cursor chat."
