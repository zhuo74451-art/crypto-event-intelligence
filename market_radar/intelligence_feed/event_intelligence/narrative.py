"""Extension B: Narrative Burst Detection — identifies topic bursts in time windows."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .models import IntelligenceEvent


@dataclass
class NarrativeBurst:
    topic: str
    event_count: int
    independent_sources: int
    unique_assets: int
    novelty: float  # 0-100
    window_hours: float
    events: list[str] = field(default_factory=list)  # event_ids


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def detect_bursts(
    events: list[IntelligenceEvent],
    window_hours: float = 4.0,
    min_events: int = 3,
    reference_time: Optional[datetime] = None,
) -> list[NarrativeBurst]:
    """Detect narrative bursts — topic spikes in a short time window.

    Args:
        events: List of IntelligenceEvents.
        window_hours: Time window for burst detection.
        min_events: Minimum events to count as a burst.
        reference_time: Deterministic time for freshness.

    Returns:
        List of NarrativeBurst sorted by novelty descending.
    """
    ref = reference_time or datetime.now(timezone.utc)
    bursts: dict[str, NarrativeBurst] = {}

    for event in events:
        if not event.latest_at:
            continue
        ets = _parse_ts(event.latest_at)
        if not ets:
            continue
        hours_ago = (ref - ets).total_seconds() / 3600
        if hours_ago > window_hours:
            continue

        for topic_obj in event.topics:
            t = topic_obj.topic
            if t not in bursts:
                bursts[t] = NarrativeBurst(
                    topic=t, event_count=0, independent_sources=0,
                    unique_assets=0, novelty=0.0, window_hours=window_hours,
                )
            bursts[t].event_count += 1
            if event.event_id not in bursts[t].events:
                bursts[t].events.append(event.event_id)

            si = event.source_independence
            if si.independent_source_count > bursts[t].independent_sources:
                bursts[t].independent_sources = si.independent_source_count

            asset_count = len(event.assets)
            if asset_count > bursts[t].unique_assets:
                bursts[t].unique_assets = asset_count

    # Filter by min_events and compute novelty
    result = []
    for b in bursts.values():
        if b.event_count >= min_events:
            # Novelty: more events + more sources in less time = higher novelty
            b.novelty = min(100.0, (
                b.event_count * 15.0 +
                b.independent_sources * 10.0 +
                b.unique_assets * 5.0
            ))
            result.append(b)

    result.sort(key=lambda x: x.novelty, reverse=True)
    return result
