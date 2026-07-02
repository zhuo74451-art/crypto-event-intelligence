"""Frozen split allocator.

D09: Allocate by correction-chain root event time with immutable
boundary/version records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from market_radar.cognition_v2.data_factory.contracts import (
    FrozenSplitAssignment,
    SplitLabel,
)


class FrozenSplitAllocator:
    """Allocate cases to BUILD/DEVELOPMENT/BLIND splits.

    Target: BUILD ~60%, DEVELOPMENT ~20%, BLIND ~20%.
    Allocation by correction-chain root event time.
    """

    def __init__(
        self,
        boundary_version: str = "1.0",
        build_cutoff: Optional[datetime] = None,
        development_cutoff: Optional[datetime] = None,
    ):
        self._boundary_version = boundary_version
        self._build_cutoff = build_cutoff
        self._development_cutoff = development_cutoff

    def allocate(
        self,
        case_id: str,
        event_time: datetime,
        chain_root_time: Optional[datetime] = None,
    ) -> FrozenSplitAssignment:
        """Allocate a case to a split based on event time.

        Uses chain_root_time when available, otherwise event_time.
        """
        alloc_time = chain_root_time or event_time
        if alloc_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")

        if self._build_cutoff is not None and alloc_time <= self._build_cutoff:
            label = SplitLabel.BUILD
        elif (self._development_cutoff is not None
              and alloc_time <= self._development_cutoff):
            label = SplitLabel.DEVELOPMENT
        else:
            label = SplitLabel.BLIND

        return FrozenSplitAssignment(
            case_id=case_id,
            split_label=label,
            split_boundary_version=self._boundary_version,
            chain_root_time=chain_root_time or event_time,
        )

    @staticmethod
    def compute_default_boundaries(
        cases: List[Tuple[str, datetime]],
        target_build: float = 0.60,
        target_development: float = 0.20,
    ) -> Tuple[datetime, datetime]:
        """Compute boundary times from case list to approximate target splits."""
        sorted_times = sorted(t for _, t in cases if t.tzinfo is not None)
        if not sorted_times:
            raise ValueError("No timezone-aware event times")

        n = len(sorted_times)
        build_idx = max(0, min(n - 1, int(n * target_build)))
        dev_idx = max(0, min(n - 1, int(n * (target_build + target_development))))

        build_cutoff = sorted_times[build_idx]
        development_cutoff = sorted_times[dev_idx]

        if build_cutoff >= development_cutoff:
            development_cutoff = sorted_times[-1]

        return build_cutoff, development_cutoff

    def validate_no_cross_split(
        self,
        assignments: List[FrozenSplitAssignment],
        case_to_group: Dict[str, str],
    ) -> List[str]:
        """Validate that groups (identities, chains) don't cross splits."""
        errors = []
        group_splits: Dict[str, Set[SplitLabel]] = {}

        for a in assignments:
            g = case_to_group.get(a.case_id)
            if g is None:
                continue
            if g not in group_splits:
                group_splits[g] = set()
            group_splits[g].add(a.split_label)

        for gid, splits in group_splits.items():
            if len(splits) > 1:
                errors.append(
                    f"Group '{gid}' crosses splits: "
                    f"{', '.join(s.value for s in splits)}"
                )
        return errors
