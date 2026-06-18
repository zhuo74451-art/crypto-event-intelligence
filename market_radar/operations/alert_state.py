"""Alert state tracker — persistent cross-run alert dedup and classification.

Tracks alert_key → state transitions across integration runs using SQLite.
Prevents repeated signals from being sent on every round.
"""

from __future__ import annotations

import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── Thresholds ─────────────────────────────────────────────────────────────

SIZE_CHANGE_RATIO = 0.10      # >= 10% relative size change → changed
LEVERAGE_CHANGE_ABS = 2.0     # >= 2x absolute leverage change → changed
PNL_CHANGE_ABS_USD = 5_000_000  # >= $5M PnL change → changed
LIQ_DIST_CHANGE_PCT = 5.0    # >= 5pp liquidation distance change → changed
COOLDOWN_HOURS = 4.0          # minimum hours between deliveries

STATE_NEW = "new"
STATE_PERSISTENT = "persistent"
STATE_CHANGED = "changed"
STATE_RESOLVED = "resolved"


def make_alert_key(address: str, coin: str, direction: str, alert_type: str) -> str:
    """Stable cross-run alert key: normalized address + asset + direction + type.

    Never includes timestamp, run_id, price, or PnL.
    """
    raw = f"{address.lower()}:{coin.upper()}:{direction}:{alert_type}"
    return "ask:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class AlertStateRecord:
    """Persistent state for a single alert_key across runs."""
    alert_key: str
    state: str                        # new / persistent / changed / resolved
    first_seen_at: str
    last_seen_at: str
    last_changed_at: Optional[str] = None
    last_delivery_at: Optional[str] = None
    severity: str = "low"
    previous_severity: Optional[str] = None
    snapshot_json: str = "{}"         # JSON of key metrics at last change
    previous_snapshot_json: str = "{}"
    resolved_at: Optional[str] = None
    delivery_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── SQLite schema ──────────────────────────────────────────────────────────

ALERT_STATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS alert_state (
    alert_key            TEXT PRIMARY KEY,
    state                TEXT NOT NULL DEFAULT 'new',
    first_seen_at        TEXT NOT NULL,
    last_seen_at         TEXT NOT NULL,
    last_changed_at      TEXT,
    last_delivery_at     TEXT,
    severity             TEXT NOT NULL DEFAULT 'low',
    previous_severity    TEXT,
    snapshot_json        TEXT NOT NULL DEFAULT '{}',
    previous_snapshot_json TEXT NOT NULL DEFAULT '{}',
    resolved_at          TEXT,
    delivery_count       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alert_state_state ON alert_state(state);
CREATE INDEX IF NOT EXISTS idx_alert_state_last_seen ON alert_state(last_seen_at);
"""


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_db_path(state_dir: str | Path) -> str:
    return str(Path(state_dir) / "alert_state.db")


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    for stmt in ALERT_STATE_TABLE_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass  # CREATE IF NOT EXISTS handles duplicates
    conn.commit()
    return conn


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        v = float(val)
        if v != v or v == float("inf") or v == float("-inf"):
            return default
        return v
    except (ValueError, TypeError):
        return default


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Snapshot extraction from alert candidate ───────────────────────────────

def _extract_metrics(alert: dict) -> dict:
    """Extract key numeric metrics from an alert candidate for state comparison."""
    current = alert.get("current", {})
    if not isinstance(current, dict):
        current = {}
    return {
        "observed_value": _safe_float(alert.get("observed_value")),
        "severity": alert.get("severity", "low"),
        "position_value_usd": _safe_float(current.get("position_value_usd")),
        "liquidation_distance_pct": _safe_float(alert.get("liquidation_distance_pct")),
        "signed_size": _safe_float(current.get("signed_size")),
        "leverage": _safe_float(current.get("leverage")),
        "unrealized_pnl_usd": _safe_float(current.get("unrealized_pnl_usd")),
    }


def _detect_change(
    current: dict,
    previous: dict,
) -> bool:
    """Detect if a meaningful change occurred between two snapshots."""
    # Severity change
    if current.get("severity") != previous.get("severity"):
        return True

    # Size change >= 10% relative
    prev_size = abs(_safe_float(previous.get("signed_size")))
    curr_size = abs(_safe_float(current.get("signed_size")))
    if prev_size > 0 and curr_size > 0:
        if abs(curr_size - prev_size) / prev_size >= SIZE_CHANGE_RATIO:
            return True

    # Leverage change >= 2x absolute
    prev_lev = _safe_float(previous.get("leverage"))
    curr_lev = _safe_float(current.get("leverage"))
    if abs(curr_lev - prev_lev) >= LEVERAGE_CHANGE_ABS:
        return True

    # PnL change >= $5M
    prev_pnl = _safe_float(previous.get("unrealized_pnl_usd"))
    curr_pnl = _safe_float(current.get("unrealized_pnl_usd"))
    if abs(curr_pnl - prev_pnl) >= PNL_CHANGE_ABS_USD:
        return True

    # Liquidation distance change >= 5pp
    prev_liq = _safe_float(previous.get("liquidation_distance_pct"))
    curr_liq = _safe_float(current.get("liquidation_distance_pct"))
    if abs(curr_liq - prev_liq) >= LIQ_DIST_CHANGE_PCT:
        return True

    return False


# ── Core state tracking ────────────────────────────────────────────────────

def _is_critical(severity: str) -> bool:
    return severity == "critical"


class AlertStateTracker:
    """Cross-run alert state manager. One instance per state_dir."""

    def __init__(self, state_dir: str | Path):
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = _get_db_path(state_dir)
        self._conn = _get_conn(self._db_path)
        self._now = _now_utc()

    def close(self) -> None:
        self._conn.close()

    def load_active_keys(self) -> set[str]:
        """Load all non-resolved alert keys from SQLite."""
        try:
            rows = self._conn.execute(
                "SELECT alert_key FROM alert_state WHERE state != ?",
                (STATE_RESOLVED,)
            ).fetchall()
            return {row["alert_key"] for row in rows}
        except Exception:
            return set()

    def _load(self, alert_key: str) -> Optional[AlertStateRecord]:
        row = self._conn.execute(
            "SELECT * FROM alert_state WHERE alert_key = ?", (alert_key,)
        ).fetchone()
        if row is None:
            return None
        return AlertStateRecord(**dict(row))

    def _save(self, rec: AlertStateRecord) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO alert_state
               (alert_key, state, first_seen_at, last_seen_at, last_changed_at,
                last_delivery_at, severity, previous_severity, snapshot_json,
                previous_snapshot_json, resolved_at, delivery_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (rec.alert_key, rec.state, rec.first_seen_at, rec.last_seen_at,
             rec.last_changed_at, rec.last_delivery_at, rec.severity,
             rec.previous_severity, rec.snapshot_json,
             rec.previous_snapshot_json, rec.resolved_at, rec.delivery_count),
        )
        self._conn.commit()

    def classify_alert(
        self,
        alert: dict,
    ) -> tuple[str, AlertStateRecord]:
        """Classify a single alert and return (state_delta_description, record).

        Returns the new state classification and the persistent record.
        """
        alert_type = alert.get("alert_type", "unknown")
        coin = alert.get("coin", "?")
        direction = alert.get("direction", "unknown")
        address = alert.get("address", "")
        label = alert.get("label", "")
        severity = alert.get("severity", "low")

        # Build stable alert_key
        alert_key = make_alert_key(address, coin, direction, alert_type)

        # Extract current metrics
        current_snapshot = _extract_metrics(alert)
        current_snapshot["label"] = label
        current_snapshot["address"] = address
        current_snapshot["coin"] = coin
        current_snapshot["direction"] = direction
        current_snapshot["alert_type"] = alert_type

        # Load previous state
        prev = self._load(alert_key)

        if prev is None:
            # First time seeing this alert_key → new
            rec = AlertStateRecord(
                alert_key=alert_key,
                state=STATE_NEW,
                first_seen_at=self._now,
                last_seen_at=self._now,
                severity=severity,
                snapshot_json=json.dumps(current_snapshot),
            )
            self._save(rec)
            return STATE_NEW, rec

        # Update last_seen
        prev.last_seen_at = self._now
        prev.previous_severity = prev.severity

        # Check for resolution: if the alert type is no longer present
        # in the current batch, mark resolved. (Handled at batch level.)

        # Compare current vs previous snapshot for change detection
        prev_snapshot = json.loads(prev.snapshot_json) if prev.snapshot_json else {}
        has_changed = _detect_change(current_snapshot, prev_snapshot)

        # Determine new state
        if _is_critical(severity):
            # Critical alerts always break through
            new_state = STATE_CHANGED
            prev.last_changed_at = self._now
        elif has_changed:
            new_state = STATE_CHANGED
            prev.last_changed_at = self._now
        else:
            new_state = STATE_PERSISTENT

        # Save previous snapshot before overwriting
        prev.previous_snapshot_json = prev.snapshot_json
        prev.state = new_state
        prev.severity = severity
        prev.snapshot_json = json.dumps(current_snapshot)
        self._save(prev)

        return new_state, prev

    def mark_delivered(self, alert_key: str) -> None:
        """Mark an alert_key as delivered (for delivery candidates)."""
        rec = self._load(alert_key)
        if rec is None:
            return
        rec.last_delivery_at = self._now
        rec.delivery_count += 1
        self._save(rec)

    def resolve_alert(self, alert_key: str) -> None:
        """Mark an alert_key as resolved (position closed / alert gone)."""
        rec = self._load(alert_key)
        if rec is None:
            return
        rec.state = STATE_RESOLVED
        rec.resolved_at = self._now
        self._save(rec)

    def classify_batch(
        self,
        alerts: list[dict],
        previous_alert_keys: Optional[set[str]] = None,
    ) -> dict[str, list[dict]]:
        if previous_alert_keys is None:
            previous_alert_keys = self.load_active_keys()
        """Classify a full batch of alerts into categories.

        Returns:
            {
                "new": [...],
                "persistent": [...],
                "changed": [...],
                "resolved": [...],
                "delivery_candidates": [...],
                "suppressed": [...],
            }
        """
        result: dict[str, list[dict]] = {
            "new": [],
            "persistent": [],
            "changed": [],
            "resolved": [],
            "delivery_candidates": [],
            "suppressed": [],
        }

        current_keys: set[str] = set()

        for alert in alerts:
            state, rec = self.classify_alert(alert)
            current_keys.add(rec.alert_key)

            entry = dict(alert)
            entry["alert_key"] = rec.alert_key
            entry["alert_state"] = state

            if state == STATE_NEW:
                result["new"].append(entry)
            elif state == STATE_PERSISTENT:
                result["persistent"].append(entry)
            elif state == STATE_CHANGED:
                result["changed"].append(entry)

            # Delivery decision
            if state == STATE_NEW:
                result["delivery_candidates"].append(entry)
            elif state == STATE_CHANGED:
                # Changed with worsening risk → deliver
                # Changed with improvement → suppress (severity drop)
                prev_sev = rec.previous_severity
                cur_sev = rec.severity
                sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                if _is_critical(cur_sev) or (
                    cur_sev and prev_sev
                    and sev_order.get(cur_sev, 0) >= sev_order.get(prev_sev, 0)
                ):
                    result["delivery_candidates"].append(entry)
                else:
                    result["suppressed"].append(entry)
            else:
                result["suppressed"].append(entry)

        # Detect resolved: previously seen keys no longer in current batch
        resolved_keys = previous_alert_keys - current_keys
        for alert_key in resolved_keys:
            self.resolve_alert(alert_key)
            result["resolved"].append({"alert_key": alert_key, "alert_state": STATE_RESOLVED})

        return result

    def get_cooldown_remaining(self, alert_key: str) -> float:
        """Hours remaining until this alert_key can be delivered again."""
        rec = self._load(alert_key)
        if rec is None or rec.last_delivery_at is None:
            return 0.0
        from datetime import datetime, timezone
        try:
            last = datetime.fromisoformat(rec.last_delivery_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            elapsed = (now - last).total_seconds() / 3600
            return max(0.0, COOLDOWN_HOURS - elapsed)
        except (ValueError, TypeError):
            return 0.0
