#!/usr/bin/env bash
# uninstall.sh -- Remove crypto-event-intel-radar systemd units
# Usage: bash uninstall.sh [--clean-data]
set -euo pipefail

CLEAN_DATA=false
if [ "${1:-}" = "--clean-data" ]; then CLEAN_DATA=true; fi

UNIT_DIR="/etc/systemd/system"

echo "[uninstall] Stopping and disabling timer..."
systemctl stop crypto-event-intel-radar.timer 2>/dev/null || true
systemctl disable crypto-event-intel-radar.timer 2>/dev/null || true

echo "[uninstall] Removing unit symlinks..."
rm -f "$UNIT_DIR/crypto-event-intel-radar.service"
rm -f "$UNIT_DIR/crypto-event-intel-radar.timer"
systemctl daemon-reload

if [ "$CLEAN_DATA" = true ]; then
    echo "[uninstall] Removing runtime data..."
    rm -rf /opt/crypto-event-intel-watchers/runtime
    rm -rf /opt/crypto-event-intel-watchers/logs
    rm -rf /opt/crypto-event-intel-watchers/results
    read -rp "Remove .env file? (y/N): " CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        rm -f /opt/crypto-event-intel-watchers/.env
    fi
fi

echo "[uninstall] Done. Releases and current symlink preserved at /opt/crypto-event-intel-watchers/"