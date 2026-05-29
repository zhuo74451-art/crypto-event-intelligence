#!/usr/bin/env bash
set -euo pipefail
cd /opt/crypto-event-intel-watchers

read_env_key() {
  python3 - "$1" "$2" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
key = sys.argv[2]
if not path.exists():
    sys.exit(0)
for raw in path.read_text(encoding='utf-8-sig', errors='replace').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    if k.startswith('export '):
        k = k[7:].strip()
    if k == key:
        print(v.strip().strip('"').strip("'"))
        break
PY
}

export TELEGRAM_BOT_TOKEN="$(read_env_key /opt/x-monitor/current/.env TELEGRAM_BOT_TOKEN)"
export TELEGRAM_PUBLISH_CHAT_IDS="$(read_env_key /opt/x-monitor/current/.env TELEGRAM_PUBLISH_CHAT_IDS)"
export ETHERSCAN_API_KEY="$(read_env_key /opt/crypto-event-intel-watchers/.env ETHERSCAN_API_KEY)"

INTERVAL_SECONDS="${V09_RADAR_INTERVAL_SECONDS:-3600}"

while true; do
  python3 -X utf8 scripts/run_v09_market_radar_cycle.py \
    --hours 24 \
    --limit-alerts 100 \
    --sample-if-no-key false \
    --send-board \
    --send-quality-summary \
    --quality-summary-min-computed 1 \
    --token-env TELEGRAM_BOT_TOKEN \
    --chat-id-env TELEGRAM_PUBLISH_CHAT_IDS \
    --load-local-secrets false || true
  sleep "$INTERVAL_SECONDS"
done
