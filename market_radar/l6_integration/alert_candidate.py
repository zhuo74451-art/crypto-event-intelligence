"""MVP+ L6 — Alert Candidate Layer.

Generates structured alert candidates from run data. Saves to
artifacts/alerts/alert_candidates.json. Never sends to Telegram/X.

Alert types:
  - WHALE_NEW_POSITION      — Unknown address opened a position
  - WHALE_INCREASE          - Position size increased significantly
  - WHALE_REDUCE            - Position size decreased significantly
  - DIRECTION_FLIP          - Whale flipped from long to short or vice versa
  - LIQUIDATION_RISK        - Position near liquidation price
  - LARGE_EXPOSURE          - Whale holding extremely large position
  - SOURCE_DEGRADED         - Data source unavailable or failing
  - STALE_DATA              - No new data within expected window
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

ALERTS_DIR = "artifacts/alerts"
ALERTS_FILE = "alert_candidates.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AlertCandidate:
    """A single alert candidate. Never sent — only saved for review."""
    alert_type: str
    severity: str  # CRITICAL | ELEVATED | INFO
    run_id: str
    generated_at: str

    asset: Optional[str] = None
    address: Optional[str] = None

    title: str = ""
    message: str = ""
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "alert_type": self.alert_type,
            "severity": self.severity,
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "asset": self.asset,
            "address": self.address,
            "title": self.title,
            "message": self.message,
            "details": self.details,
        }


class AlertCandidateGenerator:
    """Generates alert candidates from run results."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.alerts: list[AlertCandidate] = []

    def _add(self, alert_type: str, severity: str, title: str, message: str,
             asset: Optional[str] = None, address: Optional[str] = None,
             details: Optional[dict] = None):
        self.alerts.append(AlertCandidate(
            alert_type=alert_type,
            severity=severity,
            run_id=self.run_id,
            generated_at=_utc_now(),
            asset=asset,
            address=address,
            title=title,
            message=message,
            details=details or {},
        ))

    def evaluate_whale_changes(self, changes: list[dict]):
        """Evaluate position changes and generate alerts."""
        for c in changes:
            ctype = c.get("change_type", "")
            asset = c.get("asset")
            address = c.get("address")
            risk = c.get("risk_level", "")
            delta = c.get("position_delta_usd")
            factors = c.get("risk_factors", [])
            label = c.get("label")

            if ctype == "POSITION_OPENED":
                size = c.get("current_position_size_usd", 0)
                sev = "CRITICAL" if size >= 10_000_000 else "ELEVATED" if size >= 1_000_000 else "INFO"
                self._add("WHALE_NEW_POSITION", sev,
                          f"New position: {asset}",
                          f"{label or address[:10]+'...'} opened {asset} ${size:,.0f}",
                          asset=asset, address=address,
                          details={"position_size_usd": size})

            elif ctype == "POSITION_INCREASED":
                sev = "ELEVATED" if delta and abs(delta) >= 5_000_000 else "INFO"
                self._add("WHALE_INCREASE", sev,
                          f"{asset} position increased",
                          f"{label or address[:10]+'...'} increased {asset} by ${abs(delta or 0):,.0f}",
                          asset=asset, address=address,
                          details={"delta_usd": delta})

            elif ctype == "POSITION_REDUCED":
                sev = "ELEVATED" if delta and abs(delta) >= 5_000_000 else "INFO"
                self._add("WHALE_REDUCE", sev,
                          f"{asset} position reduced",
                          f"{label or address[:10]+'...'} reduced {asset} by ${abs(delta or 0):,.0f}",
                          asset=asset, address=address,
                          details={"delta_usd": delta})

            elif ctype == "DIRECTION_FLIPPED":
                self._add("DIRECTION_FLIP", "ELEVATED",
                          f"{asset} direction flip",
                          f"{label or address[:10]+'...'} flipped {asset} to {c.get('side')}",
                          asset=asset, address=address,
                          details={"new_side": c.get("side")})

            elif risk == "CRITICAL":
                self._add("LIQUIDATION_RISK", "CRITICAL",
                          f"{asset} critical risk",
                          f"{label or address[:10]+'...'} {asset}: {', '.join(factors)}",
                          asset=asset, address=address,
                          details={"risk_factors": factors})

    def evaluate_large_exposure(self, positions: list[dict], threshold: float = 50_000_000):
        """Generate alerts for whale positions exceeding exposure threshold."""
        for p in positions:
            size = p.get("position_size_usd", 0)
            if size >= threshold:
                asset = p.get("asset")
                label = p.get("label")
                self._add("LARGE_EXPOSURE", "ELEVATED",
                          f"Large {asset} exposure: ${size:,.0f}",
                          f"{label or p.get('address','?')[:10]+'...'} holds ${size:,.0f} {asset}",
                          asset=asset, address=p.get("address"),
                          details={"position_size_usd": size, "side": p.get("side")})

    def evaluate_degraded_sources(self, health_entries: list[dict]):
        for h in health_entries:
            status = h.get("status", "")
            if status in ("DEGRADED", "FAILED"):
                name = h.get("source_name", "unknown")
                err_info = h.get("degraded_info", {})
                msg = err_info.get("message_summary", "") if isinstance(err_info, dict) else ""
                sev = "ELEVATED" if status == "FAILED" else "INFO"
                self._add("SOURCE_DEGRADED", sev,
                          f"Source degraded: {name}",
                          f"{name}: {status} — {msg}",
                          details={"status": status, "error": msg})

    def get_alerts(self) -> list[dict]:
        return [a.as_dict() for a in self.alerts]

    def save(self, output_dir: str = ALERTS_DIR):
        """Save alert candidates to JSON file. Never sends."""
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, ALERTS_FILE)
        data = {
            "generated_at": _utc_now(),
            "run_id": self.run_id,
            "alert_count": len(self.alerts),
            "alerts": self.get_alerts(),
            "sent": False,
            "production_send_blocked": True,
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp, path)
        return path
