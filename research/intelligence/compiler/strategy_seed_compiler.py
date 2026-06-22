"""StrategySeedCompiler — compiles raw strategy seeds into enriched, validated seeds."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import StrategySeedStatus, generate_id
from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.compiler.provenance_validator import ProvenanceValidator


MANDATORY_SEED_FIELDS = [
    "name",
    "thesis",
    "strategy_family",
    "domains",
]


@dataclass
class SeedCompilationReport:
    """Report of a single strategy-seed compilation run."""

    seed_id: str = ""
    success: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    enriched_fields: list[str] = field(default_factory=list)
    compiled_at: datetime = field(default_factory=datetime.utcnow)


class StrategySeedCompiler:
    """Compiles a raw ``StrategySeed`` through the enrichment pipeline.

    Stages
    ------
    1. Validate — run seed.validate()
    2. Compile readiness — check mandatory fields
    3. Provenance check — run ProvenanceValidator on linked sources
    4. Enrich — apply enrichment rules to the seed
    5. Promote status — transition to SPECIFICATION_READY or REJECTED
    """

    def __init__(self) -> None:
        self._provenance = ProvenanceValidator()

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile(self, seed: StrategySeed) -> tuple[StrategySeed, SeedCompilationReport]:
        """Run the full compilation pipeline on *seed*.

        Returns the (possibly modified) seed and a report.
        """
        report = SeedCompilationReport(seed_id=seed.strategy_seed_id)

        # 1. Validate
        validation_errors = seed.validate()
        if validation_errors:
            report.errors.extend(validation_errors)
            report.success = False
            return seed, report

        # 2. Compile readiness — check mandatory fields
        readiness_errors = self.compile_readiness(seed)
        if readiness_errors:
            report.errors.extend(readiness_errors)
            report.success = False
            return seed, report

        # 3. Provenance check on origin refs
        prov_report = self._provenance.validate_chain(seed.origin_refs)
        if not prov_report.passed:
            report.errors.extend(prov_report.errors)
            report.success = False
            return seed, report

        report.warnings.extend(prov_report.warnings)

        # 4. Enrich
        try:
            seed = self._enrich(seed)
            report.enriched_fields = ["metadata"]
        except Exception as exc:
            report.errors.append(f"Enrichment failed: {exc}")
            report.success = False
            return seed, report

        # 5. Promote status
        if seed.research_status == StrategySeedStatus.UNVERIFIED:
            seed.research_status = StrategySeedStatus.RESEARCH_READY

        report.success = True
        return seed, report

    def compile_readiness(self, seed: StrategySeed) -> list[str]:
        """Check mandatory fields on a seed prior to compilation.

        Returns a list of error messages (empty = ready).
        """
        errors: list[str] = []
        for field_name in MANDATORY_SEED_FIELDS:
            value = getattr(seed, field_name, None)
            if not value or (isinstance(value, list) and not value):
                errors.append(f"Mandatory field '{field_name}' is missing or empty on seed {seed.strategy_seed_id}")
        return errors

    # ------------------------------------------------------------------
    # Enrichment helpers
    # ------------------------------------------------------------------

    def _enrich(self, seed: StrategySeed) -> StrategySeed:
        """Apply simple enrichment (normalise tags, fill description stubs)."""
        # Deduplicate domains
        seed.domains = sorted(set(d.strip() for d in seed.domains if d.strip()))

        # Add compilation timestamp to metadata
        seed.metadata["compiled_at"] = datetime.utcnow().isoformat()

        # If there are no claim_ids, note it in metadata
        if not seed.claim_ids:
            seed.metadata["warning"] = "No claim_ids provided during compilation"

        return seed
