# Copy this file to config/local_secrets.ps1 and fill values locally.
# Do not commit or send the real file. It is ignored by .gitignore.

$env:ETHERSCAN_API_KEY = "replace_with_etherscan_api_key"

# Use a newly generated Telegram bot token. Revoke any token exposed in screenshots/chat.
$env:TELEGRAM_BOT_TOKEN = "replace_with_new_telegram_bot_token"
$env:TELEGRAM_CHAT_ID = "replace_with_telegram_chat_id"
