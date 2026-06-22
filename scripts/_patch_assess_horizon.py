"""Replace _assess_horizon method in arbitration.py"""
with open('C:/Users/zhuo7/Desktop/市场认知与有效信号/market_radar/intelligence/engines/arbitration.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('def _assess_horizon')
next_def = content.find('\n    def _determine_arbitration_status', start)

new_method = '''    def _assess_horizon(
        self, horizon: str,
        hypotheses: list[EligibleHypothesis],
        bull_clusters: list[HypothesisSupportCluster],
        bear_clusters: list[HypothesisSupportCluster],
        mixed_clusters: list[HypothesisSupportCluster] | None = None,
    ) -> HorizonAssessment:
        trace = HorizonDecisionTrace(horizon=horizon)
        rule_ids = []
        for h in hypotheses:
            trace.eligible_hypotheses.append(h.hypothesis_id)
        support_ids = [h.hypothesis_id for h in hypotheses
                       if h.expected_effect.lower() in ("bullish", "positive", "up", "long")]
        oppose_ids = [h.hypothesis_id for h in hypotheses
                      if h.expected_effect.lower() in ("bearish", "negative", "down", "short")]
        alt_ids = [h.hypothesis_id for h in hypotheses
                   if h.expected_effect.lower() not in ("bullish", "bearish", "positive", "negative", "up", "down", "long", "short")]
        missing_confirmations = [
            h.hypothesis_id for h in hypotheses
            if not h.market_confirmation or h.market_confirmation == "awaiting"
        ]
        trace.support_clusters = bull_clusters
        trace.opposing_clusters = bear_clusters
        trace.mixed_clusters = mixed_clusters or []
        clean_bull = [c for c in bull_clusters if c.direction == "bullish"]
        clean_bear = [c for c in bear_clusters if c.direction == "bearish"]
        strong_bull = any(c.quality == QualityLevel.STRONG for c in clean_bull)
        strong_bear = any(c.quality == QualityLevel.STRONG for c in clean_bear)

        # ARB-001
        rule_ids.append("ARB-001")
        if not hypotheses:
            trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
            trace.rule_id_selected = "ARB-001"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-008: Mixed cluster always blocks directional
        rule_ids.append("ARB-008")
        if mixed_clusters:
            trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
            trace.rule_id_selected = "ARB-008"
            for mc in mixed_clusters:
                trace.limitations.append(f"Mixed cluster {mc.cluster_id}: internal direction conflict")
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                          ["Internal direction conflict"])

        # ARB-011: Transmission conflicts
        rule_ids.append("ARB-011")
        all_conflicts = []
        for h in hypotheses:
            if hasattr(h, 'transmission_conflicts') and h.transmission_conflicts:
                all_conflicts.extend(h.transmission_conflicts)
        if all_conflicts:
            trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
            trace.rule_id_selected = "ARB-011"
            trace.transmission_conflicts = list(set(all_conflicts))
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                          [f"Transmission conflict: {c}" for c in set(all_conflicts)])

        # ARB-002
        rule_ids.append("ARB-002")
        only_awaiting = all(h.market_confirmation in ("awaiting", "") for h in hypotheses) if hypotheses else False
        if only_awaiting:
            trace.final_verdict = VerdictState.WAIT_FOR_CONFIRMATION
            trace.rule_id_selected = "ARB-002"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-003
        rule_ids.append("ARB-003")
        only_bull = bool(clean_bull) and not clean_bear
        only_bear = bool(clean_bear) and not clean_bull
        if strong_bull and only_bull:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bullish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])
        if strong_bear and only_bear:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-003"
            trace.direction = "bearish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-004
        rule_ids.append("ARB-004")
        weak_bull = bool(bull_clusters) and not strong_bull
        weak_bear = bool(bear_clusters) and not strong_bear
        if strong_bull and weak_bear:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-004"
            trace.direction = "bullish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])
        if strong_bear and weak_bull:
            trace.final_verdict = VerdictState.DIRECTIONAL_AVAILABLE
            trace.rule_id_selected = "ARB-004"
            trace.direction = "bearish"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-005
        rule_ids.append("ARB-005")
        if strong_bull and strong_bear:
            trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
            trace.rule_id_selected = "ARB-005"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                          ["Strong evidence on both sides"])

        # ARB-007
        rule_ids.append("ARB-007")
        for h in hypotheses:
            if h.evidence_bundle_verdict == "conflicting":
                trace.final_verdict = VerdictState.CONFLICT_UNRESOLVED
                trace.rule_id_selected = "ARB-007"
                trace.rule_ids_evaluated = list(rule_ids)
                return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations,
                                              ["Evidence bundle is conflicting"])

        # ARB-010
        rule_ids.append("ARB-010")
        all_deriv = all(h.market_confirmation in ("derivatives_only", "awaiting", "") for h in hypotheses) if hypotheses else False
        if all_deriv and not strong_bull and not strong_bear:
            trace.final_verdict = VerdictState.WAIT_FOR_CONFIRMATION
            trace.rule_id_selected = "ARB-010"
            trace.rule_ids_evaluated = list(rule_ids)
            return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

        # ARB-013
        rule_ids.append("ARB-013")
        if not any(h.calibration_artifact_ref for h in hypotheses):
            trace.limitations.append("No calibration artifact -- confidence limited")

        # Default INSUFFICIENT (no ARB-199)
        trace.final_verdict = VerdictState.INSUFFICIENT_EVIDENCE
        trace.rule_id_selected = "ARB-001"
        trace.direction = "neutral"
        trace.rule_ids_evaluated = list(rule_ids)
        return self._build_assessment(horizon, trace, support_ids, oppose_ids, alt_ids, missing_confirmations, [])

'''

content = content[:start] + new_method + content[next_def:]

with open('C:/Users/zhuo7/Desktop/市场认知与有效信号/market_radar/intelligence/engines/arbitration.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replace OK')
