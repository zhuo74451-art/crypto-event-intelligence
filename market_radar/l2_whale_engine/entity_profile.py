"""L2 — Whale Entity Profile Manager.

Associates multiple addresses with a single entity.
Supports manual labels, external sources, and confidence state.
First version: no black-box entity resolution, only declared associations.
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str

# Known entity profiles (manually curated, expandable)
KNOWN_ENTITIES: list[dict] = [
    {
        "entity_id": "entity_matrixport",
        "entity_label": "Matrixport Related",
        "entity_type": "fund_wallet",
        "confidence": "medium",
        "label_source": "hyperliquid_observer",
        "notes": "Associated with Matrixport, a crypto financial services platform",
        "addresses": [
            "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
        ],
    },
    {
        "entity_id": "entity_loraclexyz",
        "entity_label": "loraclexyz",
        "entity_type": "high_leverage_trader",
        "confidence": "medium",
        "label_source": "hyperliquid_observer",
        "notes": "High-leverage multi-asset trader. Active on Hyperliquid.",
        "addresses": [
            "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
        ],
    },
    {
        "entity_id": "entity_hype_whale",
        "entity_label": "Unknown HYPE Whale",
        "entity_type": "unknown_whale",
        "confidence": "low",
        "label_source": "heuristic",
        "notes": "Large HYPE position holder. Single massive long position.",
        "addresses": [
            "0x082e843a431aef031264dc232693dd710aedca88",
        ],
    },
    {
        "entity_id": "entity_hl_whale",
        "entity_label": "Unknown Hyperliquid Whale",
        "entity_type": "unknown_whale",
        "confidence": "low",
        "label_source": "heuristic",
        "notes": "BTC long + ETH short whale, high leverage on both sides.",
        "addresses": [
            "0x50b309f78e774a756a2230e1769729094cac9f20",
        ],
    },
]


def lookup_entity(address: str) -> Optional[dict]:
    """Find the entity that owns an address."""
    addr_lower = address.lower()
    for entity in KNOWN_ENTITIES:
        for addr in entity.get("addresses", []):
            if addr.lower() == addr_lower:
                return entity
    return None


def get_entity_summary(positions: list[dict]) -> list[dict]:
    """Generate entity-level summaries from current positions."""
    now = utc_now_str()

    # Group positions by entity
    entity_positions: dict[str, dict] = {}
    unassociated: list[dict] = []

    for p in positions:
        address = p.get("address", "")
        entity = lookup_entity(address)

        if entity:
            eid = entity["entity_id"]
            if eid not in entity_positions:
                entity_positions[eid] = {
                    "entity_id": eid,
                    "entity_label": entity["entity_label"],
                    "entity_type": entity["entity_type"],
                    "confidence": entity["confidence"],
                    "label_source": entity["label_source"],
                    "notes": entity.get("notes"),
                    "addresses": entity["addresses"],
                    "positions": [],
                    "total_value_usd": 0.0,
                    "total_pnl_usd": 0.0,
                }
            ep = entity_positions[eid]
            ep["positions"].append({
                "coin": p.get("coin"),
                "direction": p.get("direction"),
                "position_value_usd": p.get("position_value_usd"),
                "leverage": p.get("leverage"),
                "unrealized_pnl_usd": p.get("unrealized_pnl_usd"),
                "liquidation_distance_pct": p.get("liquidation_distance_pct"),
            })
            ep["total_value_usd"] += p.get("position_value_usd", 0) or 0
            ep["total_pnl_usd"] += p.get("unrealized_pnl_usd", 0) or 0
        else:
            unassociated.append({
                "address": address[:10],
                "label": p.get("label"),
                "coin": p.get("coin"),
                "value_usd": p.get("position_value_usd"),
            })

    return {
        "generated_at_utc": now,
        "known_entities": [
            {
                "entity_id": e["entity_id"],
                "entity_label": e["entity_label"],
                "entity_type": e["entity_type"],
                "confidence": e["confidence"],
                "label_source": e["label_source"],
                "notes": e["notes"],
                "addresses": e["addresses"],
                "position_count": len(e["positions"]),
                "total_value_usd": round(e["total_value_usd"], 2),
                "total_pnl_usd": round(e["total_pnl_usd"], 2),
                "positions": e["positions"],
            }
            for e in sorted(entity_positions.values(), key=lambda x: x["total_value_usd"], reverse=True)
        ],
        "unassociated_positions": unassociated,
    }
