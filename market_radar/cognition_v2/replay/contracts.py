"""Replay-ready historical contracts and validators.

Dependency: domain contracts only.
R04: explicit point-in-time authority — no silent defaults for historical data.
R05: real future-leakage validation using first_seen_at and retrieval_time.
R06: real split-order integrity with frozen boundaries.
R07: correct outcome window times from event time.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from market_radar.cognition_v2.domain.contracts import (
    CANONICAL_EDGES,
    CorrectionType,
    EventFamily,
    EvidenceRef,
    FutureEvidenceBlocker,
    HistoricalCaseManifest,
    MarketRegime,
    OutcomeWindow,
    SourceAuthority,
    FactPermission,
    SplitLabel,
)


CANONICAL_WINDOW_LABELS = {"1h", "6h", "24h", "3d", "7d"}

WINDOW_DURATIONS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "3d": timedelta(days=3),
    "7d": timedelta(days=7),
}


# ═══════════════════════════════════════════════════════════════════════════════
# R04 — Explicit point-in-time authority (no silent defaults)
# ═══════════════════════════════════════════════════════════════════════════════

class HistoricalSourceRecord:
    """Source record for historical evidence — authority and times are always explicit."""
    def __init__(
        self,
        source_id: str,
        name: str,
        source_type: str,
        authority: SourceAuthority,
        fact_permission: FactPermission,
        first_seen_at: datetime,
    ):
        if not authority or authority == SourceAuthority.UNKNOWN:
            raise ValueError("Historical source authority must be explicitly supplied")
        if not fact_permission or fact_permission == FactPermission.NONE:
            raise ValueError("Historical source fact_permission must be explicitly supplied")
        if first_seen_at.tzinfo is None:
            raise ValueError("first_seen_at must be timezone-aware")
        self.source_id = source_id
        self.name = name
        self.source_type = source_type
        self.authority = authority
        self.fact_permission = fact_permission
        self.first_seen_at = first_seen_at


class HistoricalEvidenceRecord:
    """Evidence record for historical data — times are always explicit."""
    def __init__(
        self,
        evidence_id: str,
        source_id: str,
        content_hash: str,
        first_seen_at: datetime,
        retrieval_time: datetime,
        publication_time: Optional[datetime] = None,
        effective_time: Optional[datetime] = None,
        assessment_time: Optional[datetime] = None,
    ):
        if first_seen_at.tzinfo is None:
            raise ValueError("first_seen_at must be timezone-aware")
        if retrieval_time.tzinfo is None:
            raise ValueError("retrieval_time must be timezone-aware")
        if assessment_time is not None and assessment_time.tzinfo is None:
            raise ValueError("assessment_time must be timezone-aware")
        self.evidence_id = evidence_id
        self.source_id = source_id
        self.content_hash = content_hash
        self.first_seen_at = first_seen_at
        self.retrieval_time = retrieval_time
        self.publication_time = publication_time
        self.effective_time = effective_time
        self.assessment_time = assessment_time

    def available_at(self, cutoff: datetime) -> bool:
        """Evidence is available when both first_seen and retrieval are <= cutoff."""
        return self.first_seen_at <= cutoff and self.retrieval_time <= cutoff


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
        """Deterministic hash of evidence manifest — excludes outcome data."""
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
        """Build outcome windows from price data at standard intervals.

        R07: close times are computed from event_time, not set equal to it.
        """
        if event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")

        windows = []
        for label in ["1h", "6h", "24h", "3d", "7d"]:
            if label not in CANONICAL_WINDOW_LABELS:
                continue
            duration = WINDOW_DURATIONS[label]
            close_time = event_time + duration

            data = price_data.get(label, {})
            window = OutcomeWindow(
                window_label=label,
                event_id=event_id,
                open_time=event_time,
                close_time=close_time,
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
# R05 — Real future-leakage validation using evidence availability
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceLeakageResult:
    """Result of leakage validation with exact blocked IDs and reasons."""
    def __init__(self, blocked_ids: List[str], reasons: List[str], is_clean: bool):
        self.blocked_ids = blocked_ids
        self.reasons = reasons
        self.is_clean = is_clean


class LeakageValidator:
    """Validates evidence availability against an assessment cutoff.

    R05: Uses first_seen_at and retrieval_time — publication/effective time
    alone must never make later-retrieved evidence available earlier.
    """

    def __init__(self, assessment_cutoff: datetime):
        if assessment_cutoff.tzinfo is None:
            raise ValueError("assessment_cutoff must be timezone-aware")
        self._cutoff = assessment_cutoff

    @property
    def cutoff(self) -> datetime:
        return self._cutoff

    def is_available(self, evidence: HistoricalEvidenceRecord) -> bool:
        """Evidence is available when both first_seen and retrieval are <= cutoff."""
        return evidence.available_at(self._cutoff)

    def validate_evidence_list(
        self,
        evidence_list: List[HistoricalEvidenceRecord],
    ) -> EvidenceLeakageResult:
        """Validate a list of evidence records.

        Returns result with blocked IDs and reasons.
        """
        blocked_ids = []
        reasons = []

        for ev in evidence_list:
            if ev.first_seen_at.tzinfo is None or ev.retrieval_time.tzinfo is None:
                blocked_ids.append(ev.evidence_id)
                reasons.append(f"Evidence {ev.evidence_id}: timezone-naive timestamps")
                continue

            if not self.is_available(ev):
                blocked_ids.append(ev.evidence_id)
                details = []
                if ev.first_seen_at > self._cutoff:
                    details.append(f"first_seen_at {ev.first_seen_at.isoformat()} > cutoff")
                if ev.retrieval_time > self._cutoff:
                    details.append(f"retrieval_time {ev.retrieval_time.isoformat()} > cutoff")
                reasons.append(f"Evidence {ev.evidence_id}: not available — {'; '.join(details)}")

        return EvidenceLeakageResult(
            blocked_ids=blocked_ids,
            reasons=reasons,
            is_clean=len(blocked_ids) == 0,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# R06 — Real split-order integrity with frozen boundaries
# ═══════════════════════════════════════════════════════════════════════════════

class SplitBoundary:
    """A frozen boundary that separates splits.

    BUILD < DEVELOPMENT < BLIND chronologically.
    One case cannot appear in multiple splits.
    Adding a newer case cannot retroactively move an existing frozen BLIND case.
    """

    def __init__(self, build_max_time: datetime, development_max_time: datetime):
        if build_max_time.tzinfo is None or development_max_time.tzinfo is None:
            raise ValueError("Split boundaries must be timezone-aware")
        if build_max_time >= development_max_time:
            raise ValueError("BUILD max time must be before DEVELOPMENT max time")
        self.build_max_time = build_max_time
        self.development_max_time = development_max_time

    def classify(self, event_time: datetime) -> SplitLabel:
        """Classify an event time into a split label."""
        if event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if event_time <= self.build_max_time:
            return SplitLabel.BUILD
        elif event_time <= self.development_max_time:
            return SplitLabel.DEVELOPMENT
        else:
            return SplitLabel.BLIND


class SplitOrderResult:
    """Result of split-order validation with exact violations."""
    def __init__(self):
        self.errors: List[str] = []
        self.case_splits: Dict[str, SplitLabel] = {}

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class SplitOrderIntegrity:
    """Validates BUILD -> DEVELOPMENT -> BLIND ordering with frozen boundaries.

    R06: replaces the no-op validator with explicit boundary checks.
    """

    @staticmethod
    def validate(
        manifests: List[HistoricalCaseManifest],
        boundary: SplitBoundary,
    ) -> SplitOrderResult:
        """Validate all manifest splits against a frozen boundary."""
        result = SplitOrderResult()

        for m in manifests:
            # Check event time is available
            if m.event_time is None:
                result.errors.append(f"Case {m.case_id}: missing event_time, cannot classify")
                continue
            if m.event_time.tzinfo is None:
                result.errors.append(f"Case {m.case_id}: event_time must be timezone-aware")
                continue

            # Classify by boundary
            expected_label = boundary.classify(m.event_time)

            # Check if case is in multiple splits (by case_id collision)
            if m.case_id in result.case_splits:
                prev_label = result.case_splits[m.case_id]
                result.errors.append(
                    f"Case {m.case_id}: appears in both {prev_label.value} "
                    f"and {m.split_label.value}"
                )
                continue

            result.case_splits[m.case_id] = m.split_label

            # Check split label matches boundary classification
            if m.split_label != expected_label:
                result.errors.append(
                    f"Case {m.case_id}: split_label {m.split_label.value} "
                    f"does not match boundary classification {expected_label.value} "
                    f"for event_time {m.event_time.isoformat()}"
                )

        return result

    @staticmethod
    def check_blind_isolation(blind_case_ids: Set[str], training_ids: Set[str]) -> List[str]:
        """Verify BLIND IDs are not accepted as tuning/training input."""
        overlap = blind_case_ids & training_ids
        if overlap:
            return [f"BLIND case {cid} found in training set" for cid in overlap]
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# R07 — Outcome window validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_outcome_window(window: OutcomeWindow) -> List[str]:
    """Validate an outcome window's integrity.

    Returns a list of error messages (empty = valid).
    """
    errors = []

    # Label from canonical set
    if window.window_label not in CANONICAL_WINDOW_LABELS:
        errors.append(f"Label '{window.window_label}' not in canonical set")

    # Close time after open time
    if window.close_time <= window.open_time:
        errors.append(
            f"close_time {window.close_time.isoformat()} must be after "
            f"open_time {window.open_time.isoformat()}"
        )

    # Price values are finite when present
    for field, name in [
        (window.open_price, "open_price"),
        (window.close_price, "close_price"),
        (window.high_price, "high_price"),
        (window.low_price, "low_price"),
        (window.volume, "volume"),
        (window.return_pct, "return_pct"),
    ]:
        if field is not None:
            import math
            if not math.isfinite(field):
                errors.append(f"{name} must be finite, got {field}")

    # High is not below low
    if window.high_price is not None and window.low_price is not None:
        if window.high_price < window.low_price:
            errors.append(
                f"high_price {window.high_price} is below low_price {window.low_price}"
            )

    return errors


def validate_outcome_windows(windows: List[OutcomeWindow]) -> List[str]:
    """Validate a list of outcome windows."""
    all_errors = []
    for w in windows:
        all_errors.extend(validate_outcome_window(w))
    return all_errors


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

    def get_chain_members(self, root_id: str) -> Set[str]:
        """Get all members of a correction chain starting from root."""
        members = {root_id}
        queue = [root_id]
        while queue:
            current = queue.pop(0)
            if current in self._relations:
                for target, _ in self._relations[current]:
                    if target not in members:
                        members.add(target)
                        queue.append(target)
        return members


# ═══════════════════════════════════════════════════════════════════════════════
# R14 — Correction-chain split isolation
# ═══════════════════════════════════════════════════════════════════════════════

class ChainSplitResult:
    """Result of correction-chain split isolation validation."""
    def __init__(self):
        self.errors: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


class CorrectionChainSplitValidator:
    """Validates that correction chains stay within one split.

    R14: The frozen split validator must reject:
    - same event identity across more than one split
    - correction chain crossing splits
    - BLIND chain member in BUILD/DEVELOPMENT tuning
    """

    @staticmethod
    def validate(
        manifests: List[HistoricalCaseManifest],
        split_assignment: Optional[Dict[str, SplitLabel]] = None,
        tuning_case_ids: Optional[Set[str]] = None,
    ) -> ChainSplitResult:
        """Validate all correction chains stay within their assigned split.

        Uses persisted identity fields (event_identity_id, correction_chain_id,
        chain_root_case_id) from manifests only — no fallback to case_id.
        A missing event_identity_id means event-identity comparison is unavailable.
        A missing correction_chain_id means the case is not part of a chain.

        When tuning_case_ids is provided, also validates BLIND tuning exclusion:
        - BLIND case IDs cannot be in the tuning set
        - tuning cases sharing a BLIND event_identity_id are rejected
        - tuning cases belonging to a BLIND correction_chain_id are rejected
        - chain members from BLIND cannot enter tuning through alternate case IDs

        Reports exact violating case IDs in diagnostics.
        """
        if split_assignment is None:
            split_assignment = {}
        if tuning_case_ids is None:
            tuning_case_ids = set()
        result = ChainSplitResult()

        # Build case_id -> split_label lookup
        case_to_split: Dict[str, SplitLabel] = {}
        for m in manifests:
            case_to_split[m.case_id] = m.split_label
        case_to_split.update(split_assignment)

        # Build manifest lookup by case_id
        manifest_by_id: Dict[str, HistoricalCaseManifest] = {}
        for m in manifests:
            manifest_by_id[m.case_id] = m

        # ═══════════════════════════════════════════════════════════════
        # BLIND tuning exclusion check
        # ═══════════════════════════════════════════════════════════════
        if tuning_case_ids:
            # Identify BLIND case IDs
            blind_case_ids: Set[str] = set()
            for m in manifests:
                if m.split_label == SplitLabel.BLIND:
                    blind_case_ids.add(m.case_id)

            # Build BLIND event identities and correction chain IDs
            blind_event_ids: Set[str] = set()
            blind_chain_ids: Set[str] = set()
            for m in manifests:
                if m.split_label == SplitLabel.BLIND:
                    if m.event_identity_id is not None:
                        blind_event_ids.add(m.event_identity_id)
                    if m.correction_chain_id is not None:
                        blind_chain_ids.add(m.correction_chain_id)

            # 1. BLIND case ID in tuning
            for tc in sorted(tuning_case_ids):
                if tc in blind_case_ids:
                    result.errors.append(
                        f"Tuning case '{tc}' is a BLIND case"
                    )

            # 2. Tuning case sharing BLIND event identity
            for tc in sorted(tuning_case_ids):
                m = manifest_by_id.get(tc)
                if m is not None and m.event_identity_id is not None:
                    if m.event_identity_id in blind_event_ids:
                        result.errors.append(
                            f"Tuning case '{tc}' has BLIND event identity "
                            f"'{m.event_identity_id}'"
                        )

            # 3. Tuning case belonging to BLIND correction chain
            for tc in sorted(tuning_case_ids):
                m = manifest_by_id.get(tc)
                if m is not None and m.correction_chain_id is not None:
                    if m.correction_chain_id in blind_chain_ids:
                        result.errors.append(
                            f"Tuning case '{tc}' belongs to BLIND correction "
                            f"chain '{m.correction_chain_id}'"
                        )

            # 4. Chain member from BLIND entering tuning through alternate case ID
            for tc in sorted(tuning_case_ids):
                m = manifest_by_id.get(tc)
                if m is not None and m.correction_chain_id is not None:
                    cid = m.correction_chain_id
                    # Check if any member of this chain is BLIND
                    for other in manifests:
                        if (other.correction_chain_id == cid
                                and other.split_label == SplitLabel.BLIND):
                            result.errors.append(
                                f"Tuning case '{tc}' (chain '{cid}') has "
                                f"BLIND chain member '{other.case_id}'"
                            )
                            break

        # ═══════════════════════════════════════════════════════════════
        # Event identity cross-split check (explicit identity only)
        # ═══════════════════════════════════════════════════════════════
        event_identity_info: Dict[str, Tuple[Set[str], Set[SplitLabel]]] = {}
        for m in manifests:
            if m.event_identity_id is None:
                continue
            eid = m.event_identity_id
            if eid not in event_identity_info:
                event_identity_info[eid] = (set(), set())
            event_identity_info[eid][0].add(m.case_id)
            event_identity_info[eid][1].add(m.split_label)

        for eid, (case_ids, splits) in event_identity_info.items():
            if len(splits) > 1:
                result.errors.append(
                    f"Event identity '{eid}' appears in multiple splits: "
                    f"{', '.join(sorted(s.value for s in splits))}"
                    f". Violating case IDs: {sorted(case_ids)}"
                )

        # ═══════════════════════════════════════════════════════════════
        # Correction chain split check (explicit chain_id only)
        # ═══════════════════════════════════════════════════════════════
        chain_groups: Dict[str, List[HistoricalCaseManifest]] = {}
        for m in manifests:
            if m.correction_chain_id is None:
                continue
            cid = m.correction_chain_id
            if cid not in chain_groups:
                chain_groups[cid] = []
            chain_groups[cid].append(m)

        for chain_id, members in chain_groups.items():
            member_ids = sorted({m.case_id for m in members})

            # Consistent chain_root_case_id
            root_declarations: Set[str] = set()
            for m in members:
                if m.chain_root_case_id is not None:
                    root_declarations.add(m.chain_root_case_id)
            if len(root_declarations) > 1:
                result.errors.append(
                    f"Correction chain '{chain_id}' has inconsistent "
                    f"chain_root_case_id declarations: "
                    f"{sorted(root_declarations)}"
                    f". Members: {member_ids}"
                )
                continue

            # Check declared root exists
            if root_declarations:
                root_id = next(iter(root_declarations))
                root_manifest = next(
                    (m for m in members if m.case_id == root_id), None
                )
                if root_manifest is None:
                    result.errors.append(
                        f"Correction chain '{chain_id}' declares "
                        f"chain_root_case_id='{root_id}' but no manifest "
                        f"with that case_id exists in the chain"
                        f". Members: {member_ids}"
                    )
                    continue

                if root_manifest.correction_chain_id != chain_id:
                    result.errors.append(
                        f"Correction chain '{chain_id}' declares "
                        f"chain_root_case_id='{root_id}' but that case "
                        f"belongs to chain '{root_manifest.correction_chain_id}'"
                    )
            else:
                if not member_ids:
                    continue

            # Determine active root
            active_root = next(iter(root_declarations)) if root_declarations else member_ids[0]

            # Check all members in same split
            member_splits = set()
            for mid in member_ids:
                if mid in case_to_split:
                    member_splits.add(case_to_split[mid])

            if len(member_splits) > 1:
                result.errors.append(
                    f"Correction chain '{chain_id}' (root '{active_root}') "
                    f"spans multiple splits: "
                    f"{', '.join(sorted(s.value for s in member_splits))}"
                    f". Chain members: {member_ids}"
                )

        return result


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
