"""Market Radar v1.17 — Unified Evidence Ledger

Records the complete pipeline trace for each signal in a standardized,
redacted JSONL format. No raw secrets, tokens, chat_ids, or passwords
are ever stored.

This is the SIXTH and final layer in the v117 pipeline:
  ... → DryRunResult → EvidenceLedger → evidence_entry → JSONL

Design:
  - EvidenceLedger class that records pipeline entries
  - Each entry captures: snapshot → quality_gate → send_readiness → dry_run
  - All sensitive data is redacted (SHA-256 fingerprints)
  - Output format is compatible with v116l_tg_evidence_index.jsonl
  - Supports writing to file or returning entries as dicts

Constraints:
  - No external API calls
  - No TG send
  - No daemon/cron/loop
  - No token/key/secret read or print
  - Never stores raw credentials or secrets

Usage:
    from scripts.market_radar_evidence_ledger_v117 import (
        EvidenceLedger, EvidenceEntry, record_pipeline,
    )

    ledger = EvidenceLedger()
    entry = ledger.record(
        snapshot=snapshot,
        quality_gate_result=qg_result,
        send_readiness_result=sr_result,
        dry_run_result=dr_result,
        public_card=public_card,
    )
    ledger.write_jsonl("results/market_radar_v117_evidence_index.jsonl")
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
LEDGER_VERSION = "v1.17"


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _sha256_hex(text: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════
# Evidence Entry — Unified Redacted Evidence Record
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class EvidenceEntry:
    """A single redacted evidence record covering the full pipeline.

    Fields:
        card_type: Card type key.
        card_family: Same as card_type (for v116l compatibility).
        snapshot_id: The snapshot identifier.
        quality_gate_passed: Result from quality gate.
        send_readiness_passed: Result from send-readiness gate.
        dry_run_status: "dry_run_sent" | "dry_run_blocked".
        dry_run_success: Whether dry-run succeeded.
        blocked_reason: If blocked, why.
        dry_run_message_id: Deterministic mock ID.
        payload_hash: SHA-256 of the public_card.
        payload_length: Length of public_card in characters.
        payload_preview: First 300 chars of public_card.
        target_type: The intended target type.
        production_send: Always False in dry-run.
        credentials_printed: Always False.
        raw_secret_present: Always False.
        network_called: Always False.
        real_tg_sent: Always False.
        adapter_version: Version of the producing adapter.
        quality_gate_version: Version of the quality gate.
        send_readiness_version: Version of the send-readiness gate.
        sender_version: Version of the dry-run sender.
        ledger_version: Version of this ledger.
        recorded_at: ISO timestamp of record creation.
        metadata: Optional additional metadata.
    """
    card_type: str
    card_family: str
    snapshot_id: str
    quality_gate_passed: bool
    send_readiness_passed: bool
    dry_run_status: str
    dry_run_success: bool
    blocked_reason: str | None = None
    dry_run_message_id: str = ""
    payload_hash: str = ""
    payload_length: int = 0
    payload_preview: str = ""
    target_type: str = "test_channel"
    production_send: bool = False
    credentials_printed: bool = False
    raw_secret_present: bool = False
    network_called: bool = False
    real_tg_sent: bool = False
    adapter_version: str = ""
    quality_gate_version: str = ""
    send_readiness_version: str = ""
    sender_version: str = ""
    ledger_version: str = LEDGER_VERSION
    recorded_at: str = field(default_factory=china_stamp)
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        """Return entry as a plain dict (for JSONL serialization)."""
        return {
            "card_type": self.card_type,
            "card_family": self.card_family,
            "snapshot_id": self.snapshot_id,
            "quality_gate_passed": self.quality_gate_passed,
            "send_readiness_passed": self.send_readiness_passed,
            "dry_run_status": self.dry_run_status,
            "dry_run_success": self.dry_run_success,
            "blocked_reason": self.blocked_reason,
            "dry_run_message_id": self.dry_run_message_id,
            "payload_hash": self.payload_hash,
            "payload_length": self.payload_length,
            "payload_preview": self.payload_preview,
            "target_type": self.target_type,
            "production_send": self.production_send,
            "credentials_printed": self.credentials_printed,
            "raw_secret_present": self.raw_secret_present,
            "network_called": self.network_called,
            "real_tg_sent": self.real_tg_sent,
            "adapter_version": self.adapter_version,
            "quality_gate_version": self.quality_gate_version,
            "send_readiness_version": self.send_readiness_version,
            "sender_version": self.sender_version,
            "ledger_version": self.ledger_version,
            "recorded_at": self.recorded_at,
            "metadata": self.metadata,
        }

    def to_jsonl(self) -> str:
        """Return entry as a single JSONL line."""
        return json.dumps(self.as_dict(), ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════════════
# Evidence Ledger
# ══════════════════════════════════════════════════════════════════════════════════════

class EvidenceLedger:
    """Unified evidence ledger — records full pipeline traces.

    Each record captures the complete lifecycle of a signal:
      Adapter → QualityGate → SendReadinessGate → Renderer → DryRunSender

    The ledger is append-only and all entries are redacted (SHA-256 fingerprints).
    Compatible with v116l tg_evidence_index.jsonl format.
    """

    def __init__(self):
        self._entries: list[EvidenceEntry] = []
        self._total_recorded = 0
        self._passed_count = 0
        self._blocked_count = 0

    @property
    def entries(self) -> list[EvidenceEntry]:
        return list(self._entries)

    @property
    def total_recorded(self) -> int:
        return self._total_recorded

    @property
    def passed_count(self) -> int:
        return self._passed_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def record(
        self,
        snapshot,
        quality_gate_result,
        send_readiness_result,
        dry_run_result,
        public_card: str = "",
        metadata: dict | None = None,
    ) -> EvidenceEntry:
        """Record a complete pipeline trace.

        Args:
            snapshot: NormalizedSnapshot from the adapter.
            quality_gate_result: QualityGateResult.
            send_readiness_result: SendReadinessResult.
            dry_run_result: DryRunResult.
            public_card: The rendered public card text (for hash/preview).
            metadata: Optional additional metadata.

        Returns:
            EvidenceEntry with all fields populated.
        """
        # Extract from snapshot
        card_type = getattr(snapshot, "card_type", "unknown")
        snapshot_id = getattr(snapshot, "snapshot_id", "unknown")
        adapter_version = getattr(snapshot, "adapter_version", "")

        # Extract from quality gate
        qg_passed = getattr(quality_gate_result, "quality_gate_passed", False)
        qg_version = getattr(quality_gate_result, "gate_version", "")

        # Extract from send-readiness
        sr_passed = getattr(send_readiness_result, "send_ready", False)
        sr_version = getattr(send_readiness_result, "gate_version", "")

        # Extract from dry-run
        dr_status = getattr(dry_run_result, "dry_run_status", "unknown")
        dr_success = getattr(dry_run_result, "dry_run_success", False)
        dr_blocked = getattr(dry_run_result, "blocked_reason", None)
        dr_msg_id = getattr(dry_run_result, "dry_run_message_id", "")
        dr_payload_hash = getattr(dry_run_result, "payload_hash", "")
        dr_payload_len = getattr(dry_run_result, "payload_length", 0)
        dr_preview = getattr(dry_run_result, "payload_preview", "")
        dr_target = getattr(dry_run_result, "target_type", "test_channel")
        dr_sender_version = getattr(dry_run_result, "sender_version", "")

        # If dry-run didn't compute hash, compute it now
        if not dr_payload_hash and public_card:
            dr_payload_hash = _sha256_hex(public_card)
        # If no preview from dry-run, compute from public_card
        if not dr_preview and public_card:
            dr_preview = public_card[:300]
        if dr_payload_len == 0 and public_card:
            dr_payload_len = len(public_card)

        entry = EvidenceEntry(
            card_type=card_type,
            card_family=card_type,
            snapshot_id=snapshot_id,
            quality_gate_passed=qg_passed,
            send_readiness_passed=sr_passed,
            dry_run_status=dr_status,
            dry_run_success=dr_success,
            blocked_reason=dr_blocked,
            dry_run_message_id=dr_msg_id,
            payload_hash=dr_payload_hash,
            payload_length=dr_payload_len,
            payload_preview=dr_preview,
            target_type=dr_target,
            production_send=False,
            credentials_printed=False,
            raw_secret_present=False,
            network_called=False,
            real_tg_sent=False,
            adapter_version=adapter_version,
            quality_gate_version=qg_version,
            send_readiness_version=sr_version,
            sender_version=dr_sender_version,
            metadata=metadata or {},
        )

        self._entries.append(entry)
        self._total_recorded += 1
        if dr_success:
            self._passed_count += 1
        else:
            self._blocked_count += 1

        return entry

    def to_jsonl(self) -> str:
        """Return all entries as a JSONL string."""
        return "\n".join(entry.to_jsonl() for entry in self._entries) + "\n"

    def write_jsonl(self, output_path: str) -> str:
        """Write all entries to a JSONL file.

        Args:
            output_path: Path to output JSONL file (relative to project root
                         or absolute).

        Returns:
            The absolute path written.
        """
        content = self.to_jsonl()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return str(path.resolve())

    def summary(self) -> dict:
        """Return a summary of the ledger."""
        card_types = {}
        for entry in self._entries:
            ct = entry.card_type
            if ct not in card_types:
                card_types[ct] = {"total": 0, "passed": 0, "blocked": 0}
            card_types[ct]["total"] += 1
            if entry.dry_run_success:
                card_types[ct]["passed"] += 1
            else:
                card_types[ct]["blocked"] += 1

        return {
            "ledger_version": LEDGER_VERSION,
            "total_recorded": self._total_recorded,
            "passed_count": self._passed_count,
            "blocked_count": self._blocked_count,
            "card_types": card_types,
        }

    def clear(self) -> None:
        """Clear all entries (use with caution)."""
        self._entries.clear()
        self._total_recorded = 0
        self._passed_count = 0
        self._blocked_count = 0


# ── Module-level convenience ────────────────────────────────────────────────────

def record_pipeline(
    snapshot,
    quality_gate_result,
    send_readiness_result,
    dry_run_result,
    public_card: str = "",
) -> EvidenceEntry:
    """Record a complete pipeline trace (convenience function).

    Returns EvidenceEntry.
    """
    ledger = EvidenceLedger()
    return ledger.record(
        snapshot=snapshot,
        quality_gate_result=quality_gate_result,
        send_readiness_result=send_readiness_result,
        dry_run_result=dry_run_result,
        public_card=public_card,
    )
