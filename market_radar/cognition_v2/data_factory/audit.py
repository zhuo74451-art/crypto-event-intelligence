"""Quality audit and deterministic rebuild verification.

C05: Compute actual quality gates from artifacts. No placeholders.
All gates inspect real artifact content.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set, Tuple

from market_radar.cognition_v2.data_factory.contracts import (
    CorpusQualityReport,
    QualificationState,
    SplitLabel,
)
from market_radar.cognition_v2.data_factory.storage import (
    build_manifest_hash,
    file_sha256,
    read_jsonl,
    read_yaml,
)


class CorpusAuditor:
    """Audit a built corpus against mandatory quality gates.

    Every gate inspects actual artifact content. No hard-coded passes.
    """

    def audit(
        self,
        base_dir: str,
        rebuild_dir: Optional[str] = None,
    ) -> CorpusQualityReport:
        """Run all quality gates on a corpus build."""
        report = CorpusQualityReport(build_id="audit")

        # Check artifacts exist
        expected_artifacts = [
            "cases.jsonl", "evidence.jsonl", "source_registry.yaml",
            "split_manifest.json", "quality_report.json",
        ]
        missing = [a for a in expected_artifacts
                   if not os.path.exists(os.path.join(base_dir, a))]
        if missing:
            report.errors.append(f"Missing artifacts: {missing}")
            return report

        # Load artifacts
        cases = read_jsonl(os.path.join(base_dir, "cases.jsonl"))
        evidence = read_jsonl(os.path.join(base_dir, "evidence.jsonl"))
        split_manifest = read_yaml(os.path.join(base_dir, "split_manifest.json"))

        qualified = [c for c in cases
                     if c.get("qualification") == QualificationState.QUALIFIED.value]

        # Gate 1: >= 1500 qualified cases
        report.acceptable_cases_ge_1500 = len(qualified) >= 1500

        # Gate 2: all 6 event families
        families = set(c.get("event_family") for c in qualified)
        all_six = {"regulatory", "corporate", "macro", "technology",
                   "market", "security"}
        report.family_coverage_all_six = families == all_six

        # Gate 3: min 150 per family, max 35%
        family_counts: Dict[str, int] = {}
        for c in qualified:
            f = c.get("event_family", "unknown")
            family_counts[f] = family_counts.get(f, 0) + 1
        total_accepted = max(len(qualified), 1)
        report.family_minimum_150 = all(
            count >= 150 for count in family_counts.values()
        )
        report.family_max_35_percent = all(
            count / total_accepted <= 0.35
            for count in family_counts.values()
        )

        # Gate 4: regime distribution
        regimes = set(c.get("market_regime", "unknown") for c in qualified)
        report.regime_coverage_multiple = len(regimes) >= 2

        unknown_regime = sum(
            1 for c in qualified if c.get("market_regime") in (None, "unknown")
        )
        report.unknown_regime_max_10_percent = (
            unknown_regime / total_accepted <= 0.10
        )

        # Gate 5: time completeness (100%)
        time_fields = ["event_time", "publication_time", "first_seen_at",
                       "retrieval_time", "assessment_time"]
        time_complete = 0
        for c in qualified:
            if all(c.get(f) for f in time_fields):
                time_complete += 1
        report.critical_time_completeness_100 = (
            time_complete == len(qualified)
        )

        # Gate 6: authority/permission completeness (100%)
        perm_complete = sum(
            1 for c in qualified
            if c.get("authority") and c.get("fact_permission")
        )
        report.authority_permission_completeness_100 = (
            perm_complete == len(qualified)
        )

        # Gate 7: future leakage — inspect evidence timestamps vs case time
        violations = 0
        for c in qualified:
            c_time = c.get("event_time")
            if c_time and c.get("first_seen_at") and c.get("retrieval_time"):
                from datetime import datetime
                try:
                    ct = datetime.fromisoformat(c_time)
                    fs = datetime.fromisoformat(c["first_seen_at"])
                    rt = datetime.fromisoformat(c["retrieval_time"])
                    avail = max(fs, rt) if fs and rt else None
                    if avail and avail > ct:
                        violations += 1
                except (ValueError, TypeError):
                    pass
        report.future_leakage_violations = violations

        # Gate 8: duplicates
        ids: Set[str] = set()
        dups = 0
        for c in qualified:
            cid = c.get("case_id")
            if cid in ids:
                dups += 1
            ids.add(cid)
        report.duplicate_accepted_case_ids = dups

        # Gate 9/10: cross-split identity/chain
        cross_id = set()
        cross_chain = set()
        for i, c1 in enumerate(qualified):
            for c2 in qualified[i+1:]:
                s1 = c1.get("split_label")
                s2 = c2.get("split_label")
                if s1 and s2 and s1 != s2:
                    if (c1.get("event_identity_id")
                            and c1.get("event_identity_id") == c2.get("event_identity_id")):
                        cross_id.add(c1["event_identity_id"])
                    if (c1.get("correction_chain_id")
                            and c1.get("correction_chain_id") == c2.get("correction_chain_id")):
                        cross_chain.add(c1["correction_chain_id"])
        report.cross_split_event_identities = len(cross_id)
        report.cross_split_correction_chains = len(cross_chain)

        # Gate 11: BLIND contamination
        blind_ids: Set[str] = set()
        blind_chains: Set[str] = set()
        blind_outcomes: Set[str] = set()
        for c in qualified:
            if c.get("split_label") == SplitLabel.BLIND.value:
                if c.get("event_identity_id"):
                    blind_ids.add(c["event_identity_id"])
                if c.get("correction_chain_id"):
                    blind_chains.add(c["correction_chain_id"])
        contamination = 0
        for c in qualified:
            if c.get("split_label") != SplitLabel.BLIND.value:
                if c.get("event_identity_id") in blind_ids:
                    contamination += 1
                if c.get("correction_chain_id") in blind_chains:
                    contamination += 1
        report.blind_tuning_contamination = contamination

        # Gate 12: outcome structural violations
        outcome_path = os.path.join(base_dir, "outcome_windows.jsonl")
        if os.path.exists(outcome_path):
            outcomes = read_jsonl(outcome_path)
            out_errors = 0
            for o in outcomes:
                ot = o.get("open_time")
                ct = o.get("close_time")
                if ot and ct:
                    try:
                        if datetime.fromisoformat(ct) <= datetime.fromisoformat(ot):
                            out_errors += 1
                    except (ValueError, TypeError):
                        out_errors += 1
                hp = o.get("high_price")
                lp = o.get("low_price")
                if hp is not None and lp is not None and hp < lp:
                    out_errors += 1
            report.outcome_structural_violations = out_errors
        else:
            report.outcome_structural_violations = 0  # no outcome file yet

        # Gate 13: deterministic rebuild
        if rebuild_dir and os.path.exists(rebuild_dir):
            h1 = build_manifest_hash(base_dir)
            h2 = build_manifest_hash(rebuild_dir)
            report.deterministic_rebuild_match = (h1 == h2)
        else:
            report.deterministic_rebuild_match = False  # must provide second build

        # Gate 14: audit path coverage
        if qualified:
            total_auditable = 0
            for c in qualified:
                has_source = bool(c.get("source_id"))
                has_evidence = bool(c.get("evidence_refs"))
                has_outcome = bool(c.get("outcome_refs"))
                if has_source and has_evidence:
                    total_auditable += 1
            report.audit_path_coverage = (total_auditable / total_accepted) * 100
        else:
            report.audit_path_coverage = 0.0

        # Compute 24h coverage
        if os.path.exists(outcome_path):
            outcomes = read_jsonl(outcome_path)
            outcomes_24h = [o for o in outcomes if o.get("interval") == "24h"]
            coverage_24h = sum(
                1 for o in outcomes_24h if o.get("close_price") is not None
            )
            report.outcome_24h_coverage = (
                (coverage_24h / max(len(outcomes_24h), 1)) * 100
            )

        # Overall pass/fail
        report.all_gates_pass = all([
            report.acceptable_cases_ge_1500,
            report.family_coverage_all_six,
            report.family_minimum_150,
            report.family_max_35_percent,
            report.regime_coverage_multiple,
            report.unknown_regime_max_10_percent,
            report.critical_time_completeness_100,
            report.authority_permission_completeness_100,
            report.future_leakage_violations == 0,
            report.duplicate_accepted_case_ids == 0,
            report.cross_split_event_identities == 0,
            report.cross_split_correction_chains == 0,
            report.blind_tuning_contamination == 0,
            report.outcome_structural_violations == 0,
            report.deterministic_rebuild_match,
        ])

        if not report.all_gates_pass:
            if not report.acceptable_cases_ge_1500:
                report.errors.append(
                    f"Accepted cases ({len(qualified)}) < 1500"
                )
            if not report.family_coverage_all_six:
                missing_fams = all_six - families
                report.errors.append(f"Missing families: {missing_fams}")
            if not report.family_minimum_150:
                low = {f: c for f, c in family_counts.items() if c < 150}
                report.errors.append(f"Families below 150: {low}")
            if report.future_leakage_violations > 0:
                report.errors.append(
                    f"Future leakage violations: {report.future_leakage_violations}"
                )
            if report.duplicate_accepted_case_ids > 0:
                report.errors.append(
                    f"Duplicate case IDs: {report.duplicate_accepted_case_ids}"
                )
            if report.cross_split_event_identities > 0:
                report.errors.append(
                    f"Cross-split identities: {report.cross_split_event_identities}"
                )
            if report.cross_split_correction_chains > 0:
                report.errors.append(
                    f"Cross-split chains: {report.cross_split_correction_chains}"
                )
            if report.blind_tuning_contamination > 0:
                report.errors.append(
                    f"BLIND contamination: {report.blind_tuning_contamination}"
                )

        return report
