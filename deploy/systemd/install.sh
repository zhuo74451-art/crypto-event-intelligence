#!/usr/bin/env bash
# install.sh -- Install crypto-event-intel-radar systemd units
# Usage: bash install.sh [--release-path /path/to/release]
set -euo pipefail

RELEASE_PATH="${1:-/opt/crypto-event-intel-watchers/current}"
UNIT_DIR="/etc/systemd/system"

echo "[install] Release path: $RELEASE_PATH"

# Validate release structure
for f in "$RELEASE_PATH/scripts/operations/radar_one_shot.sh" \
         "$RELEASE_PATH/deploy/systemd/crypto-event-intel-radar.service" \
         "$RELEASE_PATH/deploy/systemd/crypto-event-intel-radar.timer"; do
    if [ ! -f "$f" ]; then echo "[install] MISSING: $f"; exit 1; fi
done

# Create data directories (outside release tree)
mkdir -p /opt/crypto-event-intel-watchers/{runtime,logs,results}

# Symlink current -> release (idempotent)
ln -snf "$RELEASE_PATH" /opt/crypto-event-intel-watchers/current

# Symlink unit files
ln -sf /opt/crypto-event-intel-watchers/current/deploy/systemd/crypto-event-intel-radar.service \
      "$UNIT_DIR/crypto-event-intel-radar.service"
ln -sf /opt/crypto-event-intel-watchers/current/deploy/systemd/crypto-event-intel-radar.timer \
      "$UNIT_DIR/crypto-event-intel-radar.timer"

systemctl daemon-reload

if [ ! -f /opt/crypto-event-intel-watchers/.env ]; then
    echo "[install] WARNING: /opt/crypto-event-intel-watchers/.env not found"
    echo "[install] Copy deploy/systemd/env.radar.example and fill in secrets, then chmod 0400"
fi

echo "[install] Done. Timer is NOT automatically enabled."
echo "[install] To enable: systemctl enable --now crypto-event-intel-radar.timer"
echo "[install] To check:  systemctl status crypto-event-intel-radar.{service,timer}"
echo "[install] Logs:      journalctl -u crypto-event-intel-radar.service -n 50 -f"
echo "[install] One-shot:  systemctl start crypto-event-intel-radar.service"