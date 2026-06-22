from __future__ import annotations

import datetime
from typing import Any, Optional

from ..contracts.health import DriftSeverity, ParserDriftReport


class ParserDriftDetector:
    """Detects drift in parsed source data over successive acquisitions.

    Stores previous parse snapshots in memory and compares them with
    the current parse to identify regressions such as missing required
    fields, type changes, time-format shifts, or content-type changes.
    """

    def __init__(self) -> None:
        # source_id -> dict of field-name -> (type, sample_value)
        self._snapshots: dict[str, dict[str, Any]] = {}
        # source_id -> previous content-type (string)
        self._content_types: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(
        self,
        source_id: str,
        parsed_fields: dict,
        expected_schema: Optional[dict] = None,
    ) -> ParserDriftReport:
        """Compare *parsed_fields* against the stored snapshot for *source_id*.

        Returns a ``ParserDriftReport`` summarising any detected drift.
        """
        details: list[str] = []
        fields_affected: list[str] = []
        severity = DriftSeverity.NONE

        previous = self._snapshots.get(source_id)
        if previous is None:
            # No baseline yet — nothing to compare against
            return ParserDriftReport(
                source_id=source_id,
                severity=DriftSeverity.NONE,
                details=(),
                fields_affected=(),
                detected_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1) Required fields suddenly missing
        missing = self._check_missing_fields(previous, parsed_fields)
        if missing:
            details.append(f"Required fields missing: {', '.join(missing)}")
            fields_affected.extend(missing)
            severity = DriftSeverity.BREAKING

        # 2) Field type changes
        type_changes = self._check_type_changes(previous, parsed_fields)
        if type_changes:
            for field, old_t, new_t in type_changes:
                details.append(
                    f"Type change for '{field}': {old_t} -> {new_t}"
                )
                fields_affected.append(field)
            if severity != DriftSeverity.BREAKING:
                severity = DriftSeverity.BREAKING

        # 3) Time format changes
        time_changes = self._check_time_format_changes(
            previous, parsed_fields
        )
        if time_changes:
            for field in time_changes:
                details.append(f"Time format change for '{field}'")
                fields_affected.append(field)
            if severity != DriftSeverity.BREAKING:
                severity = DriftSeverity.WARNING

        # 4) Content-Type changes
        ct_change = self._check_content_type_change(source_id, parsed_fields)
        if ct_change:
            old_ct, new_ct = ct_change
            details.append(f"Content-Type changed: '{old_ct}' -> '{new_ct}'")
            self._content_types[source_id] = new_ct
            if severity != DriftSeverity.BREAKING:
                severity = DriftSeverity.WARNING

        # 5) expected_schema validation (optional)
        if expected_schema is not None:
            schema_issues = self._validate_against_schema(
                parsed_fields, expected_schema
            )
            if schema_issues:
                for field, issue in schema_issues:
                    details.append(f"Schema mismatch for '{field}': {issue}")
                    fields_affected.append(field)
                severity = DriftSeverity.BREAKING

        # Deduplicate fields_affected while preserving order
        seen: set[str] = set()
        unique_fields: list[str] = []
        for f in fields_affected:
            if f not in seen:
                seen.add(f)
                unique_fields.append(f)

        return ParserDriftReport(
            source_id=source_id,
            severity=severity,
            details=tuple(details),
            fields_affected=tuple(unique_fields),
            detected_at=now,
        )

    def record_parse(self, source_id: str, parsed_fields: dict) -> None:
        """Store a snapshot of *parsed_fields* for future drift comparison."""
        snapshot: dict[str, Any] = {}
        for key, value in parsed_fields.items():
            snapshot[key] = {
                "type": type(value).__name__,
                "sample": value,
            }
        self._snapshots[source_id] = snapshot

        # Also store content-type if present
        if "content_type" in parsed_fields:
            self._content_types[source_id] = str(parsed_fields["content_type"])

    def get_drift_report(self, source_id: str) -> Optional[ParserDriftReport]:
        """Return the most recent drift report for *source_id*, if any.

        .. note::
           This implementation returns ``None`` because we do not persist
           reports — callers should capture the return value of :meth:`detect`.
        """
        _ = source_id
        return None

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_missing_fields(
        previous: dict,
        current: dict,
    ) -> list[str]:
        """Return field names that existed in *previous* but are absent now."""
        missing: list[str] = []
        for key in previous:
            if key not in current:
                missing.append(key)
        return missing

    @staticmethod
    def _check_type_changes(
        previous: dict,
        current: dict,
    ) -> list[tuple[str, str, str]]:
        """Return (field, old_type, new_type) for fields whose type changed."""
        changes: list[tuple[str, str, str]] = []
        for key, prev_info in previous.items():
            if key not in current:
                continue
            old_type = prev_info["type"]
            new_type = type(current[key]).__name__
            if old_type != new_type:
                changes.append((key, old_type, new_type))
        return changes

    @staticmethod
    def _check_time_format_changes(
        previous: dict,
        current: dict,
    ) -> list[str]:
        """Detect fields that changed date-time format between parses.

        Heuristic: if both old and new values look like timestamps but
        the length or character pattern differs, flag them.
        """
        import re

        _time_pattern = re.compile(
            r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", re.IGNORECASE
        )
        changed: list[str] = []
        for key, prev_info in previous.items():
            if key not in current:
                continue
            old_val = prev_info.get("sample")
            new_val = current[key]
            if isinstance(old_val, str) and isinstance(new_val, str):
                old_is_time = bool(_time_pattern.match(old_val))
                new_is_time = bool(_time_pattern.match(new_val))
                if old_is_time and new_is_time:
                    # Both are timestamps — check format consistency
                    if len(old_val) != len(new_val):
                        changed.append(key)
                elif old_is_time != new_is_time:
                    # One is a timestamp, the other is not
                    changed.append(key)
        return changed

    def _check_content_type_change(
        self,
        source_id: str,
        parsed_fields: dict,
    ) -> Optional[tuple[str, str]]:
        """Return (old_content_type, new_content_type) when a change is detected."""
        old_ct = self._content_types.get(source_id)
        if old_ct is None:
            return None
        new_ct = parsed_fields.get("content_type")
        if new_ct is None:
            return None
        new_ct = str(new_ct)
        if old_ct != new_ct:
            return (old_ct, new_ct)
        return None

    @staticmethod
    def _validate_against_schema(
        parsed_fields: dict,
        schema: dict,
    ) -> list[tuple[str, str]]:
        """Compare *parsed_fields* against an *expected_schema* dict.

        The schema is a dict of field_name -> expected_type_name (e.g.
        {"title": "str", "published": "str"}).
        """
        issues: list[tuple[str, str]] = []
        for field, expected_type in schema.items():
            if field not in parsed_fields:
                issues.append((field, "missing"))
                continue
            actual_type = type(parsed_fields[field]).__name__
            if actual_type != expected_type:
                issues.append(
                    (field, f"expected {expected_type}, got {actual_type}")
                )
        return issues
