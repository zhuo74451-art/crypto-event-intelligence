# Local Secret Setup

Do not write real API keys or Telegram tokens into code, README, runbooks, CSV files, or results.

Use a local ignored file:

```powershell
Copy-Item config/secrets.example.ps1 config/local_secrets.ps1
notepad config/local_secrets.ps1
```

Fill these values:

```powershell
$env:ETHERSCAN_API_KEY = "..."
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID = "..."
```

Load them into the current PowerShell session:

```powershell
.\scripts\load_local_secrets.ps1
```

Run live watcher:

```powershell
python scripts/run_v07_first_hand_watchers.py --hours 24 --limit-alerts 100
```

Dry-run one TG draft:

```powershell
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1
```

Send one TG test message:

```powershell
python scripts/send_tg_draft_test.py --input data/tg_drafts_v07_watcher_private_pilot.csv --limit 1 --send
```

Important:

- Revoke the Telegram bot token that was exposed in the screenshot/chat.
- Use the newly generated Telegram token in `config/local_secrets.ps1`.
- `config/local_secrets.ps1` is ignored by `.gitignore`.
- Run secret scan after any secret-related changes:

```powershell
python scripts/check_secret_leaks.py
```
