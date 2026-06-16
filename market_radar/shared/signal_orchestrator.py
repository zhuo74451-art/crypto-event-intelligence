"""Market Radar — Core Signal Orchestrator (Signal Spine v1).

Ties together: Observation → Noise Gate → Signal → Registry → Lifecycle.

This is the primary entry point for processing observations through
the Signal Spine. It provides a clear, testable interface:

  1. Accepts an Observation
  2. Runs the DeterministicNoiseGate
  3. Creates or updates a Signal in the SignalRegistry
  4. Returns a SignalSpineResult

An observation that enters twice:
  - Does NOT create a duplicate signal
  - May append new evidence to the existing signal
  - Returns a clear processing result
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.shared.models import (
    Observation,
    Signal,
    SignalStatus,
    GateVerdict,
    NoiseGateResult,
    SignalSpineResult,
    ObservationStatus,
    DataQuality,
    china_now,
    SIGNAL_SPINE_VERSION,
    CardFamily,
    DataSourceType,
)
from market_radar.shared.noise_gate import DeterministicNoiseGate
from market_radar.shared.signal_registry import SignalRegistry, create_signal_registry
from market_radar.shared.ai_fallback import (
    AIInterpreter,
    create_ai_interpreter,
    generate_template_interpretation,
)


class SignalOrchestrator:
    """Core orchestrator for the Signal Spine pipeline.

    Processes observations through the deterministic noise gate,
    manages signal lifecycle via the registry, and produces
    structured results.

    Usage:
        orchestrator = SignalOrchestrator()
        result = orchestrator.process(observation)
    """

    def __init__(
        self,
        noise_gate: Optional[DeterministicNoiseGate] = None,
        registry: Optional[SignalRegistry] = None,
        ai_interpreter: Optional[AIInterpreter] = None,
        auto_save: bool = True,
    ):
        self.noise_gate = noise_gate or DeterministicNoiseGate()
        self.registry = registry or create_signal_registry()
        self.ai_interpreter = ai_interpreter or create_ai_interpreter(available=False)
        self.auto_save = auto_save
        self._version = SIGNAL_SPINE_VERSION

        # Synchronize dedup keys from registry to gate
        self._sync_dedup_keys()

    def _sync_dedup_keys(self) -> None:
        """Sync known dedup keys from the registry to the noise gate."""
        keys = self.registry.get_dedup_keys()
        self.noise_gate.sync_dedup_keys(keys)

    def process(self, observation: Observation) -> SignalSpineResult:
        """Process a single observation through the Signal Spine.

        Steps:
          1. Mark observation as PROCESSED
          2. Run deterministic noise gate
          3. Aggregate gate verdict
          4. If gate passes, create/update signal in registry
          5. Return structured result

        Duplicate observations:
          - Same dedup_key → merged into existing signal (not duplicated)
          - New evidence appended
          - Returns existing signal reference
        """
        try:
            # Step 1: Mark observation status
            observation.ingestion_status = ObservationStatus.PROCESSED

            # Step 2: Evaluate through deterministic noise gate
            gate_results, gate_verdict = self.noise_gate.evaluate_and_aggregate(observation)

            # Step 3: Determine gate pass/fail
            gate_passed = gate_verdict in (GateVerdict.ACCEPT, GateVerdict.DOWNGRADE)

            # Check for rejected observations
            if gate_verdict == GateVerdict.REJECT:
                result = SignalSpineResult(
                    observation=observation,
                    gate_results=gate_results,
                    gate_passed=False,
                    signal=None,
                    registry_action="rejected_by_gate",
                    processed_at=china_now(),
                    pipeline_version=self._version,
                )
                if self.auto_save:
                    self.registry.save()
                return result

            # Step 4: Create or update signal in registry
            if gate_passed:
                # Generate AI fallback interpretation for signal metadata
                interpretation = self.ai_interpreter.interpret(observation)

                # Determine card family from observation or interpretation
                card_family = observation.card_family

                # Check if this observation already has a signal
                existing_signal = None
                if observation.event_dedup_key:
                    existing_signal = self.registry.get_signal_by_dedup_key(observation.event_dedup_key)
                if not existing_signal:
                    existing_signal = self.registry.get_signal_by_observation(observation.observation_id)

                if existing_signal:
                    # Duplicate observation — merge evidence
                    self.registry.merge_observation(
                        existing_signal, observation, gate_results
                    )
                    registry_action = "merged_into_existing"

                    # Update renderer payload
                    if existing_signal.renderer_payload:
                        existing_signal.renderer_payload["updated_at"] = china_now()
                        existing_signal.renderer_payload["observation_count"] = len(
                            existing_signal.observation_ids
                        )

                    signal = existing_signal
                else:
                    # Create new signal
                    direction = observation.normalized_payload.get(
                        "direction", interpretation.direction
                    )
                    confidence = interpretation.confidence
                    news_quality = self._assess_news_quality(observation)

                    signal = self.registry.create_signal(
                        title=interpretation.event_title,
                        affected_assets=observation.affected_assets,
                        event_type=interpretation.event_type,
                        direction=direction,
                        confidence=confidence,
                        observation=observation,
                        gate_results=gate_results,
                        trading_relevance=self._assess_trading_relevance(observation, interpretation),
                        news_quality=news_quality,
                        card_family=card_family,
                    )
                    registry_action = "created_new"
            else:
                signal = None
                registry_action = "gate_not_passed"

            # Step 5: Persist
            if self.auto_save:
                self.registry.save()

            return SignalSpineResult(
                observation=observation,
                gate_results=gate_results,
                gate_passed=gate_passed,
                signal=signal,
                registry_action=registry_action,
                processed_at=china_now(),
                pipeline_version=self._version,
            )

        except Exception as e:
            return SignalSpineResult(
                observation=observation,
                gate_results=[],
                gate_passed=False,
                signal=None,
                error=f"Orchestrator error: {type(e).__name__}: {e}",
                processed_at=china_now(),
                pipeline_version=self._version,
            )

    def _assess_news_quality(self, observation: Observation) -> str:
        """Assess news quality from observation data.

        Returns one of: "high", "medium", "low", "very_low"
        (standard product vocabulary).
        """
        dq = observation.data_quality
        if dq in (DataQuality.VERIFIED_HIGH,):
            return "high"
        if dq in (DataQuality.VERIFIED_MEDIUM,):
            return "medium"
        if dq is DataQuality.LOW_CREDIBILITY:
            return "very_low"
        if dq is DataQuality.UNVERIFIED:
            return "low"
        # UNKNOWN
        return "low"

    def _assess_trading_relevance(
        self,
        observation: Observation,
        interpretation: InterpretationResult,
    ) -> str:
        """Assess trading relevance from observation and interpretation.

        Returns one of: "high", "medium", "low", "none".
        Never returns arbitrary text.
        """
        # Use asset count as a heuristic
        asset_count = len(observation.affected_assets)
        intensity = observation.normalized_payload.get("intensity", "")

        if asset_count >= 3 and intensity in ("high", "critical"):
            return "high"
        if asset_count >= 1 and intensity in ("high", "medium"):
            return "medium"
        if asset_count >= 1:
            return "low"
        return "none"

    def process_batch(
        self,
        observations: list[Observation],
    ) -> list[SignalSpineResult]:
        """Process multiple observations sequentially.

        Each observation is processed independently. Observations
        referencing the same event (same dedup_key) will be merged
        into the same signal.
        """
        return [self.process(obs) for obs in observations]

    def get_registry(self) -> SignalRegistry:
        return self.registry

    def get_noise_gate(self) -> DeterministicNoiseGate:
        return self.noise_gate


def create_orchestrator(
    storage_path: Optional[str] = None,
    ai_available: bool = False,
) -> SignalOrchestrator:
    """Factory: create a fully configured SignalOrchestrator.

    Args:
        storage_path: Optional path for the signal registry JSON file.
        ai_available: Whether to enable AI interpretation (default: False).

    Returns:
        Configured SignalOrchestrator instance.
    """
    registry = create_signal_registry(storage_path=storage_path)
    ai_interpreter = create_ai_interpreter(available=ai_available)
    return SignalOrchestrator(
        registry=registry,
        ai_interpreter=ai_interpreter,
        auto_save=True,
    )
