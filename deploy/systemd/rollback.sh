#!/usr/bin/env bash
# rollback.sh -- Atomically switch current symlink to a previous release
# Usage: bash rollback.sh [--target v1.0.0]
set -euo pipefail

RELEASES_DIR="/opt/crypto-event-intel-watchers/releases"
CURRENT_LINK="/opt/crypto-event-intel-watchers/current"

if [ "${1:-}" = "--target" ] && [ -n "${2:-}" ]; then
    TARGET="$2"
else
    # Default to second-newest release
    TARGET=$(ls -1 "$RELEASES_DIR" 2>/dev/null | sort -r | sed -n '2p')
    if [ -z "$TARGET" ]; then
        echo "[rollback] No previous release found in $RELEASES_DIR"
        exit 1
    fi
fi

TARGET_PATH="$RELEASES_DIR/$TARGET"
if [ ! -d "$TARGET_PATH" ]; then
    echo "[rollback] Target release not found: $TARGET_PATH"
    echo "[rollback] Available releases:"
    ls -1 "$RELEASES_DIR" 2>/dev/null || echo "  (none)"
    exit 1
fi

# Validate target structure
for f in scripts/operations/radar_one_shot.sh deploy/systemd/crypto-event-intel-radar.service; do
    if [ ! -f "$TARGET_PATH/$f" ]; then
        echo "[rollback] Incomplete release -- missing $f in $TARGET_PATH"
        exit 1
    fi
done

OLD_TARGET=$(readlink "$CURRENT_LINK" 2>/dev/null || echo "(none)")
ln -snf "$TARGET_PATH" "$CURRENT_LINK"
systemctl daemon-reload

echo "[rollback] Switched: $OLD_TARGET -> $TARGET_PATH"
echo "[rollback] Run 'systemctl status crypto-event-intel-radar.service' to verify"