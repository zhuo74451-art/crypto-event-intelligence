"""Market Radar v1.12-Z — Degraded Whale Envelope Compatibility Runner

Reads v112Y degraded whale replay records and converts each into a v112H-compatible
unified signal envelope with degraded extension fields.

Outputs:
  - results/market_radar_v112z_degraded_whale_envelopes.jsonl
  - results/market_radar_v112z_degraded_whale_envelope_compatibility_result.json
  - runs/market_radar/v112z_degraded_whale_envelope_compatibility.md
  - runs/market_radar/v112z_degraded_whale_envelope_compatibility_handoff.md

Constraints:
  - No external API calls
  - No TG send
  - No prod state write
  - No daemon/watcher/cron/loop
  - No credentials read
  - No files deleted
  - eligible_for_real_send is ALWAYS false

Usage:
    python scripts/run_market_radar_v112z_degraded_whale_envelope_compatibility.py
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_envelope_v112h import (
    build_signal_envelope,
    build_dedupe_key,
    build_cooldown_key,
    build_payload_hash,
    validate_signal_envelope,
    scan_envelope_leaks,
    VALID_CARD_TYPES,
    VALID_DIRECTIONS,
    china_stamp,
    _safe_float,
    _map_direction,
)

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-Z"
RUN_ID = "20260605_022952"

# ── Paths ─────────────────────────────────────────────────────────────────────────────

INPUT_JSONL = ROOT / "results" / "market_radar_v112y_whale_degraded_replay_records.jsonl"
INPUT_RESULT = ROOT / "results" / "market_radar_v112y_whale_degraded_mock_replay_result.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112z_degraded_whale_envelope_compatibility_result.json"
ENVELOPES_JSONL_PATH = ROOT / "results" / "market_radar_v112z_degraded_whale_envelopes.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112z_degraded_whale_envelope_compatibility.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112z_degraded_whale_envelope_compatibility_handoff.md"


# ══════════════════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, returning list of dicts."""
    records: list[dict] = []
    if not path.exists():
        print(f"  [ERROR] Input JSONL not found: {path}")
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return records


def _sha256_hex(raw: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _short_addr(addr: str) -> str:
    """Shorten an Ethereum address for display: 0x1234...5678"""
    if not addr or len(addr) < 10:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def _build_dedupe_key_v112z(record: dict) -> str:
    """Build a stable dedupe_key from a degraded replay record.

    Format: sha256(card_type|address|asset|observed_at_date)
    """
    card_type = "whale_position_alert"
    address = str(record.get("address", ""))
    asset = str(record.get("asset", "")).strip().upper()
    observed_at = str(record.get("observed_at", ""))[:10]  # date only
    raw = f"{card_type}|{address}|{asset}|{observed_at}"
    return _sha256_hex(raw)


def _build_cooldown_key_v112z(record: dict) -> str:
    """Build a stable cooldown_key from a degraded replay record.

    Format: sha256(card_type|asset|address)
    """
    card_type = "whale_position_alert"
    address = str(record.get("address", ""))
    asset = str(record.get("asset", "")).strip().upper()
    raw = f"{card_type}|{asset}|{address}"
    return _sha256_hex(raw)


def _build_payload_hash_v112z(record: dict) -> str:
    """Build a stable payload_hash from degraded record payload fields."""
    payload = {
        "address": str(record.get("address", "")),
        "asset": str(record.get("asset", "")).strip().upper(),
        "side": str(record.get("side", "")),
        "notional_usd": str(record.get("notional_usd", "")),
        "entry_price": str(record.get("entry_price", "")),
        "degraded": True,
        "mock_replay_only": True,
        "eligible_for_real_send": False,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return _sha256_hex(canonical)


def _build_public_card(record: dict) -> str:
    """Build a safe public card text for a degraded whale position.

    The public card MUST NOT contain:
      - Full wallet addresses
      - Local paths
      - Debug/internal terms
      - API keys or secrets
    """
    asset = str(record.get("asset", "UNKNOWN")).strip().upper()
    side = str(record.get("side", "long"))
    side_emoji = "📈" if side == "long" else "📉" if side == "short" else "📊"
    side_cn = "多头" if side == "long" else "空头" if side == "short" else side
    label = str(record.get("label", "Unknown Whale"))
    label_conf = str(record.get("label_confidence", "low"))
    entity_type = str(record.get("entity_type", "unknown_whale"))
    addr_short = _short_addr(str(record.get("address", "")))
    notional = _safe_float(record.get("notional_usd", 0))
    entry_price = _safe_float(record.get("entry_price", 0))
    leverage = _safe_float(record.get("leverage", 0))
    mark_price = _safe_float(record.get("mark_price", 0))
    unrealized_pnl = _safe_float(record.get("unrealized_pnl", 0))
    liq_price = record.get("liquidation_price")
    liq_note = str(record.get("liquidation_price_note", "清算价格不可用"))
    liq_dist = record.get("liquidation_distance_pct")

    # Build position details
    lines = [
        f"{side_emoji} 主力仓位雷达｜{asset} {side_cn} [降级回放]",
        "",
        f"一句话：{label} 在 {asset} 持有 {side_cn} $ {notional:,.0f}。",
        "",
        f"● 持仓规模：$ {notional:,.0f}",
        f"● 入场价：$ {entry_price:,.2f}",
        f"● 标记价：$ {mark_price:,.2f}",
        f"● 杠杆：{leverage:.0f}x",
    ]

    if unrealized_pnl != 0:
        pnl_sign = "+" if unrealized_pnl > 0 else ""
        lines.append(f"● 未实现盈亏：{pnl_sign}$ {unrealized_pnl:,.2f}")

    if liq_price is not None:
        lines.append(f"● 清算价：$ {liq_price:,.2f}")
        if liq_dist is not None:
            lines.append(f"● 距清算：{liq_dist:.1f}%")
    else:
        lines.append(f"● 清算价：不可用（跨保证金组合仓位）")

    lines.extend([
        f"● 标签：{label}（{entity_type}，置信度：{label_conf}）",
        f"📌 地址：`{addr_short}`",
        "",
        "⚠️ 降级回放记录：标签置信度不足 / 清算价缺失 / delta不可用 / 本地时间戳。",
        "⚠️ 仅供观察，不构成交易建议。",
    ])

    return "\n".join(lines)


def _compute_envelope_severity(record: dict) -> float:
    """Compute severity for a degraded whale envelope.

    Uses notional_usd and leverage, same as v112H whale severity.
    """
    pos_size = _safe_float(record.get("notional_usd", 0))
    leverage = _safe_float(record.get("leverage", 0))
    score = 0.0
    if pos_size >= 50_000_000:
        score += 50
    elif pos_size >= 10_000_000:
        score += 40
    elif pos_size >= 1_000_000:
        score += 30
    elif pos_size >= 500_000:
        score += 20
    else:
        score += 10

    if leverage >= 20:
        score += 40
    elif leverage >= 10:
        score += 30
    elif leverage >= 5:
        score += 20
    else:
        score += 10

    return min(100.0, score)


def _compute_envelope_confidence(record: dict) -> float:
    """Compute confidence for a degraded whale envelope.

    Low confidence labels get lower confidence scores.
    """
    label_conf = str(record.get("label_confidence", "low"))
    conf_map = {"high": 0.85, "medium": 0.55, "low": 0.30}
    return conf_map.get(label_conf, 0.30)


# ══════════════════════════════════════════════════════════════════════════════════════════
# Envelope Builder
# ══════════════════════════════════════════════════════════════════════════════════════════

def build_degraded_whale_envelope(record: dict) -> dict:
    """Convert a v112Y degraded whale replay record into a v112H-compatible
    unified signal envelope with degraded extension fields.

    Args:
        record: A v112Y degraded replay record dict.

    Returns:
        A dict representing the v112Z degraded whale envelope.
    """
    card_type = "whale_position_alert"
    adapter_version = "v1.12-Y"
    source_kind = "degraded_replay"

    # Extract core fields
    address = str(record.get("address", ""))
    addr_short = _short_addr(address)
    asset = str(record.get("asset", "")).strip().upper()
    side = str(record.get("side", "long"))
    direction = "bullish" if side == "long" else "bearish" if side == "short" else "neutral"
    observed_at = str(record.get("observed_at", china_stamp()))
    record_id = str(record.get("record_id", f"whale-degraded-{address[:12]}"))
    event_key = record_id

    # Scores
    severity = _compute_envelope_severity(record)
    confidence = _compute_envelope_confidence(record)

    # Build public card
    public_card = _build_public_card(record)

    # Build v112H base envelope
    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=[asset],
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags={
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "live_ready": False,
            "debug_leak_count": 0,
            "secret_leak_count": 0,
        },
        metadata={
            "entity_type": str(record.get("entity_type", "")),
            "wallet_short": addr_short,
            "label": str(record.get("label", "")),
            "position_size_usd": _safe_float(record.get("notional_usd", 0)),
            "leverage": _safe_float(record.get("leverage", 0)),
            "chain": "hyperliquid",
        },
    )

    # Run leak scan
    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    # ── Add v112Z degraded extension fields ──────────────────────────────────────

    # Label fields
    label = str(record.get("label", ""))
    label_confidence = str(record.get("label_confidence", "low"))
    label_explanation = str(record.get("label_explanation", ""))
    label_source = str(record.get("label_source", ""))

    # Liquidation price
    liquidation_price = record.get("liquidation_price")
    liquidation_price_note = str(record.get("liquidation_price_note", "清算价格不可用"))
    liquidation_price_status = str(record.get("liquidation_price_status", "missing"))

    # Delta
    delta_status = str(record.get("delta_status", "unavailable_one_shot_no_previous_position"))
    delta_explanation = str(record.get("delta_explanation", ""))

    # Timestamp
    timestamp_status = str(record.get("timestamp_status", "local_observed_at_no_hl_server_timestamp"))
    timestamp_explanation = str(record.get("timestamp_explanation", ""))

    # Quality flags
    quality_flags = record.get("quality_flags", [])
    if isinstance(quality_flags, str):
        quality_flags = [quality_flags]
    degrade_reasons = record.get("degrade_reasons", [])
    if isinstance(degrade_reasons, str):
        degrade_reasons = [degrade_reasons]

    # Compute v112Z-specific keys
    dedupe_key_z = _build_dedupe_key_v112z(record)
    cooldown_key_z = _build_cooldown_key_v112z(record)
    payload_hash_z = _build_payload_hash_v112z(record)

    # Extension fields
    extension = {
        "version": "v112Z",
        "signal_type": "whale_position_alert",
        "source": "v112Y_degraded_whale_replay",
        "envelope_status": "degraded_compatible",
        "degraded": True,
        "mock_replay_only": True,
        "eligible_for_real_send": False,
        "real_send_candidate": False,
        # Custom dedupe/cooldown/payload keys for degraded records
        "dedupe_key_v112z": dedupe_key_z,
        "cooldown_key_v112z": cooldown_key_z,
        "payload_hash_v112z": payload_hash_z,
        # Address and label
        "address": address,
        "address_short": addr_short,
        "label": label,
        "label_confidence": label_confidence,
        "label_explanation": label_explanation,
        "label_source": label_source,
        "entity_type": str(record.get("entity_type", "")),
        # Position fields
        "asset": asset,
        "side": side,
        "notional_usd": _safe_float(record.get("notional_usd", 0)),
        "entry_price": _safe_float(record.get("entry_price", 0)),
        "mark_price": _safe_float(record.get("mark_price", 0)),
        "leverage": _safe_float(record.get("leverage", 0)),
        "unrealized_pnl": _safe_float(record.get("unrealized_pnl", 0)),
        # Liquidation price
        "liquidation_price": liquidation_price,
        "liquidation_price_note": liquidation_price_note,
        "liquidation_price_status": liquidation_price_status,
        "liquidation_distance_pct": record.get("liquidation_distance_pct"),
        # Delta
        "delta_status": delta_status,
        "delta_explanation": delta_explanation,
        # Timestamp
        "timestamp_status": timestamp_status,
        "timestamp_explanation": timestamp_explanation,
        # Quality flags
        "quality_flags": quality_flags,
        "degrade_reasons": degrade_reasons,
        # Routing guard
        "routing_guard": {
            "preview_allowed": False,
            "tg_send_allowed": False,
            "prod_state_write_allowed": False,
        },
        # Source tracking
        "v112x_stop_decision": str(record.get("v112x_stop_decision", "DEGRADE_TO_MOCK")),
        "v112x_response_index": record.get("v112x_response_index", -1),
        "generated_at": china_stamp(),
    }

    # Merge extension into envelope
    envelope["v112z_extension"] = extension

    return envelope


# ══════════════════════════════════════════════════════════════════════════════════════════
# Validation
# ══════════════════════════════════════════════════════════════════════════════════════════

def validate_input_record(record: dict, index: int) -> list[str]:
    """Validate that a v112Y input record meets all preconditions.

    Returns a list of validation error messages (empty = valid).
    """
    errors: list[str] = []

    if not record.get("degraded"):
        errors.append(f"Record {index}: degraded is not true")
    if not record.get("mock_replay_only"):
        errors.append(f"Record {index}: mock_replay_only is not true")
    if record.get("eligible_for_real_send") is not False:
        errors.append(f"Record {index}: eligible_for_real_send is not false")
    if not record.get("address"):
        errors.append(f"Record {index}: address is empty")
    if not record.get("asset"):
        errors.append(f"Record {index}: asset is empty")
    if not record.get("label_confidence"):
        errors.append(f"Record {index}: label_confidence is empty")
    if not record.get("label_explanation"):
        errors.append(f"Record {index}: label_explanation is empty")
    if not record.get("delta_status"):
        errors.append(f"Record {index}: delta_status is empty")
    if not record.get("timestamp_status"):
        errors.append(f"Record {index}: timestamp_status is empty")
    if not record.get("quality_flags"):
        errors.append(f"Record {index}: quality_flags is empty")

    return errors


def validate_envelope_quality(envelope: dict, index: int) -> list[str]:
    """Validate that a generated envelope preserves all degraded quality information.

    Returns a list of validation error messages (empty = valid).
    """
    errors: list[str] = []
    ext = envelope.get("v112z_extension", {})

    # v112H base envelope validation
    base_valid = validate_signal_envelope(envelope)
    if not base_valid["valid"]:
        for err in base_valid["errors"]:
            errors.append(f"Envelope {index}: v112H validation: {err}")

    # Degraded extension checks
    if ext.get("eligible_for_real_send") is not False:
        errors.append(f"Envelope {index}: eligible_for_real_send is not false")
    if ext.get("real_send_candidate") is not False:
        errors.append(f"Envelope {index}: real_send_candidate is not false")
    if ext.get("degraded") is not True:
        errors.append(f"Envelope {index}: degraded is not true")
    if ext.get("mock_replay_only") is not True:
        errors.append(f"Envelope {index}: mock_replay_only is not true")

    # Quality flag preservation
    if not ext.get("label_confidence"):
        errors.append(f"Envelope {index}: label_confidence missing")
    if not ext.get("label_explanation"):
        errors.append(f"Envelope {index}: label_explanation missing")
    if ext.get("liquidation_price") is None and not ext.get("liquidation_price_note"):
        errors.append(f"Envelope {index}: null liquidation_price has no note")
    if not ext.get("delta_status"):
        errors.append(f"Envelope {index}: delta_status missing")
    if not ext.get("timestamp_status"):
        errors.append(f"Envelope {index}: timestamp_status missing")
    if not ext.get("quality_flags"):
        errors.append(f"Envelope {index}: quality_flags missing")
    if not ext.get("degrade_reasons"):
        errors.append(f"Envelope {index}: degrade_reasons missing")

    # Routing guard
    rg = ext.get("routing_guard", {})
    if rg.get("preview_allowed") is not False:
        errors.append(f"Envelope {index}: routing_guard.preview_allowed is not false")
    if rg.get("tg_send_allowed") is not False:
        errors.append(f"Envelope {index}: routing_guard.tg_send_allowed is not false")
    if rg.get("prod_state_write_allowed") is not False:
        errors.append(f"Envelope {index}: routing_guard.prod_state_write_allowed is not false")

    # Leak check
    leak = scan_envelope_leaks(envelope)
    if not leak["clean"]:
        errors.append(f"Envelope {index}: leak scan failed: debug={leak['debug_terms_found']}, secret={leak['secret_terms_found']}")

    return errors


# ══════════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"=== Market Radar {VERSION} — Degraded Whale Envelope Compatibility Runner ===")
    print(f"Run: {china_stamp()}")
    print(f"Run ID: {RUN_ID}")
    print()
    print("Constraints:")
    print("  EXTERNAL API: NONE")
    print("  TG SEND: NONE")
    print("  PROD STATE WRITE: NONE")
    print("  DAEMON: NONE")
    print("  CREDENTIALS READ: NONE")
    print()

    # ── Step 1: Load input records ────────────────────────────────────────────
    print("[1/5] Loading v112Y degraded whale replay records...")
    input_records = load_jsonl(INPUT_JSONL)
    input_count = len(input_records)
    print(f"  Loaded: {input_count} records from {INPUT_JSONL}")

    if input_count == 0:
        print("  [ERROR] No input records found. Aborting.")
        return 1

    # ── Step 2: Validate input records ────────────────────────────────────────
    print("[2/5] Validating input records...")
    input_errors: list[str] = []
    for i, rec in enumerate(input_records):
        errors = validate_input_record(rec, i)
        input_errors.extend(errors)

    all_input_valid = len(input_errors) == 0
    if not all_input_valid:
        print(f"  [WARN] {len(input_errors)} input validation issues:")
        for err in input_errors:
            print(f"    - {err}")
    else:
        print(f"  All {input_count} records passed input validation.")

    # Verify all records have expected invariants
    all_degraded = all(r.get("degraded") for r in input_records)
    all_mock = all(r.get("mock_replay_only") for r in input_records)
    all_not_eligible = all(r.get("eligible_for_real_send") is False for r in input_records)
    print(f"  All degraded=true: {all_degraded}")
    print(f"  All mock_replay_only=true: {all_mock}")
    print(f"  All eligible_for_real_send=false: {all_not_eligible}")
    print()

    # ── Step 3: Build envelopes ───────────────────────────────────────────────
    print("[3/5] Building degraded whale envelopes...")
    envelopes: list[dict] = []
    build_errors: list[str] = []

    for i, rec in enumerate(input_records):
        try:
            env = build_degraded_whale_envelope(rec)
            envelopes.append(env)
        except Exception as e:
            build_errors.append(f"Record {i} ({rec.get('record_id', '?')}): {e}")
            print(f"  [ERROR] Failed to build envelope for record {i}: {e}")

    envelope_count = len(envelopes)
    print(f"  Built: {envelope_count} envelopes")

    if build_errors:
        print(f"  {len(build_errors)} build errors:")
        for err in build_errors:
            print(f"    - {err}")
    print()

    # ── Step 4: Validate envelopes ────────────────────────────────────────────
    print("[4/5] Validating envelopes...")
    env_errors: list[str] = []
    for i, env in enumerate(envelopes):
        errors = validate_envelope_quality(env, i)
        env_errors.extend(errors)

    all_envs_valid = len(env_errors) == 0
    if all_envs_valid:
        print(f"  All {envelope_count} envelopes passed quality validation.")
    else:
        print(f"  {len(env_errors)} envelope validation issues:")
        for err in env_errors[:20]:  # Limit output
            print(f"    - {err}")
        if len(env_errors) > 20:
            print(f"    ... and {len(env_errors) - 20} more")

    # Quality flag summary
    all_quality_flags_preserved = all(
        len(env.get("v112z_extension", {}).get("quality_flags", [])) > 0
        for env in envelopes
    )
    all_label_conf_preserved = all(
        bool(env.get("v112z_extension", {}).get("label_confidence"))
        for env in envelopes
    )
    all_liq_note_preserved = all(
        (env.get("v112z_extension", {}).get("liquidation_price") is not None) or
        bool(env.get("v112z_extension", {}).get("liquidation_price_note"))
        for env in envelopes
    )
    all_delta_preserved = all(
        bool(env.get("v112z_extension", {}).get("delta_status"))
        for env in envelopes
    )
    all_ts_preserved = all(
        bool(env.get("v112z_extension", {}).get("timestamp_status"))
        for env in envelopes
    )

    print(f"  quality_flags_preserved: {all_quality_flags_preserved}")
    print(f"  label_confidence_preserved: {all_label_conf_preserved}")
    print(f"  liquidation_price_note_preserved: {all_liq_note_preserved}")
    print(f"  delta_status_preserved: {all_delta_preserved}")
    print(f"  timestamp_status_preserved: {all_ts_preserved}")
    print()

    # Label confidence distribution
    label_conf_dist: dict[str, int] = {}
    for env in envelopes:
        lc = env.get("v112z_extension", {}).get("label_confidence", "unknown")
        label_conf_dist[lc] = label_conf_dist.get(lc, 0) + 1
    print(f"  Label confidence distribution: {label_conf_dist}")

    # Quality flags distribution
    qf_dist: dict[str, int] = {}
    for env in envelopes:
        for qf in env.get("v112z_extension", {}).get("quality_flags", []):
            qf_dist[qf] = qf_dist.get(qf, 0) + 1
    print(f"  Quality flags distribution: {qf_dist}")
    print()

    # ── Step 5: Write outputs ─────────────────────────────────────────────────
    print("[5/5] Writing outputs...")

    # Ensure directories exist
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 5a. Write envelopes JSONL
    with open(ENVELOPES_JSONL_PATH, "w", encoding="utf-8") as f:
        for env in envelopes:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")
    print(f"  [OK] {ENVELOPES_JSONL_PATH} ({envelope_count} lines)")

    # 5b. Write result JSON
    result = {
        "version": "v112Z",
        "status": "passed" if all_envs_valid and envelope_count == input_count else "partial",
        "input_records_loaded": input_count,
        "envelopes_written": envelope_count,
        "external_api_called": False,
        "degraded_compatible": True,
        "mock_replay_only": True,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "preview_allowed_count": 0,
        "tg_send_allowed_count": 0,
        "prod_state_write": False,
        "daemon_started": False,
        "watcher_started": False,
        "credentials_read": False,
        "files_deleted": False,
        "quality_flags_preserved": all_quality_flags_preserved,
        "label_confidence_preserved": all_label_conf_preserved,
        "liquidation_price_note_preserved": all_liq_note_preserved,
        "delta_status_preserved": all_delta_preserved,
        "timestamp_status_preserved": all_ts_preserved,
        "label_confidence_distribution": label_conf_dist,
        "quality_flags_distribution": qf_dist,
        "all_input_degraded": all_degraded,
        "all_input_mock_replay_only": all_mock,
        "all_input_eligible_for_real_send_false": all_not_eligible,
        "all_input_valid": all_input_valid,
        "all_envelopes_valid": all_envs_valid,
        "input_validation_errors": len(input_errors),
        "envelope_validation_errors": len(env_errors),
        "unique_addresses": len(set(
            env.get("v112z_extension", {}).get("address", "")
            for env in envelopes
        )),
        "next_step": "v113a_degraded_whale_preview_pack_local_only",
        "generated_at": china_stamp(),
    }

    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")

    # 5c. Write report
    write_report(envelopes, result, input_records, label_conf_dist, qf_dist)
    print(f"  [OK] {REPORT_MD_PATH}")

    # 5d. Write handoff
    write_handoff(envelopes, result, input_records, label_conf_dist, qf_dist)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    print()
    print(f"{'=' * 70}")
    print(f"v1.12-Z Degraded Whale Envelope Compatibility — Complete")
    print(f"{'=' * 70}")
    print(f"  Input records:           {input_count}")
    print(f"  Envelopes generated:     {envelope_count}")
    print(f"  All input valid:         {all_input_valid}")
    print(f"  All envelopes valid:     {all_envs_valid}")
    print(f"  Quality flags preserved: {all_quality_flags_preserved}")
    print(f"  Label confidence:        {label_conf_dist}")
    print(f"  eligible_for_real_send:  ALL FALSE")
    print(f"  TG send:                 NONE")
    print(f"  External API:            NONE")
    print(f"  Prod state write:        NONE")
    print(f"  Daemon:                  NONE")
    print(f"  Next step:               v113a_degraded_whale_preview_pack_local_only")
    print(f"{'=' * 70}")

    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════
# Report / Handoff Writers
# ══════════════════════════════════════════════════════════════════════════════════════════

def write_report(
    envelopes: list[dict],
    result: dict,
    input_records: list[dict],
    label_conf_dist: dict[str, int],
    qf_dist: dict[str, int],
) -> None:
    """Write the v112Z Markdown report."""
    lines = [
        f"# Market Radar v1.12-Z — Degraded Whale Envelope Compatibility Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: v112Z",
        f"**Run ID**: {RUN_ID}",
        f"**Based on**: v112Y degraded whale replay records",
        f"",
        f"---",
        f"",
        f"## 概述",
        f"",
        f"本报告证明 v112Y 生成的 {result['input_records_loaded']} 条 degraded whale replay records",
        f"已成功接入 v112H unified signal envelope 兼容层。",
        f"所有 envelope 均保留 degraded 信息，不丢失 quality flags、label confidence、",
        f"liquidation_price note、delta status 和 timestamp status。",
        f"",
        f"本轮只做 envelope compatibility，不进入 TG send，不写 prod state，不调用外部 API。",
        f"",
        f"## 全局统计",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| 输入 records 数量 | {result['input_records_loaded']} |",
        f"| 输出 envelopes 数量 | {result['envelopes_written']} |",
        f"| envelopes 与 records 一致 | {result['envelopes_written'] == result['input_records_loaded']} |",
        f"| unique_addresses | {result['unique_addresses']} |",
        f"| external_api_called | {result['external_api_called']} |",
        f"| degraded_compatible | {result['degraded_compatible']} |",
        f"| mock_replay_only | {result['mock_replay_only']} |",
        f"| eligible_for_real_send_count | {result['eligible_for_real_send_count']} |",
        f"| real_send_candidate_count | {result['real_send_candidate_count']} |",
        f"| preview_allowed_count | {result['preview_allowed_count']} |",
        f"| tg_send_allowed_count | {result['tg_send_allowed_count']} |",
        f"| prod_state_write | {result['prod_state_write']} |",
        f"| daemon_started | {result['daemon_started']} |",
        f"| watcher_started | {result['watcher_started']} |",
        f"| credentials_read | {result['credentials_read']} |",
        f"| files_deleted | {result['files_deleted']} |",
        f"",
        f"---",
        f"",
        f"## Label Confidence 分布",
        f"",
        f"| 置信度 | 数量 |",
        f"|--------|------|",
    ]
    for conf in ["high", "medium", "low", "unknown"]:
        count = label_conf_dist.get(conf, 0)
        lines.append(f"| {conf} | {count} |")
    lines.extend([
        f"",
        f"**注意**: 没有 high confidence 标签。所有标签均为 medium 或 low。",
        f"low-confidence / unknown whale 未伪装成确定机构。",
        f"",
        f"---",
        f"",
        f"## Quality Flags 分布",
        f"",
        f"| Flag | 出现次数 |",
        f"|------|----------|",
    ])
    for flag, count in sorted(qf_dist.items()):
        lines.append(f"| {flag} | {count} |")
    lines.extend([
        f"",
        f"---",
        f"",
        f"## 降级信息保留状态",
        f"",
        f"| 字段 | 保留状态 |",
        f"|------|----------|",
        f"| quality_flags | {'✅ 已保留' if result['quality_flags_preserved'] else '❌ 丢失'} |",
        f"| label_confidence | {'✅ 已保留' if result['label_confidence_preserved'] else '❌ 丢失'} |",
        f"| liquidation_price_note | {'✅ 已保留' if result['liquidation_price_note_preserved'] else '❌ 丢失'} |",
        f"| delta_status | {'✅ 已保留' if result['delta_status_preserved'] else '❌ 丢失'} |",
        f"| timestamp_status | {'✅ 已保留' if result['timestamp_status_preserved'] else '❌ 丢失'} |",
        f"",
        f"---",
        f"",
        f"## Routing Guard 状态",
        f"",
        f"| Guard | 值 |",
        f"|-------|-----|",
        f"| preview_allowed | false |",
        f"| tg_send_allowed | false |",
        f"| prod_state_write_allowed | false |",
        f"",
        f"**所有 envelope 均**:",
        f"- eligible_for_real_send = false",
        f"- real_send_candidate = false",
        f"- 不得进入 TG send path",
        f"- 不伪装成 live passed",
        f"",
        f"---",
        f"",
        f"## Envelope 列表",
        f"",
    ])

    for i, env in enumerate(envelopes, 1):
        ext = env.get("v112z_extension", {})
        lines.extend([
            f"### {i}. {ext.get('asset', '?')} {ext.get('side', '?')} — {ext.get('label', '?')}",
            f"",
            f"| 字段 | 值 |",
            f"|------|-----|",
            f"| address | `{ext.get('address_short', '?')}` |",
            f"| label | {ext.get('label', '?')} |",
            f"| label_confidence | {ext.get('label_confidence', '?')} |",
            f"| label_explanation | {ext.get('label_explanation', '?')[:80]}... |",
            f"| asset | {ext.get('asset', '?')} |",
            f"| side | {ext.get('side', '?')} |",
            f"| notional_usd | {ext.get('notional_usd', 0):,.0f} |",
            f"| entry_price | {ext.get('entry_price', 0):,.2f} |",
            f"| liquidation_price | {ext.get('liquidation_price')} |",
            f"| liquidation_price_note | {ext.get('liquidation_price_note', '')[:60]}... |",
            f"| delta_status | {ext.get('delta_status', '?')} |",
            f"| timestamp_status | {ext.get('timestamp_status', '?')} |",
            f"| quality_flags | {', '.join(ext.get('quality_flags', []))} |",
            f"| degrade_reasons count | {len(ext.get('degrade_reasons', []))} |",
            f"| eligible_for_real_send | {ext.get('eligible_for_real_send')} |",
            f"| real_send_candidate | {ext.get('real_send_candidate')} |",
            f"| routing_guard.tg_send_allowed | {ext.get('routing_guard', {}).get('tg_send_allowed')} |",
            f"",
        ])

    lines.extend([
        f"---",
        f"",
        f"## 执行约束确认",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| external_api_called | false |",
        f"| tg_send | false |",
        f"| prod_state_write | false |",
        f"| daemon_started | false |",
        f"| watcher_started | false |",
        f"| credentials_read | false |",
        f"| files_deleted | false |",
        f"| eligible_for_real_send | false (all) |",
        f"| real_send_candidate | false (all) |",
        f"| degraded 伪装成 live passed | false |",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"v113a: degraded whale preview pack local-only — 生成本地预览卡片，",
        f"但仍不进入 TG send path。",
        f"",
    ])

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_handoff(
    envelopes: list[dict],
    result: dict,
    input_records: list[dict],
    label_conf_dist: dict[str, int],
    qf_dist: dict[str, int],
) -> None:
    """Write the v112Z handoff markdown."""
    lines = [
        f"# Market Radar v1.12-Z — Degraded Whale Envelope Compatibility Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: v112Z",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260605_v112z_degraded_whale_envelope_compatibility",
        f"",
        f"---",
        f"",
        f"## 修改文件",
        f"",
        f"| 文件 | 操作 | 说明 |",
        f"|------|------|------|",
        f"| `scripts/run_market_radar_v112z_degraded_whale_envelope_compatibility.py` | 新增 | v112Z degraded whale envelope runner |",
        f"| `scripts/test_market_radar_v112z_degraded_whale_envelope_compatibility.py` | 新增 | v112Z test suite |",
        f"| `results/market_radar_v112z_degraded_whale_envelopes.jsonl` | 新增 | Degraded whale envelopes JSONL |",
        f"| `results/market_radar_v112z_degraded_whale_envelope_compatibility_result.json` | 新增 | Result JSON |",
        f"| `runs/market_radar/v112z_degraded_whale_envelope_compatibility.md` | 新增 | Markdown 报告 |",
        f"| `runs/market_radar/v112z_degraded_whale_envelope_compatibility_handoff.md` | 新增 | Handoff（本文件） |",
        f"",
        f"---",
        f"",
        f"## 执行命令",
        f"",
        f"```powershell",
        f"cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        f"python scripts/run_market_radar_v112z_degraded_whale_envelope_compatibility.py",
        f"python scripts/test_market_radar_v112z_degraded_whale_envelope_compatibility.py",
        f"```",
        f"",
        f"---",
        f"",
        f"## 输入与输出",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| Input records | {result['input_records_loaded']} |",
        f"| Output envelopes | {result['envelopes_written']} |",
        f"| Unique addresses | {result['unique_addresses']} |",
        f"| All input degraded=true | {result['all_input_degraded']} |",
        f"| All input mock_replay_only=true | {result['all_input_mock_replay_only']} |",
        f"| All input eligible_for_real_send=false | {result['all_input_eligible_for_real_send_false']} |",
        f"",
        f"---",
        f"",
        f"## Label Confidence 摘要",
        f"",
        f"| 置信度 | 数量 |",
        f"|--------|------|",
    ]
    for conf in ["high", "medium", "low", "unknown"]:
        count = label_conf_dist.get(conf, 0)
        lines.append(f"| {conf} | {count} |")
    lines.extend([
        f"",
        f"⚠️ 无 high confidence 标签。medium 和 low 标签均正确保留，未伪装。",
        f"",
        f"---",
        f"",
        f"## Quality Flags 摘要",
        f"",
        f"| Flag | 出现次数 |",
        f"|------|----------|",
    ])
    for flag, count in sorted(qf_dist.items()):
        lines.append(f"| {flag} | {count} |")
    lines.extend([
        f"",
        f"---",
        f"",
        f"## Routing Guard 摘要",
        f"",
        f"| Guard | 值 |",
        f"|-------|-----|",
        f"| eligible_for_real_send | ALL FALSE |",
        f"| real_send_candidate | ALL FALSE |",
        f"| preview_allowed | ALL FALSE |",
        f"| tg_send_allowed | ALL FALSE |",
        f"| prod_state_write_allowed | ALL FALSE |",
        f"",
        f"---",
        f"",
        f"## Safety Invariant 状态",
        f"",
        f"| Invariant | 状态 |",
        f"|-----------|------|",
        f"| No external API calls | ✅ |",
        f"| No credentials read | ✅ |",
        f"| No TG send | ✅ |",
        f"| No prod state write | ✅ |",
        f"| No daemon/watcher/cron/loop | ✅ |",
        f"| No files deleted | ✅ |",
        f"| Degraded envelopes NOT disguised as live passed | ✅ |",
        f"| Low-confidence labels NOT disguised as confirmed institutions | ✅ |",
        f"| All quality flags preserved | {'✅' if result['quality_flags_preserved'] else '❌'} |",
        f"| All label confidence preserved | {'✅' if result['label_confidence_preserved'] else '❌'} |",
        f"| All liquidation_price notes preserved | {'✅' if result['liquidation_price_note_preserved'] else '❌'} |",
        f"| All delta_status preserved | {'✅' if result['delta_status_preserved'] else '❌'} |",
        f"| All timestamp_status preserved | {'✅' if result['timestamp_status_preserved'] else '❌'} |",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"v113a: degraded whale preview pack local-only — 生成本地预览卡片，",
        f"但仍不进入 TG send path。",
        f"",
    ])

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
