from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from market_radar.domains.macro.contracts.release_calendar import CalendarEventRecord
from market_radar.domains.macro.contracts.expectation import ExpectationSnapshot
from market_radar.domains.macro.contracts.actual_release import OfficialReleaseRecord
from market_radar.domains.macro.contracts.revision import OfficialRevisionRecord
from market_radar.domains.macro.contracts.cross_asset import CrossAssetSnapshot


@dataclass(frozen=True)
class EventInput:
    calendar: CalendarEventRecord
    expectations: List[ExpectationSnapshot] = field(default_factory=list)
    actual_releases: List[OfficialReleaseRecord] = field(default_factory=list)
    revisions: List[OfficialRevisionRecord] = field(default_factory=list)
    cross_asset: Optional[CrossAssetSnapshot] = None


@dataclass(frozen=True)
class StrategyInput:
    strategy_version: str
    as_of_time: datetime
    events: List[EventInput] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
