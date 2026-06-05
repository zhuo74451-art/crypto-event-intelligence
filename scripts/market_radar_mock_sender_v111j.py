"""Market Radar v1.11-J-Mock — MockTelegramSender (no network, no secrets)

A drop-in mock sender that simulates Telegram sending without:
  - Reading environment variables
  - Reading .env files
  - Making network requests
  - Calling Telegram API
  - Accepting real tokens / chat_ids

Purpose:
  Verify the full send logic pipeline (SignalValueGate → CooldownGate →
  payload render → pre_send_gate → mock_sender → sent log) closes correctly
  before introducing real credentials.

Security:
  - Does NOT read, print, or save any token / chat_id / key / cookie / password.
  - Does NOT access environment variables for credentials.
  - Does NOT make network calls.
  - Blocks formal_channel / official_channel / prod / production / main_channel.

Usage:
    from scripts.market_radar_mock_sender_v111j import MockTelegramSender

    sender = MockTelegramSender(counter_start=1)
    result = sender.mock_send(
        payload_text="Hello World",
        parse_mode="MarkdownV2",
        signal_id="H6-07",
        asset="ARB",
        target_type="test_channel",
        target_alias="market_radar_test_channel",
        pre_send_gate_result={"decision": "pass"},
    )
    print(result["mock_message_id"])  # mock_v111j_001
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))

MOCK_SENDER_VERSION = "v1.11-j"

# Target types that are BLOCKED (safety hard-stop)
BLOCKED_TARGET_TYPES = frozenset({
    "formal_channel",
    "official_channel",
    "prod",
    "production",
    "main_channel",
})

# Allowed parse modes for TG
VALID_PARSE_MODES = frozenset({
    "MarkdownV2",
    "Markdown",
    "HTML",
    None,
})

# Max cards per send batch
MAX_CARDS_PER_SEND = 3

# Max payload preview characters
MAX_PREVIEW_CHARS = 300


def _now_iso() -> str:
    """Return current ISO timestamp in CN_TZ."""
    return datetime.now(CN_TZ).isoformat()


def _sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class MockTelegramSender:
    """Mock Telegram sender — proves the send pipeline without real TG.

    Key properties:
      - Deterministic: generates sequential mock_message_id values.
      - Safe: blocks formal/prod targets, validates payloads.
      - Observable: logs every send with payload hash + preview (no secrets).
    """

    def __init__(self, counter_start: int = 1):
        """Initialize the mock sender with a starting counter.

        Args:
            counter_start: First mock_message_id sequence number (default 1).
        """
        self._counter = counter_start
        self._sent_count = 0
        self._blocked_count = 0
        self._sent_log: list[dict[str, Any]] = []

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def sent_count(self) -> int:
        return self._sent_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    @property
    def sent_log(self) -> list[dict[str, Any]]:
        return list(self._sent_log)

    def mock_send(
        self,
        payload_text: str,
        parse_mode: str | None,
        signal_id: str,
        asset: str,
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
        pre_send_gate_result: dict | None = None,
        image_count: int = 0,
    ) -> dict:
        """Mock-send a card through the full validation pipeline.

        Args:
            payload_text: The rendered card text.
            parse_mode: TG parse_mode (MarkdownV2, HTML, None).
            signal_id: Signal identifier (e.g., "H6-07").
            asset: Asset symbol (e.g., "ARB").
            target_type: Must be "test_channel" — anything else is blocked.
            target_alias: Logical alias (e.g., "market_radar_test_channel").
            pre_send_gate_result: Result from pre_send_gate (must contain decision="pass").
            image_count: Number of images in the payload (max 3).

        Returns:
            Dict with keys:
              - success: bool
              - mock_message_id: str (deterministic, e.g., "mock_v111j_001")
              - send_status: str ("mock_sent" or "blocked")
              - blocked_reason: str | None
              - payload_text_sha256: str
              - payload_length: int
              - payload_preview: str (max 300 chars)
              - network_called: bool (always False)
              - real_tg_sent: bool (always False)
              - target_type: str
              - target_alias: str
              - signal_id: str
              - asset: str
              - sent_at: str (ISO timestamp)
        """
        sent_at = _now_iso()

        # ── Validation Layer 1: Target type ──
        target_check = self._validate_target(target_type)
        if not target_check["valid"]:
            self._blocked_count += 1
            return self._build_blocked_result(
                signal_id=signal_id,
                asset=asset,
                target_type=target_type,
                target_alias=target_alias,
                blocked_reason=target_check["reason"],
                sent_at=sent_at,
                payload_text=payload_text,
            )

        # ── Validation Layer 2: Payload ⊤ ──
        payload_check = self._validate_payload(payload_text, parse_mode)
        if not payload_check["valid"]:
            self._blocked_count += 1
            return self._build_blocked_result(
                signal_id=signal_id,
                asset=asset,
                target_type=target_type,
                target_alias=target_alias,
                blocked_reason=payload_check["reason"],
                sent_at=sent_at,
                payload_text=payload_text,
            )

        # ── Validation Layer 3: pre_send_gate ──
        if pre_send_gate_result is not None:
            gate_decision = pre_send_gate_result.get("decision", "")
            if gate_decision != "pass":
                self._blocked_count += 1
                return self._build_blocked_result(
                    signal_id=signal_id,
                    asset=asset,
                    target_type=target_type,
                    target_alias=target_alias,
                    blocked_reason=f"pre_send_gate decision={gate_decision}, expected=pass",
                    sent_at=sent_at,
                    payload_text=payload_text,
                )

        # ── Validation Layer 4: Image count ──
        if image_count > MAX_CARDS_PER_SEND:
            self._blocked_count += 1
            return self._build_blocked_result(
                signal_id=signal_id,
                asset=asset,
                target_type=target_type,
                target_alias=target_alias,
                blocked_reason=f"image_count={image_count} exceeds max={MAX_CARDS_PER_SEND}",
                sent_at=sent_at,
                payload_text=payload_text,
            )

        # ── Generate mock_message_id ──
        mock_id = f"mock_v111j_{self._counter:03d}"
        self._counter += 1
        self._sent_count += 1

        # ── Build result ──
        payload_hash = _sha256_hex(payload_text)
        preview = payload_text[:MAX_PREVIEW_CHARS] if payload_text else ""

        result = {
            "success": True,
            "mock_message_id": mock_id,
            "send_status": "mock_sent",
            "blocked_reason": None,
            "payload_text_sha256": payload_hash,
            "payload_length": len(payload_text) if payload_text else 0,
            "payload_preview": preview,
            "network_called": False,
            "real_tg_sent": False,
            "target_type": target_type,
            "target_alias": target_alias,
            "signal_id": signal_id,
            "asset": asset,
            "parse_mode": parse_mode,
            "sent_at": sent_at,
            "sender_version": MOCK_SENDER_VERSION,
        }

        # ── Log ──
        self._sent_log.append(result)

        return result

    def mock_send_batch(
        self,
        cards: list[dict],
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
    ) -> dict:
        """Mock-send a batch of cards.

        Args:
            cards: List of card dicts, each with keys:
                   payload_text, parse_mode, signal_id, asset,
                   pre_send_gate_result (optional), image_count (optional).
            target_type: Must be "test_channel".
            target_alias: Logical alias.

        Returns:
            Dict with keys: results (list), sent_count, blocked_count.
        """
        if len(cards) > MAX_CARDS_PER_SEND:
            return {
                "success": False,
                "results": [],
                "sent_count": 0,
                "blocked_count": len(cards),
                "blocked_reason": f"batch size={len(cards)} exceeds max={MAX_CARDS_PER_SEND}",
                "network_called": False,
                "real_tg_sent": False,
            }

        results = []
        for card in cards:
            result = self.mock_send(
                payload_text=card.get("payload_text", ""),
                parse_mode=card.get("parse_mode"),
                signal_id=card.get("signal_id", "?"),
                asset=card.get("asset", "?"),
                target_type=target_type,
                target_alias=target_alias,
                pre_send_gate_result=card.get("pre_send_gate_result"),
                image_count=card.get("image_count", 0),
            )
            results.append(result)

        return {
            "success": all(r["success"] for r in results),
            "results": results,
            "sent_count": sum(1 for r in results if r["send_status"] == "mock_sent"),
            "blocked_count": sum(1 for r in results if r["send_status"] == "blocked"),
            "network_called": False,
            "real_tg_sent": False,
        }

    def reset_counter(self, start: int = 1) -> None:
        """Reset the mock_message_id counter."""
        self._counter = start

    # ── Private validation ──────────────────────────────────────────────────

    def _validate_target(self, target_type: str) -> dict:
        """Validate target_type is allowed.

        Returns dict with valid (bool) and reason (str|None).
        """
        if not target_type:
            return {"valid": False, "reason": "target_type is empty or None"}
        t = str(target_type).strip().lower()
        if t in BLOCKED_TARGET_TYPES:
            return {"valid": False, "reason": f"target_type '{target_type}' is blocked (formal/prod)"}
        if t != "test_channel":
            return {"valid": False, "reason": f"target_type '{target_type}' is not 'test_channel'"}
        return {"valid": True, "reason": None}

    def _validate_payload(self, payload_text: str, parse_mode: str | None) -> dict:
        """Validate payload_text and parse_mode.

        Returns dict with valid (bool) and reason (str|None).
        """
        # Text must be non-empty
        if not payload_text or not isinstance(payload_text, str):
            return {"valid": False, "reason": "payload_text is empty or not a string"}
        if not payload_text.strip():
            return {"valid": False, "reason": "payload_text is whitespace-only"}
        if len(payload_text) == 0:
            return {"valid": False, "reason": "payload_text length is 0"}

        # Parse mode must be valid
        if parse_mode is not None and parse_mode not in VALID_PARSE_MODES:
            return {
                "valid": False,
                "reason": f"parse_mode '{parse_mode}' is not valid (allowed: {sorted(VALID_PARSE_MODES - {None})})",
            }

        return {"valid": True, "reason": None}

    def _build_blocked_result(
        self,
        signal_id: str,
        asset: str,
        target_type: str,
        target_alias: str,
        blocked_reason: str,
        sent_at: str,
        payload_text: str = "",
    ) -> dict:
        """Build a standard blocked result dict."""
        payload_hash = _sha256_hex(payload_text) if payload_text else ""
        preview = payload_text[:MAX_PREVIEW_CHARS] if payload_text else ""
        return {
            "success": False,
            "mock_message_id": "",
            "send_status": "blocked",
            "blocked_reason": blocked_reason,
            "payload_text_sha256": payload_hash,
            "payload_length": len(payload_text) if payload_text else 0,
            "payload_preview": preview,
            "network_called": False,
            "real_tg_sent": False,
            "target_type": target_type,
            "target_alias": target_alias,
            "signal_id": signal_id,
            "asset": asset,
            "parse_mode": None,
            "sent_at": sent_at,
            "sender_version": MOCK_SENDER_VERSION,
        }


# ── Module-level convenience ────────────────────────────────────────────────────

def create_mock_sender(counter_start: int = 1) -> MockTelegramSender:
    """Factory function — creates a fresh MockTelegramSender."""
    return MockTelegramSender(counter_start=counter_start)


def validate_mock_send_input(
    payload_text: str,
    parse_mode: str | None,
    target_type: str,
    pre_send_gate_result: dict | None = None,
    image_count: int = 0,
) -> dict:
    """Standalone input validation (stateless, for testing).

    Returns dict with valid (bool) and reason (str|None).
    """
    sender = MockTelegramSender()
    target_check = sender._validate_target(target_type)
    if not target_check["valid"]:
        return target_check

    payload_check = sender._validate_payload(payload_text, parse_mode)
    if not payload_check["valid"]:
        return payload_check

    if pre_send_gate_result is not None:
        gate_decision = pre_send_gate_result.get("decision", "")
        if gate_decision != "pass":
            return {"valid": False, "reason": f"pre_send_gate decision={gate_decision}, expected=pass"}

    if image_count > MAX_CARDS_PER_SEND:
        return {"valid": False, "reason": f"image_count={image_count} exceeds max={MAX_CARDS_PER_SEND}"}

    return {"valid": True, "reason": None}
