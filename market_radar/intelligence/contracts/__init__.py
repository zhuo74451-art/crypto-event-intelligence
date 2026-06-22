"""Intelligence kernel contracts — domain models and type definitions.

All contracts are pure data models with no I/O, no network, no time/ID generation.
"""

from .common import (
    ContractBase,
    SchemaVersion,
    DataAvailability,
    DataStatus,
    IntelligenceID,
    IDPrefix,
    hash_identity,
    hash_content,
    hash_revision,
    utc_now,
    utc_parse,
)

from .evidence import (
    VerificationStatus,
    EvidenceItem,
    EvidenceBundle,
    BundleStatus,
    EvidenceQualityReason,
)

from .event import (
    EventState,
    EventEntity,
    EventTransition,
    TransitionType,
    EventFamilyConfig,
    EventStateMachineRules,
)

from .regime import (
    RegimeDimension,
    RegimeSnapshot,
    RegimeTransition,
    RegimeApplicability,
    normalize_distribution,
)

from .expectation import (
    ExpectationType,
    NumericExpectation,
    NumericRangeExpectation,
    CategoricalExpectation,
    BinaryProbabilityExpectation,
    NoReliableExpectation,
    ExpectationGapResult,
    GapStatus,
)

from .transmission import (
    NodeType,
    TransmissionNode,
    EdgeSign,
    TransmissionEdge,
    TransmissionGraph,
)

from .strategy import (
    StrategyOrigin,
    StrategyPack,
    StrategyInstance,
    StrategyInstanceState,
    InstanceTransition,
)

from .hypothesis import (
    HypothesisStatus,
    MarketHypothesis,
)

from .arbitration import (
    ArbitrationInput,
    ArbitrationOutput,
    HorizonAssessment,
    VerdictState,
    HorizonBucket,
)

from .calibration import (
    ConfidenceType,
    ConfidenceStatement,
    CalibrationArtifactRef,
    CalibratorProtocol,
    NoCalibrationAvailable,
)

from .assessment import (
    Direction,
    ActionGuidance,
    HorizonDirectionAssessment,
    MarketAssessment,
    OverallStatus,
)

__all__ = [
    # common
    "ContractBase", "SchemaVersion", "DataAvailability", "DataStatus",
    "IntelligenceID", "IDPrefix",
    "hash_identity", "hash_content", "hash_revision",
    "utc_now", "utc_parse",
    # evidence
    "VerificationStatus", "EvidenceItem", "EvidenceBundle", "BundleStatus",
    "EvidenceQualityReason",
    # event
    "EventState", "EventEntity", "EventTransition", "TransitionType",
    "EventFamilyConfig", "EventStateMachineRules",
    # regime
    "RegimeDimension", "RegimeSnapshot", "RegimeTransition",
    "RegimeApplicability", "normalize_distribution",
    # expectation
    "ExpectationType", "NumericExpectation", "NumericRangeExpectation",
    "CategoricalExpectation", "BinaryProbabilityExpectation",
    "NoReliableExpectation", "ExpectationGapResult", "GapStatus",
    # transmission
    "NodeType", "TransmissionNode", "EdgeSign", "TransmissionEdge",
    "TransmissionGraph",
    # strategy
    "StrategyOrigin", "StrategyPack", "StrategyInstance",
    "StrategyInstanceState", "InstanceTransition",
    # hypothesis
    "HypothesisStatus", "MarketHypothesis",
    # arbitration
    "ArbitrationInput", "ArbitrationOutput", "HorizonAssessment",
    "VerdictState", "HorizonBucket",
    # calibration
    "ConfidenceType", "ConfidenceStatement", "CalibrationArtifactRef",
    "CalibratorProtocol", "NoCalibrationAvailable",
    # assessment
    "Direction", "ActionGuidance", "HorizonDirectionAssessment",
    "MarketAssessment", "OverallStatus",
]
