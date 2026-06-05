"""Market Radar v1.17 — Sender Dry-Run Interface

A local-only sender that simulates the full send pipeline without:
  - Reading environment variables for credentials
  - Making network requests
  - Calling Telegram API
  - Accepting or printing real tokens / chat_ids
  - Sending to production targets

This is the FIFTH layer in the v117 pipeline:
  ... → public_card + gate_results → DryRunSender → dry_run_artifact → ...

Design:
  - DryRunSender class with dry_send() method
  - Takes public_card + QualityGateResult + SendReadinessResult
  - Produces a standardized DryRunResult artifact
  - Blocks formal/prod targets (hard safety stop)
  - Generates deterministic mock message IDs
  - All results are redacted: SHA-256 fingerprints, no raw secrets

Key difference from v111j MockTelegramSender:
  - Accepts v117 pipeline objects (QualityGateResult, SendReadinessResult)
  - Integrated with the full v117 pipeline
  - Produces evidence-ledger-compatible artifacts
  - Explicitly states "dry_run_only" in all outputs

Constraints:
  - No external API calls
  - No TG send (real or mock — this is dry-run only)
  - No daemon/cron/loop
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_sender_dryrun_v117 import (
        DryRunSender, DryRunResult, dry_send_card,
    )

    sender = DryRunSender()
    result = sender.dry_send(
        public_card=public_card,
        quality_gate_result=qg_result,
        send_readiness_result=sr_result,
        target_type="test_channel",
    )
    print(f"Dry-run status: {result.dry_run_status}")
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
DRY_RUN_VERSION = "v1.17"

# ── Safety constants ─────────────────────────────────────────────────────────────

BLOCKED_TARGET_TYPES = frozenset({
    "formal_channel",
    "official_channel",
    "prod",
    "production",
    "main_channel",
})

ALLOWED_TARGET_TYPES = frozenset({
    "test_channel",
    "test_group",
    "dry_run",
    "none",
})

MAX_PREVIEW_CHARS = 300


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _sha256_hex(text: str) -> str:
    """SHA-256 hex digest of a UTF-8 encoded string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════
# Dry-Run Result
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DryRunResult:
    """Standardized dry-run send result.

    Fields:
        card_type: Card type key.
        snapshot_id: The snapshot being sent.
        dry_run_status: "dry_run_sent" or "dry_run_blocked".
        dry_run_success: True if the dry-run completed without blocks.
        blocked_reason: If blocked, why.
        dry_run_message_id: Deterministic mock ID (e.g., "dryrun_v117_001").
        payload_hash: SHA-256 of the public_card text.
        payload_length: Length of public_card in characters.
        payload_preview: First MAX_PREVIEW_CHARS of public_card.
        target_type: The intended target type.
        target_alias: Human-readable target alias.
        network_called: Always False.
        real_tg_sent: Always False.
        production_send: Always False.
        credentials_printed: Always False.
        raw_secret_present: Always False.
        quality_gate_passed: Whether quality gate passed.
        send_readiness_passed: Whether send-readiness gate passed.
        dry_run_at: ISO timestamp.
    """
    card_type: str
    snapshot_id: str
    dry_run_status: str
    dry_run_success: bool
    blocked_reason: str | None = None
    dry_run_message_id: str = ""
    payload_hash: str = ""
    payload_length: int = 0
    payload_preview: str = ""
    target_type: str = "test_channel"
    target_alias: str = "market_radar_test_channel"
    network_called: bool = False
    real_tg_sent: bool = False
    production_send: bool = False
    credentials_printed: bool = False
    raw_secret_present: bool = False
    quality_gate_passed: bool = False
    send_readiness_passed: bool = False
    dry_run_at: str = field(default_factory=china_stamp)
    sender_version: str = DRY_RUN_VERSION

    def as_dict(self) -> dict:
        return {
            "card_type": self.card_type,
            "snapshot_id": self.snapshot_id,
            "dry_run_status": self.dry_run_status,
            "dry_run_success": self.dry_run_success,
            "blocked_reason": self.blocked_reason,
            "dry_run_message_id": self.dry_run_message_id,
            "payload_hash": self.payload_hash,
            "payload_length": self.payload_length,
            "payload_preview": self.payload_preview,
            "target_type": self.target_type,
            "target_alias": self.target_alias,
            "network_called": self.network_called,
            "real_tg_sent": self.real_tg_sent,
            "production_send": self.production_send,
            "credentials_printed": self.credentials_printed,
            "raw_secret_present": self.raw_secret_present,
            "quality_gate_passed": self.quality_gate_passed,
            "send_readiness_passed": self.send_readiness_passed,
            "dry_run_at": self.dry_run_at,
            "sender_version": self.sender_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════════════
# Dry-Run Sender
# ══════════════════════════════════════════════════════════════════════════════════════

class DryRunSender:
    """Local-only dry-run sender — proves the send pipeline without real TG.

    Key properties:
      - Deterministic: sequential mock message IDs.
      - Safe: blocks formal/prod targets, validates all inputs.
      - Observable: every dry_send produces an auditable DryRunResult.
      - Redacted: payload hashes only, no raw secrets.
      - Explicit: all flags (network_called, real_tg_sent, etc.) are False.
    """

    def __init__(self, counter_start: int = 1):
        """Initialize dry-run sender with a starting counter.

        Args:
            counter_start: First mock message ID sequence number.
        """
        self._counter = counter_start
        self._dry_sent_count = 0
        self._dry_blocked_count = 0
        self._dry_run_log: list[DryRunResult] = []

    @property
    def dry_sent_count(self) -> int:
        return self._dry_sent_count

    @property
    def dry_blocked_count(self) -> int:
        return self._dry_blocked_count

    @property
    def dry_run_log(self) -> list[DryRunResult]:
        return list(self._dry_run_log)

    def dry_send(
        self,
        public_card: str,
        quality_gate_result,
        send_readiness_result,
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
    ) -> DryRunResult:
        """Perform a dry-run send through the full validation pipeline.

        Args:
            public_card: The rendered public card text.
            quality_gate_result: QualityGateResult from the quality gate.
            send_readiness_result: SendReadinessResult from send-readiness gate.
            target_type: Must be in ALLOWED_TARGET_TYPES.
            target_alias: Human-readable target alias.

        Returns:
            DryRunResult with status, hash, preview, and safety flags.
        """
        card_type = getattr(quality_gate_result, "card_type", "unknown")
        snapshot_id = getattr(quality_gate_result, "snapshot_id", "unknown")

        # ── Check 1: Target type validation ────────────────────────────────────
        t = str(target_type).strip().lower()
        if t in BLOCKED_TARGET_TYPES:
            result = self._build_blocked(
                card_type=card_type,
                snapshot_id=snapshot_id,
                blocked_reason=f"target_type '{target_type}' is blocked (formal/prod)",
                target_type=target_type,
                target_alias=target_alias,
                quality_gate_passed=getattr(quality_gate_result, "quality_gate_passed", False),
                send_readiness_passed=send_readiness_result.send_ready,
                public_card=public_card,
            )
            self._dry_blocked_count += 1
            self._dry_run_log.append(result)
            return result

        if t not in ALLOWED_TARGET_TYPES:
            result = self._build_blocked(
                card_type=card_type,
                snapshot_id=snapshot_id,
                blocked_reason=f"target_type '{target_type}' not in allowed set",
                target_type=target_type,
                target_alias=target_alias,
                quality_gate_passed=getattr(quality_gate_result, "quality_gate_passed", False),
                send_readiness_passed=send_readiness_result.send_ready,
                public_card=public_card,
            )
            self._dry_blocked_count += 1
            self._dry_run_log.append(result)
            return result

        # ── Check 2: Quality gate must have passed ─────────────────────────────
        qg_passed = getattr(quality_gate_result, "quality_gate_passed", False)
        if not qg_passed:
            block_reason = getattr(quality_gate_result, "block_reason", "quality gate not passed")
            result = self._build_blocked(
                card_type=card_type,
                snapshot_id=snapshot_id,
                blocked_reason=f"Quality gate blocked: {block_reason}",
                target_type=target_type,
                target_alias=target_alias,
                quality_gate_passed=False,
                send_readiness_passed=send_readiness_result.send_ready,
                public_card=public_card,
            )
            self._dry_blocked_count += 1
            self._dry_run_log.append(result)
            return result

        # ── Check 3: Send-readiness must have passed ───────────────────────────
        if not send_readiness_result.send_ready:
            block_reason = send_readiness_result.blocked_reason or "send readiness not passed"
            result = self._build_blocked(
                card_type=card_type,
                snapshot_id=snapshot_id,
                blocked_reason=f"Send-readiness blocked: {block_reason}",
                target_type=target_type,
                target_alias=target_alias,
                quality_gate_passed=True,
                send_readiness_passed=False,
                public_card=public_card,
            )
            self._dry_blocked_count += 1
            self._dry_run_log.append(result)
            return result

        # ── Check 4: Public card must be non-empty ─────────────────────────────
        if not public_card or not public_card.strip():
            result = self._build_blocked(
                card_type=card_type,
                snapshot_id=snapshot_id,
                blocked_reason="public_card is empty",
                target_type=target_type,
                target_alias=target_alias,
                quality_gate_passed=True,
                send_readiness_passed=True,
                public_card=public_card,
            )
            self._dry_blocked_count += 1
            self._dry_run_log.append(result)
            return result

        # ── Generate dry-run message ID ─────────────────────────────────────────
        mock_id = f"dryrun_v117_{self._counter:03d}"
        self._counter += 1
        self._dry_sent_count += 1

        # ── Build result ───────────────────────────────────────────────────────
        payload_hash = _sha256_hex(public_card)
        preview = public_card[:MAX_PREVIEW_CHARS]

        result = DryRunResult(
            card_type=card_type,
            snapshot_id=snapshot_id,
            dry_run_status="dry_run_sent",
            dry_run_success=True,
            blocked_reason=None,
            dry_run_message_id=mock_id,
            payload_hash=payload_hash,
            payload_length=len(public_card),
            payload_preview=preview,
            target_type=target_type,
            target_alias=target_alias,
            network_called=False,
            real_tg_sent=False,
            production_send=False,
            credentials_printed=False,
            raw_secret_present=False,
            quality_gate_passed=True,
            send_readiness_passed=True,
        )

        self._dry_run_log.append(result)
        return result

    def dry_send_batch(
        self,
        cards: list[dict],
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
    ) -> list[DryRunResult]:
        """Dry-send a batch of cards.

        Args:
            cards: List of dicts with keys:
                   public_card, quality_gate_result, send_readiness_result.
            target_type: Must be in ALLOWED_TARGET_TYPES.
            target_alias: Human-readable alias.

        Returns:
            List of DryRunResult objects.
        """
        return [
            self.dry_send(
                public_card=c.get("public_card", ""),
                quality_gate_result=c.get("quality_gate_result"),
                send_readiness_result=c.get("send_readiness_result"),
                target_type=target_type,
                target_alias=target_alias,
            )
            for c in cards
        ]

    def reset_counter(self, start: int = 1) -> None:
        """Reset the dry-run message ID counter."""
        self._counter = start

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_blocked(
        self,
        card_type: str,
        snapshot_id: str,
        blocked_reason: str,
        target_type: str,
        target_alias: str,
        quality_gate_passed: bool,
        send_readiness_passed: bool,
        public_card: str = "",
    ) -> DryRunResult:
        """Build a blocked DryRunResult."""
        payload_hash = _sha256_hex(public_card) if public_card else ""
        preview = public_card[:MAX_PREVIEW_CHARS] if public_card else ""
        return DryRunResult(
            card_type=card_type,
            snapshot_id=snapshot_id,
            dry_run_status="dry_run_blocked",
            dry_run_success=False,
            blocked_reason=blocked_reason,
            dry_run_message_id="",
            payload_hash=payload_hash,
            payload_length=len(public_card) if public_card else 0,
            payload_preview=preview,
            target_type=target_type,
            target_alias=target_alias,
            network_called=False,
            real_tg_sent=False,
            production_send=False,
            credentials_printed=False,
            raw_secret_present=False,
            quality_gate_passed=quality_gate_passed,
            send_readiness_passed=send_readiness_passed,
        )


# ── Module-level convenience ────────────────────────────────────────────────────

def dry_send_card(
    public_card: str,
    quality_gate_result,
    send_readiness_result,
    target_type: str = "test_channel",
) -> DryRunResult:
    """Dry-send a single card (convenience function)."""
    sender = DryRunSender()
    return sender.dry_send(
        public_card=public_card,
        quality_gate_result=quality_gate_result,
        send_readiness_result=send_readiness_result,
        target_type=target_type,
    )


def create_dry_sender(counter_start: int = 1) -> DryRunSender:
    """Factory function — creates a fresh DryRunSender."""
    return DryRunSender(counter_start=counter_start)
