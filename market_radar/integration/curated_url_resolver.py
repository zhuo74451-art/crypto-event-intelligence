"""Curated API URL resolver — unified priority chain.

Priority (highest first):
  1. Explicit CLI argument value (non-None, non-empty)
  2. CURATED_BASE_URL environment variable (non-empty)
  3. Repository default (loopback — co-deployment with x-monitor-app)

Usage:
    from market_radar.integration.curated_url_resolver import resolve_curated_url
    url = resolve_curated_url(cli_arg="http://...")
"""

from __future__ import annotations

import os

DEFAULT_CURATED_URL = "http://127.0.0.1:8001/api/integration/curated"
ENV_VAR_NAME = "CURATED_BASE_URL"


def resolve_curated_url(cli_arg: str | None = None) -> str:
    """Resolve the curated API base URL via priority chain.

    Args:
        cli_arg: Value from --curated-base-url CLI argument (or None).

    Returns:
        The resolved URL string. Always non-empty.

    Raises:
        ValueError: If resolved value is empty or whitespace-only.
    """
    # 1. CLI argument (highest priority)
    if cli_arg is not None and cli_arg.strip():
        return cli_arg.strip()

    # 2. Environment variable
    env_val = os.environ.get(ENV_VAR_NAME)
    if env_val is not None and env_val.strip():
        return env_val.strip()

    # 3. Repository default
    return DEFAULT_CURATED_URL
