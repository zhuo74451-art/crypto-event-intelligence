"""
Event Case Report — Generates structured reports from proposals and
market data for a single macro release event.

An ``EventCaseReport`` collates:

- The release event metadata (indicator, date, expectation, actual).
- The point-in-time snapshot just before release.
- The hypothesis, assessment, and transmission proposals.
- Validation outcomes.
- A final summary verdict.

Reports can be rendered as plain dicts (JSON-friendly) or as formatted
text for logs / dashboards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..adapters.intelligence_kernel_stub import (
    MacroAssessmentProposal,
    MacroStrategyHypothesisProposal,
    MacroTransmissionProposal,
)
from ..adapters.validation_stub import ValidationRecord
from ..replay.point_in_time_snapshot import PointInTimeSnapshot


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
@dataclass
class EventCaseReport:
    """A complete case report for one macro release event.

    Attributes:
        report_id:          Unique report identifier.
        release_event_id:   The macro release event ID.
        indicator:          Economic indicator name (e.g. "CPI", "NFP").
        release_date:       Release date string (YYYY-MM-DD).
        generated_at:       Timestamp when the report was generated.
        snapshot:           Point-in-time snapshot pre-release.
        hypothesis:         Hypothesis proposal.
        assessment:         Assessment proposal.
        transmission:       Transmission proposal.
        validation:         Validation record.
        verdict:            Short summary string.
        details:            Free-form dict of extra details.
    """

    report_id: str
    release_event_id: str
    indicator: str
    release_date: str
    generated_at: datetime

    snapshot: PointInTimeSnapshot
    hypothesis: MacroStrategyHypothesisProposal
    assessment: MacroAssessmentProposal
    transmission: MacroTransmissionProposal
    validation: ValidationRecord

    verdict: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def from_proposals(
        cls,
        release_event_id: str,
        indicator: str,
        release_date: str,
        snapshot: PointInTimeSnapshot,
        hypothesis: MacroStrategyHypothesisProposal,
        assessment: MacroAssessmentProposal,
        transmission: MacroTransmissionProposal,
        validation: ValidationRecord,
        *,
        extra_details: Optional[dict[str, Any]] = None,
    ) -> "EventCaseReport":
        """Construct a report from the full set of strategy artefacts."""
        # Build a concise verdict
        if validation.status == "fail":
            verdict = (
                f"FAIL — Validation failed for {release_event_id}: "
                f"{validation.message}"
            )
        elif hypothesis.direction == "neutral":
            verdict = (
                f"NEUTRAL — {indicator} {release_date}: "
                f"surprise within threshold. Score={assessment.score}."
            )
        else:
            signal_str = transmission.signal or "flat"
            verdict = (
                f"{hypothesis.direction.upper()} {signal_str.upper()} — "
                f"{indicator} {release_date}: "
                f"confidence={hypothesis.confidence}, "
                f"score={assessment.score}, "
                f"signal={signal_str}."
            )

        return cls(
            report_id=f"report_{release_event_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            release_event_id=release_event_id,
            indicator=indicator,
            release_date=release_date,
            generated_at=datetime.utcnow(),
            snapshot=snapshot,
            hypothesis=hypothesis,
            assessment=assessment,
            transmission=transmission,
            validation=validation,
            verdict=verdict,
            details={
                "btc_price_pre": float(snapshot.btc_price),
                "eth_price_pre": float(snapshot.eth_price),
                "open_interest": float(snapshot.open_interest),
                "funding_rate": float(snapshot.funding_rate),
                "hypothesis_direction": hypothesis.direction,
                "hypothesis_confidence": float(hypothesis.confidence),
                "assessment_score": assessment.score,
                "transmission_signal": transmission.signal,
                "validation_status": validation.status,
                **(extra_details or {}),
            },
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "report_id": self.report_id,
            "release_event_id": self.release_event_id,
            "indicator": self.indicator,
            "release_date": self.release_date,
            "generated_at": self.generated_at.isoformat(),
            "verdict": self.verdict,
            "snapshot": self.snapshot.as_dict(),
            "hypothesis": {
                "id": self.hypothesis.hypothesis_id,
                "direction": self.hypothesis.direction,
                "confidence": float(self.hypothesis.confidence),
                "triggered_at": self.hypothesis.triggered_at.isoformat(),
                "supporting_facts": self.hypothesis.supporting_facts,
            },
            "assessment": {
                "id": self.assessment.assessment_id,
                "score": self.assessment.score,
                "rationale": self.assessment.rationale,
                "assessed_at": self.assessment.assessed_at.isoformat(),
            },
            "transmission": {
                "id": self.transmission.transmission_id,
                "signal": self.transmission.signal,
                "transmitted_at": (
                    self.transmission.transmitted_at.isoformat()
                    if self.transmission.transmitted_at
                    else None
                ),
            },
            "validation": {
                "id": self.validation.record_id,
                "status": self.validation.status,
                "message": self.validation.message,
                "validated_at": self.validation.validated_at.isoformat(),
                "diagnostics": self.validation.diagnostics,
            },
            "details": self.details,
        }

    def to_text(self, *, width: int = 72) -> str:
        """Render a human-readable report string."""
        sep = "=" * width
        sub = "-" * width
        lines = [
            sep,
            f"  EVENT CASE REPORT  |  {self.report_id}",
            sep,
            f"  Release     : {self.indicator} // {self.release_date}",
            f"  Event ID    : {self.release_event_id}",
            f"  Generated   : {self.generated_at.isoformat()}",
            sub,
            f"  VERDICT     : {self.verdict}",
            sub,
            "  SNAPSHOT (pre-release)",
            f"    BTC price   : {self.snapshot.btc_price}",
            f"    ETH price   : {self.snapshot.eth_price}",
            f"    Open Int.   : {self.snapshot.open_interest}",
            f"    Funding Rt. : {self.snapshot.funding_rate}",
            sub,
            "  HYPOTHESIS",
            f"    Direction   : {self.hypothesis.direction}",
            f"    Confidence  : {self.hypothesis.confidence}",
            sub,
            "  ASSESSMENT",
            f"    Score       : {self.assessment.score}",
            f"    Rationale   : {self.assessment.rationale}",
            sub,
            "  TRANSMISSION",
            f"    Signal      : {self.transmission.signal}",
            sub,
            "  VALIDATION",
            f"    Status      : {self.validation.status}",
            f"    Message     : {self.validation.message}",
            sep,
        ]
        return "\n".join(lines)
