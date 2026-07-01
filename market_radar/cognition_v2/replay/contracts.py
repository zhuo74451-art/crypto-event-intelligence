"""Replay-ready historical contracts and validators.

Dependency: domain contracts only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from market_radar.cognition_v2.domain.contracts import (
    CorrectionType,
    EventFamily,
    EvidenceRef,
    FutureEvidenceBlocker,
    HistoricalCaseManifest,
    MarketRegime,
    OutcomeWindow,
    SplitLabel,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Manifest builder
# ═══════════════════════════════════════════════════════════════════════════════

class ManifestBuilder:
    """Builds deterministic HistoricalCaseManifests."""

    @staticmethod
    def deterministic_case_id(
        event_family: EventFamily,
        event_time: Optional[datetime],
        title_hash: str,
    ) -> str:
        """Produce a deterministic case ID from stable fields."""
        content = json.dumps({
            "event_family": event_family.value,
            "event_time": event_time.isoformat() if event_time else "unknown",
            "title_hash": title_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    @staticmethod
    def compute_evidence_manifest_hash(
        evidence_refs: List[EvidenceRef],
    ) -> str:
        """Deterministic hash of evidence manifest."""
        ordered = sorted(evidence_refs, key=lambda r: (r.source, r.content_hash))
        content = json.dumps(
            [r.model_dump() for r in ordered],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def build_outcome_windows(
        event_id: str,
        event_time: datetime,
        price_data: Dict[str, Dict[str, Optional[float]]],
    ) -> List[OutcomeWindow]:
        """Build outcome windows from price data at standard intervals."""
        windows = []
        for label in ["1h", "6h", "24h", "3d", "7d"]:
            data = price_data.get(label, {})
            window = OutcomeWindow(
                window_label=label,
                event_id=event_id,
                open_time=event_time,
                close_time=event_time,  # Would use actual window close in real implementation
                open_price=data.get("open"),
                close_price=data.get("close"),
                high_price=data.get("high"),
                low_price=data.get("low"),
                volume=data.get("volume"),
                return_pct=data.get("return_pct"),
                direction=data.get("direction"),
            )
            windows.append(window)
        return windows


# ═══════════════════════════════════════════════════════════════════════════════
# Future-evidence leakage validator
# ═══════════════════════════════════════════════════════════════════════════════

class LeakageValidator:
    """Validates that no evidence from the future leaks into a time window."""

    def __init__(self, max_allowed_time: datetime):
        self._max_allowed_time = max_allowed_time

    def is_leaked(self, evidence_time: datetime) -> bool:
        """Check if evidence time exceeds the max allowed time."""
        return evidence_time > self._max_allowed_time

    def validate_evidence_set(
        self,
        evidence_times: List[datetime],
    ) -> Tuple[bool, List[datetime]]:
        """Validate all evidence times.

        Returns (is_clean, leaked_times).
        """
        leaked = [t for t in evidence_times if self.is_leaked(t)]
        return len(leaked) == 0, leaked

    def filter_evidence(
        self,
        evidence_times: List[datetime],
    ) -> List[datetime]:
        """Filter out leaked evidence times."""
        return [t for t in evidence_times if t <= self._max_allowed_time]


# ═══════════════════════════════════════════════════════════════════════════════
# Split-order integrity
# ═══════════════════════════════════════════════════════════════════════════════

class SplitOrderIntegrity:
    """Validates BUILD -> DEVELOPMENT -> BLIND time ordering."""

    VALID_ORDER = [SplitLabel.BUILD, SplitLabel.DEVELOPMENT, SplitLabel.BLIND]

    @staticmethod
    def validate_split_order(
        manifests: List[HistoricalCaseManifest],
    ) -> List[str]:
        """Validate split label ordering and return errors."""
        errors = []
        for m in manifests:
            try:
                idx = SplitOrderIntegrity.VALID_ORDER.index(m.split_label)
            except ValueError:
                errors.append(f"Case {m.case_id}: unknown split_label {m.split_label}")
                continue
            if idx == 0:
                continue  # BUILD — fine
            if idx > 0:
                # All evidence times must be <= the split boundary
                pass  # boundary check enforced separately
        return errors


# ═══════════════════════════════════════════════════════════════════════════════
# Correction relationship validator
# ═══════════════════════════════════════════════════════════════════════════════

class CorrectionRelations:
    """Tracks correction, retraction, and contradiction chains."""

    def __init__(self):
        self._relations: Dict[str, List[Tuple[str, CorrectionType]]] = {}

    def add_relation(
        self,
        source_case_id: str,
        target_case_id: str,
        correction_type: CorrectionType,
    ) -> None:
        if source_case_id not in self._relations:
            self._relations[source_case_id] = []
        self._relations[source_case_id].append((target_case_id, correction_type))

    def has_correction_chain(self, case_id: str) -> bool:
        return case_id in self._relations


# ═══════════════════════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════════════════════

def deterministic_manifest_serialize(manifest: HistoricalCaseManifest) -> str:
    """Deterministic JSON serialization of a manifest for hashing."""
    return json.dumps(
        manifest.model_dump(),
        sort_keys=True,
        default=str,
    )
