"""
Reporting package for the macro-scheduled event intelligence system.

Generates human-readable case reports and deterministic execution
traces from the strategy's proposals and market data snapshots.
"""

from .event_case_report import EventCaseReport
from .strategy_trace import StrategyTrace

__all__ = [
    "EventCaseReport",
    "StrategyTrace",
]
