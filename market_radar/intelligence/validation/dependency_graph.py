"""Dependency graph — tracks event dependencies for bootstrap and split integrity.

Identifies:
- Same macro release (event_dependency_group)
- Same origin source (origin_dependency_group)
- Window overlap (window_overlap_group)
- Revision families (revision_family_group)
- Strategy families (strategy_family_group)

Used by BootstrapEngine (cluster bootstrap) and ChronologicalSplitter (purge).
"""

import hashlib
from typing import Any, Optional


def _hash_group(*components: str) -> str:
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class DependencyGraph:
    """Builds and queries dependency relationships among validation records."""

    def __init__(self):
        self.records: list[dict] = []
        self.event_groups: dict[str, list[int]] = {}   # group_id -> indices
        self.origin_groups: dict[str, list[int]] = {}
        self.window_groups: dict[str, list[int]] = {}
        self.revision_groups: dict[str, list[int]] = {}
        self.strategy_groups: dict[str, list[int]] = {}

    def add_records(self, records: list[dict]) -> None:
        """Add records and compute all dependency groups."""
        self.records = records
        self._build_groups()

    def _build_groups(self) -> None:
        """Build all dependency groups from scratch."""
        self.event_groups = {}
        self.origin_groups = {}
        self.window_groups = {}
        self.revision_groups = {}
        self.strategy_groups = {}

        for idx, rec in enumerate(self.records):
            # 1. Event dependency group: same event_id
            event_id = rec.get("event_id", "unknown")
            eg = _hash_group("event", event_id)
            self.event_groups.setdefault(eg, []).append(idx)

            # 2. Origin dependency group: same origin source refs
            producer_refs = rec.get("producer_refs", {})
            origin_id = producer_refs.get("hypothesis_id", "") or \
                        producer_refs.get("strategy_instance_id", "") or \
                        event_id
            og = _hash_group("origin", origin_id)
            self.origin_groups.setdefault(og, []).append(idx)

            # 3. Window overlap group: same event + reference period
            ref_period = rec.get("reference_period", event_id)
            wg = _hash_group("window", event_id, ref_period)
            self.window_groups.setdefault(wg, []).append(idx)

            # 4. Revision family group: same event family + reference period
            family = rec.get("event_family", "unknown")
            rg = _hash_group("revision", family, ref_period)
            self.revision_groups.setdefault(rg, []).append(idx)

            # 5. Strategy family group: same strategy_id
            strat_id = rec.get("strategy_id", "unknown")
            sg = _hash_group("strategy", strat_id)
            self.strategy_groups.setdefault(sg, []).append(idx)

    def get_event_dependency_groups(self) -> list[list[int]]:
        """Return list of index groups sharing the same event."""
        return list(self.event_groups.values())

    def get_origin_dependency_groups(self) -> list[list[int]]:
        """Return list of index groups sharing the same origin."""
        return list(self.origin_groups.values())

    def get_window_overlap_groups(self) -> list[list[int]]:
        """Return list of index groups with overlapping windows."""
        return list(self.window_groups.values())

    def get_revision_family_groups(self) -> list[list[int]]:
        """Return list of index groups sharing revision family."""
        return list(self.revision_groups.values())

    def get_strategy_family_groups(self) -> list[list[int]]:
        """Return list of index groups sharing the same strategy."""
        return list(self.strategy_groups.values())

    def get_all_groups(self) -> dict[str, list[list[int]]]:
        """Return all dependency groups as a dict."""
        return {
            "event_dependency_group": self.get_event_dependency_groups(),
            "origin_dependency_group": self.get_origin_dependency_groups(),
            "window_overlap_group": self.get_window_overlap_groups(),
            "revision_family_group": self.get_revision_family_groups(),
            "strategy_family_group": self.get_strategy_family_groups(),
        }

    def get_record_dependency_group(self, idx: int) -> str:
        """Return the primary dependency group id for a record index."""
        if idx < 0 or idx >= len(self.records):
            return "out_of_range"
        rec = self.records[idx]
        event_id = rec.get("event_id", "unknown")
        return _hash_group("event", event_id)

    def count_independent_groups(self) -> int:
        """Return the number of unique event dependency groups (≈ independent events)."""
        return len(self.event_groups)
