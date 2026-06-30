"""Cognition orchestrator."""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from market_radar.cognition.contracts import EventState, EventRevision, SourceConflict
from market_radar.cognition.contracts import ExpectationState, MarketSnapshot
from market_radar.cognition.contracts import ConfirmationState, TransmissionPath, Assessment, Abstention
from market_radar.cognition.contracts import EventStatus, Verdict, ExpectationType, AbstentionCode, utc_now, sha256_id
from market_radar.cognition.input_loader import load_observations, load_evidence_manifest, verify_evidence_hash, InputInventory
from market_radar.cognition.event_grouper import group_observations
from market_radar.cognition.event_store import EventStore
from market_radar.cognition.expectation import calculate_gap, detect_stale
from market_radar.cognition.confirmation import evaluate_price_direction, evaluate_volume_expansion
from market_radar.cognition.transmission import determine_paths
from market_radar.cognition.assessment import build_assessment, should_abstain


@dataclass
class StageResult:
    stage: str = ""
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    outputs: list = field(default_factory=list)
    errors: list = field(default_factory=list)

@dataclass
class CognitionRunResult:
    run_id: str = ""
    status: str = "ok"
    stages: dict = field(default_factory=dict)
    inventory: Any = None
    events: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    revisions: list = field(default_factory=list)
    expectations: list = field(default_factory=list)
    snapshots: list = field(default_factory=list)
    confirmations: list = field(default_factory=list)
    assessments: list = field(default_factory=list)
    abstentions: list = field(default_factory=list)
    output_dir: str = ""
    store: Any = None
    errors: list = field(default_factory=list)



def run_cognition(input_path, output_root, run_id, mode="replay", as_of=None, strict=False, assets=None):
    result = CognitionRunResult(run_id=run_id, output_dir=str(output_root))
    all_errors = []
    output_root.mkdir(parents=True, exist_ok=True)
    
    def make_sr(name):
        s = StageResult(stage=name, status="running", started_at=utc_now())
        return s
    
    def finish_sr(sr, status, outs=None):
        sr.status = status
        sr.completed_at = utc_now()
        if outs:
            sr.outputs.extend(outs)

    # S1: Input validation
    sr = make_sr("input_validation")
    obs_path = input_path / "observations.jsonl"
    obs_list, inventory = load_observations(obs_path, mode=mode)
    result.inventory = inventory
    rej_path = str(output_root / "rejected_observations.jsonl")
    with open(rej_path, "w") as rf:
        for vo in obs_list:
            if not vo.valid:
                rf.write(json.dumps({"id": getattr(vo.observation,"observation_id",""), "reason": vo.rejection_reason}) + chr(10))
    finish_sr(sr, "complete" if inventory.valid_observations > 0 else "failed", [rej_path])
    sr.errors.extend(inventory.errors)
    result.stages["input_validation"] = sr
    all_errors.extend(inventory.errors)
    # Evidence manifest loading
    ev_manifest_path = input_path / "evidence_manifest.jsonl"
    if ev_manifest_path.exists():
        ev_entries, ev_errors = load_evidence_manifest(ev_manifest_path)
        inventory.evidence_files_checked = len(ev_entries)
        for entry in ev_entries:
            err = verify_evidence_hash(input_path, entry)
            if err:
                inventory.evidence_hash_mismatches += 1
                inventory.errors.append(f"evidence_hash: {err}")
                if strict:
                    all_errors.append(f"strict mode: {err}")
        sr.outputs.append(str(ev_manifest_path))
    if inventory.valid_observations == 0:
        result.status = "failed"; result.errors = all_errors; return result
    
    # S2: Grouping
    sr = make_sr("event_grouping")
    events, conflicts = group_observations(obs_list)
    result.events = events; result.conflicts = conflicts
    ev_path = str(output_root / "event_states.jsonl")
    cf_path = str(output_root / "source_conflicts.jsonl")
    with open(ev_path, "w") as f:
        for ev in events: f.write(json.dumps(ev.to_dict()) + chr(10))
    with open(cf_path, "w") as f:
        for cf in conflicts: f.write(json.dumps(cf.to_dict()) + chr(10))
    finish_sr(sr, "complete", [ev_path, cf_path])
    result.stages["event_grouping"] = sr
    
    # S3: Store
    sr = make_sr("event_store")
    db_path = str(output_root / "cognition.db")
    store = EventStore(db_path)
    result.store = store
    revisions = []
    for ev in events:
        store.upsert_event(ev)
        r = EventRevision(revision_id=sha256_id(["rev",ev.event_id,"1"]), event_id=ev.event_id, revision=1, new_status=ev.status, reason="created", timestamp=utc_now())
        store.add_revision(r)
        revisions.append(r)
    result.revisions = revisions
    rv_path = str(output_root / "event_revisions.jsonl")
    with open(rv_path, "w") as f:
        for r in revisions: f.write(json.dumps(r.to_dict()) + chr(10))
    finish_sr(sr, "complete", [db_path, rv_path])
    result.stages["event_store"] = sr
    
    # S4: Expectation
    sr = make_sr("expectation")
    expectations = []; exp_meta = {}
    exp_mp = input_path / "expectation.json"
    if exp_mp.exists():
        try: exp_meta = json.loads(exp_mp.read_text())
        except: pass
    for ev in events:
        m = exp_meta.get(ev.event_dedup_key, exp_meta.get(ev.event_id, {}))
        es = calculate_gap(m.get("expected"), m.get("actual"), m.get("range_low"), m.get("range_high"))
        es.event_id = ev.event_id
        es.baseline_source = m.get("baseline_source", "")
        es.baseline_timestamp = m.get("baseline_timestamp", "")
        if as_of and es.baseline_timestamp:
            es.stale = detect_stale(es.baseline_timestamp, as_of)
        expectations.append(es)
    result.expectations = expectations
    ep = str(output_root / "expectation_states.jsonl")
    with open(ep, "w") as f:
        for es in expectations: f.write(json.dumps(es.to_dict()) + chr(10))
    finish_sr(sr, "complete", [ep])
    result.stages["expectation"] = sr


    # S5: Market snapshots
    sr = make_sr("market_snapshots")
    snapshots = []
    sp = input_path / "market_snapshots.jsonl"

    # Load existing snapshots from fixture/input
    if sp.exists():
        for line in sp.read_text().strip().split(chr(10)):
            if line.strip():
                try:
                    d = json.loads(line)
                    ms = MarketSnapshot.from_dict(d)
                    if as_of and ms.as_of and ms.as_of > as_of:
                        continue
                    if ms.event_id in [e.event_dedup_key for e in events]:
                        ms.event_id = next(e.event_id for e in events if e.event_dedup_key == ms.event_id)
                    snapshots.append(ms)
                except:
                    pass

    # In live mode, attempt to use MarketSnapshotProvider
    if mode == "live" and assets:
        try:
            from market_radar.cognition.market_snapshot import MarketSnapshotProvider
            provider = MarketSnapshotProvider()
            for ev in events:
                for asset in (assets or ["BTC", "ETH"]):
                    ms = provider.fetch_snapshot(asset, as_of=as_of)
                    if ms:
                        snapshots.append(ms)
        except Exception as e:
            all_errors.append(f"live_market_data: {e}")

    result.snapshots = snapshots
    sp_out = str(output_root / "market_snapshots.jsonl")
    with open(sp_out, "w") as f:
        for ms in snapshots: f.write(json.dumps(ms.to_dict()) + chr(10))
    finish_sr(sr, "complete" if snapshots else "partial", [sp_out])
    result.stages["market_snapshots"] = sr

    # S6: Confirmation
    sr = make_sr("confirmation")
    confirmations = []
    for ev in events:
        for snap in snapshots:
            if snap.event_id != ev.event_id:
                continue
            cd = evaluate_price_direction(snap.pre_event_ref, snap.price, 1.0)
            cd.event_id = ev.event_id
            confirmations.append(cd)
            if snap.volume_24h:
                vol_baseline = snap.pre_event_ref if snap.pre_event_ref else snap.volume_24h
                cv = evaluate_volume_expansion(snap.volume_24h, vol_baseline, 1.5)
                cv.event_id = ev.event_id
                confirmations.append(cv)
    result.confirmations = confirmations
    cp = str(output_root / "confirmation_states.jsonl")
    with open(cp, "w") as f:
        for c in confirmations: f.write(json.dumps(c.to_dict()) + chr(10))
    finish_sr(sr, "complete", [cp])
    result.stages["confirmation"] = sr

    # S7: Lifecycle transition
    sr = make_sr("lifecycle")
    for ev in events:
        old = ev.status
        has_c = any(c.verdict == Verdict.CONTRADICTS.value for c in confirmations if c.event_id == ev.event_id)
        has_s = any(c.verdict == Verdict.SUPPORTS.value for c in confirmations if c.event_id == ev.event_id)

        if ev.status in (EventStatus.RESOLVED.value,):
            pass  # terminal state
        elif ev.status == EventStatus.CONTRADICTED.value and has_c:
            # Stay contradicted unless new evidence resolves it
            pass
        elif old == EventStatus.CONTRADICTED.value and not has_c:
            ev.status = EventStatus.INVALIDATED.value
        elif has_c and ev.status not in (EventStatus.CONTRADICTED.value, EventStatus.INVALIDATED.value, EventStatus.RESOLVED.value):
            ev.status = EventStatus.CONTRADICTED.value
        elif ev.status == EventStatus.CANDIDATE.value and has_s:
            ev.status = EventStatus.ACTIVE.value
        elif ev.status == EventStatus.CANDIDATE.value:
            ev.status = EventStatus.ACTIVE.value

        if old != ev.status:
            store.upsert_event(ev)
            r = EventRevision(revision_id=sha256_id(["rev",ev.event_id,str(ev.revision)]), event_id=ev.event_id, revision=ev.revision, previous_status=old, new_status=ev.status, reason="lifecycle")
            store.add_revision(r)
            result.revisions.append(r)
    finish_sr(sr, "complete")
    result.stages["lifecycle"] = sr

    # S8: Transmission
    sr = make_sr("transmission")
    all_paths = []
    for ev in events:
        for p in determine_paths(ev.title, ev.affected_assets):
            p.event_id = ev.event_id
            all_paths.append(p)
    tp = str(output_root / "transmission_paths.jsonl")
    with open(tp, "w") as f:
        for p in all_paths: f.write(json.dumps(p.to_dict()) + chr(10))
    finish_sr(sr, "complete", [tp])
    result.stages["transmission"] = sr

    # S9: Assessment or abstention
    sr = make_sr("assessment")
    assessments = []
    abstentions = []
    for ev in events:
        eid = ev.event_id
        exp = next((e for e in expectations if e.event_id == eid), None)
        confs = [c for c in confirmations if c.event_id == eid]
        paths = [p for p in all_paths if p.event_id == eid]
        ea = exp is not None and exp.expectation_type != ExpectationType.UNAVAILABLE.value
        md = any(s for s in snapshots if s.event_id == eid and s.price is not None)
        hc = any(cf for cf in conflicts if cf.event_id == eid)
        st = exp.stale if exp else False
        ab = should_abstain(ea, md, hc, st)
        if ab:
            ab.event_id = eid
            abstentions.append(ab)
            continue
        mv = Verdict.UNAVAILABLE.value
        dirs = [c.verdict for c in confs if c.dimension == "price_direction"]
        if dirs:
            mv = dirs[0]
        gap = exp.signed_surprise if exp and exp.signed_surprise is not None else None
        cc = {"direction": 0.3 if mv != Verdict.UNAVAILABLE.value else 0.0, "expectation": 0.3 if ea else 0.0, "sources": 0.2, "volume": 0.2}
        a = build_assessment(eid, ev.title, ev.status, gap, mv, cc, [p.path_id for p in paths], ev.observation_ids)
        assessments.append(a)
    result.assessments = assessments
    result.abstentions = abstentions
    ap = str(output_root / "assessments.jsonl")
    abp = str(output_root / "abstentions.jsonl")
    with open(ap, "w") as f:
        for a in assessments: f.write(json.dumps(a.to_dict()) + chr(10))
    with open(abp, "w") as f:
        for a in abstentions: f.write(json.dumps(a.to_dict()) + chr(10))
    finish_sr(sr, "complete", [ap, abp])
    result.stages["assessment"] = sr

    # S10: Evidence manifest
    sr = make_sr("evidence")
    evp = str(output_root / "evidence_manifest.jsonl")
    with open(evp, "w") as f:
        for a in assessments:
            f.write(json.dumps({"claim_id": a.assessment_id, "stage": "assessment", "event_id": a.event_id, "confidence": a.overall_confidence}) + chr(10))
        for ab in abstentions:
            f.write(json.dumps({"claim_id": sha256_id(["abstention",ab.event_id]), "stage": "abstention", "event_id": ab.event_id, "code": ab.code}) + chr(10))
    finish_sr(sr, "complete", [evp])
    result.stages["evidence"] = sr

    # Write telemetry
    with open(str(output_root / "RUN_TELEMETRY.jsonl"), "w") as f:
        for sn, s in result.stages.items():
            f.write(json.dumps({"stage": sn, "status": s.status, "outputs": s.outputs}) + chr(10))

    # Write final manifest
    with open(str(output_root / "run_manifest.json"), "w") as f:
        f.write(json.dumps({
            "run_id": run_id, "mode": mode, "status": result.status,
            "stages": list(result.stages.keys()),
            "events": len(events), "assessments": len(assessments), "abstentions": len(abstentions)
        }))

    result.errors = all_errors
    if abstentions and not assessments:
        result.status = "abstained"
    elif all_errors:
        result.status = "degraded" if len(all_errors) < 5 else "failed"
    return result
