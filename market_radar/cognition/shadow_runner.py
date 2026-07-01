"""F08: Historical evaluation and one-shot shadow runner."""
from __future__ import annotations
import json, tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from market_radar.cognition.contracts import EventState, Assessment, Abstention, utc_now, sha256_id
from market_radar.cognition.intake_contracts import HistoricalOutcomeInput


def evaluate_coverage(events: List[EventState], assessments: List[Assessment],
                     abstentions: List[Abstention]) -> Dict[str, Any]:
    total = len(events)
    n_assess = len(assessments)
    n_abstain = len(abstentions)
    return {
        "total_events": total,
        "assessment_count": n_assess,
        "abstention_count": n_abstain,
        "assessment_rate": round(n_assess / total, 2) if total > 0 else 0.0,
        "abstention_rate": round(n_abstain / total, 2) if total > 0 else 0.0,
        "coverage_pct": round((n_assess + n_abstain) / total * 100, 1) if total > 0 else 0.0,
    }


def evaluate_confidence_calibration(assessments: List[Assessment]) -> Dict[str, Any]:
    if not assessments:
        return {"mean_confidence": 0.0, "buckets": {}}
    confs = [a.overall_confidence for a in assessments]
    buckets = {"low_0_33": 0, "med_33_66": 0, "high_66_100": 0}
    for c in confs:
        if c < 0.33: buckets["low_0_33"] += 1
        elif c < 0.66: buckets["med_33_66"] += 1
        else: buckets["high_66_100"] += 1
    return {"mean_confidence": round(sum(confs) / len(confs), 4), "buckets": buckets}


def evaluate_leakage(events: List[EventState], assessments: List[Assessment],
                    as_of: Optional[str] = None) -> Dict[str, Any]:
    leakage_count = 0
    for a in assessments:
        if "future_leakage" in str(a.known_unknowns).lower():
            leakage_count += 1
    return {"leakage_events": leakage_count, "leakage_free": leakage_count == 0}


def evaluate_baselines(assessments: List[Assessment],
                       outcomes: List[HistoricalOutcomeInput]) -> Dict[str, Any]:
    n_correct = 0
    n_total = 0
    for a in assessments:
        matched = [o for o in outcomes if o.event_dedup_key == a.event_id[:16]]
        if matched:
            n_total += 1
            expected = matched[0].expected_abstention
            is_abstention = a.overall_confidence == 0
            if expected == is_abstention:
                n_correct += 1
    always_neutral = round(sum(1 for a in assessments if a.market_confirmation == "neutral") / max(len(assessments), 1), 2)
    return {
        "direction_accuracy": round(n_correct / max(n_total, 1), 2),
        "matched_outcomes": n_total,
        "always_neutral_baseline": always_neutral,
        "assessment_rate_baseline": round(len(assessments) / max(len(assessments) + len([a for a in assessments if a.market_confirmation == "unavailable"]), 1), 2),
    }


def build_evaluation_report(
    events: List[EventState],
    assessments: List[Assessment],
    abstentions: List[Abstention],
    outcomes: Optional[List[HistoricalOutcomeInput]] = None,
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    coverage = evaluate_coverage(events, assessments, abstentions)
    calibration = evaluate_confidence_calibration(assessments)
    leakage = evaluate_leakage(events, assessments, as_of)
    baselines = evaluate_baselines(assessments, outcomes or [])
    return {
        "evaluation_as_of": as_of or utc_now(),
        "coverage": coverage,
        "confidence_calibration": calibration,
        "leakage": leakage,
        "baselines": baselines,
        "schema_version": "eval-v1",
    }


def run_shadow(
    input_dir: Path,
    output_dir: Path,
    run_id: str,
    mode: str = "replay",
    as_of: Optional[str] = None,
) -> Dict[str, Any]:
    """One-shot shadow runner that processes a directory batch."""
    from market_radar.cognition.program_runner import run_program
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run integrated program
    result = run_program(
        input_path=input_dir,
        output_root=output_dir,
        run_id=run_id,
        mode=mode,
        as_of=as_of,
    )

    # Build evaluation from cognition results
    cog = getattr(result, 'cognition', None) or result
    eval_report = build_evaluation_report(
        cog.events, cog.assessments, cog.abstentions,
        as_of=as_of,
    )

    # Write shadow outputs
    with open(str(output_dir / "evaluation_report.json"), "w") as f:
        json.dump(eval_report, f, indent=2)
    with open(str(output_dir / "input_inventory.json"), "w") as f:
        inv = getattr(getattr(result, 'cognition', None), 'inventory', None) or getattr(result, 'inventory', None)
        if inv:
            json.dump(inv.__dict__, f, indent=2)
        else:
            json.dump({"status": "no_inventory"}, f)

    return {
        "run_id": run_id,
        "status": result.status,
        "events": len(getattr(getattr(result, 'cognition', None), 'events', []) or getattr(result, 'events', [])),
        "assessments": len(getattr(getattr(result, 'cognition', None), 'assessments', []) or getattr(result, 'assessments', [])),
        "abstentions": len(getattr(getattr(result, 'cognition', None), 'abstentions', []) or getattr(result, 'abstentions', [])),
        "evaluation": eval_report,
        "output_dir": str(output_dir),
    }