"""MVP+ L6 — Centralized Configuration.

All tunable parameters for the MVP+ workbench in one place.
Config validation ensures fail-closed on misconfiguration.

Sources (precedence: later overrides earlier):
  1. Built-in defaults (this file)
  2. Environment variables (MVP_ prefix)
  3. Config file (artifacts/config.json, optional)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional

_CONFIG_FILE = "artifacts/config.json"
_ENV_PREFIX = "MVP_"

LP_DEFAULT_TIMEOUT = 15


@dataclass
class APIConfig:
    """API timeout and retry configuration."""
    connect_timeout: int = 10
    read_timeout: int = LP_DEFAULT_TIMEOUT
    max_retries: int = 2
    retry_backoff_base: float = 2.0
    max_concurrency: int = 4
    user_agent: str = "MVPPlus-Workbench/1.0 (read-only; public data)"


@dataclass
class WhaleConfig:
    """Whale monitoring configuration."""
    tracked_addresses: list[dict] = field(default_factory=lambda: [
        {"address": "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
         "label": "Matrixport Related"},
        {"address": "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
         "label": "loraclexyz"},
        {"address": "0x082e843a431aef031264dc232693dd710aedca88",
         "label": "Unknown HYPE Whale"},
        {"address": "0x50b309f78e774a756a2230e1769729094cac9f20",
         "label": "Unknown Hyperliquid Whale"},
    ])
    address_limit: int = 20
    size_change_threshold_pct: float = 1.0
    large_new_position_usd: float = 10_000_000
    large_delta_usd: float = 5_000_000
    notable_delta_usd: float = 1_000_000
    large_delta_pct: float = 50.0
    notable_delta_pct: float = 20.0
    high_leverage_threshold: float = 10.0
    very_high_leverage_threshold: float = 20.0
    liquidation_critical_distance_pct: float = 5.0


@dataclass
class AssetConfig:
    """Monitored asset configuration."""
    symbols: list[str] = field(default_factory=lambda: [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT",
    ])
    base_assets: list[str] = field(default_factory=lambda: [
        "BTC", "ETH", "SOL", "HYPE",
    ])


@dataclass
class MarketConfig:
    """Market data source configuration."""
    binance_ticker_url: str = "https://api.binance.com/api/v3/ticker/24hr"
    hyperliquid_info_url: str = "https://api.hyperliquid.xyz/info"
    enable_binance: bool = True
    enable_hyperliquid_market: bool = True


@dataclass
class SourceConfig:
    """Data source enable/disable."""
    enable_l1_hyperliquid: bool = True
    enable_l2_whale_engine: bool = True
    enable_l3_market_context: bool = True
    enable_l4_existing_feeds: bool = True
    enable_l5_workbench_ui: bool = True


@dataclass
class OutputConfig:
    """Output path configuration."""
    artifacts_dir: str = "artifacts"
    state_dir: str = "artifacts/state"
    evidence_dir: str = "artifacts/evidence"
    reports_dir: str = "artifacts/reports"
    workbench_dir: str = "artifacts/workbench"
    logs_dir: str = "artifacts/logs"
    alerts_dir: str = "artifacts/alerts"


@dataclass
class ShadowConfig:
    """Bounded shadow harness configuration."""
    max_rounds: int = 3
    round_interval_s: int = 60
    max_duration_s: int = 600


@dataclass
class AlertConfig:
    """Alert candidate generation thresholds."""
    enable_new_position_alerts: bool = True
    enable_large_change_alerts: bool = True
    enable_direction_flip_alerts: bool = True
    enable_liquidation_risk_alerts: bool = True
    enable_source_degraded_alerts: bool = True
    enable_stale_data_alerts: bool = True
    liquidation_critical_pct: float = 5.0
    large_exposure_usd: float = 50_000_000
    stale_data_minutes: int = 30


@dataclass
class MVPConfig:
    """Top-level MVP+ configuration."""
    api: APIConfig = field(default_factory=APIConfig)
    whale: WhaleConfig = field(default_factory=WhaleConfig)
    assets: AssetConfig = field(default_factory=AssetConfig)
    market: MarketConfig = field(default_factory=MarketConfig)
    sources: SourceConfig = field(default_factory=SourceConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    shadow: ShadowConfig = field(default_factory=ShadowConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    def validate(self) -> list[str]:
        """Validate configuration. Returns list of errors (empty = valid).

        Fail-closed: any invalid config is reported.
        """
        errors: list[str] = []

        if self.api.connect_timeout < 1:
            errors.append("api.connect_timeout must be >= 1")
        if self.api.read_timeout < 1:
            errors.append("api.read_timeout must be >= 1")
        if self.api.max_retries < 0:
            errors.append("api.max_retries must be >= 0")
        if self.api.max_concurrency < 1:
            errors.append("api.max_concurrency must be >= 1")

        if self.whale.address_limit < 1:
            errors.append("whale.address_limit must be >= 1")
        if self.whale.size_change_threshold_pct < 0:
            errors.append("whale.size_change_threshold_pct must be >= 0")
        if self.whale.large_new_position_usd < 0:
            errors.append("whale.large_new_position_usd must be >= 0")

        if not self.assets.symbols:
            errors.append("assets.symbols must not be empty")
        if not self.assets.base_assets:
            errors.append("assets.base_assets must not be empty")

        if not self.market.binance_ticker_url.startswith("https://"):
            errors.append("market.binance_ticker_url must use HTTPS")
        if not self.market.hyperliquid_info_url.startswith("https://"):
            errors.append("market.hyperliquid_info_url must use HTTPS")

        if self.shadow.max_rounds < 1:
            errors.append("shadow.max_rounds must be >= 1")
        if self.shadow.max_duration_s < 10:
            errors.append("shadow.max_duration_s must be >= 10")

        return errors


def load_config(config_path: Optional[str] = None) -> MVPConfig:
    """Load configuration from defaults + env + config file.

    Environment variable mapping:
      MVP_API_CONNECT_TIMEOUT → api.connect_timeout
      MVP_API_READ_TIMEOUT → api.read_timeout
      MVP_API_MAX_RETRIES → api.max_retries
    """
    cfg = MVPConfig()

    # Env var overrides
    env_map = {
        "MVP_API_CONNECT_TIMEOUT": ("api", "connect_timeout", int),
        "MVP_API_READ_TIMEOUT": ("api", "read_timeout", int),
        "MVP_API_MAX_RETRIES": ("api", "max_retries", int),
        "MVP_WHALE_ADDRESS_LIMIT": ("whale", "address_limit", int),
        "MVP_ENABLE_L1": ("sources", "enable_l1_hyperliquid", bool),
        "MVP_ENABLE_L3": ("sources", "enable_l3_market_context", bool),
        "MVP_ENABLE_L4": ("sources", "enable_l4_existing_feeds", bool),
    }
    for env_key, (section, attr, conv) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            try:
                parsed = conv(val)
                setattr(getattr(cfg, section), attr, parsed)
            except (ValueError, TypeError):
                pass  # Invalid env override, ignore

    # Config file overrides
    config_file = config_path or _CONFIG_FILE
    if os.path.isfile(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                overrides = json.load(f)
            for section, values in overrides.items():
                if hasattr(cfg, section):
                    sec_obj = getattr(cfg, section)
                    for key, val in values.items():
                        if hasattr(sec_obj, key):
                            setattr(sec_obj, key, val)
        except (json.JSONDecodeError, OSError):
            pass  # Invalid config file, use defaults

    # Validate
    errors = cfg.validate()
    if errors:
        raise ValueError(f"Configuration validation failed:\n  " + "\n  ".join(errors))

    return cfg


def save_config(cfg: MVPConfig, config_path: str):
    """Save configuration to JSON file."""
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    data = {
        "api": cfg.api.__dict__,
        "whale": cfg.whale.__dict__,
        "assets": cfg.assets.__dict__,
        "market": cfg.market.__dict__,
        "sources": cfg.sources.__dict__,
        "output": cfg.output.__dict__,
        "shadow": cfg.shadow.__dict__,
        "alerts": cfg.alerts.__dict__,
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
