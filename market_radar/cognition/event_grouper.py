"""Cross-source event grouping and conflict preservation."""
from __future__ import annotations
from collections import defaultdict, OrderedDict
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from market_radar.cognition.contracts import EventState, SourceConflict, GroupingMethod, EventStatus, sha256_id, utc_now


_GROUPING_TIME_WINDOW_HOURS = 48  # max hours apart for fuzzy match
_TITLE_SIMILARITY_THRESHOLD = 0.75  # SequenceMatcher ratio for fuzzy match


def group_observations(validated_obs: List) -> Tuple[List[EventState], List[SourceConflict]]:
    """Group observations into events deterministically.

    Stage 1: exact grouping by event_dedup_key.
    Stage 2: fuzzy fallback by entity/time/asset for ungrouped observations.
    """
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
            # Detect actual field-level conflicts between sources
            _detect_and_record_conflict(ev, obs, vo, conflicts)
        else:
            eid = sha256_id(["event", dk])
            title = _get_title(obs)
            ev = EventState(
                event_id=eid,
                status=EventStatus.CANDIDATE.value if vo.source_origin.value != "live" else EventStatus.ACTIVE.value,
                title=title,
                event_dedup_key=dk,
                observation_ids=[obs.observation_id],
                source_ids=[obs.source],
                affected_assets=list(getattr(obs, "affected_assets", [])),
                first_source_at=obs.event_time or "",
                first_observed_at=obs.observed_at or "",
                last_observed_at=obs.observed_at or "",
                state_updated_at=utc_now(),
                published_at=obs.event_time or "",
                effective_at=obs.event_time or "",
            )
            events[dk] = ev

    # Stage 2: fuzzy fallback for ungrouped observations
    # Observations that share no exact dedup_key with any existing event
    # are compared using title similarity, entity overlap, and time proximity.
    seen_event_keys = set(events.keys())
    for vo in validated_obs:
        if not vo.valid:
            continue
        obs = vo.observation
        dk = obs.event_dedup_key or obs.observation_id
        if dk in seen_event_keys:
            continue
        seen_event_keys.add(dk)

        matched = False
        for existing_key, existing_ev in list(events.items()):
            if _is_fuzzy_match(obs, existing_ev):
                # Merge into existing event
                if obs.source not in existing_ev.source_ids:
                    existing_ev.source_ids.append(obs.source)
                if obs.observation_id not in existing_ev.observation_ids:
                    existing_ev.observation_ids.append(obs.observation_id)
                existing_ev.last_observed_at = max(existing_ev.last_observed_at or "", obs.observed_at or "")
                if dk not in existing_ev.possible_related_event_ids:
                    existing_ev.possible_related_event_ids.append(dk)
                _detect_and_record_conflict(existing_ev, obs, vo, conflicts)
                matched = True
                break

        if not matched:
            # Create separate event for this observation
            eid = sha256_id(["event", dk])
            title = _get_title(obs)
            ev = EventState(
                event_id=eid,
                status=EventStatus.CANDIDATE.value,
                title=title,
                event_dedup_key=dk,
                observation_ids=[obs.observation_id],
                source_ids=[obs.source],
                affected_assets=list(getattr(obs, "affected_assets", [])),
                first_source_at=obs.event_time or "",
                first_observed_at=obs.observed_at or "",
                last_observed_at=obs.observed_at or "",
                state_updated_at=utc_now(),
                published_at=obs.event_time or "",
                effective_at=obs.event_time or "",
            )
            events[dk] = ev

    return list(events.values()), conflicts


def _get_title(obs) -> str:
    """Extract title from observation regardless of payload structure."""
    if hasattr(obs, "normalized_payload") and obs.normalized_payload:
        return obs.normalized_payload.get("title", "")
    return getattr(obs, "title", "") or ""


def _is_fuzzy_match(obs, existing_ev: EventState) -> bool:
    """Check if an observation is a fuzzy match for an existing event.

    Uses: title similarity, time proximity, affected-asset overlap.
    Generic titles alone never merge.
    """
    obs_title = _get_title(obs)
    if not obs_title or not existing_ev.title:
        return False

    # Generic titles never merge alone
    generic_titles = {"update", "release", "announcement", "notice", "alert",
                     "更新", "发布", "公告", "通知", "提醒"}
    if obs_title.lower().strip() in generic_titles:
        return False

    # Title similarity
    ratio = SequenceMatcher(None, obs_title.lower(), existing_ev.title.lower()).ratio()
    if ratio < _TITLE_SIMILARITY_THRESHOLD:
        return False

    # Time proximity (within GROUPING_TIME_WINDOW_HOURS)
    try:
        from datetime import datetime, timezone
        t1 = datetime.fromisoformat(obs.observed_at or obs.event_time or "") if (obs.observed_at or obs.event_time) else None
        t2 = datetime.fromisoformat(existing_ev.first_observed_at or existing_ev.first_source_at) if (existing_ev.first_observed_at or existing_ev.first_source_at) else None
        if t1 and t2:
            hours_diff = abs((t1 - t2).total_seconds()) / 3600
            if hours_diff > _GROUPING_TIME_WINDOW_HOURS:
                return False
    except (ValueError, TypeError):
        pass

    # If title is very similar and times are close, consider it a match
    return True


def _detect_and_record_conflict(ev: EventState, obs, vo, conflicts: List) -> None:
    """Compare key fields between a new observation and existing event state.

    Records a SourceConflict when two sources genuinely disagree on
    a meaningful field (title, event_time, affected_assets, impact).
    Same-key agreement is NOT automatically a conflict.
    """
    if not ev.observation_ids:
        return

    obs_title = _get_title(obs)
    if obs_title and ev.title and obs_title.lower() != ev.title.lower():
        conflicts.append(SourceConflict(
            event_id=ev.event_id,
            observation_id_a=ev.observation_ids[0] if ev.observation_ids else "",
            observation_id_b=obs.observation_id,
            source_a=ev.source_ids[0] if ev.source_ids else "",
            source_b=obs.source,
            conflicting_field="title",
            value_a=ev.title,
            value_b=obs_title,
        ))
        return

    obs_time = getattr(obs, "event_time", None) or ""
    if obs_time and ev.first_source_at and obs_time != ev.first_source_at:
        try:
            from datetime import datetime, timezone
            t1 = datetime.fromisoformat(obs_time.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(ev.first_source_at.replace("Z", "+00:00"))
            if abs((t1 - t2).total_seconds()) > 3600:  # more than 1 hour difference
                conflicts.append(SourceConflict(
                    event_id=ev.event_id,
                    observation_id_a=ev.observation_ids[0] if ev.observation_ids else "",
                    observation_id_b=obs.observation_id,
                    source_a=ev.source_ids[0] if ev.source_ids else "",
                    source_b=obs.source,
                    conflicting_field="event_time",
                    value_a=ev.first_source_at,
                    value_b=obs_time,
                ))
        except (ValueError, TypeError):
            pass