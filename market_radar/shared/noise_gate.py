"""Market Radar — Deterministic Noise Gate (Signal Spine v1).

Pipeline barrier that evaluates each observation against a set of rules
and produces verifiable, repeatable results. Every rule outcome records:

  - reason_code (machine-readable)
  - reason (human-readable)
  - evidence_refs (supporting observations)
  - evaluated_at (timestamp)
  - rule_version

Rules without sufficient data MUST return NOT_EVALUATED, not fabricated
pass/fail. The aggregated gate decision is:
  - Any REJECT → overall reject
  - No reject + any NOT_EVALUATED → overall downgrade (if rest pass)
  - All ACCEPT → overall accept
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.shared.models import (
    Observation,
    DataQuality,
    DataSourceType,
    NoiseGateResult,
    GateVerdict,
    china_now,
    SIGNAL_SPINE_VERSION,
    sha256_short,
)

GATE_RULE_VERSION = "signal_spine_gate_v1"


def _now() -> str:
    return china_now()


# ── Individual Rule Evaluators ─────────────────────────────────────────────


def _eval_duplicate_event(
    obs: Observation,
    known_dedup_keys: set[str],
) -> NoiseGateResult:
    """Rule 1: Check if this event is a duplicate.

    Uses the observation's dedup_key against a set of known keys.
    """
    if not known_dedup_keys:
        return NoiseGateResult(
            rule_name="duplicate_event",
            verdict=GateVerdict.ACCEPT,
            reason_code="no_prior_events",
            reason="No prior events recorded — first occurrence passes.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    if obs.dedup_key in known_dedup_keys:
        # Determine if this is truly a duplicate or new evidence
        return NoiseGateResult(
            rule_name="duplicate_event",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="duplicate_detected",
            reason=(
                f"Observation with dedup_key '{obs.dedup_key[:16]}...' "
                f"matches a previously processed event. "
                f"Treated as supplementary evidence, not a new event."
            ),
            evidence_refs=[f"dedup:{obs.dedup_key}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"dedup_key": obs.dedup_key, "is_new_evidence": True},
        )

    return NoiseGateResult(
        rule_name="duplicate_event",
        verdict=GateVerdict.ACCEPT,
        reason_code="unique_event",
        reason=f"Event with dedup_key '{obs.dedup_key[:16]}...' is unique.",
        evidence_refs=[f"dedup:{obs.dedup_key}"],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
        metadata={"dedup_key": obs.dedup_key},
    )


def _eval_stale_event(obs: Observation, max_age_hours: int = 48) -> NoiseGateResult:
    """Rule 2: Check if the event is stale or recycled content.

    Compares event_time to observed_at. If event_time is significantly
    older than observed_at, the event may be recycled news.
    """
    if not obs.event_time or not obs.observed_at:
        return NoiseGateResult(
            rule_name="stale_or_recycled_event",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="missing_timestamps",
            reason="Cannot evaluate staleness — missing event_time or observed_at.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    try:
        from datetime import datetime

        # Parse ISO timestamps (handle both Z and +HH:MM formats)
        event_dt = _parse_iso(obs.event_time)
        observed_dt = _parse_iso(obs.observed_at)

        if event_dt is None or observed_dt is None:
            raise ValueError("Failed to parse timestamps")

        age_hours = (observed_dt - event_dt).total_seconds() / 3600

        if age_hours < 0:
            # Event_time in the future relative to observed_at — possible timezone issue
            return NoiseGateResult(
                rule_name="stale_or_recycled_event",
                verdict=GateVerdict.ACCEPT,
                reason_code="future_event_time",
                reason=f"Event time is after observation time ({age_hours:.1f}h) — possible TZ diff, accepted.",
                evidence_refs=[f"event_time:{obs.event_time}", f"observed_at:{obs.observed_at}"],
                evaluated_at=_now(),
                rule_version=GATE_RULE_VERSION,
                metadata={"age_hours": age_hours, "max_age_hours": max_age_hours},
            )

        if age_hours > max_age_hours:
            return NoiseGateResult(
                rule_name="stale_or_recycled_event",
                verdict=GateVerdict.REJECT,
                reason_code="stale_event",
                reason=(
                    f"Event is {age_hours:.1f}h old (max: {max_age_hours}h). "
                    f"Likely recycled or stale content."
                ),
                evidence_refs=[f"event_time:{obs.event_time}", f"observed_at:{obs.observed_at}"],
                evaluated_at=_now(),
                rule_version=GATE_RULE_VERSION,
                metadata={"age_hours": age_hours, "max_age_hours": max_age_hours},
            )

        return NoiseGateResult(
            rule_name="stale_or_recycled_event",
            verdict=GateVerdict.ACCEPT,
            reason_code="fresh_event",
            reason=f"Event is {age_hours:.1f}h old — within threshold.",
            evidence_refs=[f"event_time:{obs.event_time}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"age_hours": age_hours},
        )

    except (ValueError, TypeError) as e:
        return NoiseGateResult(
            rule_name="stale_or_recycled_event",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="timestamp_parse_error",
            reason=f"Cannot evaluate staleness: timestamp parse error — {e}",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )


def _parse_iso(ts: str) -> Optional[datetime]:
    """Parse ISO 8601 timestamp, handling Z suffix and common formats."""
    from datetime import datetime

    ts_clean = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts_clean)
    except (ValueError, TypeError):
        pass
    # Try common format without timezone
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts[:19], fmt)
        except (ValueError, TypeError):
            continue
    return None


def _eval_tradable_asset(obs: Observation) -> NoiseGateResult:
    """Rule 3: Check if the event references at least one known tradable asset.

    Uses a built-in set of known crypto assets. If no affected_assets
    are provided, this cannot conclude there IS no asset — only that
    the observation didn't specify any.
    """
    KNOWN_ASSETS = {
        "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
        "DOT", "LINK", "MATIC", "POL", "UNI", "SHIB", "LTC", "BCH",
        "ATOM", "NEAR", "OP", "ARB", "APT", "SUI", "INJ", "SEI",
        "RUNE", "AAVE", "MKR", "CRV", "GRT", "FET", "AGIX", "PEPE",
        "FLOKI", "BONK", "WIF", "TIA", "STRK", "JUP", "JTO", "PYTH",
        "BTCUSDT", "ETHUSDT", "SOLUSDT",
    }

    assets = obs.affected_assets

    if not assets:
        return NoiseGateResult(
            rule_name="no_tradable_asset",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="no_assets_specified",
            reason="Observation specifies no affected assets — cannot verify tradability.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # Check if any affected asset is in our known list
    matched = [a.upper() for a in assets if a.upper() in KNOWN_ASSETS]

    if matched:
        return NoiseGateResult(
            rule_name="no_tradable_asset",
            verdict=GateVerdict.ACCEPT,
            reason_code="tradable_asset_found",
            reason=f"Affected assets include known tradable assets: {matched}.",
            evidence_refs=[f"assets:{','.join(matched)}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"matched_assets": matched},
        )

    # Assets specified but none recognized — could be unknown tickers
    return NoiseGateResult(
        rule_name="no_tradable_asset",
        verdict=GateVerdict.DOWNGRADE,
        reason_code="unrecognized_assets",
        reason=(
            f"Affected assets {assets} are not in the known asset list. "
            f"May be valid but unrecognized tickers."
        ),
        evidence_refs=[f"assets:{','.join(assets)}"],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
        metadata={"unrecognized_assets": assets},
    )


def _eval_source_quality(obs: Observation) -> NoiseGateResult:
    """Rule 4: Check if the source has sufficient quality/credibility.

    Evaluates based on DataQuality and DataSourceType.
    """
    quality = obs.data_quality

    if quality == DataQuality.UNKNOWN:
        return NoiseGateResult(
            rule_name="insufficient_source_quality",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="source_quality_unknown",
            reason="Source quality is unknown — downgrading to observe-only.",
            evidence_refs=[f"source:{obs.source}", f"quality:{quality.value}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"data_quality": quality.value, "source": obs.source},
        )

    if quality == DataQuality.LOW_CREDIBILITY:
        return NoiseGateResult(
            rule_name="insufficient_source_quality",
            verdict=GateVerdict.REJECT,
            reason_code="source_low_credibility",
            reason=f"Source '{obs.source}' has low credibility rating.",
            evidence_refs=[f"source:{obs.source}", f"quality:{quality.value}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"data_quality": quality.value, "source": obs.source},
        )

    if quality in (DataQuality.VERIFIED_HIGH, DataQuality.VERIFIED_MEDIUM):
        return NoiseGateResult(
            rule_name="insufficient_source_quality",
            verdict=GateVerdict.ACCEPT,
            reason_code=f"source_{quality.value}",
            reason=f"Source quality is {quality.value}.",
            evidence_refs=[f"source:{obs.source}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # UNVERIFIED
    return NoiseGateResult(
        rule_name="insufficient_source_quality",
        verdict=GateVerdict.DOWNGRADE,
        reason_code="source_unverified",
        reason=f"Source '{obs.source}' is unverified — treat with reduced confidence.",
        evidence_refs=[f"source:{obs.source}", f"quality:{quality.value}"],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
        metadata={"data_quality": quality.value, "source": obs.source},
    )


def _eval_single_unverified_source(obs: Observation) -> NoiseGateResult:
    """Rule 5: Check if only a single unverified source exists.

    Uses source_refs count and data quality.
    """
    source_count = len(obs.source_refs) if obs.source_refs else 1

    if source_count >= 2:
        return NoiseGateResult(
            rule_name="single_unverified_source",
            verdict=GateVerdict.ACCEPT,
            reason_code="multiple_sources",
            reason=f"Observation has {source_count} source references — cross-verification possible.",
            evidence_refs=[f"source_refs_count:{source_count}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"source_count": source_count},
        )

    # Single source — check quality
    quality = obs.data_quality
    if quality == DataQuality.UNKNOWN:
        return NoiseGateResult(
            rule_name="single_unverified_source",
            verdict=GateVerdict.REJECT,
            reason_code="single_unverified_source",
            reason=(
                f"Single source '{obs.source}' with unknown quality. "
                f"Cannot verify event independently."
            ),
            evidence_refs=[f"source:{obs.source}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"source_count": source_count, "data_quality": quality.value},
        )

    if quality in (DataQuality.VERIFIED_HIGH, DataQuality.VERIFIED_MEDIUM):
        return NoiseGateResult(
            rule_name="single_unverified_source",
            verdict=GateVerdict.ACCEPT,
            reason_code="single_high_quality_source",
            reason=f"Single source '{obs.source}' but quality is {quality.value}.",
            evidence_refs=[f"source:{obs.source}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"source_count": source_count, "data_quality": quality.value},
        )

    # Single source with unverified or low credibility
    return NoiseGateResult(
        rule_name="single_unverified_source",
        verdict=GateVerdict.REJECT,
        reason_code="single_low_quality_source",
        reason=(
            f"Single source '{obs.source}' with {quality.value} quality. "
            f"Insufficient for reliable event detection."
        ),
        evidence_refs=[f"source:{obs.source}", f"quality:{quality.value}"],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
        metadata={"source_count": source_count, "data_quality": quality.value},
    )


def _eval_material_expectation(obs: Observation) -> NoiseGateResult:
    """Rule 6: Check if the event represents a material expectation change.

    Without live market pricing data, this rule evaluates based on
    event metadata — intensity, event_type, and confidence indicators
    from the normalized payload.

    If no intensity/event_type data is available, returns NOT_EVALUATED.
    """
    intensity = obs.normalized_payload.get("intensity", "")
    event_type = obs.normalized_payload.get("event_type", "")

    if not intensity and not event_type:
        return NoiseGateResult(
            rule_name="no_material_expectation_change",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="missing_event_metadata",
            reason="Cannot evaluate material expectation — no intensity or event_type in payload.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # High/medium intensity events likely represent material change
    if intensity in ("high", "medium"):
        return NoiseGateResult(
            rule_name="no_material_expectation_change",
            verdict=GateVerdict.ACCEPT,
            reason_code=f"material_{intensity}_intensity",
            reason=f"Event with {intensity} intensity represents a material change.",
            evidence_refs=[f"intensity:{intensity}", f"event_type:{event_type}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"intensity": intensity, "event_type": event_type},
        )

    if intensity == "low":
        return NoiseGateResult(
            rule_name="no_material_expectation_change",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="low_intensity_event",
            reason="Low intensity event — likely not a material expectation change.",
            evidence_refs=[f"intensity:{intensity}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"intensity": intensity, "event_type": event_type},
        )

    # Intensity unknown but have event type
    return NoiseGateResult(
        rule_name="no_material_expectation_change",
        verdict=GateVerdict.NOT_EVALUATED,
        reason_code="insufficient_event_data",
        reason="Event type known but no intensity data — cannot evaluate materiality.",
        evidence_refs=[f"event_type:{event_type}"],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
        metadata={"event_type": event_type},
    )


def _eval_already_price_in(obs: Observation) -> NoiseGateResult:
    """Rule 7: Check if the event is already heavily priced in.

    Without live market data feeds (order books, recent price action),
    this rule cannot determine price-in state. Returns NOT_EVALUATED
    unless the observation provides explicit price_in data.

    This prevents the gate from fabricating market conclusions.
    """
    price_in = obs.normalized_payload.get("price_in_state")
    price_change = obs.normalized_payload.get("market_snapshot", {})

    if price_in is not None:
        # Observation explicitly provides price-in assessment
        already_priced = price_in.get("already_priced_in", False)
        if already_priced:
            return NoiseGateResult(
                rule_name="already_heavily_price_in",
                verdict=GateVerdict.DOWNGRADE,
                reason_code="already_priced_in",
                reason=f"Event assessed as already priced in: {price_in.get('reason', 'no reason')}",
                evidence_refs=[f"price_in:{price_in}"],
                evaluated_at=_now(),
                rule_version=GATE_RULE_VERSION,
                metadata={"price_in": price_in},
            )
        return NoiseGateResult(
            rule_name="already_heavily_price_in",
            verdict=GateVerdict.ACCEPT,
            reason_code="not_priced_in",
            reason="Event not assessed as already priced in.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    if price_change:
        # Has market snapshot data — could evaluate
        # But determining "priced in" from snapshot alone is unreliable
        return NoiseGateResult(
            rule_name="already_heavily_price_in",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="insufficient_market_context",
            reason=(
                "Market snapshot available but insufficient to determine "
                "if event is already priced in. Requires trend context."
            ),
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    return NoiseGateResult(
        rule_name="already_heavily_price_in",
        verdict=GateVerdict.NOT_EVALUATED,
        reason_code="no_market_data",
        reason="Cannot evaluate price-in state — no market data available.",
        evidence_refs=[],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
    )


def _eval_derivatives_overcrowding(obs: Observation) -> NoiseGateResult:
    """Rule 8: Check for derivatives overcrowding (funding rates, OI extremes).

    Requires derivatives market data (funding rates, OI ratios, L/S ratios).
    Without this data, returns NOT_EVALUATED.

    This prevents the gate from making unfounded claims about positioning.
    """
    metrics = obs.normalized_payload

    # Check for relevant derivatives data in the payload
    funding_rate = metrics.get("funding_rate")
    long_short_ratio = metrics.get("long_short_ratio")
    oi_data = metrics.get("open_interest_current")

    has_any_data = any(x is not None for x in [funding_rate, long_short_ratio, oi_data])

    if not has_any_data:
        return NoiseGateResult(
            rule_name="derivatives_overcrowding",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="no_derivatives_data",
            reason="No derivatives data (funding rate, L/S ratio, OI) available.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # Evaluate from raw per-asset data if available
    assets_data = metrics.get("assets", [])
    if not assets_data and has_any_data:
        # Single asset with OI data
        if oi_data is not None:
            if isinstance(oi_data, (int, float)) and oi_data > 10_000_000_000:
                return NoiseGateResult(
                    rule_name="derivatives_overcrowding",
                    verdict=GateVerdict.DOWNGRADE,
                    reason_code="high_open_interest",
                    reason=f"Open interest is ${oi_data/1e9:.1f}B — elevated derivative exposure.",
                    evidence_refs=[f"oi:{oi_data}"],
                    evaluated_at=_now(),
                    rule_version=GATE_RULE_VERSION,
                    metadata={"open_interest": oi_data},
                )

        # Check funding rate extremes
        if funding_rate is not None:
            fr = float(funding_rate)
            if abs(fr) > 0.001:
                direction = "long" if fr > 0 else "short"
                return NoiseGateResult(
                    rule_name="derivatives_overcrowding",
                    verdict=GateVerdict.DOWNGRADE,
                    reason_code=f"extreme_funding_{direction}",
                    reason=f"Funding rate {fr:.4f} suggests {direction} overcrowding.",
                    evidence_refs=[f"funding_rate:{fr}"],
                    evaluated_at=_now(),
                    rule_version=GATE_RULE_VERSION,
                    metadata={"funding_rate": fr},
                )

        return NoiseGateResult(
            rule_name="derivatives_overcrowding",
            verdict=GateVerdict.NOT_EVALUATED,
            reason_code="insufficient_derivatives_context",
            reason="Some derivatives data present but insufficient for overcrowding assessment.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # Per-asset evaluation from 'assets' array
    high_lsr_assets = []
    for asset in assets_data:
        symbol = asset.get("symbol", "?")
        lsr = asset.get("long_short_ratio")
        fr = asset.get("funding_rate")

        if lsr is not None and float(lsr) > 3.0:
            high_lsr_assets.append(symbol)

        if fr is not None and abs(float(fr)) > 0.001:
            high_lsr_assets.append(symbol)

    if high_lsr_assets:
        return NoiseGateResult(
            rule_name="derivatives_overcrowding",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="overcrowded_assets",
            reason=f"Assets {high_lsr_assets} show extreme derivatives positioning.",
            evidence_refs=[f"overcrowded:{','.join(high_lsr_assets)}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"overcrowded_assets": high_lsr_assets},
        )

    return NoiseGateResult(
        rule_name="derivatives_overcrowding",
        verdict=GateVerdict.ACCEPT,
        reason_code="normal_derivatives",
        reason="No derivatives overcrowding detected.",
        evidence_refs=[],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
    )


def _eval_social_heat(obs: Observation) -> NoiseGateResult:
    """Rule 9: Check for social heat without spot confirmation.

    Evaluates whether social/meme-driven hype is backed by actual
    spot market activity. Without tick-level data, defaults to
    NOT_EVALUATED unless the observation explicitly tags this.

    This is deliberately conservative — we don't fabricate social
    sentiment analysis from market data.
    """
    payload = obs.normalized_payload
    is_social_driven = payload.get("social_heat", False) or payload.get("meme_coin", False)
    price_change = None

    # Try to get price change from various metric locations
    market_snapshot = payload.get("market_snapshot", {})
    if market_snapshot:
        for asset_data in market_snapshot.values():
            if isinstance(asset_data, dict):
                pc = asset_data.get("price_change_pct")
                if pc is not None:
                    price_change = float(pc)
                    break

    if not is_social_driven:
        return NoiseGateResult(
            rule_name="social_heat_without_spot_confirmation",
            verdict=GateVerdict.ACCEPT,
            reason_code="not_social_driven",
            reason="Event is not flagged as social/meme-driven.",
            evidence_refs=[],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # Social-driven event — check for spot confirmation
    if price_change is not None and abs(price_change) > 2.0:
        return NoiseGateResult(
            rule_name="social_heat_without_spot_confirmation",
            verdict=GateVerdict.ACCEPT,
            reason_code="spot_confirmed",
            reason=f"Social heat confirmed by spot price move of {price_change:+.2f}%.",
            evidence_refs=[f"price_change:{price_change}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"price_change_pct": price_change},
        )

    if price_change is not None:
        return NoiseGateResult(
            rule_name="social_heat_without_spot_confirmation",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="social_heat_no_spot_confirmation",
            reason=f"Social/meme-driven event with no significant spot move ({price_change:+.2f}%).",
            evidence_refs=[f"price_change:{price_change}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"price_change_pct": price_change, "social_heat": True},
        )

    return NoiseGateResult(
        rule_name="social_heat_without_spot_confirmation",
        verdict=GateVerdict.NOT_EVALUATED,
        reason_code="social_heat_no_market_data",
        reason="Social-driven event flagged but no market data to confirm or refute.",
        evidence_refs=[],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
    )


def _eval_pump_risk(obs: Observation) -> NoiseGateResult:
    """Rule 10: Check for high chase or pump risk.

    Evaluates whether the event is likely a pump/chase scenario.
    Indicators: extreme social heat + no fundamentals + low market cap assets.
    Without comprehensive data, returns NOT_EVALUATED.
    """
    payload = obs.normalized_payload

    # Check for explicit pump risk flag
    pump_risk = payload.get("pump_risk")
    if pump_risk is not None:
        risk_level = str(pump_risk).lower()
        if risk_level in ("high", "critical"):
            return NoiseGateResult(
                rule_name="high_chase_or_pump_risk",
                verdict=GateVerdict.REJECT,
                reason_code="pump_risk_high",
                reason=f"Event flagged with {risk_level} pump/chase risk.",
                evidence_refs=[f"pump_risk:{pump_risk}"],
                evaluated_at=_now(),
                rule_version=GATE_RULE_VERSION,
                metadata={"pump_risk": risk_level},
            )
        if risk_level == "medium":
            return NoiseGateResult(
                rule_name="high_chase_or_pump_risk",
                verdict=GateVerdict.DOWNGRADE,
                reason_code="pump_risk_medium",
                reason="Event flagged with medium pump/chase risk — downgraded to observe.",
                evidence_refs=[f"pump_risk:{pump_risk}"],
                evaluated_at=_now(),
                rule_version=GATE_RULE_VERSION,
                metadata={"pump_risk": risk_level},
            )
        # low or none
        return NoiseGateResult(
            rule_name="high_chase_or_pump_risk",
            verdict=GateVerdict.ACCEPT,
            reason_code=f"pump_risk_{risk_level}",
            reason=f"Pump risk assessed as '{risk_level}'.",
            evidence_refs=[f"pump_risk:{pump_risk}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
        )

    # Check for meme/unusual asset indicators
    assets_lower = [a.lower() for a in obs.affected_assets]
    unusual_indicators = ["meme", "shit", "pump", "moon", "rocket", "100x"]
    has_unusual = any(
        any(ind in a for ind in unusual_indicators) for a in assets_lower
    )

    if has_unusual:
        return NoiseGateResult(
            rule_name="high_chase_or_pump_risk",
            verdict=GateVerdict.DOWNGRADE,
            reason_code="suspicious_asset_naming",
            reason="Affected asset names suggest high pump/chase risk.",
            evidence_refs=[f"assets:{','.join(obs.affected_assets)}"],
            evaluated_at=_now(),
            rule_version=GATE_RULE_VERSION,
            metadata={"suspicious_asset_pattern": True},
        )

    return NoiseGateResult(
        rule_name="high_chase_or_pump_risk",
        verdict=GateVerdict.NOT_EVALUATED,
        reason_code="no_pump_risk_data",
        reason="No pump/chase risk data available for this observation.",
        evidence_refs=[],
        evaluated_at=_now(),
        rule_version=GATE_RULE_VERSION,
    )


# ── Aggregate Gate ─────────────────────────────────────────────────────────


class DeterministicNoiseGate:
    """Pipeline barrier that evaluates observations against deterministic rules.

    This gate is placed AFTER normalization and BEFORE signal creation.
    It produces a structured, auditable result for every observation.

    The gate is a pipeline barrier — it is called synchronously and its
    results determine whether an observation proceeds to signal creation.
    """

    def __init__(self, known_dedup_keys: Optional[set[str]] = None):
        self._version = GATE_RULE_VERSION
        self._known_dedup_keys = known_dedup_keys or set()

    def sync_dedup_keys(self, keys: set[str]) -> None:
        """Synchronize the known dedup key set from the registry."""
        self._known_dedup_keys = keys

    def evaluate(self, observation: Observation) -> list[NoiseGateResult]:
        """Evaluate an observation against all gate rules.

        Returns a list of NoiseGateResult, one per rule.
        """
        return [
            _eval_duplicate_event(observation, self._known_dedup_keys),
            _eval_stale_event(observation),
            _eval_tradable_asset(observation),
            _eval_source_quality(observation),
            _eval_single_unverified_source(observation),
            _eval_material_expectation(observation),
            _eval_already_price_in(observation),
            _eval_derivatives_overcrowding(observation),
            _eval_social_heat(observation),
            _eval_pump_risk(observation),
        ]

    def aggregate(self, results: list[NoiseGateResult]) -> GateVerdict:
        """Aggregate individual rule results into a single verdict.

        Rules:
          - Any REJECT → overall REJECT
          - No reject + any NOT_EVALUATED → DOWNGRADE (if rest pass)
          - All ACCEPT → ACCEPT
          - Mixed ACCEPT/DOWNGRADE → DOWNGRADE
        """
        has_reject = any(r.verdict == GateVerdict.REJECT for r in results)
        has_not_evaluated = any(r.verdict == GateVerdict.NOT_EVALUATED for r in results)
        all_accept = all(r.verdict == GateVerdict.ACCEPT for r in results)
        all_pass = all(
            r.verdict in (GateVerdict.ACCEPT, GateVerdict.DOWNGRADE) for r in results
        )

        if has_reject:
            return GateVerdict.REJECT
        if all_accept:
            return GateVerdict.ACCEPT
        if all_pass:
            return GateVerdict.DOWNGRADE
        # Mixed with NOT_EVALUATED but no reject
        return GateVerdict.DOWNGRADE

    def evaluate_and_aggregate(self, observation: Observation) -> tuple[list[NoiseGateResult], GateVerdict]:
        """Evaluate all rules and return (results, aggregated_verdict)."""
        results = self.evaluate(observation)
        verdict = self.aggregate(results)
        return results, verdict
