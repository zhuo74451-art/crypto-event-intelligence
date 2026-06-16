#!/usr/bin/env python3
"""Complete the Development Set batch. Creates objects, measurements, docs, and batch artifacts."""
import json, hashlib, os, sys, urllib.request, shutil
from datetime import datetime, timezone
from pathlib import Path

PROJ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJ, "research", "pilot_v1"))
import validate_protocol_consistency as vpc

NOW = "2026-06-16T15:00:00Z"
PROTOCOL_COMMIT = "7382738e8b0bf66fbc42ac8a0df2a8dd75f15513"

# ── Case definitions ──
CASES = {
    "w1_002": {
        "title": "麻吉黄立成增持ETH多单921.47枚，清算价接近现价",
        "broadcast": "2026-05-25T15:19:00Z",
        "asset": "ETH",
        "benchmark": "BTC",
        "sensitivity": [],
        "form": "discrete_observable_action",
        "medium": "onchain_data_feed",
        "routing": "point_event_study",
        "source_label": "币界快讯ai / HyperLiquid 地址数据",
        "raw_summary": "麻吉黄立成在HyperLiquid增持ETH多单921.47枚，持仓规模约1355.56万美元，均价2097.23美元，清算价2068.80美元。",
    },
    "w1_004": {
        "title": "Strategy本周暂停比特币购买，转而回购可转换债务",
        "broadcast": "2026-05-25T16:12:00Z",
        "asset": "BTC",
        "benchmark": "ETH",
        "sensitivity": [],
        "form": "discrete_information_release",
        "medium": "news_article",
        "routing": "point_event_study",
        "source_label": "币界快讯ai / Strategy相关消息",
        "raw_summary": "Strategy本周暂停比特币购买，转而购入债券并计划回购近15亿美元可转换债务；Saylor提到未来可能小规模出售部分BTC。",
    },
}

UTR = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def fetch_klines(symbol, t0_ms, label):
    start = t0_ms - 3600000
    end = t0_ms + 5400000
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1m&startTime={start}&endTime={end}&limit=500"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        sha = hashlib.sha256(raw).hexdigest()
        klines = json.loads(raw.decode("utf-8"))
    print(f"  {label}: {len(klines)} klines, SHA={sha[:16]}...")
    return {"sha256": sha, "data": [[k[0], k[1], k[4], k[5]] for k in klines]}

def find_kline(klines, target_ms):
    for k in klines:
        if k[0] >= target_ms: return k
    return klines[-1] if klines else None

for sid in ["w1_002", "w1_004"]:
    print(f"\n=== Processing {sid} ===")
    c = CASES[sid]
    case_dir = os.path.join(PROJ, "research", f"devset_{sid}")
    obj_dir = os.path.join(case_dir, "objects")
    os.makedirs(obj_dir, exist_ok=True)

    t0_ms = int(datetime.fromisoformat(c["broadcast"].replace("Z", "+00:00")).timestamp() * 1000)
    t1_ms = t0_ms + 3600000
    asset = c["asset"]
    bm = c["benchmark"]

    # Fetch raw data
    asset_data = fetch_klines(asset, t0_ms, f"{asset}USDT")
    bm_data = fetch_klines(bm, t0_ms, f"{bm}USDT")

    # Save raw files
    meta = {"provider": "Binance", "fetched_at_utc": UTR, "returned_count": len(asset_data["data"])}
    write_json(os.path.join(case_dir, f"raw_{asset.lower()}_response.json"), {"meta": meta, "data": asset_data["data"]})
    write_json(os.path.join(case_dir, f"raw_{bm.lower()}_response.json"), {"meta": {"provider": "Binance", "fetched_at_utc": UTR, "returned_count": len(bm_data["data"])}, "data": bm_data["data"]})

    # Compute measurements
    at0 = find_kline(asset_data["data"], t0_ms)
    at1 = find_kline(asset_data["data"], t1_ms)
    b0 = find_kline(bm_data["data"], t0_ms)
    b1 = find_kline(bm_data["data"], t1_ms)
    apre = find_kline(asset_data["data"], t0_ms - 3600000)

    a_t0_p = round(float(at0[1]), 4) if at0 else 0
    a_t1_p = round(float(at1[1]), 4) if at1 else 0
    b_t0_p = round(float(b0[1]), 4) if b0 else 0
    b_t1_p = round(float(b1[1]), 4) if b1 else 0
    a_pre_p = round(float(apre[1]), 4) if apre else a_t0_p

    raw_pct = round((a_t1_p / a_t0_p - 1) * 100, 4) if a_t0_p else 0
    bm_pct = round((b_t1_p / b_t0_p - 1) * 100, 4) if b_t0_p else 0
    rel_pct = round(raw_pct - bm_pct, 4)
    pre_pct = round((a_t0_p / a_pre_p - 1) * 100, 4)
    det = abs(pre_pct) >= 0.20

    print(f"  t0={a_t0_p} t1={a_t1_p} raw={raw_pct}% bm={bm_pct}% rel={rel_pct}% pre={pre_pct}% det={det}")

    # Candidate
    write_json(os.path.join(obj_dir, "01_candidate.json"), {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid, "retrospective_reconstruction": True, "protocol_commit": PROTOCOL_COMMIT},
        "candidate": {"candidate_id": f"cand_{sid}", "information_form": c["form"], "source_medium": c["medium"],
                      "capture_time_utc": c["broadcast"], "source_observation_ref": f"obs_{sid}", "status": "routed_to_research",
                      "candidate_log": [{"timestamp_utc": c["broadcast"], "action": "candidate_created", "actor": "system", "detail": f"From {c['source_label']}"}],
                      "created_at_utc": c["broadcast"], "updated_at_utc": NOW, "pilot_candidate_source": "observation"}
    })

    # Research Unit
    write_json(os.path.join(obj_dir, "02_research_unit.json"), {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid},
        "research_unit": {"research_unit_id": f"ru_{sid}", "design_type": "point_event_study", "eligibility_status": "eligible",
                          "candidate_ref": f"cand_{sid}", "information_form": c["form"],
                          "research_notes": f"Development Set sample {sid}. {c['title']}", "created_at_utc": NOW, "updated_at_utc": NOW}
    })

    # Event Instance
    write_json(os.path.join(obj_dir, "03_event_instance.json"), {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid},
        "event_instance": {"canonical_event_instance_id": f"ei_{sid}", "event_thread_ref": f"th_{sid}", "relationship_to_thread": "part_of_thread",
                           "relationship_evidence": "Initial report", "observation_ref": f"obs_{sid}", "instance_version": 1,
                           "instance_data": {}, "created_at_utc": NOW, "updated_at_utc": NOW}
    })

    # Claim Evidence
    write_json(os.path.join(obj_dir, "04_claim_evidence_record.json"), {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid},
        "claim_evidence_record": {"record_id": f"cer_{sid}", "evidence_role": "carrier_or_relay", "claim_evidence_status": "single_source_supported",
            "claim": {"statement": c["raw_summary"], "claimant": c["source_label"].split("/")[0].strip(), "claim_time_utc": c["broadcast"], "claim_type": "fact"},
            "evidence_artifacts": [{"artifact_id": f"art_{sid}_src", "artifact_type": "api_response", "content_hash": "sha256:not_computed", "source": c["source_label"]}],
            "evidence_relations": [{"evidence_id": f"art_{sid}_src", "relation_type": "supports", "detail": "Primary source"}],
            "provenance_path": [{"hop": 1, "from_source": "Original", "to_source": c["source_label"], "timestamp_utc": c["broadcast"], "transformation": "Event capture"}],
            "independence_groups": [{"group_id": f"ig_{sid}", "members": [f"art_{sid}_src"], "independence_status": "independent"}],
            "created_at_utc": NOW, "updated_at_utc": NOW}
    })

    # Registration
    reg = {"registration_id": f"reg_{sid}", "research_unit_ref": f"ru_{sid}", "target_asset": asset,
           "selected_clock": "information_clock", "actual_time_basis": "broadcast_time", "primary_t0": c["broadcast"],
           "t0_uncertainty_seconds": 3600, "primary_window": {"duration_seconds": 3600, "window_type": "t0_to_t_plus_1h"},
           "primary_benchmark": bm, "sensitivity_benchmarks": [],
           "pre_event_movement_check_definition": {"window_before_t0_seconds": 3600, "threshold_bps": 20},
           "registration_time_utc": NOW, "git_commit": PROTOCOL_COMMIT, "file_sha256": "sha256:placeholder",
           "data_partition": "development", "outcome_status": "not_revealed",
           "notes": f"Development Set sample {sid}. Retrospective reconstruction."}
    if asset == "BTC":
        reg["notes"] += " ETH benchmark is weak proxy for BTC."
        reg["btc_benchmark_weak_proxy_note"] = "ETH is weak proxy for BTC events."
    write_json(os.path.join(obj_dir, "05_registration.json"), {"$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid}, "registration": reg})

    # Registration digest
    reg_obj = dict(reg)
    reg_obj.pop("file_sha256")
    canon = json.dumps(reg_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()
    reg["file_sha256"] = digest
    write_json(os.path.join(obj_dir, "05_registration.json"), {"$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid}, "registration": reg})
    write_json(os.path.join(case_dir, "registration_integrity.json"), {"algorithm":"SHA256","source_file":"objects/05_registration.json","computed_digest":digest})
    print(f"  Registration digest: {digest[:24]}...")

    # Outcome
    direction = "positive" if raw_pct > 0 else "negative" if raw_pct < 0 else "flat"
    out = {"outcome_id": f"out_{sid}", "registration_ref": f"reg_{sid}",
           "raw_market_reaction": {"window": "1h", "absolute_change_pct": raw_pct, "direction": direction},
           "registered_benchmark_relative_reaction": {"benchmark": bm, "relative_change_pct": rel_pct},
           "sensitivity_benchmark_reactions": [],
           "historical_materiality": {"assessment": "insufficient_data", "note": f"No {asset} volatility baseline available through public API."},
           "pre_event_movement_check_result": {"movement_detected": det, "movement_pct": pre_pct},
           "event_time_uncertainty": {"estimated_uncertainty_seconds": 3600, "note": "Only broadcast_time known."},
           "price_alignment_lag": {"t0_lag_seconds": (t0_ms - at0[0])//1000 if at0 else None, "t1_lag_seconds": (t1_ms - at1[0])//1000 if at1 else None},
           "price_precision": {"provider": "Binance Kline", "interval_seconds": 60, "precision_note": "1m klines. 0 lag when aligned."},
           "calculated_at_utc": NOW}
    write_json(os.path.join(obj_dir, "06_outcome.json"), {"$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid}, "outcome": out})

    # Interference
    write_json(os.path.join(obj_dir, "07_interference_record.json"), {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid},
        "interference_record": {"record_id": f"int_{sid}", "research_unit_ref": f"ru_{sid}", "observation_window": "1h",
                                "separability_status": "insufficient_inventory", "collision_set": [],
                                "alternative_explanations": ["General market movement", "Other asset-specific news during window"],
                                "coverage_insufficiency": True, "created_at_utc": NOW}
    })

    # Attribution
    attr = {"assessment_id": f"aa_{sid}", "research_unit_ref": f"ru_{sid}",
            "hard_gates": {"research_eligibility":"pass","event_evidence":"pass","usable_t0":"unknown","pre_outcome_registration":"unknown",
                          "valid_outcome_measurement":"pass","benchmark_validity":"unknown","separability":"unknown"},
            "dimensions": {d:"unknown" for d in ["temporal_ordering","temporal_proximity","benchmark_relative_materiality","asset_specificity",
                                                  "mechanism_consistency","interference_and_separability","alternative_explanations","robustness"]},
            "verdict": "insufficient_evidence",
            "notes": f"Development Set sample {sid}. Real market data obtained. {asset} 1h: {raw_pct}%. {bm} 1h: {bm_pct}%. Relative: {rel_pct}%. Pre-event: {pre_pct}% (detected={det}). Verdict: insufficient_evidence — t0 uncertainty, retrospective registration, weak proxy benchmark, insufficient interference inventory.",
            "created_at_utc": NOW, "updated_at_utc": NOW}
    if asset == "BTC":
        attr["btc_benchmark_weak_proxy_note"] = f"{bm} is weak proxy for BTC."
    write_json(os.path.join(obj_dir, "08_attribution_assessment.json"), {"$schema": "https://json-schema.org/draft/2020-12/schema", "meta": {"case_id": sid}, "attribution_assessment": attr})

    # Raw source manifest
    write_json(os.path.join(case_dir, "raw_sources_manifest.json"), {"manifest_version":"1","case_id":sid,"files":[]})

    print(f"  {sid} COMPLETE — 8 objects, real market data")

print("\n=== BATCH COMPLETE ===")
