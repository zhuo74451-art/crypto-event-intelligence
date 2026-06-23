"""Replay clock — enforces point-in-time information boundaries for historical replay.

The clock defines and validates four key timestamps per replay run:
- event_time_utc: When the macro event occurred (or was released)
- prediction_time_utc: When the strategy would have been evaluated
- available_information_cutoff_utc: The last timestamp of data available to the strategy
- evaluation_time_utc: When the market reaction is evaluated

Rules:
1. Strategy generation can only read data before available_information_cutoff_utc
2. Market confirmation can only read confirmation data before evaluation_time_utc
3. Future labels cannot enter strategy inputs
4. Future revisions cannot change historical inputs
5. Current best view must be kept separate from historical view
"""
from __future__ import annotations
from dataclasses import dataclass



from datetime import datetime, timedelta, timezone
from typing import Optional


def parse_utc(ts: str) -> datetime:
    """Parse an ISO UTC timestamp string to datetime."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def format_utc(dt: datetime) -> str:
    """Format a datetime as ISO UTC string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_now() -> str:
    """Return current UTC timestamp string."""
    return format_utc(datetime.now(timezone.utc))


@dataclass
class ReplayCutoffs:
    """The four critical timestamps for a single replay evaluation."""
    event_time_utc: str
    prediction_time_utc: str
    available_information_cutoff_utc: str
    evaluation_time_utc: str

    def validate_ordering(self) -> list[str]:
        """Validate temporal ordering constraints. Returns list of violations."""
        violations = []
        try:
            event = parse_utc(self.event_time_utc)
            prediction = parse_utc(self.prediction_time_utc)
            cutoff = parse_utc(self.available_information_cutoff_utc)
            evaluation = parse_utc(self.evaluation_time_utc)

            # The event should occur at or before prediction time
            if event > prediction:
                violations.append("event_time_utc after prediction_time_utc")

            # Prediction time should be at or after cutoff (data available before prediction)
            if prediction < cutoff:
                violations.append("prediction_time_utc before available_information_cutoff_utc")

            # Cutoff should be at or before evaluation
            if cutoff > evaluation:
                violations.append("available_information_cutoff_utc after evaluation_time_utc")

            # Event should be within 24 hours of prediction (sanity check)
            if (prediction - event) > timedelta(hours=72):
                violations.append("prediction_time_utc more than 72h after event_time_utc")

        except (ValueError, TypeError) as e:
            violations.append(f"timestamp parse error: {e}")

        return violations

    def is_data_available(self, data_timestamp_utc: str) -> bool:
        """Check if data with a given timestamp was available at cutoff."""
        try:
            data_ts = parse_utc(data_timestamp_utc)
            cutoff = parse_utc(self.available_information_cutoff_utc)
            return data_ts <= cutoff
        except (ValueError, TypeError):
            return False


def build_default_cutoffs(event_time_utc: str) -> ReplayCutoffs:
    """Build standard replay cutoffs from event time.

    Default: prediction happens at event time, cutoff is 1 minute before,
    evaluation is 1 hour after event.
    """
    try:
        event_dt = parse_utc(event_time_utc)
        prediction_dt = event_dt
        cutoff_dt = event_dt - timedelta(minutes=1)
        # For market data: evaluation at +1h for intraday, +24h for short-term
        evaluation_dt = event_dt + timedelta(hours=1)
    except (ValueError, TypeError):
        # Fallback: use current time
        now = datetime.now(timezone.utc)
        event_dt = now
        prediction_dt = now
        cutoff_dt = now - timedelta(minutes=1)
        evaluation_dt = now + timedelta(hours=1)

    return ReplayCutoffs(
        event_time_utc=format_utc(event_dt),
        prediction_time_utc=format_utc(prediction_dt),
        available_information_cutoff_utc=format_utc(cutoff_dt),
        evaluation_time_utc=format_utc(evaluation_dt),
    )


def build_horizon_cutoffs(event_time_utc: str, horizon: str) -> dict[str, ReplayCutoffs]:
    """Build cutoffs for each time horizon from the same event time.

    Different horizons have different evaluation windows:
    - intraday: 1h after event
    - short_term: 24h after event
    - medium_term: 7 days after event
    """
    horizons = {}
    try:
        event_dt = parse_utc(event_time_utc)
        offsets = {
            "intraday": timedelta(hours=1),
            "short_term": timedelta(hours=24),
            "medium_term": timedelta(days=7),
        }
        offset = offsets.get(horizon, timedelta(hours=1))
        evaluation_dt = event_dt + offset

        horizons[horizon] = ReplayCutoffs(
            event_time_utc=format_utc(event_dt),
            prediction_time_utc=format_utc(event_dt),
            available_information_cutoff_utc=format_utc(event_dt - timedelta(minutes=1)),
            evaluation_time_utc=format_utc(evaluation_dt),
        )
    except (ValueError, TypeError):
        pass
    return horizons


def is_post_event_consensus(consensus_time_utc: str, event_time_utc: str) -> bool:
    """Check if consensus was published after the event (ineligible)."""
    try:
        consensus_ts = parse_utc(consensus_time_utc)
        event_ts = parse_utc(event_time_utc)
        return consensus_ts > event_ts
    except (ValueError, TypeError):
        return True  # If we can't verify, assume ineligible


def is_future_revision(revision_time_utc: str, cutoff_utc: str) -> bool:
    """Check if a revision occurred after the information cutoff (invisible to strategy at replay time)."""
    try:
        revision_ts = parse_utc(revision_time_utc)
        cutoff_ts = parse_utc(cutoff_utc)
        return revision_ts > cutoff_ts
    except (ValueError, TypeError):
        return True  # If we can't verify, assume future revision


def is_future_information(info_time_utc: str, cutoff_utc: str) -> bool:
    """Check if information timestamp is after the cutoff."""
    try:
        info_ts = parse_utc(info_time_utc)
        cutoff_ts = parse_utc(cutoff_utc)
        return info_ts > cutoff_ts
    except (ValueError, TypeError):
        return True  # If we can't verify, conservatively assume future