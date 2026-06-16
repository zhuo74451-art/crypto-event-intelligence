"""Signal Spine v1 — Unified Event Intelligence Decision Mapper.

Single mapping layer that consumes SignalSpineResult from the core
pipeline and produces the final Event Intelligence decision.

This is the ONE place where gate rules, registry actions, and event
semantics converge into a final decision. No other module independently
evaluates event semantics for the production path.

Input: SignalSpineResult (from core orchestrator)
Output: EventIntelligenceResult (from IO lane)

Mapping rules:
  - duplicate merged → suppress_duplicate (no card)
  - stale/recycled → DISCARD
  - insufficient/unverified source → DISCARD (or RISK_TIP if deterministic)
  - high pump/chase risk → BLOCK
  - valid but uncertain → OBSERVE
  - material security/exchange risk → RISK_TIP
  - rejected no-value event → DISCARD

Final decision vocabulary (only these four):
  OBSERVE | RISK_TIP | BLOCK | DISCARD
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.shared.models import (
    SignalSpineResult,
    GateVerdict,
    SignalStatus,
    NoiseGateResult,
    Observation,
    DataOrigin,
    china_now,
    SIGNAL_SPINE_VERSION,
)
from market_radar.shared.event_intelligence_semantics import (
    IntelligenceDecision,
    EventIntelligenceResult,
)


VALID_WATCH_WINDOWS = {"1h", "4h", "24h"}


class EventIntelligenceMapper:
    """Maps core pipeline results to event intelligence decisions.

    This is the bridge between the deterministic gate + registry
    and the IO lane's decision semantics. It consumes the structured
    pipeline output and produces the final four-category decision.

    Never produces buy/sell/long/short language.
    """

    def __init__(self):
        self._version = SIGNAL_SPINE_VERSION

    def map_result(self, result: SignalSpineResult) -> EventIntelligenceResult:
        """Map a SignalSpineResult to an EventIntelligenceResult.

        This is the primary entry point for the decision mapping.
        """
        obs = result.observation
        signal = result.signal

        # ── 1. Check for duplicate/suppressed observations ──
        if result.registry_action == "merged_into_existing":
            title = result.signal.title if result.signal else obs.normalized_payload.get("title", "")
            # Preserve original data_origin — duplicate does not change provenance
            origin = self._resolve_data_origin(obs, result)
            return EventIntelligenceResult(
                event_description=f"[DUPLICATE] {title}",
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance=self._get_trade_relevance(obs),
                data_origin=origin,
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["dedup", "duplicate_content", "suppressed"],
                observation_window="N/A — suppressed",
                evidence_summary=f"Duplicate observation merged into existing signal. Source: {obs.source}",
                source_refs=obs.source_refs + ["dedup:merged"],
                dedup_key=obs.event_dedup_key,
            )

        # ── 2. Check registry/gate reject ──
        if result.registry_action == "rejected_by_gate" or not result.gate_passed:
            return self._map_rejected(obs, result)

        # ── 3. From this point, gate passed (accept or downgrade) ──
        # Check individual gate rule results for actionable findings
        if signal:
            return self._map_from_gate_rules(obs, result, signal)

        # Fallback: no signal but gate passed
        return self._default_observe(obs, result)

    def _map_rejected(self, obs: Observation, result: SignalSpineResult) -> EventIntelligenceResult:
        """Map a rejected observation to the appropriate decision.

        Priority:
          1. high_chase_or_pump_risk + REJECT → BLOCK (禁止)
          2. stale/recycled → DISCARD
          3. low credibility / insufficient source → DISCARD
          4. no tradable asset / no material value → DISCARD
          5. security / exchange / liquidation material risk → RISK_TIP
          6. default → DISCARD
        """
        gate_map = {r.rule_name: r for r in result.gate_results}
        origin = self._resolve_data_origin(obs, result)

        # Priority 1: Pump/chase risk → BLOCK
        pump_result = gate_map.get("high_chase_or_pump_risk")
        if pump_result and pump_result.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=obs.normalized_payload.get("title", "High pump/FOMO risk event"),
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance=self._get_trade_relevance(obs),
                data_origin=origin,
                decision=IntelligenceDecision.BLOCK,
                risk_tags=["pump_and_dump", "high_risk", "blocked"],
                observation_window="N/A — blocked",
                evidence_summary=f"Event blocked: high pump/chase risk detected. {pump_result.reason[:150]}",
                source_refs=obs.source_refs + ["gate:blocked_pump"],
                dedup_key=obs.event_dedup_key,
            )

        # Priority 2: Stale/recycled → DISCARD
        stale = gate_map.get("stale_or_recycled_event")
        if stale and stale.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=f"[STALE] {obs.normalized_payload.get('title', 'Recycled event')}",
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="low",
                data_origin=origin,
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["old_news", "stale_information", "recycled"],
                observation_window="N/A — stale",
                evidence_summary=f"Event stale/recycled. {stale.reason[:150]}",
                source_refs=obs.source_refs + ["gate:rejected_stale"],
                dedup_key=obs.event_dedup_key,
            )

        # Priority 3: Insufficient/unverified source → DISCARD
        source = gate_map.get("insufficient_source_quality")
        if source and source.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=obs.normalized_payload.get("title", "Low credibility event"),
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="none",
                data_origin=origin,
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["unverified_source", "low_credibility"],
                observation_window="N/A — discarded",
                evidence_summary=f"Insufficient source quality. {source.reason[:150]}",
                source_refs=obs.source_refs + ["gate:rejected_source"],
                dedup_key=obs.event_dedup_key,
            )

        single = gate_map.get("single_unverified_source")
        if single and single.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=obs.normalized_payload.get("title", "Single unverified source"),
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="none",
                data_origin=origin,
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["unverified_source", "single_source"],
                observation_window="N/A — discarded",
                evidence_summary=f"Single unverified source. {single.reason[:150]}",
                source_refs=obs.source_refs + ["gate:rejected_single_source"],
                dedup_key=obs.event_dedup_key,
            )

        # Default: generic DISCARD
        rejection_reasons = [r.reason_code for r in result.gate_results if r.verdict == GateVerdict.REJECT]
        return EventIntelligenceResult(
            event_description=obs.normalized_payload.get("title", "Rejected event"),
            assets=obs.affected_assets,
            news_quality=self._get_news_quality(obs),
            trade_relevance="none",
            data_origin=origin,
            decision=IntelligenceDecision.DISCARD,
            risk_tags=["rejected"] + [r.rule_name for r in result.gate_results if r.verdict == GateVerdict.REJECT],
            observation_window="N/A — discarded",
            evidence_summary=f"Event rejected. Reasons: {', '.join(rejection_reasons)}",
            source_refs=obs.source_refs + ["gate:rejected"],
            dedup_key=obs.event_dedup_key,
        )

    def _map_from_gate_rules(
        self,
        obs: Observation,
        result: SignalSpineResult,
        signal: Signal,
    ) -> EventIntelligenceResult:
        """Map from individual gate rule results, incorporating signal state."""
        gate_map = {r.rule_name: r for r in result.gate_results}
        risk_tags = []
        decision = IntelligenceDecision.OBSERVE
        data_origin = self._resolve_data_origin(obs, result)

        # Check for pump/chase risk (BLOCK)
        pump_result = gate_map.get("high_chase_or_pump_risk")
        if pump_result and pump_result.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=signal.title,
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance=self._get_trade_relevance(obs),
                data_origin=data_origin,
                decision=IntelligenceDecision.BLOCK,
                risk_tags=["pump_and_dump", "high_risk", "blocked"],
                observation_window="N/A — blocked",
                evidence_summary=f"Event blocked: high pump/chase risk detected. {pump_result.reason[:100]}",
                source_refs=obs.source_refs + ["gate:blocked_pump"],
                dedup_key=obs.event_dedup_key,
            )
        if pump_result and pump_result.verdict == GateVerdict.DOWNGRADE:
            risk_tags.append("pump_risk_downgrade")

        # Check for insufficient source (DISCARD)
        source_result = gate_map.get("insufficient_source_quality")
        if source_result and source_result.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=signal.title,
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="none",
                data_origin=self._resolve_data_origin(obs, result),
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["unverified_source", "low_credibility"],
                observation_window="N/A — discarded",
                evidence_summary=f"Insufficient source quality: {source_result.reason[:100]}",
                source_refs=obs.source_refs + ["gate:rejected_source"],
                dedup_key=obs.event_dedup_key,
            )

        single_source = gate_map.get("single_unverified_source")
        if single_source and single_source.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=signal.title,
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="none",
                data_origin=self._resolve_data_origin(obs, result),
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["unverified_source", "single_source", "insufficient_evidence"],
                observation_window="N/A — discarded",
                evidence_summary=f"Single unverified source: {single_source.reason[:100]}",
                source_refs=obs.source_refs + ["gate:rejected_single_source"],
                dedup_key=obs.event_dedup_key,
            )

        # Check for old news / rehash (RISK_TIP or DISCARD)
        stale_result = gate_map.get("stale_or_recycled_event")
        if stale_result and stale_result.verdict == GateVerdict.REJECT:
            return EventIntelligenceResult(
                event_description=f"[STALE] {signal.title}",
                assets=obs.affected_assets,
                news_quality=self._get_news_quality(obs),
                trade_relevance="low",
                data_origin=self._resolve_data_origin(obs, result),
                decision=IntelligenceDecision.DISCARD,
                risk_tags=["old_news", "stale_information", "recycled"],
                observation_window="N/A — stale",
                evidence_summary=f"Event is stale/recycled. {stale_result.reason[:100]}",
                source_refs=obs.source_refs + ["gate:rejected_stale"],
                dedup_key=obs.event_dedup_key,
            )

        # Build risk tags from ambiguous gate results
        for gate_name, tag_map in [
            ("duplicate_event", ["previously_seen"]),
            ("no_material_expectation_change", ["low_impact"]),
            ("already_heavily_price_in", ["already_priced"]),
            ("derivatives_overcrowding", ["derivatives_risk"]),
            ("social_heat_without_spot_confirmation", ["social_hype"]),
        ]:
            gr = gate_map.get(gate_name)
            if gr and gr.verdict == GateVerdict.DOWNGRADE:
                risk_tags.extend(tag_map)

        # Assess overall risk level
        has_risk = any(
            gr and gr.verdict == GateVerdict.DOWNGRADE
            for gr in gate_map.values()
        )

        if has_risk:
            decision = IntelligenceDecision.RISK_TIP
            risk_tags.append("risk_tip")
        else:
            risk_tags.append("observe")

        # Default: OBSERVE
        return EventIntelligenceResult(
            event_description=signal.title,
            assets=obs.affected_assets,
            news_quality=self._get_news_quality(obs),
            trade_relevance=self._get_trade_relevance(obs),
            data_origin=data_origin,
            decision=decision,
            risk_tags=risk_tags,
            observation_window=self._get_observation_window(obs, gate_map),
            evidence_summary=self._build_evidence_summary(obs, gate_map, signal),
            source_refs=obs.source_refs,
            dedup_key=obs.event_dedup_key,
        )

    def _resolve_data_origin(self, obs: Observation, result: SignalSpineResult) -> DataOrigin:
        """Resolve data origin from observation and result.

        Priority:
          1. result.data_origin (if set by pipeline)
          2. Observation card_family / source_type heuristics
          3. Default to fixture-safe value
        """
        if result.data_origin is not None:
            if isinstance(result.data_origin, DataOrigin):
                return result.data_origin
            if isinstance(result.data_origin, str):
                try:
                    return DataOrigin(result.data_origin)
                except ValueError:
                    pass

        # Heuristic from source_type
        st = obs.source_type.value if obs.source_type else ""
        if "fixture" in st:
            return DataOrigin.FIXTURE
        if "api" in st or "source" in st:
            # Check API success in metrics
            api_success = obs.normalized_payload.get("api_success", None)
            if api_success is False:
                return DataOrigin.DEGRADED
            return DataOrigin.REAL

        return DataOrigin.FIXTURE

    def _default_observe(self, obs: Observation, result: SignalSpineResult) -> EventIntelligenceResult:
        """Fallback: produce an OBSERVE decision."""
        return EventIntelligenceResult(
            event_description=obs.normalized_payload.get("title", "Market event"),
            assets=obs.affected_assets,
            news_quality=self._get_news_quality(obs),
            trade_relevance=self._get_trade_relevance(obs),
                        data_origin=self._resolve_data_origin(obs, result),
            decision=IntelligenceDecision.OBSERVE,
            risk_tags=["observe"],
            observation_window="1h",
            evidence_summary=f"Event accepted. Sources: {', '.join(obs.source_refs[:3])}",
            source_refs=obs.source_refs,
            dedup_key=obs.event_dedup_key,
        )

    def _get_news_quality(self, obs: Observation) -> str:
        """Map DataQuality to news quality string."""
        dq = obs.data_quality
        if dq.value in ("verified_high",):
            return "high"
        if dq.value in ("verified_medium",):
            return "medium"
        if dq.value in ("unverified",):
            return "low"
        if dq.value in ("low_credibility",):
            return "very_low"
        return "low"

    def _get_trade_relevance(self, obs: Observation) -> str:
        """Assess trade relevance from observation."""
        count = len(obs.affected_assets)
        intensity = obs.normalized_payload.get("intensity", "")
        if count >= 3 and intensity in ("high", "critical"):
            return "high"
        if count >= 1 and intensity in ("high", "medium"):
            return "medium"
        if count >= 1:
            return "low"
        return "none"

    def _get_observation_window(
        self,
        obs: Observation,
        gate_map: dict[str, NoiseGateResult],
    ) -> str:
        """Determine observation window based on event characteristics.

        Product windows: 1h, 4h, 24h only.
        """
        intensity = obs.normalized_payload.get("intensity", "")
        if intensity == "high":
            return "24h"
        if intensity == "medium":
            return "4h"
        return "1h"

    def _build_evidence_summary(
        self,
        obs: Observation,
        gate_map: dict[str, NoiseGateResult],
        signal: Signal,
    ) -> str:
        """Build a concise evidence summary."""
        verdicts = [f"{r.rule_name}={r.verdict.value}" for r in gate_map.values()]
        source_count = len(obs.source_refs)
        return (
            f"Gate: {len(verdicts)} rules evaluated. "
            f"Signal: {signal.status.value}. "
            f"Sources: {source_count} refs."
        )

    def populate_result(
        self,
        spine_result: SignalSpineResult,
    ) -> tuple[SignalSpineResult, EventIntelligenceResult]:
        """Populate a SignalSpineResult with decision metadata and return the EI result.

        Modifies the spine_result in place:
          - emit_card: False for duplicates, True otherwise
          - observation_decision: the mapped decision string
          - data_origin: assessed data provenance

        Returns (spine_result, ei_result) for downstream consumption.
        """
        ei_result = self.map_result(spine_result)

        # Populate spine result fields
        if spine_result.registry_action == "merged_into_existing":
            spine_result.emit_card = False
            spine_result.observation_decision = "suppress_duplicate"
        elif ei_result.decision == IntelligenceDecision.DISCARD:
            spine_result.emit_card = False
            spine_result.observation_decision = "discard"
        elif ei_result.decision == IntelligenceDecision.BLOCK:
            spine_result.emit_card = False
            spine_result.observation_decision = "block"
        elif ei_result.decision == IntelligenceDecision.RISK_TIP:
            spine_result.emit_card = True
            spine_result.observation_decision = "risk_tip"
        else:
            spine_result.emit_card = True
            spine_result.observation_decision = "observe"

        spine_result.data_origin = ei_result.data_origin.value

        return spine_result, ei_result


def create_decision_mapper() -> EventIntelligenceMapper:
    """Factory: create an EventIntelligenceMapper."""
    return EventIntelligenceMapper()
