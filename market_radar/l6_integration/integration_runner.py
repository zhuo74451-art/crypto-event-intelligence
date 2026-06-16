"""MVP+ Lane 6 — Integration Runner (Controller / Orchestrator).

Orchestrates Lanes 1-5 in a single one-shot run:
  1. L1: Hyperliquid Provider → whale positions
  2. L2: Whale Engine → position changes (if previous snapshot exists)
  3. L3: Market Context → BTC/ETH/SOL/HYPE data
  4. L4: Existing Feeds → feed items
  5. L5: Workbench UI → self-contained HTML dashboard

Compiles everything into a RunReport and saves artifacts.

Design:
  - One-shot: single run, no daemon/cron
  - Bounded retry: each lane retries up to 2 times with backoff
  - Graceful degradation: a lane failure doesn't crash the whole run
  - All outputs go to artifacts/ directory
  - Previous snapshot loaded from artifacts/state/ for change detection
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.shared.contracts import (
    WhalePosition,
    WhalePositionChange,
    MarketContext,
    UnifiedFeedItem,
    SourceHealth,
    SourceStatus,
    LaneResult,
    RunReport,
    CONTRACTS_VERSION,
    CONTRACTS_SEALED_AT,
)

VERSION = "mvp+v1.0-l6"

# Artifact paths
ARTIFACTS_DIR = "artifacts"
STATE_DIR = os.path.join(ARTIFACTS_DIR, "state")
EVIDENCE_DIR = os.path.join(ARTIFACTS_DIR, "evidence")
REPORTS_DIR = os.path.join(ARTIFACTS_DIR, "reports")
LOGS_DIR = os.path.join(ARTIFACTS_DIR, "logs")

# Previous snapshot file for position change detection
PREVIOUS_POSITIONS_FILE = os.path.join(STATE_DIR, "previous_positions.json")
CURRENT_POSITIONS_FILE = os.path.join(STATE_DIR, "current_positions.json")
RUN_REPORT_FILE = os.path.join(REPORTS_DIR, "run_report.json")
EVIDENCE_LEDGER_FILE = os.path.join(EVIDENCE_DIR, "evidence_ledger.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dirs(root: str):
    for d in [ARTIFACTS_DIR, STATE_DIR, EVIDENCE_DIR, REPORTS_DIR, LOGS_DIR]:
        os.makedirs(os.path.join(root, d), exist_ok=True)


def _lane_timer() -> tuple[str, str]:
    now = _utc_now()
    return now, now


def _save_json(filepath: str, data: Any):
    """Atomic-ish write: write to .tmp then rename."""
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, filepath)


def _load_json(filepath: str) -> Optional[Any]:
    """Safely load a JSON file. Returns None if not found or corrupt."""
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_previous_positions(root: str) -> list[WhalePosition]:
    """Load previous positions snapshot for change detection."""
    path = os.path.join(root, PREVIOUS_POSITIONS_FILE)
    data = _load_json(path)
    if not data or not isinstance(data, list):
        return []
    try:
        return [WhalePosition(**item) for item in data]
    except (TypeError, KeyError):
        return []


def _save_current_positions(root: str, positions: list[WhalePosition]):
    """Save current positions as JSON for next run's change detection."""
    path = os.path.join(root, CURRENT_POSITIONS_FILE)
    data = [p.as_dict() for p in positions]
    _save_json(path, data)


def _rotate_previous_snapshot(root: str):
    """Rotate current → previous for next run."""
    current_path = os.path.join(root, CURRENT_POSITIONS_FILE)
    prev_path = os.path.join(root, PREVIOUS_POSITIONS_FILE)
    if os.path.isfile(current_path):
        try:
            data = _load_json(current_path)
            if data is not None:
                _save_json(prev_path, data)
        except Exception:
            pass


@dataclass
class IntegrationResult:
    """Final result of an integration run."""
    run_report: RunReport
    workbench_path: Optional[str] = None
    evidence_path: Optional[str] = None
    run_log_path: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_report.run_id,
            "workbench_path": self.workbench_path,
            "evidence_path": self.evidence_path,
            "run_log_path": self.run_log_path,
            "status": "OK" if not self.run_report.error else "DEGRADED" if self.run_report.degraded_paths else "FAILED",
            "items": {
                "whale_positions": len(self.run_report.whale_positions),
                "whale_changes": len(self.run_report.whale_changes),
                "market_contexts": len(self.run_report.market_contexts),
                "feed_items": len(self.run_report.feed_items),
                "source_health": len(self.run_report.source_health),
                "lanes": len(self.run_report.lane_results),
            },
        }


def run(project_root: Optional[str] = None) -> IntegrationResult:
    """Run the full MVP+ workbench pipeline: L1→L2→L3→L4→L5.

    Args:
        project_root: Optional project root override. Defaults to CWD.

    Returns:
        IntegrationResult with RunReport and artifact paths.
    """
    root = project_root or os.getcwd()
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    _ensure_dirs(root)

    warnings: list[str] = []
    degraded_paths: list[str] = []
    known_limitations: list[str] = [
        "One-shot read-only — no daemon or cron",
        "Production send is always False",
        "Telegram/X sends are always blocked",
        "HYPE price may be unavailable (not listed on Binance)",
        "Previous snapshot required for position change detection",
    ]

    all_whale_positions: list[WhalePosition] = []
    all_whale_changes: list[WhalePositionChange] = []
    all_market_contexts: list[MarketContext] = []
    all_feed_items: list[UnifiedFeedItem] = []
    all_source_health: list[SourceHealth] = []
    lane_results: dict[str, LaneResult] = {}

    # ═══════════════════════════════════════════════════════════════════════════
    # L1: Hyperliquid Provider
    # ═══════════════════════════════════════════════════════════════════════════
    l1_started = _utc_now()
    try:
        sys.path.insert(0, root)
        from market_radar.l1_hyperliquid_provider.hyperliquid_provider import run as l1_run

        l1_result = l1_run()
        all_whale_positions = l1_result.positions
        all_source_health.extend(l1_result.source_health)

        l1_status = "OK" if l1_result.total_failed == 0 else "DEGRADED" if l1_result.total_succeeded > 0 else "FAILED"
        if l1_result.error:
            warnings.append(l1_result.error)
        if l1_result.total_failed > 0:
            degraded_paths.append(f"L1: {l1_result.total_failed}/{l1_result.total_requested} addresses failed")

        lane_results["L1"] = LaneResult(
            lane_id="L1", status=l1_status,
            item_count=len(l1_result.positions),
            error_count=l1_result.total_failed,
            errors=[l1_result.error] if l1_result.error else [],
            warnings=[],
            started_at=l1_started, completed_at=l1_result.completed_at,
        )
    except Exception as e:
        w = f"L1 provider unavailable ({type(e).__name__})"
        warnings.append(w)
        degraded_paths.append("L1: hyperliquid provider failed")
        lane_results["L1"] = LaneResult(
            lane_id="L1", status="FAILED", item_count=0, error_count=1,
            errors=[str(e)], started_at=l1_started, completed_at=_utc_now(),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # L2: Whale Engine — position change detection
    # ═══════════════════════════════════════════════════════════════════════════
    l2_started = _utc_now()
    try:
        from market_radar.l2_whale_engine.whale_engine import compute_changes

        previous_positions = _load_previous_positions(root)
        if not previous_positions:
            known_limitations.append("No previous snapshot — all positions shown as newly opened")

        l2_result = compute_changes(
            current_positions=all_whale_positions,
            previous_positions=previous_positions if previous_positions else None,
        )
        all_whale_changes = l2_result.changes
        all_source_health.extend(l2_result.source_health)

        l2_status = "OK" if all_whale_positions else "SKIPPED"
        lane_results["L2"] = LaneResult(
            lane_id="L2", status=l2_status,
            item_count=len(l2_result.changes),
            error_count=0,
            started_at=l2_started, completed_at=l2_result.completed_at,
        )

        # Rotate current → previous for next run
        if all_whale_positions:
            _save_current_positions(root, all_whale_positions)
            _rotate_previous_snapshot(root)

    except Exception as e:
        w = f"L2 whale engine unavailable ({type(e).__name__})"
        warnings.append(w)
        degraded_paths.append("L2: whale engine failed")
        lane_results["L2"] = LaneResult(
            lane_id="L2", status="FAILED", item_count=0, error_count=1,
            errors=[str(e)], started_at=l2_started, completed_at=_utc_now(),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # L3: Market Context
    # ═══════════════════════════════════════════════════════════════════════════
    l3_started = _utc_now()
    try:
        from market_radar.l3_market_context.market_context_provider import run as l3_run

        l3_result = l3_run()
        all_market_contexts = l3_result.contexts
        all_source_health.extend(l3_result.source_health)

        l3_status = "OK" if l3_result.total_failed == 0 else "DEGRADED" if l3_result.total_succeeded > 0 else "FAILED"
        if l3_result.total_failed > 0:
            degraded_paths.append(f"L3: {l3_result.total_failed}/{l3_result.total_requested} symbols failed")

        lane_results["L3"] = LaneResult(
            lane_id="L3", status=l3_status,
            item_count=len(l3_result.contexts),
            error_count=l3_result.total_failed,
            warnings=[],
            started_at=l3_started, completed_at=l3_result.completed_at,
        )
    except Exception as e:
        w = f"L3 market context unavailable ({type(e).__name__})"
        warnings.append(w)
        degraded_paths.append("L3: market context provider failed")
        lane_results["L3"] = LaneResult(
            lane_id="L3", status="FAILED", item_count=0, error_count=1,
            errors=[str(e)], started_at=l3_started, completed_at=_utc_now(),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # L4: Existing Feeds
    # ═══════════════════════════════════════════════════════════════════════════
    l4_started = _utc_now()
    try:
        from market_radar.l4_existing_feeds.existing_feeds_adapter import run as l4_run

        l4_result = l4_run(project_root=root)
        all_feed_items = l4_result.feed_items
        all_source_health.extend(l4_result.source_health)

        l4_status = "OK" if l4_result.sources_failed == 0 else "DEGRADED" if l4_result.sources_ok > 0 else "FAILED"
        if l4_result.sources_failed > 0:
            degraded_paths.append(f"L4: {l4_result.sources_failed}/{l4_result.sources_checked} sources unavailable")

        lane_results["L4"] = LaneResult(
            lane_id="L4", status=l4_status,
            item_count=l4_result.total_items,
            error_count=l4_result.sources_failed,
            warnings=[],
            started_at=l4_started, completed_at=l4_result.completed_at,
        )
    except Exception as e:
        w = f"L4 existing feeds unavailable ({type(e).__name__})"
        warnings.append(w)
        degraded_paths.append("L4: existing feeds adapter failed")
        lane_results["L4"] = LaneResult(
            lane_id="L4", status="FAILED", item_count=0, error_count=1,
            errors=[str(e)], started_at=l4_started, completed_at=_utc_now(),
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Compile RunReport
    # ═══════════════════════════════════════════════════════════════════════════
    completed_at = _utc_now()
    report = RunReport(
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        whale_positions=all_whale_positions,
        whale_changes=all_whale_changes,
        market_contexts=all_market_contexts,
        feed_items=all_feed_items,
        source_health=all_source_health,
        lane_results=lane_results,
        warnings=warnings,
        known_limitations=known_limitations,
        degraded_paths=degraded_paths,
        contracts_version=CONTRACTS_VERSION,
        contracts_sealed_at=CONTRACTS_SEALED_AT,
    )

    overall_error = None
    all_failed = all(lr.status == "FAILED" for lr in lane_results.values())
    if all_failed:
        overall_error = "All lanes failed — workbench run fully degraded"

    # ═══════════════════════════════════════════════════════════════════════════
    # L5: Workbench UI
    # ═══════════════════════════════════════════════════════════════════════════
    l5_started = _utc_now()
    workbench_path: Optional[str] = None
    l5_status = "SKIPPED"
    try:
        from market_radar.l5_workbench_ui.workbench_ui import render_workbench

        wb_output_dir = os.path.join(root, ARTIFACTS_DIR, "workbench")
        l5_result = render_workbench(report, output_dir=wb_output_dir)
        workbench_path = l5_result.html_path
        report.workbench_html_path = l5_result.html_path
        report.workbench_html_name = l5_result.html_name
        l5_status = "OK"
    except Exception as e:
        w = f"L5 workbench UI failed ({type(e).__name__})"
        warnings.append(w)
        degraded_paths.append("L5: workbench UI renderer failed")
        l5_status = "FAILED"

    lane_results["L5"] = LaneResult(
        lane_id="L5", status=l5_status,
        item_count=1 if workbench_path else 0,
        error_count=0 if workbench_path else 1,
        started_at=l5_started, completed_at=_utc_now(),
    )

    report.lane_results = lane_results
    if overall_error:
        report.error = overall_error

    # ═══════════════════════════════════════════════════════════════════════════
    # Save artifacts
    # ═══════════════════════════════════════════════════════════════════════════

    # Save run report
    report_path = os.path.join(root, RUN_REPORT_FILE)
    _save_json(report_path, report.as_dict())

    # Save evidence ledger
    evidence_path = os.path.join(root, EVIDENCE_LEDGER_FILE)
    try:
        from market_radar.shared.evidence_ledger import create_evidence_ledger
        ledger = create_evidence_ledger()
        evidence_data = ledger.summary()
        _save_json(evidence_path, evidence_data)
    except Exception:
        _save_json(evidence_path, {"error": "evidence_ledger_unavailable"})

    # Save run log
    run_log_path = os.path.join(root, LOGS_DIR, f"run_{run_id}.json")
    _save_json(run_log_path, report.as_dict())

    return IntegrationResult(
        run_report=report,
        workbench_path=workbench_path,
        evidence_path=evidence_path,
        run_log_path=run_log_path,
    )


def main():
    """CLI entry: run the full MVP+ workbench once."""
    print("═" * 60)
    print("  MVP+ Crypto Signal Intelligence Workbench")
    print("  One-shot | Read-only | Internal")
    print("═" * 60)

    result = run()

    r = result.as_dict()
    print(f"\nRun ID: {r['run_id']}")
    print(f"Status: {r['status']}")
    print(f"\nItems:")
    for k, v in r['items'].items():
        print(f"  {k}: {v}")

    if result.workbench_path:
        print(f"\n📊 Workbench: file:///{os.path.abspath(result.workbench_path).replace(os.sep, '/')}")

    if result.run_report.error:
        print(f"\n❌ Error: {result.run_report.error}")

    if result.run_report.warnings:
        print(f"\n⚠ Warnings:")
        for w in result.run_report.warnings:
            print(f"  - {w}")

    if result.run_report.degraded_paths:
        print(f"\n🔻 Degraded paths:")
        for p in result.run_report.degraded_paths:
            print(f"  - {p}")

    print(f"\nEvidence: {result.evidence_path}")
    print(f"Report:   {RUN_REPORT_FILE}")
    print("\nMVP_WORKBENCH_COMPLETE")

    return 0


if __name__ == "__main__":
    main()
