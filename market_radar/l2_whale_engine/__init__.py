"""MVP+ Window 2 — L2 Whale Position Engine.

Change detection, risk analysis, exposure aggregation,
and extension modules (watchlist, entity profiles,
behavior summary, alert candidates).
"""
from market_radar.l2_whale_engine.state_manager import StateManager, make_position_key
from market_radar.l2_whale_engine.change_detector import (
    detect_change, detect_all_changes, compute_risk_flags,
    DEFAULT_SIZE_THRESHOLD,
)
from market_radar.l2_whale_engine.exposure_aggregator import aggregate_exposure
