"""Market Radar v1.12-I — Dedupe + Cooldown Gate Layer

Provides a standardized signal gate that evaluates each unified signal envelope
against deduplication and cooldown rules before admitting to send.

Gate logic:
  1. Check dedupe: if dedupe_key already exists in prior state → block
  2. Check cooldown: if cooldown_key exists AND cooldown_until not expired → block
  3. Otherwise → pass

Features:
  - Deduplication by dedupe_key (exact match on SHA-256 hash)
  - Cooldown by cooldown_key with per-card_type cooldown windows
  - Cooldown expiry check (cooldown_until < now → pass)
  - Different card_types do NOT interfere with each other
  - Same asset different direction NOT blocked unless cooldown_key matched
  - Leak scanning on gate decisions
  - Full audit trail in gate_reasons

Constraints:
  - No external API calls
  - No real TG send
  - No daemon/loop/cron
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_dedupe_cooldown_gate_v112i import (
        load_envelopes_jsonl, load_prior_signal_state, normalize_gate_time,
        check_dedupe, check_cooldown, evaluate_signal_gate,
        evaluate_all_signal_gates, build_gate_decision, scan_gate_decision_leaks,
        COOLDOWN_POLICY, GATE_VERSION, SCHEMA_VERSION,
    )
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

GATE_VERSION = "v1.12-I"
SCHEMA_VERSION = "1.0.0"

CN_TZ = timezone(timedelta(hours=8))

# ── Cooldown Policy (hardcoded per card_type, minutes) ────────────────────────────

COOLDOWN_POLICY: dict[str, int] = {
    "price_oi_volume_anomaly": 60,
    "whale_position_alert": 90,
    "liquidation_pressure": 30,
    "multi_asset_market_sync": 45,
    "news_event_market_impact": 120,
}

VALID_GATE_STATUSES = frozenset([
    "pass",
    "blocked_dedupe",
    "blocked_cooldown",
    "blocked_invalid",
    "blocked_leak",
])

# ── Forbidden Terms for Leak Scan ─────────────────────────────────────────────

FORBIDDEN_DEBUG_TERMS = [
    "debug", "internal", "trace",
]

FORBIDDEN_SECRET_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

FORBIDDEN_PATH_TERMS = [
    "C:\\Users\\PC", "ai_relay_desk",
]

# Full wallet address pattern
WALLET_ADDRESS_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')


# ══════════════════════════════════════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════════════════════════════════════

def load_envelopes_jsonl(path: str | Path) -> list[dict]:
    """Load signal envelopes from a JSONL file.

    Each line is a JSON object representing a unified signal envelope.
    Returns a list of envelope dicts. Empty lines are skipped.
    Raises FileNotFoundError if the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Envelope JSONL not found: {path}")

    envelopes: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                env = json.loads(line)
                envelopes.append(env)
            except json.JSONDecodeError as e:
                print(f"  [WARN] Skipping malformed JSONL line: {e}")
    return envelopes


def load_prior_signal_state(path: str | Path) -> list[dict]:
    """Load prior signal state from a JSON file.

    Returns a list of prior state entry dicts.
    Raises FileNotFoundError if the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Prior signal state not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support both {"entries": [...]} and bare list formats
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entries", [])
    return []


# ══════════════════════════════════════════════════════════════════════════════════════
# Time Normalization
# ══════════════════════════════════════════════════════════════════════════════════════

def normalize_gate_time(ts: str | None) -> datetime:
    """Normalize a timestamp string to a timezone-aware datetime in UTC+8.

    Returns current time if ts is None or empty.
    """
    if not ts or not isinstance(ts, str):
        return datetime.now(CN_TZ)

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S+08:00",
        "%Y-%m-%dT%H:%M:%S UTC+8",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CN_TZ)
            return dt
        except ValueError:
            continue

    # Fallback: try ISO format
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CN_TZ)
        return dt
    except (ValueError, TypeError):
        pass

    return datetime.now(CN_TZ)


def _now_cn() -> datetime:
    """Return current time in UTC+8."""
    return datetime.now(CN_TZ)


def china_stamp() -> str:
    """Return current time in UTC+8 format string."""
    return _now_cn().strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ══════════════════════════════════════════════════════════════════════════════════════
# Dedupe Check
# ══════════════════════════════════════════════════════════════════════════════════════

def check_dedupe(
    envelope: dict,
    prior_state: list[dict],
    evaluated_at: datetime | None = None,
) -> dict:
    """Check if an envelope's dedupe_key already exists in prior state.

    A dedupe hit occurs when the envelope's dedupe_key exactly matches
    an existing entry's dedupe_key.

    Args:
        envelope: Signal envelope dict (must have dedupe_key).
        prior_state: List of prior state entry dicts.
        evaluated_at: Current time for the check (not used in dedupe check).

    Returns:
        Dict with:
          - hit: bool
          - matched_entry: dict | None (the matching prior state entry)
          - reason: str
    """
    dedupe_key = envelope.get("dedupe_key", "")
    if not dedupe_key:
        return {"hit": False, "matched_entry": None, "reason": "no dedupe_key in envelope"}

    for entry in prior_state:
        if entry.get("dedupe_key") == dedupe_key:
            return {
                "hit": True,
                "matched_entry": entry,
                "reason": f"dedupe_key already exists in prior state: {dedupe_key[:16]}...",
            }

    return {"hit": False, "matched_entry": None, "reason": "dedupe_key not found in prior state"}


# ══════════════════════════════════════════════════════════════════════════════════════
# Cooldown Check
# ══════════════════════════════════════════════════════════════════════════════════════

def check_cooldown(
    envelope: dict,
    prior_state: list[dict],
    evaluated_at: datetime | None = None,
) -> dict:
    """Check if an envelope's cooldown_key is active (not expired) in prior state.

    Cooldown logic:
      - Match by cooldown_key (same card_type + same assets + same direction).
      - If cooldown_until exists and is in the future → cooldown hit.
      - If cooldown_until is in the past (expired) → NOT a cooldown hit.
      - Different card_types produce different cooldown_keys → no interference.
      - Same asset different direction produces different cooldown_key → no interference
        (unless by coincidence the cooldown_key happens to match, which can't happen
        because direction is part of the cooldown_key composition).

    Args:
        envelope: Signal envelope dict (must have cooldown_key).
        prior_state: List of prior state entry dicts.
        evaluated_at: Current datetime for cooldown expiry comparison.

    Returns:
        Dict with:
          - hit: bool
          - matched_entry: dict | None
          - cooldown_until: str | None
          - reason: str
    """
    cooldown_key = envelope.get("cooldown_key", "")
    if not cooldown_key:
        return {
            "hit": False, "matched_entry": None, "cooldown_until": None,
            "reason": "no cooldown_key in envelope",
        }

    now = evaluated_at or _now_cn()

    for entry in prior_state:
        if entry.get("cooldown_key") != cooldown_key:
            continue

        cooldown_until_str = entry.get("cooldown_until", "")
        if not cooldown_until_str:
            # No cooldown_until — treat as active cooldown
            return {
                "hit": True, "matched_entry": entry,
                "cooldown_until": cooldown_until_str,
                "reason": f"cooldown_key hit, no expiry set: {cooldown_key[:16]}...",
            }

        cooldown_until = normalize_gate_time(cooldown_until_str)

        if cooldown_until > now:
            # Cooldown still active
            return {
                "hit": True, "matched_entry": entry,
                "cooldown_until": cooldown_until_str,
                "reason": (
                    f"cooldown_key hit, cooldown active until {cooldown_until_str}: "
                    f"{cooldown_key[:16]}..."
                ),
            }
        else:
            # Cooldown expired — this is NOT a hit
            return {
                "hit": False, "matched_entry": entry,
                "cooldown_until": cooldown_until_str,
                "reason": (
                    f"cooldown_key found but cooldown expired at {cooldown_until_str}: "
                    f"{cooldown_key[:16]}..."
                ),
            }

    return {
        "hit": False, "matched_entry": None, "cooldown_until": None,
        "reason": f"cooldown_key not found in prior state: {cooldown_key[:16]}...",
    }


# ══════════════════════════════════════════════════════════════════════════════════════
# Gate Decision Builder
# ══════════════════════════════════════════════════════════════════════════════════════

def build_gate_decision(
    signal_id: str,
    card_type: str,
    primary_assets: list[str],
    direction: str,
    dedupe_key: str,
    cooldown_key: str,
    payload_hash: str,
    gate_status: str,
    gate_reasons: list[str],
    dedupe_hit: bool,
    cooldown_hit: bool,
    cooldown_until: str | None,
    observed_at: str,
    evaluated_at: str,
    safety_flags: dict[str, Any] | None = None,
    envelope_safety: dict[str, Any] | None = None,
) -> dict:
    """Build a standardized gate decision record.

    Args:
        signal_id: Envelope signal_id.
        card_type: Card type from envelope.
        primary_assets: Asset list from envelope.
        direction: Direction from envelope.
        dedupe_key: Dedupe key from envelope.
        cooldown_key: Cooldown key from envelope.
        payload_hash: Payload hash from envelope.
        gate_status: One of pass / blocked_dedupe / blocked_cooldown / blocked_invalid / blocked_leak.
        gate_reasons: List of human-readable reason strings.
        dedupe_hit: True if dedupe check found a match.
        cooldown_hit: True if cooldown check found an active match.
        cooldown_until: ISO timestamp string when cooldown expires (or None).
        observed_at: Original observation timestamp from envelope.
        evaluated_at: When the gate was evaluated.
        safety_flags: Optional safety flags dict.
        envelope_safety: Optional envelope-level safety flags to inherit from.

    Returns:
        Gate decision dict.
    """
    if gate_status not in VALID_GATE_STATUSES:
        gate_status = "blocked_invalid"

    eligible_for_send = gate_status == "pass"

    # Merge safety flags
    merged_safety: dict[str, Any] = {
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
    }
    if envelope_safety:
        for k in merged_safety:
            if k in envelope_safety:
                merged_safety[k] = envelope_safety[k]
    if safety_flags:
        merged_safety.update(safety_flags)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "gate_version": GATE_VERSION,
        "signal_id": signal_id,
        "card_type": card_type,
        "primary_assets": primary_assets,
        "direction": direction,
        "dedupe_key": dedupe_key,
        "cooldown_key": cooldown_key,
        "payload_hash": payload_hash,
        "gate_status": gate_status,
        "gate_reasons": gate_reasons,
        "dedupe_hit": dedupe_hit,
        "cooldown_hit": cooldown_hit,
        "cooldown_until": cooldown_until,
        "eligible_for_send": eligible_for_send,
        "observed_at": observed_at,
        "evaluated_at": evaluated_at,
        "safety_flags": merged_safety,
    }

    return decision


# ══════════════════════════════════════════════════════════════════════════════════════
# Single Signal Gate Evaluation
# ══════════════════════════════════════════════════════════════════════════════════════

def evaluate_signal_gate(
    envelope: dict,
    prior_state: list[dict],
    evaluated_at: datetime | None = None,
) -> dict:
    """Evaluate a single signal envelope through the dedupe/cooldown gate.

    Steps:
      1. Validate envelope has required fields
      2. Check dedupe
      3. Check cooldown
      4. Determine gate_status
      5. Build decision

    Args:
        envelope: Signal envelope dict.
        prior_state: List of prior state entry dicts.
        evaluated_at: Current datetime. Uses real clock if None.

    Returns:
        Gate decision dict with gate_status, gate_reasons, etc.
    """
    now = evaluated_at or _now_cn()
    evaluated_at_str = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    signal_id = envelope.get("signal_id", "unknown")
    card_type = envelope.get("card_type", "unknown")
    primary_assets = envelope.get("primary_assets", [])
    direction = envelope.get("direction", "unknown")
    dedupe_key = envelope.get("dedupe_key", "")
    cooldown_key = envelope.get("cooldown_key", "")
    payload_hash = envelope.get("payload_hash", "")
    observed_at = envelope.get("observed_at", evaluated_at_str)
    envelope_safety = envelope.get("safety_flags", {})

    reasons: list[str] = []

    # ── Validate required fields ────────────────────────────────────────────
    if not dedupe_key or not cooldown_key or not signal_id or signal_id == "unknown":
        reasons.append("envelope missing required fields for gate evaluation")
        return build_gate_decision(
            signal_id=signal_id, card_type=card_type, primary_assets=primary_assets,
            direction=direction, dedupe_key=dedupe_key, cooldown_key=cooldown_key,
            payload_hash=payload_hash, gate_status="blocked_invalid",
            gate_reasons=reasons, dedupe_hit=False, cooldown_hit=False,
            cooldown_until=None, observed_at=observed_at,
            evaluated_at=evaluated_at_str, envelope_safety=envelope_safety,
        )

    # ── Check dedupe ───────────────────────────────────────────────────────
    dedupe_result = check_dedupe(envelope, prior_state, now)
    if dedupe_result["hit"]:
        reasons.append(dedupe_result["reason"])
        return build_gate_decision(
            signal_id=signal_id, card_type=card_type, primary_assets=primary_assets,
            direction=direction, dedupe_key=dedupe_key, cooldown_key=cooldown_key,
            payload_hash=payload_hash, gate_status="blocked_dedupe",
            gate_reasons=reasons, dedupe_hit=True, cooldown_hit=False,
            cooldown_until=None, observed_at=observed_at,
            evaluated_at=evaluated_at_str, envelope_safety=envelope_safety,
        )

    # ── Check cooldown ─────────────────────────────────────────────────────
    cooldown_result = check_cooldown(envelope, prior_state, now)
    cooldown_until = cooldown_result.get("cooldown_until")

    if cooldown_result["hit"]:
        reasons.append(cooldown_result["reason"])
        return build_gate_decision(
            signal_id=signal_id, card_type=card_type, primary_assets=primary_assets,
            direction=direction, dedupe_key=dedupe_key, cooldown_key=cooldown_key,
            payload_hash=payload_hash, gate_status="blocked_cooldown",
            gate_reasons=reasons, dedupe_hit=False, cooldown_hit=True,
            cooldown_until=cooldown_until, observed_at=observed_at,
            evaluated_at=evaluated_at_str, envelope_safety=envelope_safety,
        )

    # ── Cooldown expired or not found ──────────────────────────────────────
    if cooldown_result.get("matched_entry") is not None:
        # Cooldown was found but expired
        reasons.append(cooldown_result["reason"])
        reasons.append("cooldown expired — signal passes")

    # ── Pass ───────────────────────────────────────────────────────────────
    reasons.append("no active dedupe or cooldown block — signal passes")
    return build_gate_decision(
        signal_id=signal_id, card_type=card_type, primary_assets=primary_assets,
        direction=direction, dedupe_key=dedupe_key, cooldown_key=cooldown_key,
        payload_hash=payload_hash, gate_status="pass",
        gate_reasons=reasons, dedupe_hit=False, cooldown_hit=False,
        cooldown_until=cooldown_until, observed_at=observed_at,
        evaluated_at=evaluated_at_str, envelope_safety=envelope_safety,
    )


# ══════════════════════════════════════════════════════════════════════════════════════
# Batch Evaluation
# ══════════════════════════════════════════════════════════════════════════════════════

def evaluate_all_signal_gates(
    envelopes: list[dict],
    prior_state: list[dict],
    evaluated_at: datetime | None = None,
) -> list[dict]:
    """Evaluate all envelopes through the dedupe/cooldown gate.

    Each envelope is evaluated independently against the same prior state.
    The prior state is NOT mutated during evaluation — all envelopes see
    the same prior state snapshot.

    Args:
        envelopes: List of signal envelope dicts.
        prior_state: List of prior state entry dicts.
        evaluated_at: Current datetime. Uses real clock if None.

    Returns:
        List of gate decision dicts, one per envelope, in the same order.
    """
    decisions: list[dict] = []
    now = evaluated_at or _now_cn()

    for env in envelopes:
        decision = evaluate_signal_gate(env, prior_state, evaluated_at=now)
        decisions.append(decision)

    return decisions


# ══════════════════════════════════════════════════════════════════════════════════════
# Leak Scanning for Gate Decisions
# ══════════════════════════════════════════════════════════════════════════════════════

def scan_gate_decision_leaks(decision: dict) -> dict:
    """Scan a gate decision record for forbidden content.

    Checks:
      - Debug terms (debug, internal, trace)
      - Secret terms (secret, token, api_key, chat_id, password)
      - Path leaks (C:\\Users\\PC, ai_relay_desk)
      - Full wallet addresses

    Only scans human-visible string fields (gate_reasons, signal_id, etc.),
    NOT hash values.

    Args:
        decision: Gate decision dict.

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
    # Fields to scan (human-visible only, not hashes)
    scannable_fields = [
        str(decision.get("signal_id", "")),
        str(decision.get("card_type", "")),
        str(decision.get("direction", "")),
        str(decision.get("gate_status", "")),
        str(decision.get("evaluated_at", "")),
        str(decision.get("observed_at", "")),
        "; ".join(decision.get("gate_reasons", [])),
        "; ".join(str(a) for a in decision.get("primary_assets", [])),
    ]

    check_text = " ".join(scannable_fields).lower()

    # ── Debug term scan ──────────────────────────────────────────────────
    debug_found: list[str] = []
    for term in FORBIDDEN_DEBUG_TERMS:
        if term.lower() in check_text:
            debug_found.append(term)

    # ── Secret term scan ─────────────────────────────────────────────────
    secret_found: list[str] = []
    for term in FORBIDDEN_SECRET_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)
    for term in FORBIDDEN_PATH_TERMS:
        if term.lower() in check_text:
            secret_found.append(term)

    # ── Wallet address scan ──────────────────────────────────────────────
    wallet_leak_details: list[str] = []
    for field_text in scannable_fields:
        matches = WALLET_ADDRESS_PATTERN.findall(field_text)
        wallet_leak_details.extend(matches)
    full_wallet_leak = len(wallet_leak_details) > 0

    # ── Deduplicate ─────────────────────────────────────────────────────
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
# Utility
# ══════════════════════════════════════════════════════════════════════════════════════

def _sha256_hex(raw: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
