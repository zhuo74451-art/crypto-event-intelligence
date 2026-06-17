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
from market_radar.operations.file_lock import FileLock
from market_radar.operations.runner_protocol import InjectedRunner
from market_radar.operations.run_once import run_once
from market_radar.operations.stop_marker import StopMarker
from market_radar.operations.source_health import record_health
from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.atomic_json import atomic_write_json
from market_radar.operations.run_history import insert_run, update_run_finish
from market_radar.operations.snapshot_index import insert_snapshot


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── CCXT Preflight Diagnostics (Section 7) ────────────────────────────

def run_ccxt_preflight(exchange_id: str = "binance") -> dict[str, Any]:
    """Diagnose CCXT runtime environment.

    Returns a diagnostic dict. Never raises.
    Paths are sanitised — no local usernames or absolute paths.
    """
    diag: dict[str, Any] = {
        "python_executable": "(sanitised)",
        "ccxt_version": None,
        "ccxt_file": None,
        "has_exchange_class": False,
        "exchange_init_ok": False,
        "exchange_init_error": None,
        "adapter_import_smoke": False,
    }
    import sys
    # Sanitise path: keep only drive letter and last two segments
    raw_exe = sys.executable
    try:
        parts = raw_exe.replace("\\", "/").split("/")
        if len(parts) > 2:
            diag["python_executable"] = f"{parts[0]}//.../{parts[-2]}/{parts[-1]}"
        else:
            diag["python_executable"] = raw_exe
    except Exception:
        diag["python_executable"] = "(unknown)"

    try:
        from importlib.metadata import version
        diag["ccxt_version"] = version("ccxt")
    except Exception:
        pass

    try:
        import ccxt
        diag["ccxt_file"] = str(getattr(ccxt, "__file__", ""))
        diag["has_exchange_class"] = hasattr(ccxt, exchange_id)
        if hasattr(ccxt, exchange_id):
            exchange_cls = getattr(ccxt, exchange_id)
            try:
                ex = exchange_cls({"enableRateLimit": False})
                diag["exchange_init_ok"] = True
            except Exception as e:
                diag["exchange_init_error"] = f"{type(e).__name__}: {e}"
    except Exception:
        pass

    # Adapter import smoke
    try:
        from market_radar.external_adapters.ccxt_public_market_adapter import (
            CcxtPublicMarketAdapter,
        )
        _ = CcxtPublicMarketAdapter
        diag["adapter_import_smoke"] = True
    except Exception as e:
        diag["adapter_import_smoke_error"] = f"{type(e).__name__}: {e}"

    return diag


# ── Core Pipeline ──────────────────────────────────────────────────────

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
    run_history_db = str(state_dir / "run_history.db")
    source_health_db = str(state_dir / "source_health.db")

    # ── CCXT preflight (live mode only) ──
    if config.mode == "live-public":
        preflight = run_ccxt_preflight(config.exchange)
        result.ccxt_preflight = preflight
        if preflight.get("exchange_init_error") and "not install" in str(preflight.get("exchange_init_error", "")).lower():
            result.errors.append("CCXT exchange init failed — dependency issue")
            result.status = "failed"
            result.finished_at = _utc_now()
            return result

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

    # ── Initialize DBs ──
    try:
        initialize_sqlite(run_history_db)
        initialize_sqlite(source_health_db)
        insert_run(run_history_db, result.run_id, runner_label="one_shot", status="running")
    except Exception as e:
        result.errors.append(f"DB init failed: {e}")

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

    except Exception as e:
        result.status = "failed"
        result.errors.append(f"unhandled pipeline error: {type(e).__name__}: {e}")
    finally:
        # 1. Source health recording
        try:
            _record_source_health(result, Path(source_health_db))
        except Exception as e:
            result.errors.append(f"source health recording failed: {e}")

        # 2. Run history update
        try:
            update_run_finish(
                run_history_db,
                result.run_id,
                status=result.status,
                summary={"status": result.status, "mode": result.data_mode},
                error="; ".join(result.errors) if result.errors else None,
            )
        except Exception as e:
            result.errors.append(f"run history update failed: {e}")

        # 3. Write artifacts (finished_at first, then outputs)
        now_finished = _utc_now()
        result.finished_at = now_finished
        try:
            paths = _write_artifacts(result, output_dir, state_dir)
            result.output_paths = [
                paths.report_json,
                paths.workbench_html,
                paths.whale_snapshot_json,
                paths.market_snapshot_json,
            ]
        except Exception as e:
            result.errors.append(f"artifact write failed: {e}")

        # 4. Release lock
        try:
            lock.release()
        except Exception as e:
            result.errors.append(f"lock release failed: {e}")

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
        # ── Whale mapper (with W2 domain) ──
        if config.whale_address:
            state_dir = _ensure_dir(config.state_dir)
            previous_state_path = state_dir / f"whale_state_{config.whale_address.lower()}.json"
            is_baseline = not previous_state_path.exists()

            whale_result, whale_src = run_whale_mapper(
                hl_adapter,
                config.whale_address,
                config.timeout,
                is_baseline_run=is_baseline,
                state_dir=state_dir,
            )
            result.whale = whale_result
            result.sources.append(whale_src)
            statuses.append(whale_src.status)
            result.alert_candidate_count = len(whale_result.alert_candidates)
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
        context["workbench_bundle"] = bundle

    except Exception as e:
        return {"status": "failed", "error": f"pipeline exception: {type(e).__name__}: {e}"}
    finally:
        hl_adapter.close()
        ccxt_adapter.close()

    # Determine overall status
    if all(s == "ok" for s in statuses):
        return {"status": "ok"}
    elif any(s in ("unavailable", "failed") for s in statuses):
        return {"status": "failed", "degraded": True}
    else:
        return {"status": "ok", "degraded": True}


def _build_workbench_bundle(
    result: IntegrationRunResult,
    config: IntegrationConfig,
) -> WorkbenchBundle:
    """Build a WorkbenchBundle from pipeline results for W3 renderer."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── Market snapshots (typed MarketSnapshot objects) ──
    market_snapshots: list[MarketSnapshot] = []
    market_health: list[MarketHealth] = []

    for m in result.markets:
        venue = Venue.BINANCE_SPOT if m.source in ("binance", "binance_spot") else \
                Venue.HYPERLIQUID_PERP if m.source == "hyperliquid" else \
                Venue.UNKNOWN
        dmode = DataMode.LIVE if (config.mode == "live-public" and m.ok and m.last_price is not None) else \
                DataMode.FIXTURE if config.mode == "fixture" else \
                DataMode.FIXTURE

        # Section 6: NEVER create price=0 MarketSnapshot for unavailable source
        if not m.ok or m.last_price is None:
            # Source unavailable — record health as failed, skip snapshot
            asset_name = m.symbol.replace("/USDT", "") if "/USDT" in m.symbol else m.symbol
            market_health.append(MarketHealth(
                venue=venue,
                asset=asset_name,
                status="failed",
                message=m.error or "source unavailable",
            ))
            continue

        asset_name = m.symbol.replace("/USDT", "") if "/USDT" in m.symbol else m.symbol
        snap = MarketSnapshot(
            symbol=asset_name,
            price=float(m.last_price),
            venue=venue,
            data_mode=dmode,
            provenance=m.provenance or "integration",
            observed_at=now_utc,
        )
        market_snapshots.append(snap)
        market_health.append(MarketHealth(
            venue=venue,
            asset=asset_name,
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

    # ── Whale items ──
    whale_positions: list[dict] = []
    whale_changes: list[dict] = []
    whale_alerts: list[dict] = []
    if result.whale and result.whale.ok:
        whale_positions = result.whale.positions[:20]
        whale_changes = result.whale.changes[:20]
        whale_alerts = result.whale.alert_candidates[:20]

    # ── Build health / warnings ──
    warnings: list[str] = []
    degraded_reasons: list[str] = []
    health_summary: dict[str, str] = {}
    for s in result.sources:
        if s.ok:
            health_summary[s.source] = s.status
        else:
            health_summary[s.source] = s.error or s.status
            degraded_reasons.append(f"{s.source}: {s.detail or s.error or s.status}")

    if result.errors:
        warnings.extend(result.errors)

    # Section 6: degraded AND unavailable must appear in degraded reasons
    for s in result.sources:
        if s.status in ("degraded", "unavailable") and s.source not in [r.split(":")[0] for r in degraded_reasons]:
            degraded_reasons.append(f"{s.source}: {s.error or s.status}")

    feed_truth = {
        "data_mode": result.data_mode,
        "live_count": result.feed.live_count if result.feed else 0,
        "fixture_count": result.feed.fixture_count if result.feed else 0,
        "research_count": result.feed.research_count if result.feed else 0,
        "no_send": True,
        "scheduler_started": False,
        "credentials_used": False,
    }

    bundle = WorkbenchBundle(
        run_id=result.run_id,
        generated_at=now_utc,
        feed_items=feed_items,
        market_snapshots=market_snapshots,
        market_health=market_health,
        whale_positions=whale_positions,
        whale_changes=whale_changes,
        alert_candidates=whale_alerts,
        warnings=warnings,
        degraded_paths=degraded_reasons,
        feed_truth=feed_truth,
    )

    return bundle


def _write_artifacts(
    result: IntegrationRunResult,
    output_dir: Path,
    state_dir: Path,
) -> OneShotArtifactPaths:
    """Write all output artifacts after finished_at is set."""
    paths = OneShotArtifactPaths()

    # Run report JSON (with finished_at already set)
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
            "changes": result.whale.changes,
            "alert_candidates": result.whale.alert_candidates,
            "is_baseline": result.whale.is_baseline,
            "error": result.whale.error,
        }, str(whale_path))
        paths.whale_snapshot_json = str(whale_path)

    # Market snapshot JSON
    market_path = output_dir / f"market_{result.run_id}.json"
    atomic_write_json({
        "symbols": [m.as_dict() for m in result.markets],
    }, str(market_path))
    paths.market_snapshot_json = str(market_path)

    # Workbench HTML via W3 render_workbench(bundle, output_path)
    bundle = _build_workbench_bundle(result, result.config) if result.config else None
    if bundle:
        html_path = output_dir / f"workbench_{result.run_id}.html"
        try:
            render_workbench(bundle, str(html_path))
            paths.workbench_html = str(html_path)
        except Exception:
            # Fallback: render to string and write manually
            html = render_workbench(bundle)
            with open(str(html_path), "w", encoding="utf-8") as f:
                f.write(html)
            paths.workbench_html = str(html_path)

    return paths


def _record_source_health(result: IntegrationRunResult, db_path: Path) -> None:
    """Record source health to SQLite via W5 record_health."""
    for src in result.sources:
        record_health(
            db_path=str(db_path),
            source_name=src.source,
            health_status=src.status,
            response_ms=int(src.latency_ms) if src.latency_ms is not None else None,
            error_message=src.error,
        )
