"""StrategyCandidate — a fully-compiled research strategy ready for evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import (
    RuntimeContractStatus,
    StrategyCandidateValidationStatus,
    generate_id,
)
from research.intelligence.contracts.errors import (
    missing_abstention_logic,
    missing_invalidation,
    strategy_without_claims,
)


# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------

@dataclass
class DatasetSpec:
    """Specification of a dataset used by the candidate strategy."""

    name: str = ""
    source: str = ""
    version: str = ""
    path: str = ""
    description: str = ""
    columns: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("DatasetSpec: name is required")
        if not self.source:
            errors.append("DatasetSpec: source is required")
        return errors


@dataclass
class LabelSpec:
    """Specification of labels / target variable."""

    name: str = ""
    column: str = ""
    description: str = ""
    label_type: str = ""  # e.g. "binary", "regression", "multiclass"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("LabelSpec: name is required")
        if not self.column:
            errors.append("LabelSpec: column is required")
        return errors


@dataclass
class BaselineSpec:
    """Specification of a baseline model for comparison."""

    name: str = ""
    model_type: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("BaselineSpec: name is required")
        return errors


@dataclass
class SplitSpec:
    """Specification of train/validation/test splits."""

    method: str = ""  # e.g. "temporal", "random", "stratified"
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    shuffle: bool = True
    seed: int = 42

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.method:
            errors.append("SplitSpec: method is required")
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.001:
            errors.append(f"SplitSpec: ratios must sum to 1.0, got {total}")
        return errors


@dataclass
class Specification:
    """Full specification for a strategy candidate."""

    datasets: list[DatasetSpec] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    baselines: list[BaselineSpec] = field(default_factory=list)
    splits: SplitSpec = field(default_factory=SplitSpec)
    features: list[str] = field(default_factory=list)
    model_type: str = ""
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    abstention_logic: str = ""
    invalidation_criteria: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        for ds in self.datasets:
            errors.extend(ds.validate())
        for lbl in self.labels:
            errors.extend(lbl.validate())
        for bl in self.baselines:
            errors.extend(bl.validate())
        errors.extend(self.splits.validate())
        if not self.model_type:
            errors.append("Specification: model_type is required")
        return errors


# ---------------------------------------------------------------------------
# StrategyCandidate
# ---------------------------------------------------------------------------

@dataclass
class StrategyCandidate:
    """A fully compiled research strategy ready for evaluation and possible promotion."""

    strategy_candidate_id: str = field(default_factory=lambda: generate_id("SC"))
    source_seed_ids: list[str] = field(default_factory=list)
    compiled_at: datetime | None = None
    specification: Specification = field(default_factory=Specification)
    mechanism_claim_ids: list[str] = field(default_factory=list)
    counter_claim_ids: list[str] = field(default_factory=list)
    knowledge_gap_ids: list[str] = field(default_factory=list)
    dataset_spec: DatasetSpec = field(default_factory=DatasetSpec)
    label_spec: LabelSpec = field(default_factory=LabelSpec)
    baseline_spec: BaselineSpec = field(default_factory=BaselineSpec)
    split_spec: SplitSpec = field(default_factory=SplitSpec)
    leakage_checks: list[str] = field(default_factory=list)
    expected_information_increment: str = ""
    alternative_explanations: list[str] = field(default_factory=list)
    validation_status: StrategyCandidateValidationStatus = StrategyCandidateValidationStatus.UNVALIDATED
    runtime_contract_status: RuntimeContractStatus = RuntimeContractStatus.PENDING_INTEGRATION
    production_eligible: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.strategy_candidate_id:
            errors.append("strategy_candidate_id is required")

        if not self.source_seed_ids:
            errors.append("At least one source_seed_id is required")

        if not isinstance(self.validation_status, StrategyCandidateValidationStatus):
            errors.append("validation_status must be a StrategyCandidateValidationStatus enum")

        if not isinstance(self.runtime_contract_status, RuntimeContractStatus):
            errors.append("runtime_contract_status must be a RuntimeContractStatus enum")

        # Sub-specification validation
        errors.extend(self.specification.validate())

        # Business rules
        if not self.mechanism_claim_ids:
            errors.append(str(strategy_without_claims(self.strategy_candidate_id)))

        if not self.specification.abstention_logic:
            errors.append(str(missing_abstention_logic(self.strategy_candidate_id)))

        if not self.specification.invalidation_criteria:
            errors.append(str(missing_invalidation(self.strategy_candidate_id)))

        return errors
