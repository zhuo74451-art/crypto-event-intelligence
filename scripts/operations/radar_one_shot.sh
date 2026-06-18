#!/usr/bin/env bash
# radar_one_shot.sh -- systemd ExecStart for one-shot market radar cycle
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")"; cd ..; cd ..; pwd)"
cd "$SCRIPT_DIR"

LOCK_PATH="${V09_RADAR_LOCK_PATH:-$SCRIPT_DIR/runtime/radar_one_shot.lock}"
mkdir -p "$(dirname "$LOCK_PATH")"
exec 200>"$LOCK_PATH"
if ! flock -n 200; then echo "[radar-one-shot] LOCK HELD -- exiting"; exit 0; fi

STOP_PATH="${V09_RADAR_STOP_MARKER_PATH:-$SCRIPT_DIR/runtime/radar_one_shot.stop}"
if [ -f "$STOP_PATH" ]; then echo "[radar-one-shot] STOP MARKER -- exiting"; rm -f "$STOP_PATH"; exit 0; fi

NO_SEND="${V09_RADAR_NO_SEND:-true}"
ARGS=(--hours "${V09_RADAR_HOURS:-24}" --limit-alerts "${V09_RADAR_LIMIT_ALERTS:-100}")
ARGS+=(--sample-if-no-key "${V09_RADAR_SAMPLE_IF_NO_KEY:-false}" --load-local-secrets "${V09_RADAR_LOAD_LOCAL_SECRETS:-false}")
ARGS+=(--token-env TELEGRAM_BOT_TOKEN --chat-id-env TELEGRAM_PUBLISH_CHAT_IDS)
ARGS+=(--evaluate-alert-outcomes "${V09_RADAR_EVALUATE_ALERT_OUTCOMES:-true}")
ARGS+=(--refresh-v11-quality-reports "${V09_RADAR_REFRESH_V11_QUALITY_REPORTS:-true}")

if [ "$NO_SEND" != "true" ]; then
  if [ "${V09_RADAR_SEND_BOARD:-true}" = "true" ]; then ARGS+=(--send-board); fi
  if [ "${V09_RADAR_SEND_QUALITY_SUMMARY:-true}" = "true" ]; then ARGS+=(--send-quality-summary); fi
  ARGS+=(--quality-summary-min-computed "${V09_RADAR_QUALITY_SUMMARY_MIN_COMPUTED:-1}")
fi

TIMEOUT="${V09_RADAR_TIMEOUT_SECONDS:-3300}"
echo "[radar-one-shot] starting (NO_SEND=$NO_SEND, timeout=${TIMEOUT}s)"
set +e
timeout --kill-after=30 "$TIMEOUT" python3 -X utf8 scripts/run_v09_market_radar_cycle.py "${ARGS[@]}"
EXIT_CODE=$?; set -e
[ $EXIT_CODE -eq 124 ] && echo "[radar-one-shot] TIMEOUT"
[ $EXIT_CODE -ne 0 ] && [ $EXIT_CODE -ne 124 ] && echo "[radar-one-shot] FAILED exit=$EXIT_CODE"
[ $EXIT_CODE -eq 0 ] && echo "[radar-one-shot] completed"
exit $EXIT_CODE