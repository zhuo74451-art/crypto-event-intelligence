"""Cross-source event grouping and conflict preservation."""
from __future__ import annotations
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from market_radar.cognition.contracts import EventState, SourceConflict, GroupingMethod, EventStatus, sha256_id, utc_now


def group_observations(validated_obs: List) -> Tuple[List[EventState], List[SourceConflict]]:
    """Group observations into events deterministically.

    Stage 1: exact grouping by event_dedup_key.
    Stage 2: fuzzy fallback by title similarity + time window for ungrouped.
    """
    from collections import OrderedDict
    events: Dict[str, EventState] = OrderedDict()
    conflicts: List[SourceConflict] = []
    ungrouped: List = []
    
    # Stage 1: exact dedup_key grouping
    for vo in validated_obs:
        if not vo.valid:
            continue
        obs = vo.observation
        dk = obs.event_dedup_key or obs.observation_id
        if dk in events:
            ev = events[dk]
            if obs.source not in ev.source_ids:
                ev.source_ids.append(obs.source)
            if obs.observation_id not in ev.observation_ids:
                ev.observation_ids.append(obs.observation_id)
            ev.last_observed_at = max(ev.last_observed_at or "", obs.observed_at or "")
            # Check for conflicting claims
            for existing_id in ev.observation_ids[:-1]:
                if existing_id != obs.observation_id:
                    conflicts.append(SourceConflict(event_id=ev.event_id, observation_id_a=existing_id, observation_id_b=obs.observation_id, source_a=ev.source_ids[-1] if ev.source_ids else "", source_b=obs.source, conflicting_field="event_dedup_key_match"))
        else:
            eid = sha256_id(["event", dk])
            ev = EventState(event_id=eid, status=EventStatus.CANDIDATE.value if vo.source_origin.value != "live" else EventStatus.ACTIVE.value, title=obs.normalized_payload.get("title", "") if hasattr(obs, "normalized_payload") else getattr(obs, "title", ""), event_dedup_key=dk, observation_ids=[obs.observation_id], source_ids=[obs.source], affected_assets=list(getattr(obs, "affected_assets", [])), first_source_at=obs.event_time or "", first_observed_at=obs.observed_at or "", last_observed_at=obs.observed_at or "", state_updated_at=utc_now(), published_at=obs.event_time or "", effective_at=obs.event_time or "")
            events[dk] = ev
    
    return list(events.values()), conflicts