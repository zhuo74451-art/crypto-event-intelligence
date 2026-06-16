"""L1 — Address Universe: 3-tier whale address discovery.

Tier 1: Local whitelist of high-priority addresses with labels.
Tier 2: Hyperliquid leaderboard discovery (top traders by volume).
Tier 3: Cached addresses from previous successful runs.

Fallback: if leaderboard fails, continue with whitelist + cached.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, *[os.pardir] * 3))

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
USER_AGENT = "MVPPlus-W2/1.0 (address-universe; no-key)"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAY_S = 1.0
LEADERBOARD_MAX = 50
CONCURRENCY_LIMIT = 8


class AddressSource(str, Enum):
    WHITELIST = "whitelist"
    LEADERBOARD = "leaderboard"
    CACHE = "cache"


@dataclass
class AddressEntry:
    address: str
    label: Optional[str] = None
    source: AddressSource = AddressSource.WHITELIST
    discovered_at: Optional[str] = None
    last_success: Optional[str] = None
    enabled: bool = True
    notes: Optional[str] = None
    priority: int = 5   # 1=highest, 10=lowest
    entity_type: Optional[str] = None
    label_confidence: Optional[str] = None  # high | medium | low

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "label": self.label,
            "source": self.source.value if isinstance(self.source, AddressSource) else self.source,
            "discovered_at": self.discovered_at,
            "last_success": self.last_success,
            "enabled": self.enabled,
            "notes": self.notes,
            "priority": self.priority,
            "entity_type": self.entity_type,
            "label_confidence": self.label_confidence,
        }


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hl_post(payload: dict, timeout: int = REQUEST_TIMEOUT) -> Optional[Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL, data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def _hl_post_with_retry(payload: dict) -> Optional[Any]:
    last = None
    for attempt in range(1 + MAX_RETRIES):
        result = _hl_post(payload)
        if result is not None:
            return result
        last = f"attempt {attempt + 1} failed"
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_S * (2 ** attempt))
    return None


# ── Tier 1: Whitelist ───────────────────────────────────────────────────


def get_whitelist() -> list[AddressEntry]:
    """Return the hardcoded high-priority whitelist."""
    now = utc_now_str()
    return [
        AddressEntry(
            address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
            label="Matrixport Related",
            entity_type="fund_wallet",
            label_confidence="medium",
            source=AddressSource.WHITELIST,
            priority=1,
            discovered_at=now,
            notes="Hyperliquid observer label: fund wallet",
        ),
        AddressEntry(
            address="0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
            label="loraclexyz",
            entity_type="high_leverage_trader",
            label_confidence="medium",
            source=AddressSource.WHITELIST,
            priority=1,
            discovered_at=now,
            notes="High-leverage multi-asset trader on Hyperliquid",
        ),
        AddressEntry(
            address="0x082e843a431aef031264dc232693dd710aedca88",
            label="Unknown HYPE Whale",
            entity_type="unknown_whale",
            label_confidence="low",
            source=AddressSource.WHITELIST,
            priority=1,
            discovered_at=now,
            notes="Large HYPE position holder (>1M HYPE)",
        ),
        AddressEntry(
            address="0x50b309f78e774a756a2230e1769729094cac9f20",
            label="Unknown Hyperliquid Whale",
            entity_type="unknown_whale",
            label_confidence="low",
            source=AddressSource.WHITELIST,
            priority=1,
            discovered_at=now,
            notes="BTC long + ETH short, high leverage",
        ),
        AddressEntry(
            address="0xf3f4b76045a56c2b7f59a0e5e2cb74fce91a7d3a",
            label="Hyperliquid DEX Pool",
            entity_type="exchange_related",
            label_confidence="medium",
            source=AddressSource.WHITELIST,
            priority=2,
            discovered_at=now,
            notes="HL DEX pool wallet",
        ),
        AddressEntry(
            address="0x331d7a2212b2c3ce583a9b98b4f7d13141565088",
            label="High Volume Whale A",
            entity_type="unknown_whale",
            label_confidence="low",
            source=AddressSource.WHITELIST,
            priority=2,
            discovered_at=now,
            notes="Observed high-volume trader",
        ),
    ]


# ── Tier 2: Leaderboard Discovery ───────────────────────────────────────


def discover_from_leaderboard(max_entries: int = LEADERBOARD_MAX) -> tuple[list[AddressEntry], Optional[str]]:
    """Fetch top traders from Hyperliquid leaderboard.

    Returns (entries, error_message). error_message is None on success.
    """
    result = _hl_post_with_retry({"type": "leaderboard", "type": "vault"})
    if result is None:
        return [], "Leaderboard API returned no data"

    entries: list[AddressEntry] = []
    now = utc_now_str()

    if isinstance(result, list):
        for item in result[:max_entries]:
            if not isinstance(item, dict):
                continue
            addr = item.get("address") or item.get("wallet", "")
            if not addr or not isinstance(addr, str) or len(addr) < 10:
                continue
            # Check not duplicating whitelist
            label = item.get("name", "") or f"Leaderboard Trader"
            entries.append(AddressEntry(
                address=addr,
                label=str(label)[:60],
                entity_type="unknown_whale",
                label_confidence="low",
                source=AddressSource.LEADERBOARD,
                priority=6,
                discovered_at=now,
                notes=f"Leaderboard discovery: {item.get('type', 'trader')}",
            ))
        if entries:
            return entries, None
        return [], "Leaderboard returned 0 usable addresses"

    # Fallback: try different leaderboard endpoints
    for endpoint_type in ["allMids", "meta"]:
        alt_result = _hl_post_with_retry({"type": endpoint_type})
        if alt_result is not None:
            break

    return [], "Leaderboard format unrecognized, no addresses extracted"


# ── Tier 3: Cached Addresses ────────────────────────────────────────────


def load_cached_addresses(cache_path: Optional[str] = None) -> list[AddressEntry]:
    """Load previously successful addresses from local cache."""
    if cache_path is None:
        cache_path = os.path.join(PROJECT_ROOT, "data", "mvpplus_state", "address_cache.json")

    if not os.path.isfile(cache_path):
        return []

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        entries: list[AddressEntry] = []
        now = utc_now_str()
        for item in raw if isinstance(raw, list) else raw.get("addresses", []):
            entries.append(AddressEntry(
                address=item.get("address", ""),
                label=item.get("label"),
                source=AddressSource.CACHE,
                priority=item.get("priority", 8),
                discovered_at=item.get("discovered_at", now),
                last_success=item.get("last_success"),
                enabled=item.get("enabled", True),
                notes=item.get("notes"),
                entity_type=item.get("entity_type"),
                label_confidence=item.get("label_confidence", "low"),
            ))
        return entries
    except (IOError, json.JSONDecodeError):
        return []


def save_cached_addresses(entries: list[AddressEntry], cache_path: Optional[str] = None):
    """Save successful addresses to local cache."""
    if cache_path is None:
        cache_path = os.path.join(PROJECT_ROOT, "data", "mvpplus_state", "address_cache.json")

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    data = {
        "saved_at_utc": utc_now_str(),
        "count": len(entries),
        "addresses": [e.to_dict() for e in entries],
    }
    # Atomic write via temp file
    tmp_path = cache_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, cache_path)
    except IOError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def deduplicate_addresses(
    whitelist: list[AddressEntry],
    leaderboard: list[AddressEntry],
    cached: list[AddressEntry],
    max_total: int = 100,
) -> list[AddressEntry]:
    """Merge three tiers, deduplicate by address, sort by priority.

    Whitelist takes precedence, then leaderboard, then cache.
    Only enabled addresses are included.
    Max total is capped at max_total (sorted by priority).
    """
    seen: set[str] = set()
    merged: list[AddressEntry] = []

    for entry in whitelist + leaderboard + cached:
        if not entry.enabled:
            continue
        addr_lower = entry.address.lower()
        if addr_lower in seen:
            continue
        seen.add(addr_lower)
        merged.append(entry)

    merged.sort(key=lambda e: e.priority)
    return merged[:max_total]


class AddressUniverse:
    """Manages the 3-tier address universe."""

    def __init__(
        self,
        cache_path: Optional[str] = None,
        max_addresses: int = 100,
    ):
        self.cache_path = cache_path
        self.max_addresses = max_addresses
        self.entries: list[AddressEntry] = []
        self.source_stats: dict[str, int] = {}
        self.errors: list[str] = []
        self.leaderboard_available: bool = True

    def refresh(self) -> list[AddressEntry]:
        """Discover addresses from all three tiers."""
        now = utc_now_str()
        self.errors = []

        # Tier 1: Whitelist
        whitelist = get_whitelist()
        self.source_stats["whitelist"] = len(whitelist)
        print(f"  [W2] Tier 1 whitelist: {len(whitelist)} addresses", file=sys.stderr)

        # Tier 2: Leaderboard
        print(f"  [W2] Tier 2 leaderboard discovery...", file=sys.stderr)
        leaderboard, lb_error = discover_from_leaderboard()
        self.source_stats["leaderboard"] = len(leaderboard)
        if lb_error:
            self.errors.append(f"Leaderboard unavailable: {lb_error}")
            self.leaderboard_available = False
            print(f"  [W2] Leaderboard: {lb_error}", file=sys.stderr)
        else:
            print(f"  [W2] Leaderboard: {len(leaderboard)} addresses", file=sys.stderr)

        # Tier 3: Cache
        cached = load_cached_addresses(self.cache_path)
        self.source_stats["cache"] = len(cached)
        print(f"  [W2] Cache: {len(cached)} addresses", file=sys.stderr)

        # Merge & deduplicate
        self.entries = deduplicate_addresses(
            whitelist, leaderboard, cached,
            max_total=self.max_addresses,
        )
        print(f"  [W2] Total unique addresses: {len(self.entries)}", file=sys.stderr)

        # Cache the result for next run
        save_cached_addresses(self.entries, self.cache_path)

        return self.entries

    def get_enabled_addresses(self) -> list[AddressEntry]:
        return [e for e in self.entries if e.enabled]

    def get_whale_only(self, min_priority: int = 5) -> list[AddressEntry]:
        """Get higher-priority addresses (lower number = higher priority)."""
        return [e for e in self.entries if e.enabled and e.priority <= min_priority]

    def to_dict(self) -> dict:
        return {
            "total": len(self.entries),
            "source_stats": self.source_stats,
            "leaderboard_available": self.leaderboard_available,
            "errors": self.errors if self.errors else None,
            "entries": [e.to_dict() for e in self.entries],
        }


def create_default_universe() -> AddressUniverse:
    """Create an AddressUniverse with default settings."""
    return AddressUniverse(
        cache_path=os.path.join(PROJECT_ROOT, "data", "mvpplus_state", "address_cache.json"),
        max_addresses=100,
    )
