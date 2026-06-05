"""Market Radar Shared Pipeline — v117.

Adapter → NormalizedSignal → QualityGate → Renderer → SendReadinessGate → TG Test Sender → Evidence Ledger
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
