"""Structured Operator Diagnosis for common Integration issues.

Each diagnosis includes severity, operator explanation, cause, safe action,
and whether retry is safe. No automatic repair.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class OperatorDiagnosis:
    """Structured diagnosis for a single operational issue."""
    code: str
    severity: str  # "info" | "warning" | "error" | "critical"
    summary: str
    explanation: str
    likely_cause: str
    safe_next_action: str
    retry_safe: bool = True
    data_may_be_incomplete: bool = False

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "summary": self.summary,
            "explanation": self.explanation,
            "likely_cause": self.likely_cause,
            "safe_next_action": self.safe_next_action,
            "retry_safe": self.retry_safe,
            "data_may_be_incomplete": self.data_may_be_incomplete,
        }


# ── Diagnostic Registry ──────────────────────────────────────────────

def diagnose_curated_api_unavailable(error: Optional[str] = None) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="CURATED_API_UNAVAILABLE",
        severity="error",
        summary="Curated API is unreachable",
        explanation="The Curated feed API did not return a valid response. "
                    "Feed items will be absent from the run.",
        likely_cause=error or "Network issue or API server down",
        safe_next_action="Check network connectivity and API status. "
                          "Retry with --mode fixture to verify other sources.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_normal_empty_feed() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="NORMAL_EMPTY_FEED",
        severity="info",
        summary="Feed returned zero new items (normal)",
        explanation="The Curated API responded successfully but returned "
                    "zero new items since the cursor. This is expected when "
                    "no new content has been published.",
        likely_cause="No new content since last cursor position",
        safe_next_action="No action needed. This is a normal empty batch.",
        retry_safe=True,
    )


def diagnose_cursor_corrupt() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="CURSOR_CORRUPT",
        severity="warning",
        summary="Feed cursor state is corrupted",
        explanation="The persisted cursor file could not be parsed. "
                    "Feed will start from the initial_since or None.",
        likely_cause="Manual edit, file system error, or version mismatch",
        safe_next_action="The cursor will be recreated on next successful run. "
                          "No manual repair needed.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_cursor_rollback() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="CURSOR_ROLLBACK",
        severity="warning",
        summary="Feed cursor attempted to roll back",
        explanation="The new cursor value is older than the persisted cursor. "
                    "This is rejected to prevent re-processing old items.",
        likely_cause="API returned inconsistent timestamps, or state corruption",
        safe_next_action="Retry the same run. If persistent, check API cursor stability.",
        retry_safe=True,
    )


def diagnose_hyperliquid_unavailable(error: Optional[str] = None) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="HYPERLIQUID_UNAVAILABLE",
        severity="error",
        summary="Hyperliquid API is unreachable",
        explanation="The Hyperliquid public adapter could not fetch data. "
                    "Whale positions and HYPE market price will be unavailable.",
        likely_cause=error or "Network issue or Hyperliquid API rate limit",
        safe_next_action="Check network and retry after a few minutes.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_ccxt_unavailable(source: str = "", error: Optional[str] = None) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="CCXT_UNAVAILABLE",
        severity="error",
        summary=f"CCXT exchange {source} is unreachable",
        explanation=f"The CCXT adapter could not fetch data from {source}. "
                    "Market prices for this source will be absent.",
        likely_cause=error or "Exchange rate limiting or network issue",
        safe_next_action="Check exchange status and retry. If persistent, verify API access.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_db_locked() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="DB_LOCKED",
        severity="error",
        summary="Run history database is locked",
        explanation="Another run or process is holding the SQLite lock. "
                    "This run cannot proceed until the lock is released.",
        likely_cause="Concurrent run or unclean shutdown",
        safe_next_action="Wait for the other run to finish. "
                          "Check for stale lock files if no other run is active.",
        retry_safe=True,
    )


def diagnose_stop_marker() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="STOP_MARKER_SET",
        severity="warning",
        summary="Stop marker is set — run was blocked",
        explanation="A STOP file exists in the state directory. The run "
                    "refused to start as a safety measure.",
        likely_cause="Previous emergency stop or manual intervention",
        safe_next_action="Verify it is safe to continue, then remove the STOP file.",
        retry_safe=True,
    )


def diagnose_schema_mismatch(expected: int, actual: int) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="SCHEMA_MISMATCH",
        severity="critical",
        summary="Database schema version mismatch",
        explanation=f"Expected schema v{expected} but found v{actual}. "
                    "The run history database may be from a different version.",
        likely_cause="Version upgrade or downgrade without migration",
        safe_next_action="Run schema migration or recreate the state directory.",
        retry_safe=False,
        data_may_be_incomplete=True,
    )


def diagnose_report_missing(path: str = "") -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="REPORT_MISSING",
        severity="error",
        summary="Run report file not found",
        explanation=f"The expected run report JSON was not found at {path}. "
                    "The run may have failed before writing the report.",
        likely_cause="Run failure, disk full, or permission issue",
        safe_next_action="Check disk space and permissions. Re-run if needed.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_parent_child_mismatch() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="PARENT_CHILD_MISMATCH",
        severity="error",
        summary="Run-history parent/child relationship is inconsistent",
        explanation="The shadow parent run exists but child runs do not "
                    "match the expected count or ordinals.",
        likely_cause="Partial shadow execution or DB corruption",
        safe_next_action="Inspect run_history.db manually. Consider re-running the shadow.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_runtime_artifact_incomplete(missing: list[str]) -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="RUNTIME_ARTIFACT_INCOMPLETE",
        severity="warning",
        summary=f"Missing run artifacts: {', '.join(missing)}",
        explanation="Some expected output files were not found. The run "
                    "may not have completed successfully.",
        likely_cause="Partial run failure or cleanup",
        safe_next_action="Check run status and errors in the report.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_stale_market_snapshot(asset: str = "") -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="STALE_MARKET_SNAPSHOT",
        severity="info",
        summary=f"Market snapshot for {asset} may be stale" if asset else "Market snapshot may be stale",
        explanation="The market data timestamp is older than expected. "
                    "This may indicate a delay in data delivery.",
        likely_cause="Exchange latency or delayed feed",
        safe_next_action="Verify market data freshness in the run report.",
        retry_safe=True,
    )


def diagnose_adapter_capability_missing(adapter: str = "", capability: str = "") -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="ADAPTER_CAPABILITY_MISSING",
        severity="warning",
        summary=f"{adapter} missing capability: {capability}" if adapter else "Adapter capability missing",
        explanation="An adapter does not support the requested operation. "
                    "This may cause degraded results for specific data types.",
        likely_cause="Adapter version mismatch or configuration",
        safe_next_action="Check adapter documentation for supported capabilities.",
        retry_safe=True,
        data_may_be_incomplete=True,
    )


def diagnose_whale_empty_positions() -> OperatorDiagnosis:
    return OperatorDiagnosis(
        code="WHALE_EMPTY_POSITIONS",
        severity="info",
        summary="Whale address has no open positions",
        explanation="The configured whale address returned zero positions. "
                    "This is normal for addresses that have closed all positions.",
        likely_cause="Address has no open positions on Hyperliquid",
        safe_next_action="Verify the address is correct. No action if expected.",
        retry_safe=True,
    )
