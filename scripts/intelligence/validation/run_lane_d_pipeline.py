#!/usr/bin/env python
"""Lane D pipeline entry point."""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone

def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + datetime.now(timezone.utc).strftime("%f")[:3] + "Z"

def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return None


def main():
    parser = argparse.ArgumentParser(description="Lane D Pipeline")
    parser.add_argument("--replay-results", required=True)
    parser.add_argument("--baseline-results")
    parser.add_argument("--abstentions")
    parser.add_argument("--output-dir", default="data/intelligence/validation")
    parser.add_argument("--dataset-id", default="validation_v1")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()
    sys.path.insert(0, os.getcwd())

    from market_radar.intelligence.validation.dataset_builder import DatasetBuilder
    from market_radar.intelligence.validation.splitter import ChronologicalSplitter
    from market_radar.intelligence.validation.baselines import BaselineRunner
    from market_radar.intelligence.validation.bootstrap import BootstrapEngine
    from market_radar.intelligence.validation.calibration import CalibrationFitter
    from market_radar.intelligence.validation.abstention_analysis import AbstentionAnalyzer
    from market_radar.intelligence.validation.drift_analysis import DriftAnalyzer
    from market_radar.intelligence.validation.leakage_audit import LeakageAuditor
    from market_radar.intelligence.validation.dependency_graph import DependencyGraph

    replay_records = load_jsonl(args.replay_results)
    baseline_records = []
    if args.baseline_results and os.path.exists(args.baseline_results):
        baseline_records = load_jsonl(args.baseline_results)
    abstention_records = []
    if args.abstentions and os.path.exists(args.abstentions):
        abstention_records = load_jsonl(args.abstentions)

    builder = DatasetBuilder(os.path.join(args.output_dir, "datasets"))
    for rec in replay_records: builder.add_replay_result(rec)
    for rec in baseline_records: builder.add_baseline_result(rec)
    for rec in abstention_records: builder.add_abstention_record(rec)
    dataset = builder.build(args.dataset_id, {"lane_c": args.replay_results})

    dep_graph = DependencyGraph()
    dep_graph.add_records(builder.records)

    splitter = ChronologicalSplitter(purge_hours=24, embargo_days=7)
    ti, vi, hi, manifest = splitter.fixed_time_split(builder.records, dataset_id=dataset.dataset_id)

    runner = BaselineRunner(builder.records)
    bl_results = runner.run_all(dataset.dataset_id, manifest.split_manifest_id)

    boot = BootstrapEngine(builder.records, dep_graph, random_seed=args.random_seed)
    def acc_fn(recs):
        if not recs: return 0.0
        c = sum(1 for r in recs if not r.get("abstained") and r.get("expected_effect") == r.get("observed_direction"))
        t = sum(1 for r in recs if not r.get("abstained"))
        return c / t if t > 0 else 0.0
    boot_res = boot.event_cluster_bootstrap(acc_fn, resamples=1000)

    auditor = LeakageAuditor(builder.records, {"train": ti, "holdout": hi, "test": hi})
    audit_res = auditor.audit_all(dataset.dataset_id, manifest.split_manifest_id)

    fitter = CalibrationFitter()
    confs, outs = [], []
    for rec in builder.records:
        if not rec.get("abstained"):
            confs.append(0.5)
            outs.append(1 if rec.get("expected_effect") == rec.get("observed_direction") else 0)
    cal = fitter.fit_empirical_binning(confs, outs)

    aa = AbstentionAnalyzer(builder.records)
    ar = aa.analyze()

    train_recs = [builder.records[i] for i in ti]
    hold_recs = [builder.records[i] for i in hi]
    dr = DriftAnalyzer()
    dr_res = dr.analyze(train_recs, hold_recs)

    base = args.output_dir
    bl_path = os.path.join(base, "baselines", "baseline_evaluations_v1.jsonl")
    write_jsonl(bl_path, [e.to_dict() for e in bl_results.values()])
    boot_path = os.path.join(base, "bootstrap", "bootstrap_intervals_v1.jsonl")
    write_jsonl(boot_path, [boot_res.to_dict()])
    if cal:
        cal_path = os.path.join(base, "calibration", "calibration_artifacts_v1.jsonl")
        write_jsonl(cal_path, [cal.to_dict()])
    return 0


if __name__ == "__main__":
    sys.exit(main())