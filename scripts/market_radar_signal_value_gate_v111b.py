"""
Market Radar v1.11-D — Multi-Factor Signal Value Gate 多因子信号价值门控（已校准）

Solves the core issue identified in v1.11-C replay: multi_asset_sync was triggering
too easily in large batch contexts, inflating the allow rate to 87% with zero observe
decisions. This calibration tightens multi_asset_sync to require OI/volume backup
and ensures the observe layer can actually fire.

Calibration changes from v1.11-B/C:
  1. multi_asset_sync no longer auto-allows with strong_price_move alone —
     must have OI or volume non-zero as backing.
  2. fixture signals excluded from multi_asset_sync counting (both as target
     and in context).
  3. context.real_same_direction_asset_count respected if present.
  4. observe layer now reachable when price_move hit but fields are insufficient.
  5. decision matrix refined to prevent "batch size inflation" effect.

Deterministic rules only — no AI, no external API calls, no paid services.

Usage:
    from scripts.market_radar_signal_value_gate_v111b import evaluate_signal_value

    result = evaluate_signal_value(signal, context)
    if result["allowed"]:
        # proceed to send pipeline
    elif result["decision"] == "observe":
        # log for monitoring, do not send
    else:
        # block entirely

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
"""

from __future__ import annotations

from typing import Any

GATE_VERSION = "v1.11-d"


# ── Field extractors ──────────────────────────────────────────────────────────

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely parse a value to float.

    Handles: None, str, int, float, bool, and formatted strings like "-7.24%".
    Returns default if parsing fails.
    """
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


def _is_nonzero(value: Any) -> bool:
    """Check if a value is present and meaningfully non-zero."""
    v = _safe_float(value)
    return abs(v) > 1e-10


def _extract_asset(signal: dict) -> str:
    """Extract asset symbol from signal."""
    return str(signal.get("asset") or signal.get("core_entity") or "unknown")


def _extract_signal_type(signal: dict) -> str:
    """Extract signal_type from signal."""
    return str(signal.get("signal_type") or "unknown").strip().lower()


def _is_fixture(signal: dict) -> bool:
    """Check if a signal is a fixture (not real market data).

    Respects explicit is_fixture flag and source_type="fixture" fallback.
    """
    if signal.get("is_fixture") in (True, "true", "True"):
        return True
    if str(signal.get("source_type", "")).lower() == "fixture":
        return True
    return False


# ── Factor detectors ──────────────────────────────────────────────────────────

def _detect_price_move(signal: dict) -> dict:
    """Detect price movement and classify strength.

    Returns dict with:
      - hit: bool — abs(price_change_pct) >= 5
      - strong: bool — abs(price_change_pct) >= 8
      - value: float — the raw price_change_pct value
    """
    pct = _safe_float(signal.get("price_change_pct"))
    abs_pct = abs(pct)
    return {
        "hit": abs_pct >= 5.0,
        "strong": abs_pct >= 8.0,
        "value": pct,
    }


def _detect_oi_confirmation(signal: dict) -> dict:
    """Detect open interest confirmation.

    Returns dict with:
      - hit: bool — open_interest present and non-zero
      - missing: bool — field absent or None
      - value: float
    """
    raw = signal.get("open_interest") or signal.get("oi") or signal.get("oi_usd")
    if raw is None and "open_interest" not in signal and "oi" not in signal and "oi_usd" not in signal:
        return {"hit": False, "missing": True, "value": 0.0}
    if raw is None:
        return {"hit": False, "missing": True, "value": 0.0}
    v = _safe_float(raw)
    return {"hit": abs(v) > 1e-10, "missing": False, "value": v}


def _detect_volume_confirmation(signal: dict) -> dict:
    """Detect volume confirmation.

    Returns dict with:
      - hit: bool — volume present and non-zero
      - missing: bool — field absent or None
      - value: float
    """
    raw = signal.get("volume") or signal.get("dayNtlVlm") or signal.get("volume_24h")
    if raw is None and "volume" not in signal and "dayNtlVlm" not in signal and "volume_24h" not in signal:
        return {"hit": False, "missing": True, "value": 0.0}
    if raw is None:
        return {"hit": False, "missing": True, "value": 0.0}
    v = _safe_float(raw)
    return {"hit": abs(v) > 1e-10, "missing": False, "value": v}


def _detect_funding_extreme(signal: dict) -> dict:
    """Detect funding rate extremity.

    Returns dict with:
      - hit: bool — funding present and abs(funding) >= 0.01
      - missing: bool — field absent or None
      - near_zero: bool — funding present but very close to 0 (|funding| < 0.0001)
      - value: float
    """
    raw = signal.get("funding") or signal.get("funding_rate")
    if raw is None and "funding" not in signal and "funding_rate" not in signal:
        return {"hit": False, "missing": True, "near_zero": False, "value": 0.0}
    if raw is None:
        return {"hit": False, "missing": True, "near_zero": False, "value": 0.0}
    v = _safe_float(raw)
    near_zero = abs(v) < 0.0001
    return {
        "hit": abs(v) >= 0.01,
        "missing": False,
        "near_zero": near_zero,
        "value": v,
    }


def _detect_multi_asset_sync(signal: dict, context: dict | None) -> dict:
    """Detect multi-asset synchronization (v1.11-D calibrated).

    v1.11-D changes:
      - Fixture signals are NOT counted in the same-direction tally.
      - context.real_same_direction_asset_count is respected if present.
      - If the target signal itself is a fixture, multi_asset_sync is suppressed
        (hit=False) unless context has real_same_direction_asset_count >= 3.

    Returns dict with:
      - hit: bool — >= 3 real assets in same direction
      - count: int — number of same-direction real assets (including self if real)
      - total_count: int — total same-direction including fixtures
      - direction: str — "up", "down", or "neutral"
      - fixture_target: bool — True if the target signal is a fixture
    """
    pct = _safe_float(signal.get("price_change_pct"))
    if abs(pct) < 1e-10:
        direction = "neutral"
    elif pct > 0:
        direction = "up"
    else:
        direction = "down"

    target_is_fixture = _is_fixture(signal)

    if context is None:
        return {
            "hit": False, "count": 1, "total_count": 1,
            "direction": direction, "fixture_target": target_is_fixture,
        }

    # Check if context provides a pre-computed real_same_direction_asset_count
    real_count_from_context = context.get("real_same_direction_asset_count")
    if isinstance(real_count_from_context, (int, float)) and real_count_from_context >= 3:
        # Context explicitly provides a pre-computed real asset count
        real_total = int(real_count_from_context) + (0 if target_is_fixture else 1)
        return {
            "hit": real_total >= 3,
            "count": real_total,
            "total_count": context.get("same_direction_asset_count", real_total),
            "direction": direction,
            "fixture_target": target_is_fixture,
        }

    # Fall back to counting from assets/signals list
    assets = context.get("assets") or context.get("signals") or []
    if not isinstance(assets, list):
        return {
            "hit": False, "count": 1, "total_count": 1,
            "direction": direction, "fixture_target": target_is_fixture,
        }

    asset_name = _extract_asset(signal)
    real_same = 0
    total_same = 0

    for entry in assets:
        if isinstance(entry, dict):
            entry_pct = _safe_float(entry.get("price_change_pct"))
            entry_asset = _extract_asset(entry)
            entry_is_fixture = _is_fixture(entry)
        elif isinstance(entry, (int, float)):
            entry_pct = float(entry)
            entry_asset = ""
            entry_is_fixture = False
        else:
            continue

        if entry_asset and entry_asset == asset_name:
            continue  # skip self

        if direction == "up" and entry_pct > 0:
            total_same += 1
            if not entry_is_fixture:
                real_same += 1
        elif direction == "down" and entry_pct < 0:
            total_same += 1
            if not entry_is_fixture:
                real_same += 1

    # +1 for self (only count toward real if target is not a fixture)
    real_total = real_same + (0 if target_is_fixture else 1)
    total = total_same + 1

    # v1.11-D: require >= 3 real assets in same direction
    hit = real_total >= 3

    return {
        "hit": hit,
        "count": real_total,
        "total_count": total,
        "direction": direction,
        "fixture_target": target_is_fixture,
    }


# ── Main gate function ────────────────────────────────────────────────────────

def evaluate_signal_value(signal: dict, context: dict | None = None) -> dict:
    """Evaluate the information value of a market signal using multi-factor rules.

    Determines whether a signal has sufficient explanatory power beyond raw price
    movement to justify entering the send pipeline.

    v1.11-D calibration — see module docstring for changes.

    Args:
        signal: Signal dict. Expected fields:
            - price_change_pct: float or string (required for price_move check)
            - open_interest or oi or oi_usd: OI value (optional)
            - volume or dayNtlVlm or volume_24h: volume value (optional)
            - funding or funding_rate: funding rate value (optional)
            - asset: asset symbol (optional)
            - signal_type: signal type string (optional)
            - is_fixture: bool (optional) — mark synthetic/test signals
            - source_type: str (optional) — "fixture" treated as is_fixture=True
        context: Optional context dict for multi-asset sync detection.
            Expected shape: {"assets": [{"price_change_pct": ..., "asset": ...}, ...]}
            or {"signals": [signal_dict, ...]}
            Supports: {"real_same_direction_asset_count": int} for pre-computed counts.

    Returns:
        Dict with keys:
          - allowed: bool — True if signal passes value gate
          - decision: "allow" | "observe" | "block" — final decision
          - value_score: int — computed score (0-100+)
          - value_tier: "high" | "medium" | "low" — score tier
          - reasons: list[str] — positive findings
          - warnings: list[str] — cautions and concerns
          - factor_hits: dict — per-factor detection results
          - gate_version: str — "v1.11-d"

    Security: No API calls, no credentials, no network access.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    # ── Factor detection ──
    price = _detect_price_move(signal)
    oi = _detect_oi_confirmation(signal)
    vol = _detect_volume_confirmation(signal)
    funding = _detect_funding_extreme(signal)
    multi = _detect_multi_asset_sync(signal, context)
    is_fixture = _is_fixture(signal)

    # ── Warnings for missing/insufficient fields ──
    if oi["missing"]:
        warnings.append("open_interest field missing — OI confirmation not available")
    if vol["missing"]:
        warnings.append("volume field missing — volume confirmation not available")
    if funding["missing"]:
        warnings.append("funding field missing — funding extreme not available")
    if funding.get("near_zero"):
        warnings.append("funding rate is near zero — no extreme funding signal in current market")
    if is_fixture:
        warnings.append("signal is a fixture — value assessment is synthetic")
    if multi.get("fixture_target") and multi.get("hit"):
        warnings.append("multi_asset_sync hit via real assets only — fixture target excluded from count")

    # ── Value score calculation ──
    value_score = 0

    # Price movement scoring
    if price["hit"]:
        value_score += 30
        reasons.append(f"price_move: abs({price['value']:.2f}%) >= 5%")
    if price["strong"]:
        value_score += 20
        reasons.append(f"strong_price_move: abs({price['value']:.2f}%) >= 8%")

    # OI confirmation
    if oi["hit"]:
        value_score += 25
        reasons.append(f"oi_confirmation: open_interest={oi['value']:.1f}")
    elif oi["missing"] and price["hit"]:
        value_score -= 10
        warnings.append("missing open_interest: -10 score penalty")

    # Volume confirmation
    if vol["hit"]:
        value_score += 20
        reasons.append(f"volume_confirmation: volume={vol['value']:.1f}")
    elif vol["missing"] and price["hit"]:
        value_score -= 10
        warnings.append("missing volume: -10 score penalty")

    # Funding extreme
    if funding["hit"]:
        value_score += 20
        reasons.append(f"funding_extreme: abs(funding)={abs(funding['value']):.4f} >= 0.01")

    # Multi-asset sync — v1.11-D: conditional scoring
    # multi_asset_sync only awards points if it can be backed by OI or volume
    if multi["hit"]:
        if oi["hit"] or vol["hit"]:
            # multi_asset_sync + OI/volume backing → full credit
            value_score += 25
            reasons.append(f"multi_asset_sync: {multi['count']} real assets in same direction ({multi['direction']}) — backed by OI/volume")
        else:
            # multi_asset_sync without OI/volume backing → half credit, flagged
            value_score += 10
            reasons.append(f"multi_asset_sync: {multi['count']} real assets in same direction ({multi['direction']}) — NO OI/volume backing (half score)")
            warnings.append("multi_asset_sync hit but OI and volume both missing/zero — reduced to half score; field quality insufficient for full multi-asset confirmation")

    # Clamp score floor at 0
    value_score = max(0, value_score)

    # ── Decision logic (v1.11-D calibrated) ──

    # Determine whether multi_asset_sync can serve as a "strong confirmation"
    # v1.11-D: multi_asset_sync ONLY counts as strong when backed by OI or volume
    multi_backed = multi["hit"] and (oi["hit"] or vol["hit"])

    # Count strong confirmation factors (excluding multi_asset_sync unless backed)
    strong_confirmations = []
    if oi["hit"]:
        strong_confirmations.append("oi_confirmation")
    if vol["hit"]:
        strong_confirmations.append("volume_confirmation")
    if funding["hit"]:
        strong_confirmations.append("funding_extreme")
    if multi_backed:
        strong_confirmations.append("multi_asset_sync (backed)")

    has_strong_confirmation = len(strong_confirmations) > 0

    decision: str
    if not price["hit"]:
        # No significant price movement at all
        decision = "block"
        reasons.append("price_move not hit — no significant price change detected")

    elif price["hit"] and has_strong_confirmation:
        # Price + at least 1 strong confirmation factor
        decision = "allow"
        reasons.append(f"price_move + strong confirmation(s): {', '.join(strong_confirmations)}")

    elif price["hit"] and not has_strong_confirmation:
        # Price only, no strong confirmation
        # v1.11-D: multi_asset_sync without OI/volume backing does NOT push to allow
        if price["strong"]:
            # Strong price but no confirmation — escalate to observe
            decision = "observe"
            reasons.append("strong price_move without strong confirmation — moved to observe")
            warnings.append("strong price but fields insufficient for allow")
        else:
            decision = "observe"
            reasons.append("price_move hit but no strong confirmation factors present — observe only")

    else:
        # Fallback: block
        decision = "block"

    # ── Fixture override: fixtures can never be "allow" via multi_asset_sync alone ──
    # v1.11-D: Even if multi_asset_sync is "backed" by OI/volume, if the signal is a fixture,
    # and the ONLY strong confirmation is multi_asset_sync, downgrade to observe.
    if is_fixture and decision == "allow" and multi["hit"] and not (oi["hit"] or vol["hit"] or funding["hit"]):
        # multi_asset_sync was the only strong confirmation — but it's fixture-backed
        # This shouldn't happen because multi_backed requires OI or vol...
        # But if we got here somehow, downgrade
        pass  # Already handled by multi_backed check above

    if is_fixture and decision == "allow" and multi_backed and not (oi["hit"] or vol["hit"] or funding["hit"]):
        # Safety: fixture with only multi_asset_sync (backed means oi or vol, so this is unreachable)
        # Already caught above; keep as belt-and-suspenders
        decision = "observe"
        reasons.append("fixture signal: multi_asset_sync-only allow downgraded to observe")

    # ── Determine tier ──
    if value_score >= 70:
        value_tier = "high"
    elif value_score >= 45:
        value_tier = "medium"
    else:
        value_tier = "low"

    # ── Build factor_hits ──
    factor_hits = {
        "price_move": price["hit"],
        "oi_confirmation": oi["hit"],
        "volume_confirmation": vol["hit"],
        "funding_extreme": funding["hit"],
        "multi_asset_sync": multi["hit"],
    }

    return {
        "allowed": decision == "allow",
        "decision": decision,
        "value_score": value_score,
        "value_tier": value_tier,
        "reasons": reasons,
        "warnings": warnings,
        "factor_hits": factor_hits,
        "gate_version": GATE_VERSION,
    }
