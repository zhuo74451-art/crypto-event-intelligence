"""Bounded Shadow Runner — wraps W5 run_bounded_shadow for Integration one-shot.

Wires run_one_shot with a fresh CuratedFeedProvider per round.
No daemon, no scheduler, no threads.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Callable

from market_radar.integration.one_shot import run_one_shot
from market_radar.integration.models import IntegrationConfig
from market_radar.operations.bounded_shadow import run_bounded_shadow


def run_integration_shadow(
    state_dir: str | Path,
    output_dir: str | Path,
    max_runs: int = 2,
    interval_seconds: float = 0.0,
    feed_provider_factory: Optional[Callable] = None,
    **config_kw: Any,
) -> list[dict]:
    """Execute a bounded shadow of run_one_shot using W5's run_bounded_shadow.

    Args:
        state_dir: Shared state directory across runs.
        output_dir: Output directory (each run gets its own subdir or shared).
        max_runs: Number of one-shot runs (default 2).
        interval_seconds: Delay between runs (0 = no delay).
        feed_provider_factory: Callable that returns a FeedProviderProtocol.
        **config_kw: Additional IntegrationConfig fields.

    Returns:
        List of run result dicts, one per execution.
    """
    def runner_fn(run_index: int) -> dict:
        cfg = IntegrationConfig(
            mode="live-public",
            no_send=True,
            state_dir=str(state_dir),
            output_dir=str(output_dir),
            **config_kw,
        )
        provider = feed_provider_factory() if feed_provider_factory else None
        result = run_one_shot(cfg, feed_provider=provider)
        return result.as_dict()

    return run_bounded_shadow(
        runner_fn=runner_fn,
        max_runs=max_runs,
        interval_seconds=interval_seconds,
        state_dir=str(state_dir),
    )
