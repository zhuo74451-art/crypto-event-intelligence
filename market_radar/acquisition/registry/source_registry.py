from __future__ import annotations

import threading
from typing import Optional

from ..contracts.source import SourceContract, AuthorityTier, SourceRole


class SourceRegistry:
    """Thread-safe in-memory registry for SourceContract instances."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._contracts: dict[str, SourceContract] = {}

    def register(self, contract: SourceContract) -> None:
        """Add or replace a contract. Validates source_id is non-empty."""
        if not contract.source_id:
            raise ValueError("source_id must be non-empty")
        with self._lock:
            self._contracts[contract.source_id] = contract

    def get(self, source_id: str) -> Optional[SourceContract]:
        """Return the contract for the given source_id, or None."""
        with self._lock:
            return self._contracts.get(source_id)

    def list(self) -> list[SourceContract]:
        """Return all registered contracts."""
        with self._lock:
            return list(self._contracts.values())

    def list_by_tier(self, tier: AuthorityTier) -> list[SourceContract]:
        """Filter contracts by authority tier."""
        with self._lock:
            return [c for c in self._contracts.values() if c.authority_tier == tier]

    def list_by_role(self, role: SourceRole) -> list[SourceContract]:
        """Filter contracts by role (contract may have multiple roles)."""
        with self._lock:
            return [c for c in self._contracts.values() if role in c.roles]

    def list_enabled(self) -> list[SourceContract]:
        """Return only enabled sources."""
        with self._lock:
            return [c for c in self._contracts.values() if c.enabled]

    def validate_dependencies(self) -> list[str]:
        """Check that all upstream_source_refs exist in the registry.

        Returns a list of warning messages for missing dependencies.
        """
        warnings: list[str] = []
        with self._lock:
            for contract in self._contracts.values():
                for ref in contract.upstream_source_refs:
                    if ref not in self._contracts:
                        warnings.append(
                            f"Contract '{contract.source_id}' references "
                            f"upstream source '{ref}' which is not registered"
                        )
        return warnings
