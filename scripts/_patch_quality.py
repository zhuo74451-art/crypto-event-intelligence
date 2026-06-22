"""Fix _compute_cluster_qualities: remove MODERATE fallbacks, use STRONG-only chain."""
with open('C:/Users/zhuo7/Desktop/市场认知与有效信号/market_radar/intelligence/engines/arbitration.py', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('def _compute_cluster_qualities')
next_def = content.find('\n    # ── Horizon Assessment', start)

new = '''    def _compute_cluster_qualities(
        self, clusters: list[HypothesisSupportCluster],
        hypotheses: list[EligibleHypothesis],
    ) -> None:
        hyp_lookup: dict[str, EligibleHypothesis] = {h.hypothesis_id: h for h in hypotheses}
        for c in clusters:
            dims = QualityDimensions()
            best_verdict = QualityLevel.INSUFFICIENT
            all_confirmed = True
            any_confirmed = False
            has_required_inputs = False
            all_inputs_available = True
            regime_data_present = False
            regime_ok = False
            transmission_data_present = False
            transmission_ok = False
            has_calibration = False

            for hid in c.hypotheses:
                h = hyp_lookup.get(hid)
                if not h:
                    continue
                v = h.evidence_bundle_verdict
                if v in ("verified_multi_source", "verified_primary",
                         "verified_primary_with_secondary_support"):
                    best_verdict = QualityLevel.STRONG
                elif v in ("credible_secondary",) and best_verdict != QualityLevel.STRONG:
                    best_verdict = QualityLevel.MODERATE
                elif v in ("single_source_unverified",) and best_verdict == QualityLevel.INSUFFICIENT:
                    best_verdict = QualityLevel.WEAK
                elif v in ("", "missing", "unsupported", "retracted", "insufficient"):
                    if best_verdict == QualityLevel.INSUFFICIENT:
                        best_verdict = QualityLevel.INSUFFICIENT
                if h.market_confirmation == "confirmed":
                    any_confirmed = True
                else:
                    all_confirmed = False
                if h.strategy_state in ("supported", "confirmed"):
                    dims.strategy_state_quality = QualityLevel.STRONG
                elif h.strategy_state in ("triggered", "awaiting_confirmation", "active", "candidate"):
                    if dims.strategy_state_quality != QualityLevel.STRONG:
                        dims.strategy_state_quality = QualityLevel.MODERATE
                else:
                    dims.strategy_state_quality = QualityLevel.INSUFFICIENT
                # Input completeness: undeclared = insufficient
                if h.required_inputs:
                    has_required_inputs = True
                    if set(h.required_inputs) - set(h.available_inputs):
                        all_inputs_available = False
                # Regime: missing data = insufficient
                if h.current_regime_matches or h.invalid_regimes or h.regime_quality:
                    regime_data_present = True
                    if h.current_regime_matches and h.regime_quality != "insufficient":
                        regime_ok = True
                # Transmission: missing data = insufficient
                if h.transmission_signature or h.transmission_coherence:
                    transmission_data_present = True
                    if h.transmission_coherence in ("strong", "valid", "moderate"):
                        transmission_ok = True
                if h.calibration_artifact_ref:
                    has_calibration = True

            dims.evidence_quality = best_verdict
            dims.input_completeness = QualityLevel.INSUFFICIENT if (not has_required_inputs or not all_inputs_available) else QualityLevel.STRONG
            dims.regime_fit = QualityLevel.INSUFFICIENT if (not regime_data_present or not regime_ok) else QualityLevel.STRONG
            dims.market_confirmation_quality = (
                QualityLevel.STRONG if (all_confirmed and any_confirmed) else
                QualityLevel.MODERATE if any_confirmed else
                QualityLevel.INSUFFICIENT
            )
            dims.transmission_coherence = QualityLevel.INSUFFICIENT if (not transmission_data_present or not transmission_ok) else QualityLevel.STRONG
            dims.calibration_quality = QualityLevel.MODERATE if has_calibration else QualityLevel.INSUFFICIENT
            c.quality_dimensions = dims

            # Strong chain: ALL critical dimensions must be STRONG
            critical = [
                dims.evidence_quality,
                dims.input_completeness,
                dims.strategy_state_quality,
                dims.regime_fit,
                dims.transmission_coherence,
                dims.market_confirmation_quality,
            ]
            if all(d == QualityLevel.STRONG for d in critical):
                c.quality = QualityLevel.STRONG
            elif any(d == QualityLevel.INSUFFICIENT for d in critical):
                c.quality = QualityLevel.INSUFFICIENT
            else:
                c.quality = QualityLevel.WEAK

'''

content = content[:start] + new + content[next_def:]

with open('C:/Users/zhuo7/Desktop/市场认知与有效信号/market_radar/intelligence/engines/arbitration.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Quality fix applied')
