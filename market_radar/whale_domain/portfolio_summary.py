"""Portfolio Intelligence Summary — deterministic interpretation layer.

Generates FACT, DERIVED_METRIC, RULE_TRIGGER, and INTERPRETATION_LIMIT
observations from the WhalePortfolioSnapshot. No investment advice.
No LLM. No random.
"""

from __future__ import annotations

from typing import Any

from market_radar.whale_domain.portfolio_models import (
    WhalePortfolioSnapshot, PortfolioIntelligenceSummary,
)


def _determine_posture(snap: WhalePortfolioSnapshot) -> str:
    """Classify overall portfolio posture."""
    if snap.data_quality in ("stale", "incomplete"):
        return "uncertain_low_quality"
    if snap.gross_exposure_usd == 0:
        return "no_exposure"
    net_pct = abs(snap.net_exposure_usd) / snap.gross_exposure_usd if snap.gross_exposure_usd else 0
    if net_pct < 0.1 and snap.gross_exposure_usd > 0:
        return "hedged" if snap.long_exposure_usd > 0 and snap.short_exposure_usd > 0 else "neutral"
    if snap.net_exposure_usd > 0 and net_pct > 0.5:
        return "aggressive_long"
    if snap.net_exposure_usd < 0 and net_pct > 0.5:
        return "aggressive_short"
    if snap.net_exposure_usd > 0:
        return "biased_long"
    if snap.net_exposure_usd < 0:
        return "biased_short"
    return "neutral"


def _determine_dominant_exposure(snap: WhalePortfolioSnapshot) -> str:
    """Identify dominant exposure in the portfolio."""
    if not snap.coin_summaries:
        return "none"
    sorted_coins = sorted(
        snap.coin_summaries,
        key=lambda c: abs(c.total_long_usd) + abs(c.total_short_usd),
        reverse=True,
    )
    top = sorted_coins[0]
    net = top.total_long_usd - top.total_short_usd
    direction = "long" if net > 0 else "short"
    return f"{top.coin} ({direction}, ${abs(top.total_long_usd) + abs(top.total_short_usd):,.0f})"


def _generate_interpretations(snap: WhalePortfolioSnapshot) -> list[str]:
    """Generate FACT, DERIVED_METRIC, RULE_TRIGGER interpretations."""
    lines = []

    # Facts
    lines.append(f"[FACT] {len(snap.addresses)} addresses across {len(snap.coin_summaries)} coins")
    lines.append(f"[FACT] Gross: ${snap.gross_exposure_usd:,.0f}, Net: ${snap.net_exposure_usd:,.0f}")
    lines.append(f"[FACT] Long: ${snap.long_exposure_usd:,.0f}, Short: ${snap.short_exposure_usd:,.0f}")
    if snap.weighted_leverage is not None:
        lines.append(f"[FACT] Weighted leverage: {snap.weighted_leverage:.1f}x")

    # Derived metrics
    if snap.gross_exposure_usd > 0:
        ls_ratio = snap.long_exposure_usd / snap.short_exposure_usd if snap.short_exposure_usd > 0 else float("inf")
        lines.append(f"[DERIVED_METRIC] Long/short ratio: {ls_ratio:.2f}")
        net_pct = (abs(snap.net_exposure_usd) / snap.gross_exposure_usd) * 100
        lines.append(f"[DERIVED_METRIC] Net exposure: {net_pct:.1f}% of gross")

    # Rule triggers
    for rf in snap.risk_findings:
        lines.append(f"[RULE_TRIGGER] {rf.rule_id}: {rf.explanation} ({rf.severity})")

    # Coordinated observations
    for ca in snap.coordinated_actions:
        lines.append(
            f"[INTERPRETATION_LIMIT] {ca.action_type}: {ca.address_count} addresses "
            f"on {ca.coin} ({ca.direction}) — time correlation only, not collusion evidence"
        )

    # Data quality
    if snap.data_quality != "complete":
        lines.append(f"[INTERPRETATION_LIMIT] Data quality: {snap.data_quality} — "
                     f"metrics may be unreliable")

    return lines


def _generate_invalidation_conditions(snap: WhalePortfolioSnapshot) -> list[str]:
    """List conditions that would invalidate current observations."""
    conditions = []
    if snap.data_quality != "complete":
        conditions.append("Improved data completeness could change risk assessment")
    if snap.liquidation_exposure_usd.get("within_5pct_count", 0) > 0:
        conditions.append("Price moves of 5%+ could trigger liquidation cascade")
    return conditions


def generate_summary(
    snapshot: WhalePortfolioSnapshot,
) -> PortfolioIntelligenceSummary:
    """Generate deterministic, structured portfolio intelligence summary."""
    posture = _determine_posture(snapshot)
    dominant = _determine_dominant_exposure(snapshot)
    interpretations = _generate_interpretations(snapshot)

    top_risks = [
        rf.rule_id for rf in snapshot.risk_findings
        if rf.severity in ("critical", "high")
    ]

    coord_obs = [
        f"{ca.action_type}: {ca.address_count} addresses on {ca.coin}"
        for ca in snapshot.coordinated_actions
    ]

    changes_summary = [
        pc.description for pc in snapshot.changes_since_previous
    ]

    invalidation = _generate_invalidation_conditions(snapshot)

    return PortfolioIntelligenceSummary(
        portfolio_posture=posture,
        dominant_exposure=dominant,
        top_risks=top_risks[:5] if len(top_risks) > 5 else top_risks,
        coordinated_observations=coord_obs,
        data_quality=snapshot.data_quality,
        changes_summary=changes_summary,
        invalidation_conditions=invalidation,
    )
