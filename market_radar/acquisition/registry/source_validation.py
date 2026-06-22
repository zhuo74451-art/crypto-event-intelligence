from __future__ import annotations

from ..contracts.source import (
    SourceContract,
    AuthorityTier,
    SourceRole,
    AcquisitionMethod,
)


class SourceValidator:
    """Validates SourceContract instances and collections of contracts."""

    @classmethod
    def validate(cls, contract: SourceContract) -> list[str]:
        """Return a list of validation errors for a single contract.

        Checks:
        - source_id is non-empty
        - source_name is non-empty
        - authority_tier is a valid AuthorityTier enum
        - at least one role present
        - primary_method is a valid AcquisitionMethod
        - timeout_seconds > 0
        - If content_hash_required, preserve_raw_payload should be True
        """
        errors: list[str] = []

        if not contract.source_id:
            errors.append("source_id must be non-empty")

        if not contract.source_name:
            errors.append("source_name must be non-empty")

        if not isinstance(contract.authority_tier, AuthorityTier):
            errors.append(
                f"authority_tier must be an AuthorityTier enum, "
                f"got {type(contract.authority_tier).__name__}"
            )

        if not contract.roles:
            errors.append("at least one role must be present")
        else:
            for role in contract.roles:
                if not isinstance(role, SourceRole):
                    errors.append(
                        f"role {role!r} is not a valid SourceRole enum"
                    )

        if not isinstance(contract.primary_method, AcquisitionMethod):
            errors.append(
                f"primary_method must be an AcquisitionMethod enum, "
                f"got {type(contract.primary_method).__name__}"
            )

        if contract.timeout_seconds <= 0:
            errors.append(
                f"timeout_seconds must be > 0, got {contract.timeout_seconds}"
            )

        if contract.content_hash_required and not contract.preserve_raw_payload:
            errors.append(
                "if content_hash_required is True, "
                "preserve_raw_payload should also be True"
            )

        return errors

    @classmethod
    def validate_registry(cls, contracts: list[SourceContract]) -> list[str]:
        """Cross-source validation checks across a list of contracts.

        Current checks:
        - Duplicate source_ids
        - Upstream refs that point to non-existent contracts
        """
        errors: list[str] = []

        # Check for duplicate source_ids
        seen: dict[str, int] = {}
        for contract in contracts:
            seen[contract.source_id] = seen.get(contract.source_id, 0) + 1
        for sid, count in seen.items():
            if count > 1:
                errors.append(f"duplicate source_id '{sid}' found {count} times")

        # Build a set of all registered source_ids for cross-reference checks
        all_ids: set[str] = {c.source_id for c in contracts}

        for contract in contracts:
            for ref in contract.upstream_source_refs:
                if ref not in all_ids:
                    errors.append(
                        f"contract '{contract.source_id}' references upstream "
                        f"source '{ref}' which is not in the registry"
                    )

        return errors

    @classmethod
    def validate_independence_group(
        cls, contracts: list[SourceContract]
    ) -> list[str]:
        """Check for shared independence groups across contracts.

        Returns warnings about sources sharing the same independence group.
        """
        warnings: list[str] = []

        # Group contracts by independence_group (skip empty groups)
        groups: dict[str, list[str]] = {}
        for contract in contracts:
            if contract.independence_group:
                groups.setdefault(contract.independence_group, []).append(
                    contract.source_id
                )

        for group_name, members in groups.items():
            if len(members) > 1:
                warnings.append(
                    f"independence group '{group_name}' is shared by "
                    f"multiple sources: {', '.join(members)}"
                )

        return warnings
