"""StrategyCandidateCompiler — compiles strategy candidates from seeds + claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import StrategySeedStatus, generate_id
from research.intelligence.contracts.strategy_candidate import (
    BaselineSpec,
    DatasetSpec,
    LabelSpec,
    Specification,
    SplitSpec,
    StrategyCandidate,
)
from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.compiler.provenance_validator import ProvenanceValidator


@dataclass
class CandidateCompilationReport:
    """Report of a single strategy-candidate compilation run."""

    candidate_id: str = ""
    success: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compiled_at: datetime = field(default_factory=datetime.utcnow)


class StrategyCandidateCompiler:
    """Compiles a ``StrategyCandidate`` from a validated ``StrategySeed``.

    Stages
    ------
    1. Validate seed — ensure the seed is ready
    2. Build specification skeleton from seed metadata
    3. Provenance check on linked claims
    4. Produce final StrategyCandidate
    """

    def __init__(self) -> None:
        self._provenance = ProvenanceValidator()

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile(
        self,
        seed: StrategySeed,
        claim_ids: list[str] | None = None,
        hypothesis_ids: list[str] | None = None,
    ) -> tuple[StrategyCandidate, CandidateCompilationReport]:
        """Compile a strategy candidate from a validated seed.

        Parameters
        ----------
        seed : StrategySeed
            A research-ready (or higher) strategy seed.
        claim_ids : list[str], optional
            Additional claim IDs to associate.
        hypothesis_ids : list[str], optional
            Additional hypothesis IDs to associate.

        Returns
        -------
        tuple[StrategyCandidate, CandidateCompilationReport]
        """
        report = CandidateCompilationReport()
        claim_ids = claim_ids or []
        hypothesis_ids = hypothesis_ids or []

        # 1. Validate the seed is ready for candidate creation
        if seed.research_status not in (
            StrategySeedStatus.RESEARCH_READY,
            StrategySeedStatus.SPECIFICATION_READY,
            StrategySeedStatus.VALIDATION_READY,
        ):
            report.errors.append(
                f"Seed {seed.strategy_seed_id} has status {seed.research_status.value}; "
                f"expected RESEARCH_READY, SPECIFICATION_READY, or VALIDATION_READY"
            )
            report.success = False
            return StrategyCandidate(), report

        # 2. Build specification skeleton
        try:
            spec = self._build_specification(seed)
        except Exception as exc:
            report.errors.append(f"Specification build failed: {exc}")
            report.success = False
            return StrategyCandidate(), report

        # 3. Provenance check on claims
        all_claim_ids = list(set(seed.claim_ids + claim_ids))
        prov_report = self._provenance.validate_chain(all_claim_ids)
        if not prov_report.passed:
            report.errors.extend(prov_report.errors)
            report.success = False
            return StrategyCandidate(), report
        report.warnings.extend(prov_report.warnings)

        # 4. Build candidate
        candidate = StrategyCandidate(
            name=seed.name,
            seed_id=seed.strategy_seed_id,
            specification=spec,
            claim_ids=all_claim_ids,
            hypothesis_ids=hypothesis_ids,
            domains=list(seed.domains),
            assets=list(seed.assets),
        )

        report.candidate_id = candidate.strategy_candidate_id
        report.success = True
        return candidate, report

    # ------------------------------------------------------------------
    # Specification builder
    # ------------------------------------------------------------------

    def _build_specification(self, seed: StrategySeed) -> Specification:
        """Build a bare-bones Specification from seed metadata."""
        spec = Specification(
            datasets=[
                DatasetSpec(
                    name="default",
                    source="unknown",
                    description=f"Dataset derived from seed: {seed.name}",
                )
            ],
            labels=[
                LabelSpec(
                    name="target",
                    column="target",
                    label_type="binary",
                )
            ],
            splits=SplitSpec(
                method="temporal",
                train_ratio=0.7,
                val_ratio=0.15,
                test_ratio=0.15,
                shuffle=False,
                seed=42,
            ),
            model_type="unset",
            abstention_logic="",
            invalidation_criteria="",
        )

        # Carry over any metadata from the seed that looks like hyperparameters
        if "hyperparameters" in seed.metadata:
            spec.hyperparameters = seed.metadata["hyperparameters"]

        return spec
