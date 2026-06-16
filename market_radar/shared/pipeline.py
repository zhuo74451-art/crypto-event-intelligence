"""Market Radar v117 — Shared Pipeline Orchestrator.

Chains:
  adapter → quality gate → renderer → send-readiness gate → TG test-group sender → evidence ledger

Requirements:
  - 5 fixture card families can enter the shared pipeline
  - 3 verified card families output allow
  - liquidation fixture outputs blocked_gate_not_passed
  - whale fixture outputs blocked_manual_evidence
  - production readiness always False
  - At least 1 real free API adapter can complete the full pipeline
  - If TG safe config available, complete 1 TG test group one-shot; if not, output skipped
"""

from __future__ import annotations

import os
from typing import Any, Optional

from market_radar.shared.models import (
    CardFamily,
    DataSourceType,
    DataQuality,
    Observation,
    SharedPipelineResult,
    SignalSpineResult,
    china_now,
    PIPELINE_VERSION,
    FIVE_CARD_FAMILIES,
    THREE_VERIFIED_CARD_FAMILIES,
)
from market_radar.shared.adapter_contract import (
    SignalAdapter,
    FixtureSignalAdapter,
    FixtureCatalog,
)
from market_radar.shared.free_api_adapters import (
    create_real_free_api_adapter,
    MultiAssetMarketSyncFreeApiAdapter,
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
from market_radar.shared.noise_gate import DeterministicNoiseGate
from market_radar.shared.signal_registry import SignalRegistry, create_signal_registry
from market_radar.shared.signal_orchestrator import SignalOrchestrator, create_orchestrator
from market_radar.shared.ai_fallback import create_ai_interpreter
from market_radar.shared.event_intelligence_mapper import EventIntelligenceMapper, create_decision_mapper
from market_radar.shared.dry_run_renderer import DryRunRenderer, create_dry_run_renderer


class SharedPipeline:
    """Orchestrates the complete shared pipeline for one signal."""

    def __init__(
        self,
        quality_gate: Optional[QualityGate] = None,
        send_readiness_gate: Optional[SendReadinessGate] = None,
        renderer: Optional[CardRenderer] = None,
        tg_sender: Optional[TGTestGroupSender] = None,
        evidence_ledger: Optional[EvidenceLedger] = None,
        # Signal Spine v1 components
        signal_orchestrator: Optional[SignalOrchestrator] = None,
        decision_mapper: Optional[EventIntelligenceMapper] = None,
        dry_run_renderer: Optional[DryRunRenderer] = None,
        registry: Optional[SignalRegistry] = None,
    ):
        self.quality_gate = quality_gate or QualityGate()
        self.send_readiness_gate = send_readiness_gate or SendReadinessGate()
        self.renderer = renderer or create_renderer()
        self.tg_sender = tg_sender or create_tg_sender()
        self.evidence_ledger = evidence_ledger or create_evidence_ledger()

        # Signal Spine v1 components
        self.signal_orchestrator = signal_orchestrator
        self.decision_mapper = decision_mapper
        self.dry_run_renderer = dry_run_renderer
        self.registry = registry

    def run(self, adapter: SignalAdapter) -> SharedPipelineResult:
        """Run the full pipeline for a single adapter.

        Returns SharedPipelineResult with all stages recorded.
        """
        try:
            # Stage 1: Adapter → NormalizedSignal
            signal = adapter.fetch()

            # Stage 2: Quality Gate
            gate_decision = self.quality_gate.evaluate(signal)

            # Stage 3: Renderer → RenderedCard
            rendered_card = self.renderer.render(signal, gate_decision)

            # Stage 4: Send-Readiness Gate
            send_readiness = self.send_readiness_gate.evaluate(
                rendered_card,
                gate_decision,
                target="test_group",
            )

            # Stage 5: TG Test Group Sender (only if send-readiness allows)
            tg_result = None
            if send_readiness.allow_test_group:
                tg_result = self.tg_sender.send(rendered_card, send_readiness)
            else:
                from market_radar.shared.models import TGTestSendResult
                tg_result = TGTestSendResult(
                    attempted=False,
                    success=False,
                    status="blocked",
                    reason=f"Send-readiness not passed: {send_readiness.reason[:200]}",
                    target_type="test_group",
                    one_shot=True,
                    production_send=False,
                )

            # Stage 6: Evidence Ledger
            evidence = self.evidence_ledger.record(
                card_family=signal.card_family,
                asset_or_topic=signal.asset_or_topic,
                quality_gate_allow=gate_decision.allow,
                send_readiness_allow=send_readiness.allow_test_group,
                tg_result=tg_result,
            )

            return SharedPipelineResult(
                card_family=signal.card_family,
                asset_or_topic=signal.asset_or_topic,
                signal=signal,
                gate_decision=gate_decision,
                rendered_card=rendered_card,
                send_readiness=send_readiness,
                tg_result=tg_result,
                evidence=evidence,
            )

        except Exception as e:
            return SharedPipelineResult(
                card_family=adapter.card_family,
                asset_or_topic=adapter.card_family.value,
                error=f"Pipeline exception: {type(e).__name__}: {e}",
            )

    def run_signal_spine(
        self,
        adapter: SignalAdapter,
        source_label: Optional[str] = None,
        dry_run: bool = True,
        storage_path: Optional[str] = None,
    ) -> tuple[SignalSpineResult, Any]:
        """Run the full Signal Spine v1 pipeline for a single adapter.

        This is the unified end-to-end path:

          SignalAdapter → NormalizedSignal → Observation →
          DeterministicNoiseGate → SignalOrchestrator → SignalRegistry →
          EventIntelligenceMapper → DryRunRenderer → Evidence record

        Args:
            adapter: SignalAdapter instance to fetch data from.
            source_label: Optional human-readable source label.
            dry_run: If True (default), produce dry-run output without real send.
            storage_path: Optional registry storage path.

        Returns:
            (SignalSpineResult, DryRunOutput or None)
        """
        # Lazy-init spine components if not provided at construction
        if self.signal_orchestrator is None:
            reg = self.registry or create_signal_registry(storage_path=storage_path)
            self.registry = reg
            self.signal_orchestrator = create_orchestrator(storage_path=storage_path)
        if self.decision_mapper is None:
            self.decision_mapper = create_decision_mapper()
        if self.dry_run_renderer is None:
            self.dry_run_renderer = create_dry_run_renderer()

        try:
            # Stage 1: Adapter → NormalizedSignal
            signal = adapter.fetch()

            # Stage 2: NormalizedSignal → Observation
            obs = Observation.from_normalized_signal(
                signal=signal,
                source=source_label or adapter.adapter_label,
                data_quality=DataQuality.VERIFIED_MEDIUM
                if signal.source_type in (DataSourceType.FREE_PUBLIC_API, DataSourceType.FREE_PUBLIC_SOURCE)
                else DataQuality.UNVERIFIED,
            )

            # Stage 3: Observation → NoiseGate → SignalOrchestrator → Registry
            spine_result = self.signal_orchestrator.process(obs)

            # Stage 4: Event Intelligence Decision Mapper
            spine_result, ei_result = self.decision_mapper.populate_result(spine_result)

            # Stage 5: Dry-Run Renderer
            dry_run_output = None
            if dry_run:
                # Build fixture-like dict for renderer compatibility
                fixture_dict = {
                    "fixture_id": obs.observation_id[:12],
                    "card_family": signal.card_family.value if signal.card_family else "unknown",
                    "asset_or_topic": signal.asset_or_topic,
                    "dedup_key": obs.event_dedup_key,
                    "source_refs": signal.source_refs,
                    "risk_notes": signal.risk_notes,
                    "metrics": {
                        **signal.metrics,
                        "news_quality": ei_result.news_quality,
                        "trade_relevance": ei_result.trade_relevance,
                    },
                }
                dry_run_output = self.dry_run_renderer.render(
                    fixture_data=fixture_dict,
                    is_duplicate=(spine_result.registry_action == "merged_into_existing"),
                    signal=signal,
                )

            # Stage 6: Evidence Ledger
            self.evidence_ledger.record(
                card_family=signal.card_family,
                asset_or_topic=signal.asset_or_topic,
                quality_gate_allow=spine_result.gate_passed,
                send_readiness_allow=False,
                event_id=spine_result.signal.signal_id[:12] if spine_result.signal else None,
            )

            return spine_result, dry_run_output

        except Exception as e:
            from market_radar.shared.models import SignalSpineResult
            error_result = SignalSpineResult(
                observation=None,
                gate_results=[],
                gate_passed=False,
                error=f"SignalSpine exception: {type(e).__name__}: {e}",
            )
            return error_result, None

    def run_all_fixtures(self) -> list[SharedPipelineResult]:
        """Run all 5 fixture card families through the pipeline."""
        catalog = FixtureCatalog()
        results: list[SharedPipelineResult] = []
        for cf in FIVE_CARD_FAMILIES:
            adapter = catalog.adapter_for(cf)
            result = self.run(adapter)
            results.append(result)
        return results

    def run_real_free_api(
        self,
        card_family: Optional[CardFamily] = None,
    ) -> list[SharedPipelineResult]:
        """Run real free API adapters through the pipeline.

        Defaults to multi_asset_market_sync (the most reliable free data source).
        """
        results: list[SharedPipelineResult] = []
        families = [card_family] if card_family else [
            CardFamily.MULTI_ASSET_MARKET_SYNC,
            CardFamily.PRICE_OI_VOLUME_ANOMALY,
        ]

        for cf in families:
            adapter = create_real_free_api_adapter(cf)
            if adapter is None:
                results.append(SharedPipelineResult(
                    card_family=cf,
                    asset_or_topic="N/A",
                    error=f"No real free API adapter available for {cf.value}",
                ))
                continue
            result = self.run(adapter)
            results.append(result)

        return results


def run_pipeline(
    include_fixtures: bool = True,
    include_real_api: bool = True,
    card_family_for_real: Optional[CardFamily] = None,
) -> tuple[list[SharedPipelineResult], list[SharedPipelineResult], EvidenceLedger]:
    """Convenience function: run fixtures + real API and return all results.

    Returns:
        (fixture_results, real_api_results, evidence_ledger)
    """
    ledger = create_evidence_ledger()
    pipeline = SharedPipeline(evidence_ledger=ledger)

    fixture_results: list[SharedPipelineResult] = []
    real_results: list[SharedPipelineResult] = []

    if include_fixtures:
        fixture_results = pipeline.run_all_fixtures()

    if include_real_api:
        real_results = pipeline.run_real_free_api(card_family_for_real)

    return fixture_results, real_results, ledger
