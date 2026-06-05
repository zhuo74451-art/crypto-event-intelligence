"""Market Radar v1.12-H — Unified Signal Envelope Layer

Provides a standardized signal envelope for all 5 fixed card types, enabling:
  - Stable deduplication (dedupe_key)
  - Rate limiting / cooldown (cooldown_key)
  - Audit trail (payload_hash)
  - Leak scanning (debug, secret, path, wallet)

Functions:
  build_signal_envelope(...)
  build_dedupe_key(card_type, event_key, primary_assets, observed_at)
  build_cooldown_key(card_type, primary_assets, direction)
  build_payload_hash(public_card, card_type, primary_assets, direction)
  validate_signal_envelope(envelope)
  scan_envelope_leaks(envelope)

Constraints:
  - No external API calls
  - No real TG send
  - No daemon/loop/cron
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_signal_envelope_v112h import (
        build_signal_envelope, build_dedupe_key, build_cooldown_key,
        build_payload_hash, validate_signal_envelope, scan_envelope_leaks,
        VALID_CARD_TYPES, VALID_DIRECTIONS,
    )
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any

VERSION = "v1.12-H"
SCHEMA_VERSION = "1.0.0"

CN_TZ = timezone(timedelta(hours=8))

# ── Enums ────────────────────────────────────────────────────────────────────────────

VALID_CARD_TYPES = frozenset([
    "price_oi_volume_anomaly",
    "whale_position_alert",
    "liquidation_pressure",
    "multi_asset_market_sync",
    "news_event_market_impact",
])

VALID_DIRECTIONS = frozenset(["bullish", "bearish", "neutral", "mixed", "unknown"])

# ── Forbidden Terms for Leak Scan ───────────────────────────────────────────────────

FORBIDDEN_DEBUG_TERMS = [
    "debug", "internal", "trace", "fixture",
]

FORBIDDEN_SECRET_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

FORBIDDEN_PATH_TERMS = [
    "C:\\Users\\PC", "C:\\Users", "D:\\", "E:\\",
    "/home/", "/Users/", "/tmp/", "/var/",
    "ai_relay_desk",
]

FORBIDDEN_REGISTRY_TERMS = [
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "gate_decision", "score↑", "blocked_by", "gate_version",
    "factor_hits", "block_reason", "block_rules", "block_triggered",
    "admission_result",
    "not_reached", "mock_sent", "mock_message_id",
]

# ══════════════════════════════════════════════════════════════════════════════════════
# Core Envelope Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_signal_envelope(
    card_type: str,
    adapter_version: str,
    source_kind: str,
    observed_at: str,
    primary_assets: list[str],
    direction: str,
    severity_score: float,
    confidence_score: float,
    event_key: str,
    public_card: str,
    safety_flags: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """Build a unified signal envelope from adapter output.

    This is the single entry point for producing standardized signal envelopes.
    All 5 card types MUST use this function.

    Args:
        card_type: One of VALID_CARD_TYPES.
        adapter_version: Version string of the producing adapter (e.g. "v1.12-F").
        source_kind: Data source kind (e.g. "fixture", "local_snapshot", "local_enrichment").
        observed_at: ISO-8601 timestamp of observation.
        primary_assets: List of asset symbols (e.g. ["BTC", "ETH"]).
        direction: One of VALID_DIRECTIONS.
        severity_score: 0-100 severity score.
        confidence_score: 0-1 confidence score.
        event_key: Stable event identifier from the adapter.
        public_card: The rendered public card text.
        safety_flags: Dict of safety flags (will be merged with defaults).
        metadata: Additional metadata dict.

    Returns:
        Dict representing the unified signal envelope.
    """
    # ── Validate card_type ───────────────────────────────────────────────────
    if card_type not in VALID_CARD_TYPES:
        raise ValueError(
            f"Invalid card_type: {card_type!r}. Must be one of: "
            f"{sorted(VALID_CARD_TYPES)}"
        )

    # ── Validate direction ───────────────────────────────────────────────────
    if direction not in VALID_DIRECTIONS:
        raise ValueError(
            f"Invalid direction: {direction!r}. Must be one of: "
            f"{sorted(VALID_DIRECTIONS)}"
        )

    # ── Clamp scores ─────────────────────────────────────────────────────────
    severity_score = max(0.0, min(100.0, float(severity_score)))
    confidence_score = max(0.0, min(1.0, float(confidence_score)))

    # ── Merge safety flags ───────────────────────────────────────────────────
    merged_flags = {
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }
    if safety_flags:
        merged_flags.update(safety_flags)

    # ── Normalize observed_at ────────────────────────────────────────────────
    observed_at = _normalize_timestamp(observed_at)

    # ── Normalize primary_assets ─────────────────────────────────────────────
    if isinstance(primary_assets, str):
        primary_assets = [a.strip() for a in primary_assets.split(",") if a.strip()]
    if not isinstance(primary_assets, list):
        primary_assets = [str(primary_assets)]
    primary_assets = [str(a).strip().upper() for a in primary_assets if str(a).strip()]

    # ── Normalize event_key ──────────────────────────────────────────────────
    event_key = str(event_key).strip()

    # ── Compute key fields ───────────────────────────────────────────────────
    dedupe_key = build_dedupe_key(card_type, event_key, primary_assets, observed_at)
    cooldown_key = build_cooldown_key(card_type, primary_assets, direction)
    payload_hash = build_payload_hash(public_card, card_type, primary_assets, direction)

    # ── Readiness ────────────────────────────────────────────────────────────
    readiness = "partial"
    if source_kind in ("fixture", "local_snapshot", "local_enrichment", "local_correlation"):
        readiness = "fixture"

    # ── Generate signal_id ───────────────────────────────────────────────────
    signal_id = _generate_signal_id(card_type, event_key, observed_at)

    # ── Build envelope ───────────────────────────────────────────────────────
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "signal_id": signal_id,
        "card_type": card_type,
        "adapter_version": adapter_version,
        "source_kind": source_kind,
        "observed_at": observed_at,
        "primary_assets": primary_assets,
        "direction": direction,
        "severity_score": round(severity_score, 1),
        "confidence_score": round(confidence_score, 4),
        "event_key": event_key,
        "dedupe_key": dedupe_key,
        "cooldown_key": cooldown_key,
        "payload_hash": payload_hash,
        "readiness": readiness,
        "live_ready": merged_flags.get("live_ready", False),
        "public_card": public_card,
        "safety_flags": merged_flags,
        "metadata": metadata or {},
    }

    return envelope


# ══════════════════════════════════════════════════════════════════════════════════════
# Key/Hash Builders
# ══════════════════════════════════════════════════════════════════════════════════════

def build_dedupe_key(
    card_type: str,
    event_key: str,
    primary_assets: list[str],
    observed_at: str,
) -> str:
    """Build a stable deduplication key.

    Minimum composition:
      - card_type
      - event_key
      - primary_assets (sorted, joined)
      - observed_at normalized to minute granularity

    The same input MUST produce the same dedupe_key every time.

    Args:
        card_type: Card type string.
        event_key: Stable event key from adapter.
        primary_assets: List of asset symbols.
        observed_at: ISO-8601 timestamp.

    Returns:
        SHA-256 hex digest of the composed key.
    """
    # Normalize assets
    if isinstance(primary_assets, str):
        primary_assets = [a.strip() for a in primary_assets.split(",") if a.strip()]
    assets_sorted = sorted([str(a).strip().upper() for a in primary_assets if str(a).strip()])
    assets_str = ",".join(assets_sorted)

    # Normalize observed_at to minute granularity
    ts_minute = _normalize_to_minute(observed_at)

    # Compose
    raw = f"{card_type}|{event_key}|{assets_str}|{ts_minute}"
    return _sha256_hex(raw)


def build_cooldown_key(
    card_type: str,
    primary_assets: list[str],
    direction: str,
) -> str:
    """Build a stable cooldown key.

    Minimum composition:
      - card_type
      - primary_assets (sorted, joined)
      - direction

    cooldown_key MUST NOT contain volatile fields (timestamps, event-specific keys).
    The same input MUST produce the same cooldown_key every time.

    Args:
        card_type: Card type string.
        primary_assets: List of asset symbols.
        direction: Signal direction.

    Returns:
        SHA-256 hex digest of the composed key.
    """
    # Normalize assets
    if isinstance(primary_assets, str):
        primary_assets = [a.strip() for a in primary_assets.split(",") if a.strip()]
    assets_sorted = sorted([str(a).strip().upper() for a in primary_assets if str(a).strip()])
    assets_str = ",".join(assets_sorted)

    direction_norm = str(direction).strip().lower()

    # Compose
    raw = f"{card_type}|{assets_str}|{direction_norm}"
    return _sha256_hex(raw)


def build_payload_hash(
    public_card: str,
    card_type: str,
    primary_assets: list[str],
    direction: str,
) -> str:
    """Build a stable payload hash.

    Hashes the canonical representation of:
      - public_card (full text, stripped)
      - card_type
      - primary_assets (sorted, deduplicated)
      - direction

    MUST NOT include:
      - Local paths
      - Volatile runtime paths
      - Timestamps
      - Random values

    The same input MUST produce the same hash every time.

    Args:
        public_card: The full rendered public card text.
        card_type: Card type string.
        primary_assets: List of asset symbols.
        direction: Signal direction.

    Returns:
        SHA-256 hex digest.
    """
    # Normalize assets
    if isinstance(primary_assets, str):
        primary_assets = [a.strip() for a in primary_assets.split(",") if a.strip()]
    assets_sorted = sorted([str(a).strip().upper() for a in primary_assets if str(a).strip()])

    direction_norm = str(direction).strip().lower()

    # Build canonical dict
    payload = {
        "public_card": str(public_card).strip(),
        "card_type": str(card_type).strip(),
        "primary_assets": assets_sorted,
        "direction": direction_norm,
    }

    # Canonical JSON: sorted keys, no extra whitespace, ensure_ascii=True
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

    return _sha256_hex(canonical)


# ══════════════════════════════════════════════════════════════════════════════════════
# Validation
# ══════════════════════════════════════════════════════════════════════════════════════

def validate_signal_envelope(envelope: dict) -> dict:
    """Validate a signal envelope against the v1.12-H schema.

    Checks:
      - All required fields are present and non-null
      - Field types are correct
      - Enum values are valid
      - Score ranges are valid
      - Keys/hashes are non-empty

    Args:
        envelope: A signal envelope dict.

    Returns:
        Dict with:
          - valid: bool
          - errors: list[str]
          - warnings: list[str]
    """
    errors: list[str] = []
    warnings: list[str] = []

    required_fields = [
        "schema_version", "signal_id", "card_type", "adapter_version",
        "source_kind", "observed_at", "primary_assets", "direction",
        "severity_score", "confidence_score", "event_key",
        "dedupe_key", "cooldown_key", "payload_hash",
        "readiness", "live_ready", "public_card", "safety_flags", "metadata",
    ]

    # ── Required fields check ───────────────────────────────────────────────
    for field in required_fields:
        if field not in envelope:
            errors.append(f"Missing required field: {field}")
        elif envelope[field] is None:
            errors.append(f"Required field is None: {field}")

    if errors:
        # Early exit — can't validate further without required fields
        return {"valid": False, "errors": errors, "warnings": warnings}

    # ── card_type check ─────────────────────────────────────────────────────
    ct = envelope.get("card_type", "")
    if ct not in VALID_CARD_TYPES:
        errors.append(f"Invalid card_type: {ct!r}")

    # ── direction check ─────────────────────────────────────────────────────
    d = envelope.get("direction", "")
    if d not in VALID_DIRECTIONS:
        errors.append(f"Invalid direction: {d!r}")

    # ── severity_score check ────────────────────────────────────────────────
    ss = envelope.get("severity_score", 0)
    if not isinstance(ss, (int, float)) or ss < 0 or ss > 100:
        errors.append(f"severity_score out of range [0, 100]: {ss}")

    # ── confidence_score check ──────────────────────────────────────────────
    cs = envelope.get("confidence_score", 0)
    if not isinstance(cs, (int, float)) or cs < 0 or cs > 1:
        errors.append(f"confidence_score out of range [0, 1]: {cs}")

    # ── primary_assets check ────────────────────────────────────────────────
    pa = envelope.get("primary_assets", [])
    if not isinstance(pa, list) or len(pa) == 0:
        errors.append("primary_assets must be a non-empty list")
    else:
        for a in pa:
            if not isinstance(a, str) or not a.strip():
                errors.append(f"primary_assets contains invalid entry: {a!r}")

    # ── public_card check ───────────────────────────────────────────────────
    pc = envelope.get("public_card", "")
    if not pc or not pc.strip():
        errors.append("public_card must not be empty")

    # ── signal_id check ─────────────────────────────────────────────────────
    sid = envelope.get("signal_id", "")
    if not sid or not sid.strip():
        errors.append("signal_id must not be empty")

    # ── key/hash checks ─────────────────────────────────────────────────────
    for key_name in ["dedupe_key", "cooldown_key", "payload_hash"]:
        val = envelope.get(key_name, "")
        if not val or not isinstance(val, str) or len(val) < 16:
            errors.append(f"{key_name} must be a non-empty hash string (got: {val!r})")

    # ── safety_flags check ──────────────────────────────────────────────────
    sf = envelope.get("safety_flags", {})
    if not isinstance(sf, dict):
        errors.append(f"safety_flags must be a dict, got: {type(sf).__name__}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Leak Scanning
# ══════════════════════════════════════════════════════════════════════════════════════

# Full wallet address pattern (0x + 40 hex chars)
WALLET_ADDRESS_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')


def scan_envelope_leaks(envelope: dict) -> dict:
    """Scan an envelope and its public_card for forbidden content.

    Checks for:
      - Debug terms (debug, internal, trace, fixture)
      - Secret terms (secret, token, api_key, chat_id, password)
      - Path leaks (C:\\Users\\PC, ai_relay_desk, etc.)
      - Registry internal terms (value_gate, cooldown_gate, etc.)
      - Full wallet addresses in public fields

    Args:
        envelope: A signal envelope dict.

    Returns:
        Dict with:
          - debug_leak_count: int
          - secret_leak_count: int
          - debug_terms_found: list[str]
          - secret_terms_found: list[str]
          - full_wallet_leak: bool
          - wallet_leak_details: list[str]
          - clean: bool
    """
    # Only scan public_card — metadata is internal and not sent to TG.
    # The task requires public_card to be clean of debug/secret/path terms.
    public_card = str(envelope.get("public_card", ""))

    # Only check public_card for forbidden terms
    check_text = public_card.lower()

    # ── Debug term scan ─────────────────────────────────────────────────────
    debug_found: list[str] = []
    for term in FORBIDDEN_DEBUG_TERMS:
        if term.lower() in check_text:
            debug_found.append(term)
    for term in FORBIDDEN_REGISTRY_TERMS:
        if term.lower() in check_text:
            debug_found.append(term)

    # ── Secret term scan ────────────────────────────────────────────────────
    secret_found: list[str] = []
    for term in FORBIDDEN_SECRET_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)
    for term in FORBIDDEN_PATH_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)
    # Check for Windows absolute paths
    if re.search(r'[A-Za-z]:\\(?:Users|Program|Windows)', public_card):
        secret_found.append("local_absolute_path")
    # Check for Unix-like paths
    if re.search(r'/(?:home|Users|tmp|var|etc|opt|dev)/', public_card):
        secret_found.append("unix_absolute_path")

    # ── Full wallet address scan ───────────────────────────────────────────
    wallet_leak_details: list[str] = []
    # Scan public_card for full 0x... wallet addresses
    wallet_matches = WALLET_ADDRESS_PATTERN.findall(public_card)
    wallet_leak_details.extend(wallet_matches)

    # Also check primary_assets list doesn't contain a wallet address
    pa = envelope.get("primary_assets", [])
    if isinstance(pa, list):
        for a in pa:
            if isinstance(a, str) and WALLET_ADDRESS_PATTERN.match(a):
                wallet_leak_details.append(f"primary_asset_is_wallet: {a}")

    full_wallet_leak = len(wallet_leak_details) > 0

    # ── Deduplicate ────────────────────────────────────────────────────────
    debug_found = sorted(set(debug_found))
    secret_found = sorted(set(secret_found))

    debug_leak_count = len(debug_found)
    secret_leak_count = len(secret_found) + (1 if full_wallet_leak else 0)

    clean = debug_leak_count == 0 and secret_leak_count == 0 and not full_wallet_leak

    return {
        "debug_leak_count": debug_leak_count,
        "secret_leak_count": secret_leak_count,
        "debug_terms_found": debug_found,
        "secret_terms_found": secret_found,
        "full_wallet_leak": full_wallet_leak,
        "wallet_leak_details": wallet_leak_details,
        "clean": clean,
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

def _sha256_hex(raw: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_timestamp(ts: str) -> str:
    """Normalize a timestamp to ISO-8601 with seconds precision in UTC+8.

    If parsing fails, returns the input as-is.
    """
    if not ts:
        return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S+08:00",
        "%Y-%m-%dT%H:%M:%S+08:00",
        "%Y-%m-%d %H:%M:%S UTC+8",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CN_TZ)
            return dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        except ValueError:
            continue

    return str(ts).strip()


def _normalize_to_minute(ts: str) -> str:
    """Normalize a timestamp to minute-level granularity (YYYY-MM-DDTHH:MM).

    Used for dedupe_key to group events within the same minute.
    """
    if not ts:
        return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M")

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S+08:00",
        "%Y-%m-%d %H:%M:%S UTC+8",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CN_TZ)
            return dt.strftime("%Y-%m-%dT%H:%M")
        except ValueError:
            continue

    # Fallback: truncate to minute-ish
    return str(ts).strip()[:16]


def _generate_signal_id(card_type: str, event_key: str, observed_at: str) -> str:
    """Generate a stable signal_id from envelope components.

    Format: <card_type_short>-<event_key_hash8>-<ts_short>
    """
    ct_short_map = {
        "price_oi_volume_anomaly": "pova",
        "whale_position_alert": "wpa",
        "liquidation_pressure": "lipr",
        "multi_asset_market_sync": "mams",
        "news_event_market_impact": "nemi",
    }
    ct_short = ct_short_map.get(card_type, card_type[:4])

    ek_hash = hashlib.sha256(str(event_key).encode("utf-8")).hexdigest()[:8]

    ts = _normalize_timestamp(observed_at)
    ts_short = ts.replace(":", "").replace("-", "").replace("+", "").replace("T", "")[:12]

    return f"sig-{ct_short}-{ek_hash}-{ts_short}"


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ══════════════════════════════════════════════════════════════════════════════════════
# Convenience: build envelopes from adapter results
# ══════════════════════════════════════════════════════════════════════════════════════

def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def _map_direction(direction_str: str) -> str:
    """Map various direction strings to the standard 5 directions."""
    d = str(direction_str).strip().lower()
    mapping = {
        "up": "bullish",
        "down": "bearish",
        "long": "bullish",
        "short": "bearish",
        "多头": "bullish",
        "空头": "bearish",
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "mixed": "mixed",
        "unknown": "unknown",
    }
    return mapping.get(d, "neutral")


def build_envelope_from_position_result(
    pr: dict,
    source_kind: str = "fixture",
) -> dict:
    """Build an envelope from a v112f whale position result dict.

    Args:
        pr: A position_result entry from v112f result JSON.
        source_kind: Data source kind.

    Returns:
        A signal envelope dict.
    """
    card_type = "whale_position_alert"
    adapter_version = "v1.12-F"
    event_key = pr.get("event_id", "unknown")
    observed_at = pr.get("observed_at", china_stamp())
    asset = str(pr.get("asset", "")).strip().upper()
    primary_assets = [asset] if asset else ["UNKNOWN"]
    side = str(pr.get("side", "long"))
    direction = _map_direction(side)

    # Severity: based on position size and leverage
    pos_size = _safe_float(pr.get("position_size_usd", 0))
    leverage = _safe_float(pr.get("leverage", 0))
    severity = _compute_whale_severity(pos_size, leverage)

    # Confidence: based on label confidence
    label_conf = str(pr.get("label_confidence", "medium"))
    conf_map = {"high": 0.85, "medium": 0.65, "low": 0.4}
    confidence = conf_map.get(label_conf, 0.5)

    public_card = str(pr.get("public_card", ""))

    safety_flags = {
        "real_tg_sent": bool(pr.get("real_tg_sent", False)),
        "external_api_called": bool(pr.get("external_api_called", False)),
        "external_ai_called": bool(pr.get("external_ai_called", False)),
        "daemon_started": bool(pr.get("daemon_started", False)),
        "live_ready": bool(pr.get("live_ready", False)),
        "debug_leak_count": int(pr.get("debug_leak_count", 0)),
        "secret_leak_count": int(pr.get("secret_leak_count", 0)),
    }

    metadata = {
        "entity_type": str(pr.get("entity_type", "")),
        "alert_type": str(pr.get("alert_type", "")),
        "wallet_short": str(pr.get("wallet_short", "")),
        "label": str(pr.get("label", "")),
        "position_size_usd": pos_size,
        "leverage": leverage,
        "chain": str(pr.get("chain", "hyperliquid")),
    }

    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=primary_assets,
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags=safety_flags,
        metadata=metadata,
    )

    # Post-build: run leak scan and update flags
    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    return envelope


def build_envelope_from_sync_result(
    sr: dict,
    source_kind: str = "fixture",
) -> dict:
    """Build an envelope from a v112g multi-asset sync result dict.

    Args:
        sr: A result entry from v112g result JSON.
        source_kind: Data source kind.

    Returns:
        A signal envelope dict.
    """
    card_type = "multi_asset_market_sync"
    adapter_version = "v1.12-G"
    event_key = sr.get("event_id", "unknown")
    observed_at = sr.get("observed_at", china_stamp())

    # primary_assets from the result
    primary_assets = sr.get("primary_assets", [])
    if isinstance(primary_assets, str):
        primary_assets = [a.strip() for a in primary_assets.split(",") if a.strip()]
    if not primary_assets:
        # Try to extract from assets list
        assets_list = sr.get("assets", [])
        if isinstance(assets_list, list):
            primary_assets = [
                a.get("asset", "") if isinstance(a, dict) else str(a)
                for a in assets_list
            ]
        primary_assets = [a for a in primary_assets if a]

    direction_raw = str(sr.get("direction", "neutral"))
    direction = _map_direction(direction_raw)

    # Severity: based on sync_score and direction_agreement
    sync_score = _safe_float(sr.get("sync_score", 0))
    dir_agree = _safe_float(sr.get("direction_agreement", 0))
    severity = _compute_sync_severity(sync_score, dir_agree)

    # Confidence: based on asset count and sync score
    asset_count = int(sr.get("asset_count", 0))
    confidence = _compute_sync_confidence(sync_score, dir_agree, asset_count)

    public_card = str(sr.get("public_card", ""))

    safety_flags = {
        "real_tg_sent": bool(sr.get("real_tg_sent", False)),
        "external_api_called": bool(sr.get("external_api_called", False)),
        "external_ai_called": bool(sr.get("external_ai_called", False)),
        "daemon_started": bool(sr.get("daemon_started", False)),
        "live_ready": bool(sr.get("live_ready", False)),
        "debug_leak_count": int(sr.get("debug_leak_count", 0)),
        "secret_leak_count": int(sr.get("secret_leak_count", 0)),
    }

    metadata = {
        "sync_type": str(sr.get("sync_type", "unknown")),
        "sector": str(sr.get("sector", "")),
        "sync_score": sync_score,
        "direction_agreement": dir_agree,
        "asset_count": asset_count,
        "avg_price_change": _safe_float(sr.get("avg_price_change", 0)),
        "avg_volume_change": _safe_float(sr.get("avg_volume_change", 0)),
        "avg_oi_change": _safe_float(sr.get("avg_oi_change", 0)),
    }

    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=primary_assets,
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags=safety_flags,
        metadata=metadata,
    )

    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    return envelope


def build_envelope_from_liquidation_record(
    lr: dict,
    source_kind: str = "fixture",
) -> dict:
    """Build an envelope from a v112c liquidation pipeline record dict.

    Args:
        lr: A record entry from v112c result JSON.
        source_kind: Data source kind.

    Returns:
        A signal envelope dict.
    """
    card_type = "liquidation_pressure"
    adapter_version = "v1.12-C"
    event_key = lr.get("signal_id", lr.get("sample_id", "unknown"))
    observed_at = lr.get("observed_at", lr.get("timestamp_utc", china_stamp()))
    asset = str(lr.get("asset", "")).strip().upper()
    primary_assets = [asset] if asset else ["UNKNOWN"]

    # Build signal from the record's signal dict
    signal = lr.get("signal", lr)
    pressure_type = str(signal.get("pressure_type", ""))

    # Map pressure type to direction:
    # long liquidation = longs forced out = bearish pressure
    # short liquidation = shorts forced out = bullish pressure (short squeeze)
    if "two_sided" in pressure_type.lower():
        direction = "mixed"
    elif "long" in pressure_type.lower():
        direction = "bearish"
    elif "short" in pressure_type.lower():
        direction = "bullish"
    else:
        direction = "neutral"

    # Severity based on liquidation totals
    long_liq = _safe_float(signal.get("long_liquidation_usd_1h", 0))
    short_liq = _safe_float(signal.get("short_liquidation_usd_1h", 0))
    cluster_above = _safe_float(signal.get("cluster_above_total_usd", 0))
    cluster_below = _safe_float(signal.get("cluster_below_total_usd", 0))
    total_liq = long_liq + short_liq + cluster_above + cluster_below
    severity = _compute_liq_severity(total_liq)

    # Confidence based on data completeness
    has_clusters = cluster_above > 0 or cluster_below > 0
    has_1h = long_liq > 0 or short_liq > 0
    has_24h = _safe_float(signal.get("long_liquidation_usd_24h", 0)) > 0 or _safe_float(signal.get("short_liquidation_usd_24h", 0)) > 0
    confidence = 0.7 if has_clusters else (0.5 if has_1h else 0.3)

    # public_card from record or from signal
    public_card = str(lr.get("public_card", signal.get("trigger_description", "")))

    safety_flags = {
        "real_tg_sent": bool(lr.get("real_tg_sent", False)),
        "external_api_called": bool(lr.get("external_api_called", False)),
        "external_ai_called": bool(lr.get("external_ai_called", False)),
        "daemon_started": bool(lr.get("daemon_started", False)),
        "live_ready": bool(lr.get("live_ready", False)),
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }

    metadata = {
        "pressure_type": pressure_type,
        "long_liquidation_usd_1h": long_liq,
        "short_liquidation_usd_1h": short_liq,
        "cluster_above_total_usd": cluster_above,
        "cluster_below_total_usd": cluster_below,
        "total_liquidation_usd": total_liq,
    }

    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=primary_assets,
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags=safety_flags,
        metadata=metadata,
    )

    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    return envelope


def build_envelope_from_news_signal(
    ns: dict,
    source_kind: str = "fixture",
) -> dict:
    """Build an envelope from a v112d news event signal dict.

    Args:
        ns: A valid signal entry from v112d result JSON.
        source_kind: Data source kind.

    Returns:
        A signal envelope dict.
    """
    card_type = "news_event_market_impact"
    adapter_version = "v1.12-D"
    event_key = ns.get("sample_id", ns.get("event_id", "unknown"))
    observed_at = ns.get("published_at", china_stamp())

    affected_assets = ns.get("affected_assets", [])
    if isinstance(affected_assets, str):
        affected_assets = [a.strip() for a in affected_assets.split(",") if a.strip()]
    if not affected_assets:
        affected_assets = ["UNKNOWN"]
    primary_assets = [str(a).strip().upper() for a in affected_assets if str(a).strip()]

    impact_dir = str(ns.get("impact_direction", "neutral"))
    direction = _map_direction(impact_dir)

    # Severity based on trading relevance
    trading_rel = str(ns.get("trading_relevance", "中"))
    severity_map = {"高": 85, "中": 60, "低": 30, "待评估": 40}
    severity = severity_map.get(trading_rel, 50)

    # Confidence based on data completeness
    confidence = 0.6  # baseline for fixture news

    public_card = str(ns.get("public_card", ""))

    safety_flags = {
        "real_tg_sent": bool(ns.get("real_tg_sent", False)),
        "external_api_called": bool(ns.get("external_api_called", False)),
        "external_ai_called": bool(ns.get("external_ai_called", False)),
        "daemon_started": bool(ns.get("daemon_started", False)),
        "live_ready": bool(ns.get("live_ready", False)),
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }

    metadata = {
        "category": str(ns.get("category", "unknown")),
        "event_type": str(ns.get("event_type", "其他")),
        "trading_relevance": trading_rel,
        "already_priced": str(ns.get("already_priced", "未知")),
        "source": str(ns.get("source", "")),
    }

    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=primary_assets,
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags=safety_flags,
        metadata=metadata,
    )

    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    return envelope


def build_envelope_from_pova_sample(
    sample: dict,
    source_kind: str = "fixture",
) -> dict:
    """Build an envelope from a v112e price_oi_volume_anomaly sample result.

    Args:
        sample: A sample_result entry from v112e pipeline output.
        source_kind: Data source kind.

    Returns:
        A signal envelope dict.
    """
    card_type = "price_oi_volume_anomaly"
    adapter_version = "v1.12-A"
    event_key = sample.get("sample_id", "unknown")
    observed_at = sample.get("observed_at", china_stamp())
    asset = str(sample.get("asset", "")).strip().upper()
    primary_assets = [asset] if asset else ["UNKNOWN"]

    pc = _safe_float(sample.get("price_change_pct", 0))
    direction = "bullish" if pc > 0 else "bearish" if pc < 0 else "neutral"

    # Severity based on price change magnitude
    severity = _compute_pova_severity(pc)

    # Confidence based on data completeness
    has_oi = _safe_float(sample.get("open_interest", 0)) > 0
    has_vol = _safe_float(sample.get("volume", 0)) > 0
    confidence = 0.8 if (has_oi and has_vol) else (0.6 if (has_oi or has_vol) else 0.4)

    public_card = str(sample.get("public_preview", sample.get("public_card", "")))

    safety_flags = {
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }

    metadata = {
        "price_change_pct": pc,
        "trigger_reason": str(sample.get("trigger_reason", "")),
        "source_type": str(sample.get("source_type", "fixture")),
    }

    envelope = build_signal_envelope(
        card_type=card_type,
        adapter_version=adapter_version,
        source_kind=source_kind,
        observed_at=observed_at,
        primary_assets=primary_assets,
        direction=direction,
        severity_score=severity,
        confidence_score=confidence,
        event_key=event_key,
        public_card=public_card,
        safety_flags=safety_flags,
        metadata=metadata,
    )

    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    return envelope


# ══════════════════════════════════════════════════════════════════════════════════════
# Severity / Confidence Computation Helpers
# ══════════════════════════════════════════════════════════════════════════════════════

def _compute_whale_severity(pos_size_usd: float, leverage: float) -> float:
    """Compute severity for whale position alerts."""
    score = 0.0
    if pos_size_usd >= 50_000_000:
        score += 50
    elif pos_size_usd >= 10_000_000:
        score += 40
    elif pos_size_usd >= 1_000_000:
        score += 30
    elif pos_size_usd >= 500_000:
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


def _compute_sync_severity(sync_score: float, direction_agreement: float) -> float:
    """Compute severity for multi-asset sync."""
    base = min(80.0, sync_score * 0.8 + direction_agreement * 20)
    return min(100.0, base)


def _compute_sync_confidence(sync_score: float, direction_agreement: float, asset_count: int) -> float:
    """Compute confidence for multi-asset sync."""
    conf = 0.5
    if sync_score >= 80:
        conf += 0.2
    elif sync_score >= 50:
        conf += 0.1
    if direction_agreement >= 0.8:
        conf += 0.2
    elif direction_agreement >= 0.6:
        conf += 0.1
    if asset_count >= 5:
        conf += 0.1
    return min(1.0, conf)


def _compute_liq_severity(total_liq_usd: float) -> float:
    """Compute severity for liquidation pressure."""
    if total_liq_usd >= 100_000_000:
        return 90.0
    elif total_liq_usd >= 50_000_000:
        return 75.0
    elif total_liq_usd >= 10_000_000:
        return 60.0
    elif total_liq_usd >= 5_000_000:
        return 45.0
    elif total_liq_usd >= 1_000_000:
        return 30.0
    else:
        return 15.0


def _compute_pova_severity(price_change_pct: float) -> float:
    """Compute severity for price/OI/volume anomaly."""
    abs_pc = abs(price_change_pct)
    if abs_pc >= 20:
        return 90.0
    elif abs_pc >= 15:
        return 75.0
    elif abs_pc >= 10:
        return 60.0
    elif abs_pc >= 7:
        return 45.0
    elif abs_pc >= 5:
        return 30.0
    else:
        return 15.0
