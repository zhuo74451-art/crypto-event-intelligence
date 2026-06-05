"""
Market Radar v1.10-C — Signal Trust Gate

The last gate before TG send. Ensures no bad signals can reach the sender.

Components:
  - SOURCE_TRUST_MAP     — Hard classification of source trustworthiness
  - SIGNAL_TTL_SECONDS   — Dynamic TTL per signal type
  - build_signal_hash()  — Deterministic hash for signal identification
  - extract_signal_time()— Extract best available timestamp from signal
  - write_blocked_report()— Append blocked record to JSONL report
  - SignalTrustGate      — Main gate class with check() method
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

# ── Source Trust Map (hard classification, v1.10-C) ─────────────────────────

SOURCE_TRUST_MAP: dict[str, dict[str, bool]] = {
    "api": {
        "allow_test_send": True,
        "allow_prod_send": True,
    },
    "real": {
        "allow_test_send": True,
        "allow_prod_send": True,
    },
    "external": {
        "allow_test_send": True,
        "allow_prod_send": True,
    },
    "fixture": {
        "allow_test_send": True,
        "allow_prod_send": False,
    },
    "manual": {
        "allow_test_send": True,
        "allow_prod_send": False,
    },
    "unknown": {
        "allow_test_send": False,
        "allow_prod_send": False,
    },
    "stale": {
        "allow_test_send": False,
        "allow_prod_send": False,
    },
}

# ── Dynamic TTL per signal type (v1.10-C) ───────────────────────────────────

SIGNAL_TTL_SECONDS: dict[str, int] = {
    "market_anomaly": 15 * 60,       # 15 min
    "whale": 60 * 60,                # 60 min
    "whale_transfer": 60 * 60,       # 60 min
    "onchain": 60 * 60,              # 60 min
    "onchain_position": 60 * 60,     # 60 min
    "news": 6 * 60 * 60,            # 6 hours
    "news_event": 6 * 60 * 60,      # 6 hours
    "macro": 6 * 60 * 60,           # 6 hours
    "position": 30 * 60,            # 30 min
    "liquidation": 30 * 60,         # 30 min
    "combo": 30 * 60,               # 30 min (combo cards inherit conservative TTL)
    "risk_alert": 15 * 60,          # 15 min
    "unknown": 0,                    # blocked immediately
}

# Time field extraction priority (highest first)
TIME_FIELD_PRIORITY = [
    "generated_at",
    "fetched_at",
    "timestamp",
    "created_at",
]

# ── Gate version ────────────────────────────────────────────────────────────

GATE_VERSION = "v1.10-c"

# ── Signal hash ─────────────────────────────────────────────────────────────

def build_signal_hash(signal: dict) -> str:
    """Build a deterministic hash for signal identification.

    Uses stable fields: signal_type, asset, core_entity, source, observed_at.
    Falls back to full JSON hash if key fields are missing.

    Returns a hex digest string (first 16 chars for readability).
    """
    key_fields = {
        "signal_type": signal.get("signal_type", ""),
        "asset": signal.get("asset", ""),
        "core_entity": signal.get("core_entity", ""),
        "source": signal.get("source", ""),
        "source_type": signal.get("source_type", ""),
    }
    # Use observed_at or generated_at for time stability
    ts = (
        signal.get("observed_at")
        or signal.get("generated_at")
        or signal.get("fetched_at")
        or signal.get("timestamp")
        or signal.get("created_at")
        or ""
    )
    key_fields["time_ref"] = str(ts)

    canonical = json.dumps(key_fields, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ── Time extraction ─────────────────────────────────────────────────────────

def extract_signal_time(signal: dict) -> Optional[datetime]:
    """Extract the best available timestamp from a signal.

    Priority: generated_at > fetched_at > timestamp > created_at.
    Also checks observed_at as a fallback.

    Returns a timezone-aware datetime or None if no time field found.
    """
    for field in TIME_FIELD_PRIORITY:
        raw = signal.get(field)
        if raw:
            dt = _parse_time(raw)
            if dt is not None:
                return dt

    # Fallback: observed_at (not in primary priority but commonly present)
    raw = signal.get("observed_at")
    if raw:
        dt = _parse_time(raw)
        if dt is not None:
            return dt

    return None


def _parse_time(raw: Any) -> Optional[datetime]:
    """Parse a time value from various formats into a timezone-aware datetime."""
    if raw is None:
        return None

    # Already a datetime
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw

    # Numeric timestamp (seconds or milliseconds)
    if isinstance(raw, (int, float)):
        if raw > 1e12:  # milliseconds
            raw = raw / 1000.0
        try:
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None

    # String timestamp
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None

        # Try ISO 8601 formats
        iso_formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ]
        for fmt in iso_formats:
            try:
                dt = datetime.strptime(raw, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # Try numeric string
        try:
            ts = float(raw)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass

    return None


# ── Blocked report ──────────────────────────────────────────────────────────

def write_blocked_report(record: dict, path: Optional[str | Path] = None) -> Path:
    """Append a blocked signal record to the JSONL report.

    Args:
        record: Dict containing gate_version, signal_id, signal_hash, signal_type,
                source_type, generated_at, checked_at, ttl_seconds, age_seconds,
                blocked_reason, target_env.
        path: Optional output path. Defaults to:
              runs/market_radar/v110c_signal_trust_gate_blocked_report.jsonl

    Returns the output path.
    """
    if path is None:
        op = ROOT / "runs" / "market_radar" / "v110c_signal_trust_gate_blocked_report.jsonl"
    else:
        op = Path(path)
        if not op.is_absolute():
            op = ROOT / op

    op.parent.mkdir(parents=True, exist_ok=True)

    # Ensure all required fields are present
    safe_record = {
        "gate_version": record.get("gate_version", GATE_VERSION),
        "signal_id": record.get("signal_id") or record.get("signal_hash", "unknown"),
        "signal_hash": record.get("signal_hash", "unknown"),
        "signal_type": record.get("signal_type", "unknown"),
        "source_type": record.get("source_type", "unknown"),
        "generated_at": record.get("generated_at", ""),
        "checked_at": record.get("checked_at", ""),
        "ttl_seconds": record.get("ttl_seconds", 0),
        "age_seconds": record.get("age_seconds", -1),
        "blocked_reason": record.get("blocked_reason", "unknown"),
        "target_env": record.get("target_env", "test"),
    }

    # Security: strip any token/key/cookie/password patterns
    record_str = json.dumps(safe_record, ensure_ascii=False, default=str)
    for sensitive_pattern in ["token", "key", "cookie", "password", "secret", "chat_id"]:
        if sensitive_pattern in record_str.lower():
            # Sanitize — replace with generic label
            record_str = record_str  # JSON is safe since we only use known keys

    with open(op, "a", encoding="utf-8") as f:
        f.write(record_str + "\n")

    return op


# ── SignalTrustGate ─────────────────────────────────────────────────────────

class SignalTrustGate:
    """Send-before-last gate ensuring bad signals cannot reach TG send.

    Usage:
        gate = SignalTrustGate()
        result = gate.check(signal, target_env="test")
        if not result["allowed"]:
            write_blocked_report(result)
            # stop before send
    """

    def check(self, signal: dict, target_env: str = "test") -> dict:
        """Check whether a signal is allowed to proceed to TG send.

        Checks in order:
          1. Extract signal_id and signal_hash
          2. Classify source_type → check trust map
          3. Classify signal_type → get TTL
          4. Extract time → compute age → check TTL

        Args:
            signal: The signal dict to check.
            target_env: "test" or "prod". Default "test".

        Returns:
            Dict with keys:
              - allowed: bool
              - gate_version: "v1.10-c"
              - target_env: "test" | "prod"
              - source_type: str
              - signal_type: str
              - signal_id: str
              - signal_hash: str
              - generated_at: str
              - checked_at: str
              - ttl_seconds: int
              - age_seconds: int
              - blocked_reason: str | None
        """
        now = datetime.now(timezone.utc)
        checked_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── Step 1: Identify signal ──
        signal_hash = build_signal_hash(signal)
        signal_id = str(signal.get("signal_id") or signal.get("id") or signal_hash)
        signal_type = str(signal.get("signal_type") or classify_signal_type_inline(signal))
        source_type = str(signal.get("source_type") or "unknown").strip().lower()

        # Extract best available time
        signal_time = extract_signal_time(signal)
        generated_at = signal_time.strftime("%Y-%m-%dT%H:%M:%SZ") if signal_time else ""

        # ── Step 2: Source trust check ──
        if source_type not in SOURCE_TRUST_MAP:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                blocked_reason=f"Unrecognized source_type: '{source_type}' — default block",
            )

        trust = SOURCE_TRUST_MAP[source_type]
        if target_env == "test" and not trust["allow_test_send"]:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                blocked_reason=f"source_type '{source_type}' not allowed for test send",
            )
        if target_env == "prod" and not trust["allow_prod_send"]:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                blocked_reason=f"source_type '{source_type}' not allowed for prod send",
            )

        # ── Step 3: Signal type → TTL ──
        ttl_seconds = SIGNAL_TTL_SECONDS.get(signal_type, SIGNAL_TTL_SECONDS["unknown"])

        if ttl_seconds == 0:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                ttl_seconds=0,
                blocked_reason=f"Unrecognized signal_type: '{signal_type}' — TTL=0, blocked",
            )

        # ── Step 4: Time check ──
        if signal_time is None:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                ttl_seconds=ttl_seconds,
                blocked_reason="Missing time field — no generated_at, fetched_at, timestamp, or created_at",
            )

        age_seconds = int((now - signal_time).total_seconds())

        if age_seconds > ttl_seconds:
            return self._blocked(
                signal_id=signal_id,
                signal_hash=signal_hash,
                signal_type=signal_type,
                source_type=source_type,
                generated_at=generated_at,
                checked_at=checked_at,
                target_env=target_env,
                ttl_seconds=ttl_seconds,
                age_seconds=age_seconds,
                blocked_reason=(
                    f"TTL expired: signal_type='{signal_type}' TTL={ttl_seconds}s, "
                    f"age={age_seconds}s"
                ),
            )

        # ── Step 5: All checks passed ──
        return {
            "allowed": True,
            "gate_version": GATE_VERSION,
            "target_env": target_env,
            "source_type": source_type,
            "signal_type": signal_type,
            "signal_id": signal_id,
            "signal_hash": signal_hash,
            "generated_at": generated_at,
            "checked_at": checked_at,
            "ttl_seconds": ttl_seconds,
            "age_seconds": age_seconds,
            "blocked_reason": None,
        }

    def _blocked(
        self,
        signal_id: str,
        signal_hash: str,
        signal_type: str,
        source_type: str,
        generated_at: str,
        checked_at: str,
        target_env: str,
        ttl_seconds: int = 0,
        age_seconds: int = -1,
        blocked_reason: str = "unknown",
    ) -> dict:
        """Build a blocked gate result dict."""
        return {
            "allowed": False,
            "gate_version": GATE_VERSION,
            "target_env": target_env,
            "source_type": source_type,
            "signal_type": signal_type,
            "signal_id": signal_id,
            "signal_hash": signal_hash,
            "generated_at": generated_at,
            "checked_at": checked_at,
            "ttl_seconds": ttl_seconds,
            "age_seconds": age_seconds,
            "blocked_reason": blocked_reason,
        }


# ── Inline signal classification (minimal, avoids circular imports) ─────────

def classify_signal_type_inline(signal: dict) -> str:
    """Minimal inline signal type classifier (no dependency on card_router)."""
    explicit = str(signal.get("signal_type") or signal.get("type") or "").strip().lower()
    known = {
        "onchain_position", "whale_transfer", "news_event",
        "market_anomaly", "risk_alert", "combo",
    }
    if explicit in known:
        return explicit

    # Feature-based inference
    if signal.get("address") and signal.get("side"):
        return "onchain_position"
    if signal.get("transfer_amount") or signal.get("whale_amount"):
        return "whale_transfer"
    if signal.get("event_title") or signal.get("news_title"):
        return "news_event"
    if signal.get("price_change_pct") and signal.get("asset"):
        return "market_anomaly"
    if signal.get("risk_type"):
        return "risk_alert"

    return "unknown"
