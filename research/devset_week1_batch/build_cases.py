#!/usr/bin/env python3
"""Build all week1 development cases from manifest data and classification rules."""
import json, hashlib, os, sys, shutil
from datetime import datetime, timezone

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = json.load(open(os.path.join(PROJ, "research", "week1_samples_v1.json"), "r", encoding="utf-8"))

NOW = "2026-06-16T14:00:00Z"
PROTOCOL_COMMIT = "7382738e8b0bf66fbc42ac8a0df2a8dd75f15513"

def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Classification rules
CLASSIFICATION = {
    "w1_001": {"form": "discrete_observable_action", "medium": "onchain_data_feed", "routing": "point_event_study"},
    "w1_002": {"form": "discrete_observable_action", "medium": "onchain_data_feed", "routing": "point_event_study"},
    "w1_003": {"form": "cumulative_trend", "medium": "analyst_report", "routing": "routed_to_other_design"},
    "w1_004": {"form": "discrete_information_release", "medium": "news_article", "routing": "point_event_study"},
    "w1_005": {"form": "market_outcome_or_context", "medium": "market_data_feed", "routing": "interference_context"},
}

def get_sample(sid):
    for s in MANIFEST["samples"]:
        if s["sample_id"] == sid:
            return s
    return None

def gen_candidate(sid, s, cls):
    return {
        "candidate_id": f"cand_{sid}",
        "information_form": cls["form"],
        "source_medium": cls["medium"],
        "capture_time_utc": s["broadcast_time_utc"],
        "source_observation_ref": f"obs_{sid}",
        "status": "routed_to_research" if cls["routing"] == "point_event_study" else cls["routing"],
        "exclusion_reason": None,
        "candidate_log": [{"timestamp_utc": s["broadcast_time_utc"], "action": "candidate_created", "actor": "system", "detail": f"From {s['source_label']}"}],
        "created_at_utc": s["broadcast_time_utc"],
        "updated_at_utc": NOW,
        "pilot_candidate_source": "observation",
    }

def gen_research_unit(sid, s, cls):
    eligibility = "eligible" if cls["routing"] == "point_event_study" else "context_only"
    return {
        "research_unit_id": f"ru_{sid}",
        "design_type": "point_event_study" if cls["routing"] == "point_event_study" else "point_event_study",
        "eligibility_status": eligibility,
        "candidate_ref": f"cand_{sid}",
        "information_form": cls["form"],
        "research_notes": f"Development Set sample {sid}. {s['title']}",
        "created_at_utc": NOW,
        "updated_at_utc": NOW,
    }

def gen_event_instance(sid, s):
    return {
        "canonical_event_instance_id": f"ei_{sid}",
        "event_thread_ref": f"th_{sid}",
        "relationship_to_thread": "part_of_thread",
        "relationship_evidence": "Initial report",
        "observation_ref": f"obs_{sid}",
        "instance_version": 1,
        "instance_data": {},
        "created_at_utc": NOW,
        "updated_at_utc": NOW,
    }

def gen_claim_evidence(sid, s):
    claim_type = "fact"
    ev_role = "carrier_or_relay"
    ev_status = "single_source_supported"
    return {
        "record_id": f"cer_{sid}",
        "evidence_role": ev_role,
        "claim_evidence_status": ev_status,
        "claim": {"statement": s["raw_summary"], "claimant": s["source_label"].split("/")[0].strip(), "claim_time_utc": s["broadcast_time_utc"], "claim_type": claim_type},
        "evidence_artifacts": [{"artifact_id": f"art_{sid}_src", "artifact_type": "api_response", "content_hash": "sha256:not_computed_yet", "source": s["source_label"]}],
        "evidence_relations": [{"evidence_id": f"art_{sid}_src", "relation_type": "supports", "detail": "Primary source event"}],
        "provenance_path": [{"hop": 1, "from_source": "Original", "to_source": s["source_label"], "timestamp_utc": s["broadcast_time_utc"], "transformation": "Event capture"}],
        "independence_groups": [{"group_id": f"ig_{sid}", "members": [f"art_{sid}_src"], "independence_status": "independent"}],
        "created_at_utc": NOW,
        "updated_at_utc": NOW,
    }

def gen_eth_price_url():
    return None  # placeholder

# Process each case
for sid in ["w1_001","w1_002","w1_003","w1_004","w1_005"]:
    s = get_sample(sid)
    cls = CLASSIFICATION[sid]
    case_dir = os.path.join(PROJ, "research", f"devset_{sid}")
    obj_dir = os.path.join(case_dir, "objects")
    os.makedirs(obj_dir, exist_ok=True)

    is_point = cls["routing"] == "point_event_study"

    # Always create Candidate
    cand = gen_candidate(sid, s, cls)
    with open(os.path.join(obj_dir, "01_candidate.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid,"created_at_utc":NOW,"protocol_commit":PROTOCOL_COMMIT,"retrospective_reconstruction":True},"candidate":cand}, f, indent=2, ensure_ascii=False)

    # Research Unit
    ru = gen_research_unit(sid, s, cls)
    with open(os.path.join(obj_dir, "02_research_unit.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"research_unit":ru}, f, indent=2, ensure_ascii=False)

    # Event Instance
    ei = gen_event_instance(sid, s)
    with open(os.path.join(obj_dir, "03_event_instance.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"event_instance":ei}, f, indent=2, ensure_ascii=False)

    # Claim Evidence
    cer = gen_claim_evidence(sid, s)
    with open(os.path.join(obj_dir, "04_claim_evidence_record.json"), "w", encoding="utf-8") as f:
        json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"claim_evidence_record":cer}, f, indent=2, ensure_ascii=False)

    if is_point:
        # Registration
        reg = {
            "registration_id": f"reg_{sid}",
            "research_unit_ref": f"ru_{sid}",
            "target_asset": s["subject_asset"] if s["subject_asset"] not in ("WTI",) else "BTC",
            "selected_clock": "information_clock",
            "actual_time_basis": "broadcast_time",
            "primary_t0": s["broadcast_time_utc"],
            "t0_uncertainty_seconds": 3600,
            "primary_window": {"duration_seconds": 3600, "window_type": "t0_to_t_plus_1h"},
            "primary_benchmark": "ETH" if s["subject_asset"] == "BTC" else "BTC",
            "sensitivity_benchmarks": ["ETH"] if s["subject_asset"] != "WTI" else [],
            "pre_event_movement_check_definition": {"window_before_t0_seconds": 3600, "threshold_bps": 20},
            "registration_time_utc": NOW,
            "git_commit": PROTOCOL_COMMIT,
            "file_sha256": "sha256:placeholder",
            "data_partition": "development",
            "outcome_status": "not_revealed",
            "notes": f"Development Set sample {sid}. Retrospective reconstruction.",
        }
        if s["subject_asset"] == "BTC":
            reg["primary_benchmark"] = "ETH"
            reg["notes"] += " BTC target — ETH benchmark is weak proxy."
        with open(os.path.join(obj_dir, "05_registration.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"registration":reg}, f, indent=2, ensure_ascii=False)

        # Outcome (with null price data — to be filled by case-specific scripts)
        out = {
            "outcome_id": f"out_{sid}",
            "registration_ref": f"reg_{sid}",
            "raw_market_reaction": {"window": "1h", "absolute_change_pct": 0.0, "direction": "flat"},
            "registered_benchmark_relative_reaction": {"benchmark": reg["primary_benchmark"], "relative_change_pct": 0.0},
            "sensitivity_benchmark_reactions": [{"benchmark": b, "relative_change_pct": 0.0} for b in reg.get("sensitivity_benchmarks", [])],
            "historical_materiality": {"assessment": "insufficient_data", "note": "Sentinel — replace with real computation"},
            "pre_event_movement_check_result": {"movement_detected": False, "movement_pct": 0.0},
            "event_time_uncertainty": {"estimated_uncertainty_seconds": 3600, "note": "Only broadcast_time known"},
            "calculated_at_utc": NOW,
        }
        with open(os.path.join(obj_dir, "06_outcome.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"outcome":out}, f, indent=2, ensure_ascii=False)

        # Interference
        inter = {
            "record_id": f"int_{sid}",
            "research_unit_ref": f"ru_{sid}",
            "observation_window": "1h",
            "separability_status": "insufficient_inventory",
            "collision_set": [],
            "alternative_explanations": ["General market movement", "Other asset-specific news"],
            "coverage_insufficiency": True,
            "created_at_utc": NOW,
        }
        with open(os.path.join(obj_dir, "07_interference_record.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"interference_record":inter}, f, indent=2, ensure_ascii=False)

        # Attribution
        attr = {
            "assessment_id": f"aa_{sid}",
            "research_unit_ref": f"ru_{sid}",
            "hard_gates": {"research_eligibility":"pass","event_evidence":"pass","usable_t0":"unknown","pre_outcome_registration":"unknown","valid_outcome_measurement":"unknown","benchmark_validity":"unknown","separability":"unknown"},
            "dimensions": {d:"unknown" for d in ["temporal_ordering","temporal_proximity","benchmark_relative_materiality","asset_specificity","mechanism_consistency","interference_and_separability","alternative_explanations","robustness"]},
            "verdict": "insufficient_evidence",
            "notes": f"Development Set sample {sid}. Insufficient evidence for attribution.",
            "created_at_utc": NOW,
            "updated_at_utc": NOW,
        }
        if s["subject_asset"] == "BTC":
            attr["btc_benchmark_weak_proxy_note"] = "ETH is a weak proxy benchmark for BTC events."
        with open(os.path.join(obj_dir, "08_attribution_assessment.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema":"https://json-schema.org/draft/2020-12/schema","meta":{"case_id":sid},"attribution_assessment":attr}, f, indent=2, ensure_ascii=False)

        print(f"{sid}: point_event_study — 8 objects created (sentinel placeholders)")

    else:
        # Routed case — only core objects
        print(f"{sid}: routed ({cls['routing']}) — candidate + research_unit + event_instance + claim_evidence")
        # Remove any non-existent outcome files
        for fname in ["06_outcome.json", "07_interference_record.json", "08_attribution_assessment.json"]:
            p = os.path.join(obj_dir, fname)
            if os.path.exists(p):
                os.remove(p)

print("\nAll cases initialized.")
