#!/usr/bin/env python3
"""MVP+ Lane 6 — Master Integration Runner.

Orchestrates all MVP+ lanes in dependency order:
  Stage 1: Lane 1 — Hyperliquid Whale Positions    (network)
  Stage 2: Lane 3 — Market Context Provider         (network)
  Stage 3: Lane 4 — Existing Feeds Reader           (local)
  Stage 4: Lane 2 — Whale Position Change Engine    (depends on L1)
  Stage 5: Lane 5 — Workbench UI Generator          (depends on all)

Generates RunReport matching contracts/mvpplus/v1/run_report.schema.json.

One-shot execution. No daemon, no cron, no auto-refresh.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 3))
RESULT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
LOG_DIR = os.path.join(PROJECT_ROOT, "artifacts", "logs")
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "artifacts", "evidence")
REPORT_DIR = os.path.join(PROJECT_ROOT, "artifacts", "reports")
os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(EVIDENCE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

LANE_SCRIPTS = {
    "lane1_hyperliquid": {
        "path": "scripts/mvpplus/lane1_hyperliquid/fetch_whale_positions.py",
        "depends_on": [],
        "stage": 1,
    },
    "lane3_market_context": {
        "path": "scripts/mvpplus/lane3_market_context/fetch_market_context.py",
        "depends_on": [],
        "stage": 2,
    },
    "lane4_existing_feeds": {
        "path": "scripts/mvpplus/lane4_existing_feeds/fetch_existing_feeds.py",
        "depends_on": [],
        "stage": 3,
    },
    "lane2_whale_engine": {
        "path": "scripts/mvpplus/lane2_whale_engine/detect_position_changes.py",
        "depends_on": ["lane1_hyperliquid"],
        "stage": 4,
    },
    "lane5_workbench_ui": {
        "path": "scripts/mvpplus/lane5_workbench_ui/generate_workbench_html.py",
        "depends_on": ["lane1_hyperliquid", "lane2_whale_engine", "lane3_market_context", "lane4_existing_feeds"],
        "stage": 5,
    },
}

LANE_LABELS = {
    "lane1_hyperliquid": "🚀 Lane 1 — Hyperliquid Whale Provider",
    "lane2_whale_engine": "🔍 Lane 2 — Whale Position Change Engine",
    "lane3_market_context": "📊 Lane 3 — Market Context Provider",
    "lane4_existing_feeds": "📰 Lane 4 — Existing Feeds Reader",
    "lane5_workbench_ui": "🖥  Lane 5 — Workbench UI Generator",
}


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_lane(lane_name: str, run_id: str) -> dict:
    """Execute a single lane script and return its result."""
    info = LANE_SCRIPTS[lane_name]
    label = LANE_LABELS.get(lane_name, lane_name)
    script_path = os.path.join(PROJECT_ROOT, info["path"])
    log_path = os.path.join(LOG_DIR, f"{lane_name}_{run_id}.log")

    start = time.time()
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  {label}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        with open(log_path, "w", encoding="utf-8") as log:
            log.write(f"=== {label} ===\n")
            log.write(f"Run ID: {run_id}\n")
            log.write(f"Started: {utc_now_str()}\n\n")

            result = subprocess.run(
                [sys.executable, "-X", "utf8", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                env=env,
            )
            log.write(result.stdout.decode("utf-8", errors="replace"))

        elapsed = time.time() - start
        success = result.returncode == 0
        status = "success" if success else "degraded"

        # Count records from output
        records_count = 0
        lane_result_key = {
            "lane1_hyperliquid": "positions",
            "lane2_whale_engine": "changes",
            "lane3_market_context": "market_contexts",
            "lane4_existing_feeds": "feed_items",
            "lane5_workbench_ui": None,
        }.get(lane_name)

        if lane_result_key:
            lane_output_path = os.path.join(RESULT_DIR, {
                "lane1_hyperliquid": "lane1_whale_positions.json",
                "lane2_whale_engine": "lane2_whale_changes.json",
                "lane3_market_context": "lane3_market_context.json",
                "lane4_existing_feeds": "lane4_existing_feeds.json",
            }.get(lane_name, ""))
            if os.path.isfile(lane_output_path):
                try:
                    with open(lane_output_path, "r", encoding="utf-8") as f:
                        lane_data = json.load(f)
                    records_count = len(lane_data.get(lane_result_key, []))
                except (IOError, json.JSONDecodeError):
                    pass

        output_summary = f"exit={result.returncode}" if success else f"exit={result.returncode} (degraded)"
        print(f"  → {output_summary} in {elapsed:.1f}s", file=sys.stderr)
        if records_count:
            print(f"  → {records_count} records", file=sys.stderr)

        return {
            "lane": lane_name,
            "status": status,
            "records_count": records_count,
            "duration_seconds": round(elapsed, 2),
            "error": None,
            "log_path": os.path.relpath(log_path, PROJECT_ROOT),
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"  → TIMEOUT after {elapsed:.1f}s", file=sys.stderr)
        return {
            "lane": lane_name,
            "status": "failed",
            "records_count": 0,
            "duration_seconds": round(elapsed, 2),
            "error": "timeout",
            "log_path": os.path.relpath(log_path, PROJECT_ROOT),
        }
    except Exception as e:
        elapsed = time.time() - start
        print(f"  → ERROR: {e}", file=sys.stderr)
        return {
            "lane": lane_name,
            "status": "failed",
            "records_count": 0,
            "duration_seconds": round(elapsed, 2),
            "error": str(e)[:200],
            "log_path": os.path.relpath(log_path, PROJECT_ROOT),
        }


def generate_run_report(
    run_id: str,
    start_time_utc: str,
    end_time_utc: str,
    lane_results: dict[str, dict],
    artifact_paths: dict[str, str],
) -> dict:
    """Generate RunReport matching run_report.schema.json."""
    record_counts: dict[str, int] = {
        "whale_positions": 0,
        "position_changes": 0,
        "market_contexts": 0,
        "feed_items": 0,
        "claims": 0,
        "event_clusters": 0,
    }
    degraded_sources: list[dict] = []
    errors: list[dict] = []

    for lane_name, result in lane_results.items():
        status = result.get("status", "failed")

        if lane_name == "lane1_hyperliquid":
            record_counts["whale_positions"] = result.get("records_count", 0)
        elif lane_name == "lane2_whale_engine":
            record_counts["position_changes"] = result.get("records_count", 0)
        elif lane_name == "lane3_market_context":
            record_counts["market_contexts"] = result.get("records_count", 0)
        elif lane_name == "lane4_existing_feeds":
            record_counts["feed_items"] = result.get("records_count", 0)

        if status != "success":
            degraded_sources.append({
                "source": lane_name,
                "status": status,
                "error_type": result.get("error", "unknown"),
                "occurred_at_utc": end_time_utc,
            })
            errors.append({
                "source": lane_name,
                "error_type": result.get("error", "unknown"),
                "message_summary": f"{lane_name} completed with status={status}",
                "occurred_at_utc": end_time_utc,
            })

    # Overall decision
    all_success = all(r["status"] == "success" for r in lane_results.values())
    any_failed = any(r["status"] == "failed" for r in lane_results.values())
    if all_success:
        decision = "accept"
    elif any_failed:
        decision = "rejected"
    else:
        decision = "review_needed"

    report: dict[str, Any] = {
        "run_id": run_id,
        "started_at_utc": start_time_utc,
        "ended_at_utc": end_time_utc,
        "source_results": lane_results,
        "record_counts": record_counts,
        "artifact_paths": {
            k: os.path.relpath(v, PROJECT_ROOT) if v else None
            for k, v in artifact_paths.items()
        },
        "degraded_sources": degraded_sources,
        "errors": errors if errors else None,
        "decision": decision,
    }
    return report


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_{str(uuid.uuid4())[:8]}"
    start_time_utc = utc_now_str()

    print(f"{'='*60}", file=sys.stderr)
    print(f"  🏗  MVP+ MASTER RUNNER — {run_id}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    print(f"  Started: {start_time_utc} UTC", file=sys.stderr)
    print(f"  Python: {sys.executable}", file=sys.stderr)
    print(f"  Project: {PROJECT_ROOT}", file=sys.stderr)

    # Execute lanes in stage order
    lane_results: dict[str, dict] = {}
    completed: set[str] = set()

    for stage in range(1, 6):
        stage_lanes = [name for name, info in LANE_SCRIPTS.items() if info["stage"] == stage]
        if not stage_lanes:
            continue

        print(f"\n{'─'*60}", file=sys.stderr)
        print(f"  Stage {stage}", file=sys.stderr)
        print(f"{'─'*60}", file=sys.stderr)

        for lane_name in stage_lanes:
            info = LANE_SCRIPTS[lane_name]

            # Check dependencies
            deps_met = all(dep in completed for dep in info["depends_on"])
            if not deps_met:
                missing = [d for d in info["depends_on"] if d not in completed]
                print(f"  ⏭ Skipping {lane_name} (missing deps: {missing})", file=sys.stderr)
                lane_results[lane_name] = {
                    "lane": lane_name, "status": "skipped", "records_count": 0,
                    "duration_seconds": None, "error": f"dependencies not met: {missing}",
                }
                continue

            result = run_lane(lane_name, run_id)
            lane_results[lane_name] = result
            completed.add(lane_name)

    # Generate artifacts
    print(f"\n{'─'*60}", file=sys.stderr)
    print(f"  Generating Run Report & Copying Evidence", file=sys.stderr)
    print(f"{'─'*60}", file=sys.stderr)

    end_time_utc = utc_now_str()

    artifact_paths: dict[str, str] = {
        "whale_report": os.path.join(RESULT_DIR, "lane1_whale_positions.json"),
        "market_context": os.path.join(RESULT_DIR, "lane3_market_context.json"),
        "feed_report": os.path.join(RESULT_DIR, "lane4_existing_feeds.json"),
        "event_report": os.path.join(RESULT_DIR, "lane2_whale_changes.json"),
        "workbench_html": os.path.join(RESULT_DIR, "workbench.html"),
        "run_log": os.path.join(LOG_DIR, f"run_{run_id}.log"),
    }

    # Generate Run Report
    run_report = generate_run_report(
        run_id, start_time_utc, end_time_utc, lane_results, artifact_paths
    )
    report_path = os.path.join(REPORT_DIR, f"mvpplus_run_report_{run_id}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(run_report, f, indent=2, ensure_ascii=False)
    print(f"  Run report: {report_path}", file=sys.stderr)

    # Generate evidence summary
    evidence = {
        "run_id": run_id,
        "started_at_utc": start_time_utc,
        "ended_at_utc": end_time_utc,
        "decision": run_report["decision"],
        "record_counts": run_report["record_counts"],
        "lane_summary": {k: {"status": v["status"], "records": v["records_count"]}
                         for k, v in lane_results.items()},
        "total_duration_seconds": round(time.time() - start_time, 2),
    }
    evidence_path = os.path.join(EVIDENCE_DIR, f"mvpplus_evidence_{run_id}.json")
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    print(f"  Evidence: {evidence_path}", file=sys.stderr)

    # Summary
    total_elapsed = time.time() - start_time
    success_count = sum(1 for r in lane_results.values() if r["status"] == "success")
    total_records = sum(r.get("records_count", 0) for r in lane_results.values())

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  ✅ MVP+ RUN COMPLETE", file=sys.stderr)
    print(f"  Run ID: {run_id}", file=sys.stderr)
    print(f"  Duration: {total_elapsed:.1f}s", file=sys.stderr)
    print(f"  Lanes: {success_count}/{len(lane_results)} succeeded", file=sys.stderr)
    print(f"  Total records: {total_records}", file=sys.stderr)
    print(f"  Decision: {run_report['decision']}", file=sys.stderr)
    print(f"  Workbench: {os.path.relpath(artifact_paths['workbench_html'], PROJECT_ROOT)}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

    # Print run report JSON
    print(json.dumps(run_report, indent=2, ensure_ascii=False))

    return 0 if run_report["decision"] == "accept" else 1


if __name__ == "__main__":
    sys.exit(main())
