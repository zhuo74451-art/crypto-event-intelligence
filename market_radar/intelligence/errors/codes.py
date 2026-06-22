"""Structured error codes for the intelligence kernel.

Every error is serializable, has a machine code, and a human-readable explanation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    INVALID_SCHEMA_VERSION = "INVALID_SCHEMA_VERSION"
    NAIVE_DATETIME = "NAIVE_DATETIME"
    PROBABILITY_OUT_OF_RANGE = "PROBABILITY_OUT_OF_RANGE"
    PROBABILITY_SUM_INVALID = "PROBABILITY_SUM_INVALID"
    MISSING_REQUIRED_EVIDENCE = "MISSING_REQUIRED_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    ILLEGAL_EVENT_TRANSITION = "ILLEGAL_EVENT_TRANSITION"
    INVALID_STRATEGY_TRANSITION = "INVALID_STRATEGY_TRANSITION"
    MISSING_ABSTENTION_LOGIC = "MISSING_ABSTENTION_LOGIC"
    MISSING_INVALIDATION = "MISSING_INVALIDATION"
    UNSUPPORTED_CALIBRATED_CONFIDENCE = "UNSUPPORTED_CALIBRATED_CONFIDENCE"
    TRANSMISSION_PATH_LIMIT = "TRANSMISSION_PATH_LIMIT"
    REFLEXIVE_CYCLE_NOT_DECLARED = "REFLEXIVE_CYCLE_NOT_DECLARED"
    LEGACY_MAPPING_LOSS = "LEGACY_MAPPING_LOSS"
    INSUFFICIENT_EXPECTATION_DATA = "INSUFFICIENT_EXPECTATION_DATA"
    UNKNOWN_VERSION = "UNKNOWN_VERSION"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    DUPLICATE_NODE = "DUPLICATE_NODE"
    MISSING_NODE = "MISSING_NODE"

    def describe(self) -> str:
        descriptions = {
            ErrorCode.INVALID_SCHEMA_VERSION: "Schema version is incompatible or malformed",
            ErrorCode.NAIVE_DATETIME: "Naive datetime provided without timezone",
            ErrorCode.PROBABILITY_OUT_OF_RANGE: "Probability value is not in [0.0, 1.0]",
            ErrorCode.PROBABILITY_SUM_INVALID: "Mutually exclusive probabilities do not sum to 1.0",
            ErrorCode.MISSING_REQUIRED_EVIDENCE: "Required evidence is missing or insufficient",
            ErrorCode.CONFLICTING_EVIDENCE: "Multiple evidence sources are in conflict",
            ErrorCode.ILLEGAL_EVENT_TRANSITION: "Event state transition is not allowed",
            ErrorCode.INVALID_STRATEGY_TRANSITION: "Strategy instance transition is not allowed",
            ErrorCode.MISSING_ABSTENTION_LOGIC: "Strategy pack is missing abstention logic",
            ErrorCode.MISSING_INVALIDATION: "Component is missing invalidation conditions",
            ErrorCode.UNSUPPORTED_CALIBRATED_CONFIDENCE: "Calibrated probability used without valid artifact",
            ErrorCode.TRANSMISSION_PATH_LIMIT: "Transmission path search exceeded maximum depth",
            ErrorCode.REFLEXIVE_CYCLE_NOT_DECLARED: "Self-loop edge must have reflexive=True",
            ErrorCode.LEGACY_MAPPING_LOSS: "Legacy adapter mapping loses semantic information",
            ErrorCode.INSUFFICIENT_EXPECTATION_DATA: "Insufficient data to compute expectation gap",
            ErrorCode.UNKNOWN_VERSION: "Unknown schema major version, refusing to read",
            ErrorCode.INVALID_TRANSITION: "General invalid state transition",
            ErrorCode.DUPLICATE_NODE: "Node already exists in the graph",
            ErrorCode.MISSING_NODE: "Referenced node does not exist in the graph",
        }
        return descriptions.get(self, "Unknown error")


class IntelligenceError(Exception):
    """Structured exception for intelligence kernel errors.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable explanation.
        details: Optional structured details.
        sensitive: If True, do not log raw payload.
    """

    def __init__(self, code: ErrorCode, message: str = "",
                 details: Optional[dict] = None, sensitive: bool = False):
        if isinstance(code, str):
            code = ErrorCode(code)
        self.code = code
        self.message = message or code.describe()
        self.details = details or {}
        self.sensitive = sensitive
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details if not self.sensitive else {},
        }

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"
