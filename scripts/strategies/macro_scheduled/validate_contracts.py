"""Validate that all contract types can be instantiated."""
import sys
sys.path.insert(0, ".")
from datetime import datetime
from market_radar.domains.macro.contracts.common import DataQuality, ObservationPeriod
from market_radar.domains.macro.contracts.release_calendar import CalendarEventRecord, CalendarEventStatus
from market_radar.domains.macro.contracts.expectation import ExpectationSnapshot, ExpectationQuality
from market_radar.domains.macro.contracts.actual_release import OfficialReleaseRecord
from market_radar.domains.macro.contracts.cross_asset import CrossAssetSnapshot
from market_radar.domains.macro.taxonomy.event_types import EventFamily, EventComponent
from market_radar.strategies.macro_scheduled.contracts.surprise import ComponentSurprise, MacroSurprise
from market_radar.strategies.macro_scheduled.contracts.strategy_output import MacroAssessmentProposal, AssessmentDirection
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision, AbstentionReason

contracts = [
    ("DataQuality", DataQuality.STRONG),
    ("CalendarEventRecord", CalendarEventRecord(
        calendar_event_id="test", release_family=EventFamily.CPI_HEADLINE,
        scheduled_release_time=datetime.utcnow(), status=CalendarEventStatus.SCHEDULED)),
    ("ExpectationSnapshot", ExpectationSnapshot(
        expectation_snapshot_id="exp1", release_event_id="cpi1", component_id="headline_mom",
        captured_at=datetime.utcnow(), valid_for_release_time=datetime.utcnow())),
    ("OfficialReleaseRecord", OfficialReleaseRecord(
        release_event_id="cpi1", component_id="headline_mom",
        actual_value=0.3, published_at=datetime.utcnow())),
    ("ComponentSurprise", ComponentSurprise(component_id="a", actual_value=0.3, expected_value=0.2,
        raw_gap=0.1, relative_gap=0.5, standardized_gap=1.0)),
    ("MacroSurprise", MacroSurprise(release_event_id="cpi1")),
    ("AbstentionDecision", AbstentionDecision(should_abstain=True, reasons=[AbstentionReason.EXPECTATION_MISSING])),
    ("MacroAssessmentProposal", MacroAssessmentProposal(
        proposal_id="p1", release_event_id="cpi1", as_of_time=datetime.utcnow())),
]

all_ok = True
for name, instance in contracts:
    try:
        assert instance is not None
        print(f"  PASS: {name}")
    except Exception as e:
        print(f"  FAIL: {name} - {e}")
        all_ok = False

sys.exit(0 if all_ok else 1)
