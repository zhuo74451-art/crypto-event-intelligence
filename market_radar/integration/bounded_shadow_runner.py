"""Bounded Shadow Runner — wraps W5 run_bounded_shadow for Integration one-shot.

Uses the real W5 API:
  BoundedShadowConfig + ShadowCallable -> BoundedShadowResult

Each round constructs a fresh CuratedFeedProvider and calls run_one_shot.
No daemon, no scheduler, no threads.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Callable

from market_radar.integration.one_shot import run_one_shot
from market_radar.integration.models import IntegrationConfig
from market_radar.integration.curated_feed_provider import CuratedFeedProvider
from market_radar.integration.curated_url_resolver import resolve_curated_url
from market_radar.operations.bounded_shadow import (
    run_bounded_shadow,
    BoundedShadowConfig,
    BoundedShadowResult,
    ShadowCallable,
    ShadowCallableResult,
)


def run_integration_shadow(
    state_dir: str | Path,
    output_dir: str | Path,
    max_runs: int = 2,
    interval_seconds: float = 0.0,
    whale_address: str = "",
    exchange: str = "binance",
    timeout: float = 30.0,
    curated_base_url: Optional[str] = None,
    feed_limit: int = 100,
    feed_max_items: int = 500,
    feed_max_pages: int = 5,
    feed_timeout_seconds: float = 15.0,
    feed_initial_since: Optional[str] = None,
) -> BoundedShadowResult:
    """Execute a bounded shadow of run_one_shot via W5's run_bounded_shadow.

    Returns W5's BoundedShadowResult with per-child-run records.
    """
    state_dir_str = str(state_dir)
    output_dir_str = str(output_dir)

    def _make_provider() -> CuratedFeedProvider:
        resolved_url = resolve_curated_url(cli_arg=curated_base_url)
        return CuratedFeedProvider(
            base_url=resolved_url,
            limit=feed_limit,
            max_items=feed_max_items,
            max_pages=feed_max_pages,
            timeout_seconds=feed_timeout_seconds,
        )

    def _shadow_callable(
        ordinal: int,
        shared_state_dir: str,
        no_send: bool,
        parent_shadow_run_id: str,
    ) -> ShadowCallableResult:
        if not no_send:
            return ShadowCallableResult(
                child_run_id="",
                status="failed",
                error="no_send is False — shadow refused",
            )

        cfg = IntegrationConfig(
            mode="live-public",
            state_dir=shared_state_dir,
            output_dir=output_dir_str,
            whale_address=whale_address,
            exchange=exchange,
            timeout=timeout,
            no_send=True,
            feed_enabled=True,
            feed_limit=feed_limit,
            feed_max_items=feed_max_items,
            feed_timeout_seconds=feed_timeout_seconds,
            feed_initial_since=feed_initial_since if ordinal == 1 else None,
        )

        provider = _make_provider()
        try:
            result = run_one_shot(cfg, feed_provider=provider)
            return ShadowCallableResult(
                child_run_id=result.run_id,
                status=result.status,
                summary={
                    "mode": result.data_mode,
                    "source_count": len(result.sources),
                    "feed_status": result.feed.status if result.feed else None,
                    "whale_ok": result.whale.ok if result.whale else None,
                    "whale_positions": result.whale.position_count if result.whale else 0,
                    "whale_changes": len(result.whale.changes) if result.whale else 0,
                    "whale_alerts": len(result.whale.alert_candidates) if result.whale else 0,
                    "whale_is_baseline": result.whale.is_baseline if result.whale else None,
                    "output_paths": result.output_paths,
                },
            )
        except Exception as e:
            return ShadowCallableResult(
                child_run_id="",
                status="failed",
                error=f"{type(e).__name__}: {e}",
            )

    # Verify shared DB path: Integration's run_history.db is the same file
    integration_db = str(Path(state_dir_str) / "run_history.db")
    shadow_db = str(BoundedShadowConfig(state_dir=state_dir_str).run_history_db)
    assert os.path.normpath(integration_db) == os.path.normpath(shadow_db), \
        f"DB path mismatch: integration={integration_db} shadow={shadow_db}"

    config = BoundedShadowConfig(
        max_runs=max_runs,
        interval_seconds=interval_seconds,
        no_send=True,
        state_dir=state_dir_str,
        stop_on_failure=True,
        continue_on_degraded=True,
        child_history_mode="link_existing",
    )

    return run_bounded_shadow(config, _shadow_callable)
