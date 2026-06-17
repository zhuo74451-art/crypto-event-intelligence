"""Whale Domain — entity profile aggregation.

Associates addresses with known entities. Manual/declared associations only.
No black-box entity resolution.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhaleEntityProfile,
)

# Known entity profiles — manually curated, addresses map to entities.
KNOWN_ENTITIES: list[WhaleEntityProfile] = [
    WhaleEntityProfile(
        entity_id="entity_matrixport",
        entity_label="Matrixport Related",
        entity_type="fund_wallet",
        confidence="medium",
        label_source="hyperliquid_observer",
        addresses=["0x6c8512516ce5669d35113a11ca8b8de322fd84f6"],
        notes="Associated with Matrixport, a crypto financial services platform",
    ),
    WhaleEntityProfile(
        entity_id="entity_loraclexyz",
        entity_label="loraclexyz",
        entity_type="high_leverage_trader",
        confidence="medium",
        label_source="hyperliquid_observer",
        addresses=["0x8def9f50456c6c4e37fa5d3d57f108ed23992dae"],
        notes="High-leverage multi-asset trader on Hyperliquid",
    ),
    WhaleEntityProfile(
        entity_id="entity_hype_whale",
        entity_label="Unknown HYPE Whale",
        entity_type="unknown_whale",
        confidence="low",
        label_source="heuristic",
        addresses=["0x082e843a431aef031264dc232693dd710aedca88"],
        notes="Large HYPE position holder. Single massive long position.",
    ),
    WhaleEntityProfile(
        entity_id="entity_hl_whale",
        entity_label="Unknown Hyperliquid Whale",
        entity_type="unknown_whale",
        confidence="low",
        label_source="heuristic",
        addresses=["0x50b309f78e774a756a2230e1769729094cac9f20"],
        notes="BTC long + ETH short whale, high leverage on both sides.",
    ),
]

# Build address -> entity lookup
_ADDRESS_TO_ENTITY: dict[str, WhaleEntityProfile] = {}
for ent in KNOWN_ENTITIES:
    for addr in ent.addresses:
        _ADDRESS_TO_ENTITY[addr.lower()] = ent


def lookup_entity(address: str) -> Optional[WhaleEntityProfile]:
    """Find the entity that owns an address, or None."""
    return _ADDRESS_TO_ENTITY.get(address.lower())


def get_entity_summary(
    snapshots: list[WhaleSnapshot],
) -> tuple[list[WhaleEntityProfile], list[dict]]:
    """Generate entity-level summaries from snapshots.

    Returns:
        (known_entity_profiles, unassociated_positions)
    """
    entity_positions: dict[str, WhaleEntityProfile] = {}
    unassociated: list[dict] = []

    for snap in snapshots:
        entity = lookup_entity(snap.address)
        if entity:
            eid = entity.entity_id
            if eid not in entity_positions:
                # Copy profile for mutation
                import copy
                ep = copy.deepcopy(entity)
                ep.total_value_usd = 0.0
                ep.total_pnl_usd = 0.0
                ep.position_count = 0
                entity_positions[eid] = ep

            ep = entity_positions[eid]
            ep.total_value_usd += snap.position_value_usd
            ep.total_pnl_usd += snap.unrealized_pnl_usd or 0
            ep.position_count += 1
        else:
            unassociated.append({
                "address": snap.address[:10],
                "label": snap.label,
                "coin": snap.coin,
                "value_usd": snap.position_value_usd,
            })

    result = sorted(
        entity_positions.values(),
        key=lambda e: e.total_value_usd, reverse=True,
    )
    return result, unassociated


def get_known_entities() -> list[WhaleEntityProfile]:
    """Return the known entity registry."""
    return KNOWN_ENTITIES
