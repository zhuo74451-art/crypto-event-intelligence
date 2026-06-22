from __future__ import annotations

from typing import Dict, List, Optional

from market_radar.strategies.macro_scheduled.contracts.abstention import (
    AbstentionReason,
    AbstentionDecision,
)
from market_radar.strategies.macro_scheduled.contracts.surprise import (
    MacroSurprise,
)
from market_radar.strategies.macro_scheduled.contracts.confirmation import (
    MarketConfirmationSnapshot,
    ConfirmationStatus,
)
from market_radar.strategies.macro_scheduled.contracts.regime_context import (
    RegimeContext,
    RegimeQuality,
)
from market_radar.strategies.macro_scheduled.contracts.pricing import (
    PricedInEstimate,
    PricedInStatus,
)
from market_radar.domains.macro.contracts.release_calendar import (
    CalendarEventRecord,
)
from market_radar.domains.macro.contracts.expectation import (
    ExpectationSnapshot,
    ExpectationQuality,
)
from market_radar.domains.macro.contracts.actual_release import (
    OfficialReleaseRecord,
)
from market_radar.domains.macro.contracts.cross_asset import (
    CrossAssetSnapshot,
)


class AbstentionEngine:
    """Evaluates whether the system should abstain from producing an
    assessment for a macro scheduled event.

    The engine checks a battery of preconditions.  If *any* hard reason
    applies, ``should_abstain`` must be ``True``.  The engine collects
    ALL applicable reasons rather than short-circuiting on the first one.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_abstention(
        self,
        calendar: Optional[CalendarEventRecord],
        expectations: List[ExpectationSnapshot],
        actuals: List[OfficialReleaseRecord],
        regime: Optional[RegimeContext],
        market_data: Optional[object],
        concurrent_events: List[object],
    ) -> AbstentionDecision:
        """Run all abstention checks and return a decision.

        Args:
            calendar: The calendar record for the event.
            expectations: Collected expectation snapshots.
            actuals: Official release records.
            regime: Current macro regime context.
            market_data: Market data snapshot (or None if unavailable).
            concurrent_events: List of other events occurring at the same
                time (e.g., other macro releases, central bank speeches).

        Returns:
            An :class:`AbstentionDecision` containing the aggregated
            result.  ``should_abstain`` is ``True`` if any *hard* reason
            was found.
        """
        reasons: List[AbstentionReason] = []
        details_parts: List[str] = []

        # Ordered check execution — all checks are always run to collect
        # every applicable reason.

        # --- Expectation issues
        reason = self.check_expectation_missing(expectations)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Expectation data is missing")

        reason = self.check_expectation_reconstructed(expectations)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Expectation is reconstructed-only")

        reason = self.check_expectation_conflicting(expectations)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Expectation snapshots are conflicting")

        # --- Result issues
        reason = self.check_result_unverified(actuals)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Official result is unverified")

        # --- Concurrent events
        reason = self.check_concurrent_event(concurrent_events)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Major concurrent event detected")

        # --- Regime issues
        reason = self.check_regime_unknown(regime)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Current regime is unknown")

        # --- Market data issues
        reason = self.check_market_data_missing(market_data)
        if reason is not None:
            reasons.append(reason)
            details_parts.append("Market data is missing")

        # Determine whether to abstain
        should_abstain = len(reasons) > 0

        details = "; ".join(details_parts) if details_parts else ""
        return AbstentionDecision(
            should_abstain=should_abstain,
            reasons=reasons,
            details=details,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_expectation_missing(
        self,
        expectations: List[ExpectationSnapshot],
    ) -> Optional[AbstentionReason]:
        """If no expectation data is available at all, abstain.

        Returns ``AbstentionReason.EXPECTATION_MISSING`` or ``None``.
        """
        if not expectations:
            return AbstentionReason.EXPECTATION_MISSING
        return None

    def check_expectation_reconstructed(
        self,
        expectations: List[ExpectationSnapshot],
    ) -> Optional[AbstentionReason]:
        """If *all* available expectations are reconstructed (no survey
        or model-based estimate), abstain.

        Returns ``AbstentionReason.EXPECTATION_RECONSTRUCTED_ONLY``
        or ``None``.
        """
        if not expectations:
            return None  # handled by check_expectation_missing

        # Check whether every expectation is reconstructed or proxy
        all_reconstructed_or_proxy = all(
            getattr(e, "quality", None) in (
                ExpectationQuality.RECONSTRUCTED,
                ExpectationQuality.WEAK,
            )
            for e in expectations
        )

        if all_reconstructed_or_proxy:
            return AbstentionReason.EXPECTATION_RECONSTRUCTED_ONLY
        return None

    def check_expectation_conflicting(
        self,
        expectations: List[ExpectationSnapshot],
    ) -> Optional[AbstentionReason]:
        """If multiple expectation snapshots disagree on the central
        value to a degree that cannot be resolved, abstain.

        Returns ``AbstentionReason.EXPECTATION_CONFLICTING`` or ``None``.
        """
        if len(expectations) < 2:
            return None

        # Collect numeric central values (expected_value / consensus)
        central_values: List[float] = []
        for e in expectations:
            val = getattr(e, "expected_value", None) or getattr(e, "consensus", None)
            if val is not None:
                try:
                    central_values.append(float(val))
                except (TypeError, ValueError):
                    continue

        if len(central_values) < 2:
            return None

        # Compute relative spread
        mean_val = sum(central_values) / len(central_values)
        if mean_val == 0.0:
            # Avoid division by zero — check absolute spread instead
            max_spread = max(central_values) - min(central_values)
            if max_spread > 0.01:
                return AbstentionReason.EXPECTATION_CONFLICTING
            return None

        # Relative spread > 10% signals conflict
        relative_spread = (max(central_values) - min(central_values)) / abs(mean_val)
        if relative_spread > 0.10:
            return AbstentionReason.EXPECTATION_CONFLICTING

        return None

    def check_result_unverified(
        self,
        actuals: List[OfficialReleaseRecord],
    ) -> Optional[AbstentionReason]:
        """If no official result record has been verified (no source
        attribution), abstain.

        Returns ``AbstentionReason.OFFICIAL_RESULT_UNVERIFIED`` or
        ``None``.
        """
        if not actuals:
            return AbstentionReason.OFFICIAL_RESULT_UNVERIFIED

        verified = any(
            getattr(r, "is_official", False)
            or getattr(r, "source_ref", None) is not None
            for r in actuals
        )

        if not verified:
            return AbstentionReason.OFFICIAL_RESULT_UNVERIFIED
        return None

    def check_component_conflict(
        self,
        surprise: Optional[MacroSurprise],
    ) -> Optional[AbstentionReason]:
        """If the composite surprise contains unresolved component
        conflicts, abstain.

        Returns ``AbstentionReason.COMPONENT_CONFLICT_UNRESOLVED``
        or ``None``.
        """
        if surprise is None:
            return None

        if surprise.composite is not None and surprise.composite.has_conflict:
            return AbstentionReason.COMPONENT_CONFLICT_UNRESOLVED
        return None

    def check_concurrent_event(
        self,
        concurrent_events: List[object],
    ) -> Optional[AbstentionReason]:
        """If there is a major concurrent event (e.g., FOMC decision,
        NFP, presidential election) that could overshadow the current
        release, abstain.

        Returns ``AbstentionReason.MAJOR_CONCURRENT_EVENT`` or ``None``.
        """
        if not concurrent_events:
            return None

        # Define recognised "major" event patterns
        major_keywords = [
            "fomc",
            "interest rate decision",
            "nonfarm payrolls",
            "nfp",
            "employment situation",
            "cpi",
            "core cpi",
            "presidential election",
            "central bank",
        ]

        for event in concurrent_events:
            name = (
                getattr(event, "event_name", None)
                or getattr(event, "title", None)
                or getattr(event, "name", None)
                or ""
            ).lower()

            for keyword in major_keywords:
                if keyword in name:
                    return AbstentionReason.MAJOR_CONCURRENT_EVENT

            # Also check event_type / category attributes
            etype = (
                getattr(event, "event_type", None)
                or getattr(event, "category", None)
                or ""
            )
            if isinstance(etype, str) and "central_bank" in etype.lower():
                return AbstentionReason.MAJOR_CONCURRENT_EVENT

        return None

    def check_regime_unknown(
        self,
        regime: Optional[RegimeContext],
    ) -> Optional[AbstentionReason]:
        """If the regime context is unknown / insufficient, abstain.

        Returns ``AbstentionReason.REGIME_UNKNOWN`` or ``None``.
        """
        if regime is None:
            return AbstentionReason.REGIME_UNKNOWN

        if regime.quality == RegimeQuality.INSUFFICIENT:
            return AbstentionReason.REGIME_UNKNOWN
        return None

    def check_market_data_missing(
        self,
        market_data: Optional[object],
    ) -> Optional[AbstentionReason]:
        """If market data is entirely unavailable, abstain.

        Returns ``AbstentionReason.MARKET_DATA_MISSING`` or ``None``.
        """
        if market_data is None:
            return AbstentionReason.MARKET_DATA_MISSING
        return None

    def check_reaction_reversed(
        self,
        confirmation: Optional[MarketConfirmationSnapshot],
    ) -> Optional[AbstentionReason]:
        """If the initial market reaction has already reversed,
        abstain.

        Returns ``AbstentionReason.REACTION_ALREADY_REVERSED`` or
        ``None``.
        """
        if confirmation is None:
            return None

        # A reversed reaction is indicated when confirmation channels
        # initially moved in one direction but subsequently reversed,
        # or when the overall status is CONTRADICTING while the
        # limitations mention reversal.
        if confirmation.overall_status == ConfirmationStatus.CONTRADICTING:
            # Check for explicit reversal mention in limitations
            reversal_hints = [
                "reversal",
                "reversed",
                "retracement",
                "whipsaw",
                "false breakout",
            ]
            for lim in confirmation.limitations:
                lim_lower = lim.lower()
                if any(hint in lim_lower for hint in reversal_hints):
                    return AbstentionReason.REACTION_ALREADY_REVERSED

            # If contradictory channels outnumber confirming ones,
            # also flag as potential reversal.
            confirming_count = sum(
                1
                for ch in confirmation.channels.values()
                if ch.status == ConfirmationStatus.CONFIRMING
            )
            contradicting_count = len(confirmation.contradictory_channels)

            if contradicting_count > confirming_count and contradicting_count >= 2:
                return AbstentionReason.REACTION_ALREADY_REVERSED

        return None
