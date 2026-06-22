"""
Historical Event Replay — Deterministic replay of macro release events.

The ``HistoricalEventReplay`` orchestrates a full strategy cycle for a
single historical macro release event.  It:

1. Loads fixture data for the event (expectation, actual release).
2. Captures a point-in-time snapshot just before the release.
3. Runs the strategy hypothesis / assessment pipeline.
4. Produces a ``StrategyOutput`` containing the hypothesis, assessment,
   transmission proposal, and validation record.

All data is fetched exclusively from point-in-time-safe sources so that
replays are deterministic and free of future leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from ..adapters.acquisition_stub import AcquisitionStub
from ..adapters.intelligence_kernel_stub import (
    MacroAssessmentProposal,
    MacroStrategyHypothesisProposal,
    MacroTransmissionProposal,
)
from ..adapters.legacy_market_reader import LegacyMarketReader
from ..adapters.legacy_price_reader import LegacyPriceReader
from ..adapters.validation_stub import ValidationRecord, ValidationStub
from .point_in_time_snapshot import PointInTimeSnapshot


# ---------------------------------------------------------------------------
# Strategy output — the single return value of a replay
# ---------------------------------------------------------------------------
@dataclass
class StrategyOutput:
    """Deterministic result of replaying one macro release event.

    Attributes:
        release_event_id:  The ID of the replayed release event.
        snapshot:          Point-in-time market state before the release.
        hypothesis:        Hypothesis proposal formed by the strategy.
        assessment:        Assessment proposal produced by the strategy.
        transmission:      Transmission proposal (hypothesis + assessment).
        validation:        Validation record for the full pipeline.
        raw_fixtures:      The fixture data used as input.
    """

    release_event_id: str
    snapshot: PointInTimeSnapshot
    hypothesis: MacroStrategyHypothesisProposal
    assessment: MacroAssessmentProposal
    transmission: MacroTransmissionProposal
    validation: ValidationRecord
    raw_fixtures: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Replay engine
# ---------------------------------------------------------------------------
class HistoricalEventReplay:
    """Replay a historical macro release event end-to-end.

    The replay is fully deterministic given the same fixture data and
    point-in-time constraints.  No real-time data is accessed.

    Args:
        acquisition:    Fixture data provider (default: AcquisitionStub).
        price_reader:   Price adapter (default: LegacyPriceReader stub).
        market_reader:  Market-data adapter (default: LegacyMarketReader stub).
        validator:      Validation stub (default: ValidationStub).
    """

    def __init__(
        self,
        acquisition: Optional[AcquisitionStub] = None,
        price_reader: Optional[LegacyPriceReader] = None,
        market_reader: Optional[LegacyMarketReader] = None,
        validator: Optional[ValidationStub] = None,
    ) -> None:
        self._acq = acquisition or AcquisitionStub()
        self._prices = price_reader or LegacyPriceReader()
        self._market = market_reader or LegacyMarketReader()
        self._validator = validator or ValidationStub()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def replay(self, release_event_id: str) -> StrategyOutput:
        """Run a full replay for the given *release_event_id*.

        The *release_event_id* must be one of the fixture IDs defined
        in ``AcquisitionStub`` (e.g. ``"CPI_2025_06"`` or
        ``"NFP_2025_06"``).

        Args:
            release_event_id: Identifies the macro release to replay.

        Returns:
            A fully populated ``StrategyOutput``.

        Raises:
            ValueError: If the fixture for *release_event_id* is unknown.
        """
        # ---- 1. Load fixtures -------------------------------------------
        raw = self._resolve_fixtures(release_event_id)
        indicator: str = raw["indicator"]
        release_date: str = raw["release_date"]
        release_dt = datetime.fromisoformat(f"{release_date}T{raw.get('release_time', '08:30')}:00").replace(
            tzinfo=timezone.utc
        )

        # Build the expectation / actual record
        expectation = self._acq.get_fixture_expectation(indicator, release_date)
        actual = self._acq.get_fixture_actual_release(indicator, release_date)
        surprise = actual["actual"] - expectation["consensus"]

        # ---- 2. Point-in-time snapshot (moments before release) ---------
        snapshot_time = release_dt - timedelta(seconds=5)
        snapshot = PointInTimeSnapshot.capture(
            at=snapshot_time,
            prices=self._prices,
            market=self._market,
        )

        # ---- 3. Form hypothesis -----------------------------------------
        hypothesis = self._build_hypothesis(
            release_event_id=release_event_id,
            indicator=indicator,
            expectation=expectation,
            actual=actual,
            surprise=surprise,
            snapshot=snapshot,
        )

        # ---- 4. Assess --------------------------------------------------
        assessment = self._assess_hypothesis(
            hypothesis=hypothesis,
            expectation=expectation,
            actual=actual,
            surprise=surprise,
            snapshot=snapshot,
        )

        # ---- 5. Build transmission --------------------------------------
        signal = self._derive_signal(hypothesis, assessment)
        transmission = MacroTransmissionProposal(
            transmission_id=f"trn_{release_event_id}",
            hypothesis=hypothesis,
            assessment=assessment,
            signal=signal,
            transmitted_at=datetime.now(timezone.utc),
        )

        # ---- 6. Validate ------------------------------------------------
        validation = self._validator.validate_transmission(transmission)

        return StrategyOutput(
            release_event_id=release_event_id,
            snapshot=snapshot,
            hypothesis=hypothesis,
            assessment=assessment,
            transmission=transmission,
            validation=validation,
            raw_fixtures={
                "indicator": indicator,
                "release_date": release_date,
                "release_dt": release_dt.isoformat(),
                "expectation": expectation,
                "actual": actual,
                "surprise": surprise,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_fixtures(self, release_event_id: str) -> dict[str, Any]:
        """Look up fixture metadata for the given event ID."""
        # Search CPI calendar
        for evt in self._acq.get_fixture_cpi_calendar():
            if evt["release_id"] == release_event_id:
                return evt
        # Search NFP calendar
        for evt in self._acq.get_fixture_nfp_calendar():
            if evt["release_id"] == release_event_id:
                return evt
        raise ValueError(
            f"Unknown release_event_id: {release_event_id!r}. "
            f"Available IDs can be obtained from "
            f"AcquisitionStub.get_fixture_cpi_calendar() and "
            f"AcquisitionStub.get_fixture_nfp_calendar()."
        )

    def _build_hypothesis(
        self,
        release_event_id: str,
        indicator: str,
        expectation: dict[str, Any],
        actual: dict[str, Any],
        surprise: float,
        snapshot: PointInTimeSnapshot,
    ) -> MacroStrategyHypothesisProposal:
        """Form a hypothesis based on the release surprise."""
        # Simple rule: positive surprise → bullish, negative → bearish
        threshold = Decimal("0.01")  # 1% of consensus
        consensus = Decimal(str(expectation["consensus"]))
        surprise_dec = Decimal(str(surprise))

        if abs(consensus) > 0 and abs(surprise_dec / consensus) > threshold:
            direction = "bullish" if surprise_dec > 0 else "bearish"
        else:
            direction = "neutral"

        confidence = min(
            Decimal("1.0"),
            abs(surprise_dec / consensus) if consensus != 0 else Decimal("0.5"),
        )

        return MacroStrategyHypothesisProposal(
            hypothesis_id=f"hyp_{release_event_id}",
            release_event_id=release_event_id,
            direction=direction,
            confidence=confidence.quantize(Decimal("0.0001")),
            triggered_at=datetime.now(timezone.utc),
            supporting_facts={
                "indicator": indicator,
                "consensus": float(consensus),
                "actual": actual["actual"],
                "surprise": float(surprise_dec),
                "btc_price_pre": float(snapshot.btc_price),
                "eth_price_pre": float(snapshot.eth_price),
            },
        )

    def _assess_hypothesis(
        self,
        hypothesis: MacroStrategyHypothesisProposal,
        expectation: dict[str, Any],
        actual: dict[str, Any],
        surprise: float,
        snapshot: PointInTimeSnapshot,
    ) -> MacroAssessmentProposal:
        """Score the hypothesis based on the magnitude of surprise."""
        # Score = scaled absolute surprise relative to consensus
        consensus = float(expectation["consensus"])
        abs_surprise_pct = (
            abs(surprise) / consensus if consensus != 0 else 0.5
        )
        score = min(100.0, max(0.0, abs_surprise_pct * 100))

        return MacroAssessmentProposal(
            assessment_id=f"asm_{hypothesis.release_event_id}",
            hypothesis_id=hypothesis.hypothesis_id,
            assessed_at=datetime.now(timezone.utc),
            score=round(score, 2),
            rationale=(
                f"{hypothesis.direction.title()} hypothesis with "
                f"confidence {hypothesis.confidence}: "
                f"surprise={surprise:+.2f} vs consensus={consensus:.2f}."
            ),
        )

    def _derive_signal(
        self,
        hypothesis: MacroStrategyHypothesisProposal,
        assessment: MacroAssessmentProposal,
    ) -> Optional[str]:
        """Derive a trade signal from the hypothesis and assessment."""
        if hypothesis.direction == "neutral":
            return "flat"
        if assessment.score >= 50.0:
            return "long" if hypothesis.direction == "bullish" else "short"
        return "flat"
