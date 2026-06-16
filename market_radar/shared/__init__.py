"""Market Radar Shared Pipeline — v117 + Signal Spine v1.

Adapter → NormalizedSignal → QualityGate → Renderer → SendReadinessGate → TG Test Sender → Evidence Ledger

Signal Spine v1:
  Observation → DeterministicNoiseGate → Signal → SignalRegistry → Lifecycle → Renderer-ready Payload
"""

__version__ = "1.17.0"

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    NormalizedSignal,
    GateDecision,
    SendReadinessDecision,
    RenderedCard,
    TGTestSendResult,
    EvidenceRecord,
    SharedPipelineResult,
    # Signal Spine v1
    Observation,
    ObservationStatus,
    DataQuality,
    DataOrigin,
    Signal,
    SignalStatus,
    StatusTransition,
    GateVerdict,
    NoiseGateResult,
    EvidenceLink,
    SignalSpineResult,
    is_valid_transition,
    SIGNAL_SPINE_VERSION,
)

from market_radar.shared.adapter_contract import (
    SignalAdapter,
    FixtureSignalAdapter,
)

from market_radar.shared.gate_contract import (
    QualityGate,
    SendReadinessGate,
)

from market_radar.shared.renderer_contract import (
    CardRenderer,
    create_renderer,
)

from market_radar.shared.sender_contract import (
    TGTestGroupSender,
    create_tg_sender,
)

from market_radar.shared.evidence_ledger import (
    EvidenceLedger,
    create_evidence_ledger,
)

from market_radar.shared.pipeline import (
    SharedPipeline,
    run_pipeline,
)

# Signal Spine v1 — new modules
from market_radar.shared.noise_gate import (
    DeterministicNoiseGate,
)
from market_radar.shared.signal_registry import (
    SignalRegistry,
    create_signal_registry,
)
from market_radar.shared.signal_orchestrator import (
    SignalOrchestrator,
    create_orchestrator,
)
from market_radar.shared.ai_fallback import (
    AIInterpreter,
    InterpretationResult,
    generate_template_interpretation,
    create_ai_interpreter,
)

# Signal Spine v1 — IO lane
from market_radar.shared.event_intelligence_semantics import (
    IntelligenceDecision,
    EventIntelligenceResult,
    evaluate_event_semantics,
)
from market_radar.shared.dry_run_renderer import (
    DryRunRenderer,
    DryRunOutput,
    create_dry_run_renderer,
)
from market_radar.shared.event_intelligence_mapper import (
    EventIntelligenceMapper,
    create_decision_mapper,
)
