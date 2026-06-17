"""Whale Domain — deterministic Hyperliquid whale intelligence.

Pure domain logic with no network, SDK, or I/O dependencies.
All inputs injected via function parameters or dataclass instances.
"""
from market_radar.whale_domain.models import (
    WhalePositionInput, WhaleSnapshot, WhalePositionChange,
    WhaleExposure, WhaleEntityProfile, WhaleWatchlistEntry,
    WhaleAlertCandidate, WhaleDomainResult, ChangeType,
    make_position_key, compute_liquidation_distance,
    extract_snapshot,
)
from market_radar.whale_domain.change_detector import (
    detect_change, detect_all_changes,
)
from market_radar.whale_domain.exposure import aggregate_exposure
from market_radar.whale_domain.watchlist import apply_watchlist
from market_radar.whale_domain.entity_profile import get_entity_summary
from market_radar.whale_domain.alert_candidate import generate_alert_candidates
