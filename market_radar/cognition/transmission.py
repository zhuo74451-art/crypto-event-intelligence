"""Transmission path analysis."""
from typing import List
from market_radar.cognition.contracts import TransmissionPath, TransmissionChannel, sha256_id

def determine_paths(event_title: str, assets: List[str]) -> List[TransmissionPath]:
    """Determine defensible transmission paths based on event characteristics."""
    paths = []
    title_lower = event_title.lower()
    if any(kw in title_lower for kw in ["sec", "regulation", "cfpb", "finra", "compliance"]):
        paths.append(TransmissionPath(
            path_id=sha256_id(["path", "regulatory", event_title]),
            channel=TransmissionChannel.REGULATORY_LIQUIDITY.value,
            mechanism="Regulatory action affects market liquidity and risk appetite",
            affected_assets=list(assets),
        ))
    if any(kw in title_lower for kw in ["cve", "vulnerability", "exploit", "hack", "breach", "security"]):
        paths.append(TransmissionPath(
            path_id=sha256_id(["path", "security", event_title]),
            channel=TransmissionChannel.SECURITY_OPERATIONAL.value,
            mechanism="Security incident affects operational confidence",
            affected_assets=list(assets),
        ))
    if any(kw in title_lower for kw in ["release", "upgrade", "fork", "mainnet"]):
        paths.append(TransmissionPath(
            path_id=sha256_id(["path", "software", event_title]),
            channel=TransmissionChannel.DIRECT_ASSET.value,
            mechanism="Software release directly affects asset utility",
            affected_assets=list(assets),
        ))
    if not paths:
        paths.append(TransmissionPath(
            path_id=sha256_id(["path", "default", event_title]),
            channel=TransmissionChannel.NO_DEFENSIBLE_PATH.value,
            mechanism="No defensible market transmission path identified",
            confidence="low",
        ))
    return paths
