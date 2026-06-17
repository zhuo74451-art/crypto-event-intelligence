"""One-shot integration runner — no-send, read-only pipeline.

Wires W2 (whale domain), W3 (feeds, workbench), W4 (adapters), W5 (ops).
Never sends, never signs, never trades.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)
from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter,
)
from market_radar.integration.models import (
    IntegrationConfig,
    IntegrationRunResult,
    OneShotArtifactPaths,
    SourceRunStatus,
)
from market_radar.integration.whale_mapper import run_whale_mapper
from market_radar.integration.market_mapper import run_market_snapshot
from market_radar.integration.feed_handler import run_feed

# W3 workbench — typed models
from market_radar.workbench.bundle import WorkbenchBundle
from market_radar.workbench.renderer import render_workbench
from market_radar.intelligence_feed.models import FeedItem, FeedSourceType, FeedDataMode, make_feed_id
from market_radar.market_view.models import MarketSnapshot, MarketHealth, Venue, DataMode

# W5 operations
from market_radar.operations.file_lock import FileLock, STALE_LOCK_SECONDS
from market_radar.operations.runner_protocol import InjectedRunner
from market_radar.operations.run_once import run_once
from market_radar.operations.stop_marker import StopMarker
from market_radar.operations.source_health import record_health
from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.atomic_json import atomic_write_json


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_one_shot(config: IntegrationConfig) -> IntegrationRunResult:
    """Execute one integration one-shot. Returns run result, never raises."""
    result = IntegrationRunResult(
        data_mode=config.mode,
        no_send=config.no_send,
        config=config,
    )

    state_dir = _ensure_dir(config.state_dir)
    output_dir = _ensure_dir(config.output_dir)
    lock_path = state_dir / "one_shot.lock"

    # ── Check stop marker ──
    stop = StopMarker(state_dir / "STOP")
    if stop.check():
        result.status = "failed"
        result.errors.append("stop marker set at start — refusing to run")
        result.finished_at = _utc_now()
        return result

    # ── Acquire file lock ──
    # FileLock.try_acquire() returns None on success (acquired) or
    # an error string on denial (lock held by another process).
    try:
        lock = FileLock(lock_path)
        acquire_result = lock.try_acquire()
        if acquire_result is not None:
            result.status = "failed"
            result.errors.append(f"another one-shot is already running: {acquire_result}")
            result.finished_at = _utc_now()
            return result
    except Exception as e:
        result.status = "failed"
        result.errors.append(f"lock acquisition failed: {e}")
        result.finished_at = _utc_now()
        return result

    try:
        # ── Run via W5 run_once for ops-wrapped execution ──
        runner = InjectedRunner(label="one_shot", fn=lambda ctx: _run_pipeline(ctx, config, result))
        run_result = run_once(runner, config=config.as_dict(), run_id=result.run_id)

        if run_result.status == "ok":
            result.status = "completed"
        elif run_result.status == "failed":
            if "degraded" in str(run_result.summary):
                result.status = "degraded"
            else:
                result.status = "failed"

        if run_result.error:
            result.errors.append(run_result.error)

        # ── Write artifacts ──
        paths = _write_artifacts(result, output_dir, state_dir)
        result.output_paths = [
            paths.report_json,
            paths.workbench_html,
            paths.whale_snapshot_json,
            paths.market_snapshot_json,
        ]

        # ── Record source health ──
        _record_source_health(result, state_dir)

    except Exception as e:
        result.status = "failed"
        result.errors.append(f"unhandled pipeline error: {type(e).__name__}: {e}")
    finally:
        lock.release()
        result.finished_at = _utc_now()

    return result


def _run_pipeline(
    context: dict[str, Any],
    config: IntegrationConfig,
    result: IntegrationRunResult,
) -> dict[str, Any]:
    """Core pipeline logic — extracted for W5 run_once wrapping."""
    statuses: list[str] = []

    # ── Adapters ──
    hl_adapter = HyperliquidPublicAdapter()
    ccxt_adapter = CcxtPublicMarketAdapter(exchange_timeout=config.timeout)

    try:
        # ── Whale mapper ──
        if config.whale_address:
            whale_result, whale_src = run_whale_mapper(
                hl_adapter, config.whale_address, config.timeout,
            )
            result.whale = whale_result
            result.sources.append(whale_src)
            statuses.append(whale_src.status)
        else:
            result.sources.append(SourceRunStatus(
                source="whale", status="degraded", ok=False,
                error="no whale address configured",
            ))
            statuses.append("skipped")

        # ── Market mapper ──
        market_snapshots, market_sources = run_market_snapshot(
            ccxt_adapter, hl_adapter, config.exchange,
        )
        result.markets = market_snapshots
        result.sources.extend(market_sources)
        statuses.extend(s.status for s in market_sources)

        # ── Feed handler ──
        feed_result, feed_src = run_feed(config.mode)
        result.feed = feed_result
        result.sources.append(feed_src)
        statuses.append(feed_src.status)

        # ── Build workbench bundle ──
        bundle = _build_workbench_bundle(result, config)
        html = render_workbench(bundle)

        # Persist HTML for write phase
        context["workbench_html"] = html
        context["workbench_bundle"] = bundle

    finally:
        hl_adapter.close()
        ccxt_adapter.close()

    # Determine overall status
    if all(s == "ok" for s in statuses):
        return {"status": "ok"}
    elif any(s == "unavailable" for s in statuses):
        return {"status": "failed", "degraded": True}
    else:
        return {"status": "ok", "degraded": True}


def _build_workbench_bundle(
    result: IntegrationRunResult,
    config: IntegrationConfig,
) -> WorkbenchBundle:
    """Build a WorkbenchBundle from pipeline results for W3 renderer."""
    from datetime import datetime, timezone

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Market snapshots (typed MarketSnapshot objects) ──
    market_snapshots: list[MarketSnapshot] = []
    market_health: list[MarketHealth] = []

    for m in result.markets:
        venue = Venue.BINANCE_SPOT if m.source in ("binance", "binance_spot") else \
                Venue.HYPERLIQUID_PERP if m.source == "hyperliquid" else \
                Venue.UNKNOWN
        dmode = DataMode.LIVE if config.mode == "live-public" else DataMode.FIXTURE
        snap = MarketSnapshot(
            symbol=m.symbol.replace("/USDT", "") if "/USDT" in m.symbol else m.symbol,
            price=float(m.last_price) if m.last_price is not None else 0.0,
            venue=venue,
            data_mode=dmode,
            provenance=m.provenance or "integration",
            observed_at=now_utc,
        )
        market_snapshots.append(snap)
        market_health.append(MarketHealth(
            venue=venue,
            asset=snap.symbol,
            status="ok" if m.ok else "failed",
            message=m.error or "",
        ))

    # ── Feed items (typed FeedItem objects) ──
    feed_items: list[FeedItem] = []
    if result.feed and result.feed.items:
        for item in result.feed.items:
            title = item.get("title", "")
            fid = make_feed_id(title, "integration_fixture")
            feed_items.append(FeedItem(
                feed_id=fid,
                source_type=FeedSourceType.UNKNOWN,
                source_label="integration_fixture",
                data_mode=FeedDataMode.FIXTURE,
                title=title,
            ))

    # ── Whale items (dicts) ──
    whale_positions: list[dict] = []
    whale_changes: list[dict] = []
    whale_alerts: list[dict] = []
    if result.whale and result.whale.ok:
        whale_positions = result.whale.positions[:20]
        whale_changes = result.whale.changes[:20]
        whale_alerts = result.whale.alert_candidates[:20]

    # ── Build health / warnings ──
    warnings: list[str] = []
    degraded_paths: list[str] = []
    health_summary: dict[str, str] = {}
    for s in result.sources:
        if s.ok:
            health_summary[s.source] = s.status
        else:
            health_summary[s.source] = s.error or s.status
            if s.status == "unavailable":
                degraded_paths.append(s.source)
                warnings.append(f"{s.source}: {s.error}")

    if result.errors:
        warnings.extend(result.errors)

    feed_truth = {
        "data_mode": result.data_mode,
        "live_count": result.feed.live_count if result.feed else 0,
        "fixture_count": result.feed.fixture_count if result.feed else 0,
        "research_count": result.feed.research_count if result.feed else 0,
        "no_send": True,
        "scheduler_started": False,
        "credentials_used": False,
    }

    return WorkbenchBundle(
        run_id=result.run_id,
        generated_at=now_utc,
        feed_items=feed_items,
        market_snapshots=market_snapshots,
        market_health=market_health,
        whale_positions=whale_positions,
        whale_changes=whale_changes,
        alert_candidates=whale_alerts,
        warnings=warnings,
        degraded_paths=degraded_paths,
        feed_truth=feed_truth,
    )


def _write_artifacts(
    result: IntegrationRunResult,
    output_dir: Path,
    state_dir: Path,
) -> OneShotArtifactPaths:
    """Write all output artifacts."""
    paths = OneShotArtifactPaths()

    # Run report JSON
    report_path = output_dir / f"run_{result.run_id}.json"
    atomic_write_json(result.as_dict(), str(report_path))
    paths.report_json = str(report_path)

    # Whale snapshot JSON
    if result.whale:
        whale_path = output_dir / f"whale_{result.run_id}.json"
        atomic_write_json({
            "address": result.whale.address,
            "ok": result.whale.ok,
            "position_count": result.whale.position_count,
            "positions": result.whale.positions,
            "error": result.whale.error,
        }, str(whale_path))
        paths.whale_snapshot_json = str(whale_path)

    # Market snapshot JSON
    market_path = output_dir / f"market_{result.run_id}.json"
    atomic_write_json({
        "symbols": [m.as_dict() for m in result.markets],
    }, str(market_path))
    paths.market_snapshot_json = str(market_path)

    # Workbench HTML (stored in context during pipeline run)
    # The HTML is written here since render happened in _run_pipeline
    from market_radar.workbench.renderer import render_workbench
    # Re-render from bundle if needed — bundle should be minimal
    html_path = output_dir / f"workbench_{result.run_id}.html"
    # Bundle data is reconstructed, but we can use the static HTML content
    # if it was stored. For now render directly.
    bundle = _build_workbench_bundle(result, result.config) if result.config else None
    if bundle:
        html = render_workbench(bundle)
        with open(str(html_path), "w", encoding="utf-8") as f:
            f.write(html)
        paths.workbench_html = str(html_path)

    return paths


def _record_source_health(result: IntegrationRunResult, state_dir: Path) -> None:
    """Record source health to SQLite via W5 record_health."""
    try:
        db_path = state_dir / "source_health.db"
        initialize_sqlite(str(db_path))
        for src in result.sources:
            record_health(
                db_path=str(db_path),
                source_name=src.source,
                health_status=src.status,
                response_ms=int(src.latency_ms) if src.latency_ms is not None else None,
                error_message=src.error,
            )
    except Exception as e:
        result.errors.append(f"source health recording failed: {e}")
