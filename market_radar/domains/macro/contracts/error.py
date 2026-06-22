from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum


@dataclass(frozen=True)
class MacroErrorCode:
    """A structured error code with code string, message and description."""
    code: str
    message: str
    description: str


class MacroError(MacroEnum):
    """Domain-level error codes for the macro scheduled event system.

    Each member carries ``code``, ``message`` and ``description`` attributes
    accessible via ``.value.code``, ``.value.message``, ``.value.description``.
    """

    # ── Calendar / Scheduling ──────────────────────────────────────
    RELEASE_NOT_SCHEDULED = MacroErrorCode(
        code="RELEASE_NOT_SCHEDULED",
        message="Release event is not on the calendar",
        description="The requested release event ID does not correspond to any "
                    "known calendar entry.",
    )
    SCHEDULE_CONFLICT = MacroErrorCode(
        code="SCHEDULE_CONFLICT",
        message="Conflicting schedule information from different sources",
        description="Two or more calendar sources report different scheduled "
                    "times for the same release event.",
    )
    EVENT_ALREADY_RELEASED = MacroErrorCode(
        code="EVENT_ALREADY_RELEASED",
        message="Event has already been released",
        description="An attempt was made to update or modify a calendar event "
                    "that has already been published.",
    )
    INVALID_TIMEZONE = MacroErrorCode(
        code="INVALID_TIMEZONE",
        message="Source timezone is invalid or missing",
        description="The IANA timezone identifier provided for the release "
                    "authority could not be resolved.",
    )

    # ── Expectation / Consensus ────────────────────────────────────
    NO_EXPECTATION_AVAILABLE = MacroErrorCode(
        code="NO_EXPECTATION_AVAILABLE",
        message="No expectation data available for the given component",
        description="The system has no recorded expectations for the "
                    "specified release component.",
    )
    EXPECTATION_SOURCE_MISMATCH = MacroErrorCode(
        code="EXPECTATION_SOURCE_MISMATCH",
        message="Expectation sources provide conflicting values",
        description="Two or more expectation sources disagree beyond "
                    "the configured tolerance threshold.",
    )
    STALE_EXPECTATION = MacroErrorCode(
        code="STALE_EXPECTATION",
        message="Expectation data is too old to be reliable",
        description="The captured expectation predates the acceptable "
                    "freshness window for the given release.",
    )
    INSUFFICIENT_RESPONDENTS = MacroErrorCode(
        code="INSUFFICIENT_RESPONDENTS",
        message="Too few respondents to form a reliable consensus",
        description="The number of contributors in the survey falls below "
                    "the minimum threshold for this release family.",
    )

    # ── Actual / Publication ───────────────────────────────────────
    ACTUAL_NOT_PUBLISHED = MacroErrorCode(
        code="ACTUAL_NOT_PUBLISHED",
        message="Actual data has not been published yet",
        description="The requested actual release data is not yet available.",
    )
    PRIOR_VALUE_MISSING = MacroErrorCode(
        code="PRIOR_VALUE_MISSING",
        message="Prior value for comparison is missing",
        description="The system has no prior-period value to compute "
                    "a period-over-period comparison.",
    )
    REVISION_NOT_FOUND = MacroErrorCode(
        code="REVISION_NOT_FOUND",
        message="No revision record found for the given parameters",
        description="A revision lookup by event / component / date "
                    "returned no results.",
    )
    VALUE_OUT_OF_BOUNDS = MacroErrorCode(
        code="VALUE_OUT_OF_BOUNDS",
        message="Published value is outside expected range",
        description="The officially released value deviates from the "
                    "expectation band beyond the configured outlier threshold.",
    )

    # ── Data Quality ───────────────────────────────────────────────
    DATA_INTEGRITY_ERROR = MacroErrorCode(
        code="DATA_INTEGRITY_ERROR",
        message="Data integrity check failed",
        description="The retrieved data failed one or more integrity "
                    "checks (e.g. checksum, schema validation).",
    )
    PARSING_FAILURE = MacroErrorCode(
        code="PARSING_FAILURE",
        message="Failed to parse source data",
        description="The raw source document could not be parsed into "
                    "a structured macro record.",
    )
    SOURCE_UNAVAILABLE = MacroErrorCode(
        code="SOURCE_UNAVAILABLE",
        message="Source feed or document is unavailable",
        description="The external source (API, web page, file) could "
                    "not be reached or returned an error status.",
    )
    TIMELINE_GAP = MacroErrorCode(
        code="TIMELINE_GAP",
        message="Gap in the data timeline detected",
        description="A chronological gap exists between consecutive "
                    "observations for the same component.",
    )

    # ── Configuration / System ─────────────────────────────────────
    UNSUPPORTED_RELEASE_FAMILY = MacroErrorCode(
        code="UNSUPPORTED_RELEASE_FAMILY",
        message="Release family is not supported by this configuration",
        description="The release family is not registered in the system "
                    "configuration and cannot be processed.",
    )
    MISSING_COMPONENT_MAPPING = MacroErrorCode(
        code="MISSING_COMPONENT_MAPPING",
        message="Component identifier mapping not found",
        description="The component ID could not be resolved to a known "
                    "canonical component definition.",
    )
    PIPELINE_ALREADY_RUNNING = MacroErrorCode(
        code="PIPELINE_ALREADY_RUNNING",
        message="The requested pipeline execution is already in progress",
        description="A concurrent pipeline execution for the same event "
                    "or component is already running.",
    )
    INTERNAL_ERROR = MacroErrorCode(
        code="INTERNAL_ERROR",
        message="An unexpected internal error occurred",
        description="The system encountered an unexpected condition "
                    "that prevented completion of the requested operation.",
    )

    # ── Cross-Asset / Context ──────────────────────────────────────
    CROSS_ASSET_DATA_UNAVAILABLE = MacroErrorCode(
        code="CROSS_ASSET_DATA_UNAVAILABLE",
        message="Cross-asset snapshot data is unavailable",
        description="The cross-asset context data required for analysis "
                    "could not be retrieved.",
    )
    MARKET_CONTEXT_STALE = MacroErrorCode(
        code="MARKET_CONTEXT_STALE",
        message="Market context data exceeds freshness threshold",
        description="The market context snapshot is older than the "
                    "acceptable freshness limit for the requested analysis.",
    )

    @property
    def code(self) -> str:
        return self.value.code

    @property
    def message(self) -> str:
        return self.value.message

    @property
    def description(self) -> str:
        return self.value.description
