"""
Acquisition Stub — Synthetic fixture data provider for the macro strategy.

Provides deterministic fixture data for calendar events (CPI, NFP),
market expectations, and actual releases so that the macro strategy
can be tested / replayed in isolation without a live data feed.

All fixture methods return plain dicts or lists-of-dicts for
maximum compatibility with the rest of the adapter layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


class AcquisitionStub:
    """Stub acquisition layer that yields synthetic fixture data.

    Every method is marked as a stub; in production these calls would
    be replaced by a real economic-calendar API client.

    Usage::

        stub = AcquisitionStub()
        cpi_events = stub.get_fixture_cpi_calendar()
        nfp_events = stub.get_fixture_nfp_calendar()
        expectation = stub.get_fixture_expectation("CPI", "2025-06-11")
        actual = stub.get_fixture_actual_release("CPI", "2025-06-11")
    """

    # ------------------------------------------------------------------
    # Fixture: CPI calendar
    # ------------------------------------------------------------------
    @staticmethod
    def get_fixture_cpi_calendar() -> list[dict[str, Any]]:
        """Return a synthetic list of CPI release events.

        Each entry contains:
            - release_id      : str   — unique event identifier
            - indicator       : str   — "CPI"
            - release_date    : str   — YYYY-MM-DD format (release day)
            - release_time    : str   - HH:MM UTC
            - country         : str   — "US"
            - source          : str   — "Bureau of Labor Statistics"
        """
        return [
            {
                "release_id": "CPI_2025_01",
                "indicator": "CPI",
                "release_date": "2025-01-15",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "CPI_2025_02",
                "indicator": "CPI",
                "release_date": "2025-02-12",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "CPI_2025_03",
                "indicator": "CPI",
                "release_date": "2025-03-12",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "CPI_2025_04",
                "indicator": "CPI",
                "release_date": "2025-04-10",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "CPI_2025_05",
                "indicator": "CPI",
                "release_date": "2025-05-14",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "CPI_2025_06",
                "indicator": "CPI",
                "release_date": "2025-06-11",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
        ]

    # ------------------------------------------------------------------
    # Fixture: NFP (Non-Farm Payroll) calendar
    # ------------------------------------------------------------------
    @staticmethod
    def get_fixture_nfp_calendar() -> list[dict[str, Any]]:
        """Return a synthetic list of NFP release events.

        Each entry contains:
            - release_id      : str
            - indicator       : str  — "NFP"
            - release_date    : str  — YYYY-MM-DD
            - release_time    : str  — HH:MM UTC
            - country         : str  — "US"
            - source          : str  — "Bureau of Labor Statistics"
        """
        return [
            {
                "release_id": "NFP_2025_01",
                "indicator": "NFP",
                "release_date": "2025-01-10",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "NFP_2025_02",
                "indicator": "NFP",
                "release_date": "2025-02-07",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "NFP_2025_03",
                "indicator": "NFP",
                "release_date": "2025-03-07",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "NFP_2025_04",
                "indicator": "NFP",
                "release_date": "2025-04-04",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "NFP_2025_05",
                "indicator": "NFP",
                "release_date": "2025-05-09",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
            {
                "release_id": "NFP_2025_06",
                "indicator": "NFP",
                "release_date": "2025-06-06",
                "release_time": "08:30",
                "country": "US",
                "source": "Bureau of Labor Statistics",
            },
        ]

    # ------------------------------------------------------------------
    # Fixture: Market expectation (consensus estimate)
    # ------------------------------------------------------------------
    @staticmethod
    def get_fixture_expectation(
        indicator: str,
        release_date: str,
    ) -> dict[str, Any]:
        """Return a synthetic consensus expectation for *indicator*.

        The returned dict contains:
            - indicator       : str
            - release_date    : str
            - consensus       : float  — the median economist forecast
            - high            : float  — high-end forecast
            - low             : float  — low-end forecast
            - num_estimates   : int    — number of economists surveyed
            - prior           : float  — previous release value
        """
        # Realistic-ish numbers by indicator
        fixtures: dict[str, dict[str, float]] = {
            "CPI": {
                "consensus": 3.4,
                "high": 3.7,
                "low": 3.1,
                "prior": 3.3,
            },
            "NFP": {
                "consensus": 185_000.0,
                "high": 250_000.0,
                "low": 120_000.0,
                "prior": 175_000.0,
            },
        }
        base = fixtures.get(indicator, fixtures["CPI"])

        return {
            "indicator": indicator,
            "release_date": release_date,
            "consensus": base["consensus"],
            "high": base["high"],
            "low": base["low"],
            "num_estimates": 72,
            "prior": base["prior"],
            "source": "Bloomberg Survey of Economists (fixture)",
        }

    # ------------------------------------------------------------------
    # Fixture: Actual release (realised value)
    # ------------------------------------------------------------------
    @staticmethod
    def get_fixture_actual_release(
        indicator: str,
        release_date: str,
    ) -> dict[str, Any]:
        """Return a synthetic actual release value for *indicator*.

        The returned dict contains:
            - indicator       : str
            - release_date    : str
            - actual          : float  — the realised figure
            - revised         : float  — revised prior (None if unchanged)
            - unit            : str    — e.g. "%", "k", "USD"
            - source          : str
        """
        # Realistic-ish actuals by indicator
        fixtures: dict[str, dict[str, Any]] = {
            "CPI": {
                "actual": 3.5,
                "revised_prior": None,
                "unit": "%",
            },
            "NFP": {
                "actual": 195_000.0,
                "revised_prior": 172_000.0,
                "unit": "k",
            },
        }
        base = fixtures.get(indicator, fixtures["CPI"])

        return {
            "indicator": indicator,
            "release_date": release_date,
            "actual": base["actual"],
            "revised_prior": base["revised_prior"],
            "unit": base["unit"],
            "source": "Bureau of Labor Statistics (fixture)",
        }

    # ------------------------------------------------------------------
    # Convenience: get a full release fixture (expectation + actual)
    # ------------------------------------------------------------------
    @classmethod
    def get_fixture_full_release(
        cls,
        indicator: str,
        release_date: str,
    ) -> dict[str, Any]:
        """Combine expectation + actual into a single release record."""
        exp = cls.get_fixture_expectation(indicator, release_date)
        act = cls.get_fixture_actual_release(indicator, release_date)
        return {
            **act,
            "consensus": exp["consensus"],
            "prior": exp["prior"],
            "surprise": round(act["actual"] - exp["consensus"], 4),
        }
