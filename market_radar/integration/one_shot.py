"""One-shot integration runner — no-send, read-only pipeline.

Wires W2 (whale domain), W3 (feeds, workbench), W4 (adapters), W5 (ops).
Never sends, never signs, never trades.

NOTE: import ccxt before hyperliquid to prevent hyperliquid.ccxt shadowing.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Pre-import ccxt before hyperliquid to prevent hyperliquid.ccxt namespace shadowing.
import ccxt as _real_ccxt
_CCXT_ID = id(_real_ccxt)

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)

# Restore real ccxt in sys.modules if hyperliquid shadowed it
import sys as _sys
if id(_sys.modules.get("ccxt")) != _CCXT_ID:
    _sys.modules["ccxt"] = _real_ccxt

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
from market_radar.integration.feed_handler import run_feed, run_feed_with_provider, create_not_connected_feed
from market_radar.integration.feed_provider_protocol import FeedProviderProtocol

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


def _ensure_real_ccxt() -> None:
    """Ensure sys.modules['ccxt'] is the real ccxt, not hyperliquid.ccxt shadow."""
    if id(_sys.modules.get("ccxt")) != _CCXT_ID:
        _sys.modules["ccxt"] = _real_ccxt


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── CCXT Preflight Diagnostics (Section 7) ────────────────────────────

def run_ccxt_preflight(exchange_id: str = "binance") -> dict[str, Any]:
    """Diagnose CCXT runtime environment. Paths sanitised."""
    diag: dict[str, Any] = {
        "python_executable": "(sanitised)",
        "ccxt_version": None,
        "ccxt_file": None,
        "has_exchange_class": False,
        "exchange_init_ok": False,
        "exchange_init_error": None,
        "adapter_import_smoke": False,
    }
    raw_exe = _sys.executable
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

def _compute_final_status(result: IntegrationRunResult) -> str:
    """Compute final run status from source statuses.

    Rules:
    - Any critical internal exception → "failed"
    - No internal exception, but degraded/unavailable sources → "degraded"
    - All sources ok → "completed"
    """
    if any("unhandled pipeline" in e for e in result.errors):
        return "failed"

    if not result.sources:
        return result.status  # fallback to stored status

    has_unavailable = any(s.status in ("unavailable", "failed") for s in result.sources)
    has_degraded = any(s.status == "degraded" for s in result.sources)
    all_ok = all(s.ok for s in result.sources)

    if all_ok and not has_degraded and not has_unavailable:
        return "completed"
    if has_unavailable:
        return "degraded"
    if has_degraded:
        return "degraded"
    return "failed"


def run_one_shot(
    config: IntegrationConfig,
    feed_provider: Optional[FeedProviderProtocol] = None,
) -> IntegrationRunResult:
    """Execute one integration one-shot. Returns run result, never raises.

    Args:
        config: Run configuration.
        feed_provider: Optional FeedProvider for live feed data.
            When None, feed reports degraded/not_connected.
            When provided, called once per run (no loop, no retry).
    """
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

    # Pre-compute all output/state paths (Section 2)
    output_base = str(output_dir)
    state_base = str(state_dir)
    report_json = os.path.join(output_base, f"run_{result.run_id}.json")
    workbench_html = os.path.join(output_base, f"workbench_{result.run_id}.html")
    whale_snapshot_json = os.path.join(output_base, f"whale_{result.run_id}.json")
    market_snapshot_json = os.path.join(output_base, f"market_{result.run_id}.json")
    whale_state_path = os.path.join(state_base, f"whale_state_{config.whale_address.lower()}.json") if config.whale_address else ""

    # ── CCXT preflight (live mode only) ──
    if config.mode == "live-public":
        _ensure_real_ccxt()
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
        runner = InjectedRunner(label="one_shot", fn=lambda ctx: _run_pipeline(ctx, config, result, feed_provider))
        run_result = run_once(runner, config=config.as_dict(), run_id=result.run_id)

        if run_result.status == "failed" and run_result.error:
            result.errors.append(run_result.error)

        # Always compute final status from source statuses, not from run_once status
        # (Section 1: degraded sources must produce degraded final status)
        result.status = _compute_final_status(result)

    except Exception as e:
        result.status = "failed"
        result.errors.append(f"unhandled pipeline error: {type(e).__name__}: {e}")

    # Order (Section 2):
    # 1. finished_at
    # 2. output/state paths in result
    # 3. source health
    # 4. artifacts (whale/market/workbench) — NO run report
    # 5. run history update
    # 6. run report LAST — captures all final values and errors
    finally:
        try:
            lock.release()
        except Exception:
            pass

    result.finished_at = _utc_now()

    # Set output/state paths
    result.output_paths = [report_json, workbench_html, whale_snapshot_json, market_snapshot_json]
    result.state_db_paths = [run_history_db, source_health_db]

    # Source health (Section 2 step 3)
    try:
        for src in result.sources:
            record_health(
                db_path=source_health_db,
                source_name=src.source,
                health_status=src.status,
                response_ms=int(src.latency_ms) if src.latency_ms is not None else None,
                error_message=src.error,
            )
    except Exception as e:
        result.errors.append(f"source health recording failed: {e}")

    # Artifacts (Section 2 step 4) — run report is NOT written here
    artifact_errors: list[str] = []
    try:
        artifact_errors = _write_artifacts(result, output_dir, state_dir,
                                           report_json, workbench_html,
                                           whale_snapshot_json, market_snapshot_json)
    except Exception as e:
        artifact_errors.append(f"artifact write failed: {e}")

    for err in artifact_errors:
        result.errors.append(err)

    if artifact_errors and result.status == "completed":
        result.status = "degraded"

    # Run history update (Section 2 step 5)
    history_failed = False
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
        history_failed = True

    if history_failed and result.status == "completed":
        result.status = "degraded"

    # Run report LAST (Section 2 step 6) — written after all other artifacts
    # and update_run_finish, so it captures final finished_at, output_paths,
    # state_db_paths, status, and all errors including artifact/history failures
    try:
        atomic_write_json(result.as_dict(), report_json)
    except Exception as e:
        result.errors.append(f"run report write failed: {e}")

    return result


def _run_pipeline(
    context: dict[str, Any],
    config: IntegrationConfig,
    result: IntegrationRunResult,
    feed_provider: Optional[FeedProviderProtocol] = None,
) -> dict[str, Any]:
    """Core pipeline logic — extracted for W5 run_once wrapping."""
    statuses: list[str] = []

    # ── Adapters ──
    hl_adapter = HyperliquidPublicAdapter()
    _ensure_real_ccxt()
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

        # Ensure real ccxt before market mapper (HL methods re-shadow it)
        _ensure_real_ccxt()

        # ── Market mapper ──
        market_snapshots, market_sources = run_market_snapshot(
            ccxt_adapter, hl_adapter, config.exchange,
        )
        result.markets = market_snapshots
        result.sources.extend(market_sources)
        statuses.extend(s.status for s in market_sources)

        # ── Feed handler (via provider or not_connected) ──
        feed_result: Optional[FeedResult] = None
        feed_src: Optional[SourceRunStatus] = None
        feed_sub_sources: list[SourceRunStatus] = []

        if feed_provider is not None and config.feed_enabled:
            feed_result, feed_src, raw_batch, cursor_err, feed_summary, feed_sub_sources = \
                run_feed_with_provider(feed_provider, config, _ensure_dir(config.state_dir), result.run_id)
            if feed_summary:
                result.feed_summary = feed_summary
            if cursor_err:
                result.errors.append(cursor_err)
        else:
            feed_result, feed_src = create_not_connected_feed()

        if feed_result is not None:
            result.feed = feed_result
        if feed_src is not None:
            result.sources.append(feed_src)
            statuses.append(feed_src.status)
        # Sub-sources from provider
        for sub in feed_sub_sources:
            result.sources.append(sub)

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

    # ── Feed items ──
    # Feed items come from the feed_provider protocol result.
    # Items are already FeedItem instances — use them directly.
    # When no provider is configured, feed.items contains lightweight dicts.
    feed_items: list[FeedItem] = []
    if result.feed and result.feed.items:
        for item in result.feed.items:
            if isinstance(item, FeedItem):
                feed_items.append(item)
            elif isinstance(item, dict):
                # Fallback: reconstruct from dict (pre-provider mode)
                try:
                    from market_radar.intelligence_feed.models import (
                        FeedSourceType, FeedDataMode, make_feed_id,
                    )
                    title = item.get("title", "")
                    fid = make_feed_id(title, "integration_fixture")
                    feed_items.append(FeedItem(
                        feed_id=item.get("feed_id", fid),
                        source_type=FeedSourceType.UNKNOWN,
                        source_label=item.get("source_label", "integration_fixture"),
                        data_mode=FeedDataMode.FIXTURE,
                        title=title,
                    ))
                except Exception:
                    pass

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
    for s in result.sources:
        if s.ok:
            pass
        else:
            degraded_reasons.append(f"{s.source}: {s.detail or s.error or s.status}")

    if result.errors:
        warnings.extend(result.errors)

    # All degraded/unavailable sources must appear in degraded reasons
    for s in result.sources:
        if s.status in ("degraded", "unavailable") and \
           s.source not in [r.split(":")[0] for r in degraded_reasons]:
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
    report_json: str = "",
    workbench_html: str = "",
    whale_snapshot_json: str = "",
    market_snapshot_json: str = "",
) -> list[str]:
    """Write all output artifacts EXCEPT the run report.

    Run report is written LAST by the caller after update_run_finish(),
    so that it captures final finished_at, output_paths, state_db_paths,
    status, and all errors including artifact and run-history failures.

    Returns a list of error messages from individual artifact writes.
    The caller appends these to result.errors so they appear in the final report.
    """
    errors: list[str] = []

    # Whale snapshot JSON
    if result.whale:
        try:
            atomic_write_json({
                "address": result.whale.address,
                "ok": result.whale.ok,
                "position_count": result.whale.position_count,
                "positions": result.whale.positions,
                "changes": result.whale.changes,
                "alert_candidates": result.whale.alert_candidates,
                "is_baseline": result.whale.is_baseline,
                "error": result.whale.error,
            }, whale_snapshot_json)
        except Exception as e:
            errors.append(f"whale snapshot write failed: {e}")

    # Market snapshot JSON
    try:
        atomic_write_json({
            "symbols": [m.as_dict() for m in result.markets],
        }, market_snapshot_json)
    except Exception as e:
        errors.append(f"market snapshot write failed: {e}")

    # Workbench HTML via W3 render_workbench(bundle, output_path)
    bundle = _build_workbench_bundle(result, result.config) if result.config else None
    if bundle:
        try:
            render_workbench(bundle, workbench_html)
        except Exception as e:
            errors.append(f"workbench render failed: {e}")

    return errors
