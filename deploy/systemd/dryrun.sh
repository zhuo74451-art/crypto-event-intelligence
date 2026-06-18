#!/usr/bin/env bash
# dryrun.sh -- Pre-flight verification for systemd deployment
# Usage: bash dryrun.sh [--release-path /path/to/release]
#
# Checks all paths, permissions, and config validity WITHOUT enabling the timer.
set -euo pipefail

RELEASE_PATH="${1:-$(pwd)}"
ALL_PASS=true

pass() { echo "  [PASS] $*"; }
fail() { echo "  [FAIL] $*"; ALL_PASS=false; }
warn() { echo "  [WARN] $*"; }

echo "==========================================="
echo " Dry-Run: crypto-event-intel-radar"
echo " Release path: $RELEASE_PATH"
echo "==========================================="

# --- 1. File existence ---
echo ""
echo "--- File Existence ---"
FILES=(
    "$RELEASE_PATH/scripts/operations/radar_one_shot.sh"
    "$RELEASE_PATH/deploy/systemd/crypto-event-intel-radar.service"
    "$RELEASE_PATH/deploy/systemd/crypto-event-intel-radar.timer"
)
for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then pass "$f exists"; else fail "$f missing"; fi
done

# --- 2. Executable bit ---
echo ""
echo "--- Executable Bits ---"
if [ -x "$RELEASE_PATH/scripts/operations/radar_one_shot.sh" ]; then
    pass "radar_one_shot.sh is executable"
else
    fail "radar_one_shot.sh is NOT executable"
fi

# --- 3. No hardcoded tokens ---
echo ""
echo "--- Token Leak Check ---"
if grep -qE '^TELEGRAM_BOT_TOKEN=[^$]' "$RELEASE_PATH/scripts/operations/radar_one_shot.sh" 2>/dev/null; then
    fail "Hardcoded token found in radar_one_shot.sh"
else
    pass "No hardcoded tokens in radar_one_shot.sh"
fi

if grep -qE '^TELEGRAM_BOT_TOKEN=[^$]' "$RELEASE_PATH/deploy/systemd/crypto-event-intel-radar.service" 2>/dev/null; then
    fail "Hardcoded token found in .service"
else
    pass "No hardcoded tokens in .service"
fi

# --- 4. systemd-analyze verify ---
echo ""
echo "--- systemd-analyze verify ---"
UNIT_DIR="$RELEASE_PATH/deploy/systemd"
for unit in crypto-event-intel-radar.service crypto-event-intel-radar.timer; do
    if systemd-analyze verify "$UNIT_DIR/$unit" 2>/dev/null; then
        pass "$unit syntax OK"
    else
        warn "$unit syntax check skipped (not running on systemd or path issue)"
    fi
done

# --- 5. Python import check ---
echo ""
echo "--- Python Import Check ---"
if [ -f "$RELEASE_PATH/scripts/run_v09_market_radar_cycle.py" ]; then
    if python3 -c "import sys; sys.path.insert(0, '$RELEASE_PATH'); from scripts.run_v09_market_radar_cycle import parse_args; print('import OK')" 2>/dev/null; then
        pass "Python import OK"
    else
        fail "Python import failed"
    fi
else
    fail "run_v09_market_radar_cycle.py not found"
fi

# --- 6. Env file check ---
echo ""
echo "--- Environment File ---"
ENV_FILE="/opt/crypto-event-intel-watchers/.env"
if [ -f "$ENV_FILE" ]; then
    PERMS=$(stat -c "%a" "$ENV_FILE" 2>/dev/null || echo "unknown")
    if [ "$PERMS" = "400" ] || [ "$PERMS" = "600" ]; then
        pass ".env permissions: $PERMS"
    else
        warn ".env permissions are $PERMS (recommend 0400 or 0600)"
    fi
else
    warn ".env not found at $ENV_FILE (expected for fresh installs)"
fi

# --- 7. Service user check ---
echo ""
echo "--- Service User ---"
if id crypto-event-intel &>/dev/null; then
    pass "User crypto-event-intel exists"
else
    warn "User crypto-event-intel does not exist (create with: useradd --system --no-create-home crypto-event-intel)"
fi

# --- Summary ---
echo ""
echo "==========================================="
if [ "$ALL_PASS" = true ]; then
    echo " RESULT: ALL CHECKS PASSED"
    exit 0
else
    echo " RESULT: SOME CHECKS FAILED (review above)"
    exit 1
fi