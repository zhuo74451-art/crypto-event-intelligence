from __future__ import annotations

import datetime
from typing import Optional

from ..contracts.health import (
    HealthIndicator,
    HealthStatus,
    SourceHealthReport,
)


class SourceHealthEvaluator:
    """Evaluates source health based on collected indicators.

    Maintains an in-memory tracking state suitable for one-shot or
    short-lived acquisition runs (not persisted across restarts).
    """

    def __init__(self) -> None:
        self._state: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        source_id: str,
        indicators: list[HealthIndicator],
    ) -> SourceHealthReport:
        """Aggregate a list of *indicators* into a single report.

        Aggregation rules (first-match wins):
        - any UNHEALTHY  → overall UNHEALTHY
        - any DEGRADED   → overall DEGRADED
        - any UNKNOWN    → overall UNKNOWN
        - else           → overall HEALTHY
        """
        status = self._aggregate(indicators)
        state = self._state.get(source_id, {})
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Calculate success rate if we have tracked data
        total = state.get("total_requests", 0)
        consecutive_failures = state.get("consecutive_failures", 0)
        last_success_at = state.get("last_success_at", "")
        last_failure_at = state.get("last_failure_at", "")
        success_rate = 0.0
        if total > 0:
            successes = state.get("successes", 0)
            success_rate = round(successes / total, 4)

        return SourceHealthReport(
            source_id=source_id,
            overall_status=status,
            indicators=tuple(indicators),
            last_success_at=last_success_at,
            last_failure_at=last_failure_at,
            consecutive_failures=consecutive_failures,
            total_requests=total,
            success_rate=success_rate,
            reported_at=now,
        )

    def record_success(self, source_id: str) -> None:
        """Record a successful acquisition for *source_id*."""
        state = self._state.setdefault(source_id, self._fresh_state())
        state["last_success_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        state["consecutive_failures"] = 0
        state["successes"] += 1
        state["total_requests"] += 1

    def record_failure(self, source_id: str, error: str) -> None:
        """Record a failed acquisition for *source_id*."""
        state = self._state.setdefault(source_id, self._fresh_state())
        state["last_failure_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        state["last_error"] = error
        state["consecutive_failures"] += 1
        state["total_requests"] += 1

    def get_report(self, source_id: str) -> Optional[SourceHealthReport]:
        """Return a snapshot report based on the current in-memory state.

        Returns ``None`` when no state exists for *source_id*.
        """
        state = self._state.get(source_id)
        if state is None:
            return None
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        total = state.get("total_requests", 0)
        successes = state.get("successes", 0)
        success_rate = round(successes / total, 4) if total > 0 else 0.0
        # Derive an overall status from tracked history
        if state.get("consecutive_failures", 0) > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY
        return SourceHealthReport(
            source_id=source_id,
            overall_status=overall,
            indicators=(),
            last_success_at=state.get("last_success_at", ""),
            last_failure_at=state.get("last_failure_at", ""),
            consecutive_failures=state.get("consecutive_failures", 0),
            total_requests=total,
            success_rate=success_rate,
            reported_at=now,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fresh_state() -> dict:
        return {
            "successes": 0,
            "total_requests": 0,
            "consecutive_failures": 0,
            "last_success_at": "",
            "last_failure_at": "",
            "last_error": "",
        }

    @staticmethod
    def _aggregate(indicators: list[HealthIndicator]) -> HealthStatus:
        """Apply the priority-based aggregation rule."""
        has_degraded = False
        has_unknown = False

        for ind in indicators:
            if ind.status == HealthStatus.UNHEALTHY:
                return HealthStatus.UNHEALTHY
            if ind.status == HealthStatus.DEGRADED:
                has_degraded = True
            elif ind.status == HealthStatus.UNKNOWN:
                has_unknown = True

        if has_degraded:
            return HealthStatus.DEGRADED
        if has_unknown:
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY
