"""
Market Radar v1.11-F — Same-Asset Cooldown Gate 同资产冷却门控

Implements independent same-asset cooldown logic as a separate layer between
SignalValueGate and pre_send_gate. SignalValueGate answers "is this signal
valuable?"; CooldownGate answers "should we send this now, or did we just
send for this asset?"

Design principles (v1.11-F):
  1. Separate concern — cooldown is NOT part of SignalValueGate.
  2. First occurrence per asset always passes (within lookback window).
  3. Subsequent occurrences within cooldown window are suppressed UNLESS
     the value_score improves significantly (upgrade_override).
  4. Cooldown state is in-memory and returned to caller — no file I/O,
     no database, no persistence by default.
  5. Deterministic rules only — no AI, no external API, no paid services.

Cooldown rules:
  - default window: 10 minutes (configurable)
  - upgrade_override delta: 15 points (configurable)
  - If value_score improves by >= delta → upgrade_override (allow)
  - If value_score does NOT improve significantly → cooldown_suppress
  - If cooldown window has expired → allow (reset window)
  - Different assets are tracked independently

Usage:
    from scripts.market_radar_same_asset_cooldown_gate_v111f import (
        evaluate_cooldown, CooldownState, COOLDOWN_GATE_VERSION,
    )

    state = CooldownState()
    for signal, value_result in batch:
        cooldown_result = evaluate_cooldown(signal, value_result, state)
        state.apply(cooldown_result["updated_state"])
        if cooldown_result["allowed"]:
            # proceed to pre_send_gate
            pass

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

COOLDOWN_GATE_VERSION = "v1.11-f"

# ── Default configuration ───────────────────────────────────────────────────────

DEFAULT_COOLDOWN_WINDOW_MINUTES = 10
DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA = 15


# ── CooldownState ───────────────────────────────────────────────────────────────

class CooldownState:
    """Per-asset cooldown state tracker.

    Tracks the last time each asset was allowed through SignalValueGate,
    plus the value_score at that time and the total occurrence count.

    This is a plain Python object — no persistence, no DB, no file I/O.
    The caller is responsible for serializing if needed.

    State shape (internal):
        {
            "BTC": {
                "last_allowed_at": "2026-06-04T19:00:00+08:00",
                "last_value_score": 75,
                "occurrence_count": 2,
                "last_decision": "allow",
            },
            ...
        }
    """

    def __init__(self, initial_state: dict | None = None):
        self._assets: dict[str, dict] = {}
        if initial_state and isinstance(initial_state, dict):
            # Shallow copy to avoid mutating caller's dict
            for asset, entry in initial_state.items():
                if isinstance(entry, dict):
                    self._assets[asset] = dict(entry)

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self, asset: str) -> dict | None:
        """Get cooldown entry for an asset, or None if never seen."""
        return self._assets.get(asset)

    def record(self, asset: str, value_score: int, decision: str,
               timestamp: str | None = None) -> None:
        """Record that an asset was allowed through the cooldown gate.

        Increments occurrence_count or initializes to 1 on first record.
        """
        if asset not in self._assets:
            self._assets[asset] = {
                "last_allowed_at": timestamp or _now_iso(),
                "last_value_score": value_score,
                "occurrence_count": 1,
                "last_decision": decision,
            }
        else:
            entry = self._assets[asset]
            entry["last_allowed_at"] = timestamp or _now_iso()
            entry["last_value_score"] = value_score
            entry["occurrence_count"] = entry.get("occurrence_count", 0) + 1
            entry["last_decision"] = decision

    def record_suppression(self, asset: str, value_score: int,
                           timestamp: str | None = None) -> None:
        """Record a suppression event (does NOT reset the cooldown window).

        Increments the suppression counter for observability.
        """
        if asset not in self._assets:
            self._assets[asset] = {
                "last_allowed_at": None,
                "last_value_score": value_score,
                "occurrence_count": 1,
                "suppression_count": 1,
                "last_decision": "cooldown_suppress",
            }
        else:
            entry = self._assets[asset]
            entry["suppression_count"] = entry.get("suppression_count", 0) + 1
            entry["occurrence_count"] = entry.get("occurrence_count", 0) + 1
            entry["last_decision"] = "cooldown_suppress"

    def apply(self, updated_state: dict) -> None:
        """Apply an updated state dict (from evaluate_cooldown result)."""
        if not isinstance(updated_state, dict):
            return
        for asset, entry in updated_state.items():
            if isinstance(entry, dict):
                self._assets[asset] = dict(entry)

    def is_empty(self) -> bool:
        """Return True if no assets have been tracked."""
        return len(self._assets) == 0

    def reset(self) -> None:
        """Clear all cooldown state."""
        self._assets.clear()

    def to_dict(self) -> dict:
        """Export current state as a plain dict (for serialization)."""
        return {asset: dict(entry) for asset, entry in self._assets.items()}

    def __repr__(self) -> str:
        return f"CooldownState(assets={list(self._assets.keys())})"

    def __len__(self) -> int:
        return len(self._assets)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current time in ISO 8601 with timezone (UTC+8 / China)."""
    cn_tz = timezone(timedelta(hours=8))
    return datetime.now(cn_tz).isoformat()


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string to a datetime object.

    Returns None if ts is None/empty or parsing fails.
    """
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Handle both offset-aware and offset-naive formats
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            # Treat naive timestamps as UTC+8
            cn_tz = timezone(timedelta(hours=8))
            dt = dt.replace(tzinfo=cn_tz)
        return dt
    except (ValueError, TypeError):
        return None


def _extract_asset(signal: dict) -> str:
    """Extract asset symbol from signal dict.

    Tries multiple field names and normalizes to uppercase string.
    Returns empty string if not found.
    """
    asset = signal.get("asset") or signal.get("core_entity") or signal.get("symbol") or ""
    if not asset:
        return ""
    return str(asset).strip().upper()


def _extract_value_score(value_result: dict | None) -> int:
    """Extract value_score from a SignalValueGate result dict.

    Returns 0 if value_result is None or missing the field.
    """
    if not isinstance(value_result, dict):
        return 0
    score = value_result.get("value_score", 0)
    if isinstance(score, (int, float)):
        return int(score)
    return 0


def _extract_decision(value_result: dict | None) -> str:
    """Extract the gate decision from a SignalValueGate result dict.

    Returns "unknown" if value_result is None or missing the field.
    """
    if not isinstance(value_result, dict):
        return "unknown"
    return str(value_result.get("decision", "unknown")).strip().lower()


def _parse_cooldown_window_minutes(config: dict | None) -> int:
    """Parse cooldown_window_minutes from config, with validation."""
    if not isinstance(config, dict):
        return DEFAULT_COOLDOWN_WINDOW_MINUTES
    val = config.get("cooldown_window_minutes", DEFAULT_COOLDOWN_WINDOW_MINUTES)
    if isinstance(val, (int, float)) and val > 0:
        return int(val)
    return DEFAULT_COOLDOWN_WINDOW_MINUTES


def _parse_upgrade_delta(config: dict | None) -> int:
    """Parse upgrade_override_score_delta from config, with validation."""
    if not isinstance(config, dict):
        return DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA
    val = config.get("upgrade_override_score_delta", DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA)
    if isinstance(val, (int, float)) and val > 0:
        return int(val)
    return DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA


# ── Main gate function ──────────────────────────────────────────────────────────

def evaluate_cooldown(
    signal: dict,
    signal_value_result: dict | None = None,
    cooldown_state: CooldownState | dict | None = None,
    config: dict | None = None,
    current_time: str | None = None,
) -> dict:
    """Evaluate whether a signal should be suppressed by the same-asset cooldown.

    This is the core function. It checks whether the signal's asset was recently
    allowed through the gate, and if so, whether this repeat should be suppressed
    or allowed as an upgrade.

    Args:
        signal: Signal dict. Expected fields:
            - asset: str — the asset symbol (required for tracking)
            - core_entity: str — fallback for asset
            - symbol: str — fallback for asset
        signal_value_result: Output from SignalValueGate.evaluate_signal_value().
            Expected fields: decision, value_score.
            If None, cooldown gate will pass the signal (conservative: no cooldown
            without value context).
        cooldown_state: Current cooldown state — either a CooldownState instance
            or a plain dict. If None, a fresh state is created.
        config: Optional config overrides:
            - cooldown_window_minutes: int (default 10)
            - upgrade_override_score_delta: int (default 15)
        current_time: Optional ISO 8601 timestamp for "now". If None, uses real
            clock. Useful for deterministic testing.

    Returns:
        Dict with keys:
          - allowed: bool — True if signal may proceed to send
          - decision: "allow" | "cooldown_suppress" | "upgrade_override"
          - cooldown_reason: str — human-readable explanation
          - cooldown_state: dict — the updated state (for caller to persist)
          - asset: str — the extracted asset symbol
          - value_score: int — the signal's value score
          - previous_value_score: int | None — score from previous occurrence
          - minutes_since_last: float | None — minutes elapsed since last allow
          - occurrence_count: int — how many times this asset has been seen
          - cooldown_config: dict — effective config used
          - gate_version: str — "v1.11-f"

    Security: No API calls, no credentials, no network access.
    """
    # ── Parse config ──
    cooldown_window_minutes = _parse_cooldown_window_minutes(config)
    upgrade_delta = _parse_upgrade_delta(config)

    effective_config = {
        "cooldown_window_minutes": cooldown_window_minutes,
        "upgrade_override_score_delta": upgrade_delta,
    }

    # ── Extract asset ──
    asset = _extract_asset(signal)
    if not asset or len(asset) < 1:
        return {
            "allowed": True,
            "decision": "allow",
            "cooldown_reason": "no asset identifier — cooldown not applicable",
            "cooldown_state": cooldown_state.to_dict() if isinstance(cooldown_state, CooldownState) else (cooldown_state or {}),
            "asset": asset or "unknown",
            "value_score": 0,
            "previous_value_score": None,
            "minutes_since_last": None,
            "occurrence_count": 0,
            "cooldown_config": effective_config,
            "gate_version": COOLDOWN_GATE_VERSION,
        }

    # ── Extract value context ──
    value_score = _extract_value_score(signal_value_result)
    signal_decision = _extract_decision(signal_value_result)

    # If the signal was blocked by SignalValueGate, skip cooldown check
    if signal_decision == "block":
        return {
            "allowed": False,
            "decision": "cooldown_suppress",
            "cooldown_reason": f"Signal blocked by value gate — cooldown not evaluated (asset={asset})",
            "cooldown_state": cooldown_state.to_dict() if isinstance(cooldown_state, CooldownState) else (cooldown_state or {}),
            "asset": asset,
            "value_score": value_score,
            "previous_value_score": None,
            "minutes_since_last": None,
            "occurrence_count": 0,
            "cooldown_config": effective_config,
            "gate_version": COOLDOWN_GATE_VERSION,
        }

    # ── Normalize cooldown_state ──
    if isinstance(cooldown_state, CooldownState):
        state = cooldown_state
    elif isinstance(cooldown_state, dict):
        state = CooldownState(cooldown_state)
    else:
        state = CooldownState()

    # ── Resolve current time ──
    now_ts = current_time or _now_iso()
    now_dt = _parse_timestamp(now_ts)
    if now_dt is None:
        now_dt = datetime.now(timezone(timedelta(hours=8)))

    # ── Check cooldown ──
    previous = state.get(asset)

    if previous is None:
        # First occurrence — always allow
        state.record(asset, value_score, "allow", now_ts)
        return {
            "allowed": True,
            "decision": "allow",
            "cooldown_reason": f"First occurrence of {asset} — no cooldown applied",
            "cooldown_state": state.to_dict(),
            "asset": asset,
            "value_score": value_score,
            "previous_value_score": None,
            "minutes_since_last": None,
            "occurrence_count": 1,
            "cooldown_config": effective_config,
            "gate_version": COOLDOWN_GATE_VERSION,
        }

    # ── Previous occurrence exists — check time window ──
    last_allowed_at = previous.get("last_allowed_at")
    previous_score = previous.get("last_value_score", 0)
    previous_count = previous.get("occurrence_count", 1)

    last_dt = _parse_timestamp(last_allowed_at)
    minutes_since_last: float | None = None

    if last_dt is not None:
        delta = now_dt - last_dt
        minutes_since_last = delta.total_seconds() / 60.0

        if minutes_since_last > cooldown_window_minutes:
            # Cooldown window expired — allow and reset
            state.record(asset, value_score, "allow", now_ts)
            return {
                "allowed": True,
                "decision": "allow",
                "cooldown_reason": (
                    f"Cooldown window expired for {asset} "
                    f"({minutes_since_last:.1f} min since last > {cooldown_window_minutes} min window) — allow"
                ),
                "cooldown_state": state.to_dict(),
                "asset": asset,
                "value_score": value_score,
                "previous_value_score": previous_score,
                "minutes_since_last": round(minutes_since_last, 1),
                "occurrence_count": previous_count + 1,
                "cooldown_config": effective_config,
                "gate_version": COOLDOWN_GATE_VERSION,
            }

    # ── Within cooldown window — check upgrade override ──
    score_delta = value_score - previous_score

    if score_delta >= upgrade_delta:
        # Value score improved significantly — upgrade override
        state.record(asset, value_score, "upgrade_override", now_ts)
        return {
            "allowed": True,
            "decision": "upgrade_override",
            "cooldown_reason": (
                f"Upgrade override for {asset}: value_score improved from "
                f"{previous_score} → {value_score} (Δ+{score_delta} >= {upgrade_delta}) "
                f"within cooldown window — allow as upgrade"
            ),
            "cooldown_state": state.to_dict(),
            "asset": asset,
            "value_score": value_score,
            "previous_value_score": previous_score,
            "minutes_since_last": round(minutes_since_last, 1) if minutes_since_last is not None else None,
            "occurrence_count": previous_count + 1,
            "cooldown_config": effective_config,
            "gate_version": COOLDOWN_GATE_VERSION,
        }

    # ── Within cooldown window, no significant improvement → suppress ──
    state.record_suppression(asset, value_score, now_ts)
    return {
        "allowed": False,
        "decision": "cooldown_suppress",
        "cooldown_reason": (
            f"Same-asset cooldown for {asset}: last allowed {minutes_since_last:.1f} min ago "
            f"(window={cooldown_window_minutes} min). Value score {value_score} vs previous "
            f"{previous_score} (Δ{score_delta:+d} < {upgrade_delta} required for override). "
            f"Suppressing repeat."
        ) if minutes_since_last is not None else (
            f"Same-asset cooldown for {asset}: repeat within cooldown window. "
            f"Value score {value_score} vs previous {previous_score} "
            f"(Δ{score_delta:+d} < {upgrade_delta} required for override). Suppressing repeat."
        ),
        "cooldown_state": state.to_dict(),
        "asset": asset,
        "value_score": value_score,
        "previous_value_score": previous_score,
        "minutes_since_last": round(minutes_since_last, 1) if minutes_since_last is not None else None,
        "occurrence_count": previous_count + 1,
        "cooldown_config": effective_config,
        "gate_version": COOLDOWN_GATE_VERSION,
    }


# ── Batch helper ────────────────────────────────────────────────────────────────

def evaluate_cooldown_batch(
    signals_and_results: list[tuple[dict, dict | None]],
    cooldown_state: CooldownState | dict | None = None,
    config: dict | None = None,
    base_time: str | None = None,
    time_step_minutes: float = 1.0,
) -> list[dict]:
    """Evaluate cooldown for an ordered batch of signals.

    Each signal is evaluated in sequence, with the cooldown state updated
    after each one. This simulates real-time processing where signals arrive
    with time gaps between them.

    Args:
        signals_and_results: List of (signal, value_result) tuples.
        cooldown_state: Initial cooldown state.
        config: Cooldown config overrides.
        base_time: ISO 8601 starting timestamp. If None, uses real clock
            (all signals get the same time — not realistic for batch test).
        time_step_minutes: Minutes to advance the clock between signals
            when base_time is provided.

    Returns:
        List of cooldown result dicts, one per input signal.
    """
    if isinstance(cooldown_state, CooldownState):
        state = cooldown_state
    elif isinstance(cooldown_state, dict):
        state = CooldownState(cooldown_state)
    else:
        state = CooldownState()

    results: list[dict] = []

    # Resolve base_time
    if base_time:
        base_dt = _parse_timestamp(base_time)
    else:
        base_dt = None

    for i, (signal, value_result) in enumerate(signals_and_results):
        # Compute current time for this signal
        if base_dt is not None:
            signal_time = base_dt + timedelta(minutes=time_step_minutes * i)
            cn_tz = timezone(timedelta(hours=8))
            current_time = signal_time.astimezone(cn_tz).isoformat()
        else:
            current_time = None  # use real clock

        result = evaluate_cooldown(
            signal=signal,
            signal_value_result=value_result,
            cooldown_state=state,
            config=config,
            current_time=current_time,
        )

        # Apply the result's state back to the shared state
        state.apply(result["cooldown_state"])

        results.append(result)

    return results
