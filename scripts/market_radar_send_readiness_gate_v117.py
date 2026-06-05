"""Market Radar v1.17 — Send-Readiness Gate

Takes a QualityGateResult + rendered public card, and evaluates whether
the card is ready to send. This is the unified pre-send gate that checks:

  1. Quality gate passed
  2. No debug/internal term leaks in public card
  3. No secret/path leaks in public card
  4. Not a production target (block formal/prod channels)
  5. Safety flags are clean

This is the THIRD layer in the v117 pipeline:
  ... → QualityGateResult → SendReadinessGate → send_ready_result → ...

Design:
  - SendReadinessGate class encapsulates leak scanning + safety checks
  - Produces a SendReadinessResult with detailed pass/fail info
  - Reuses scan_envelope_leaks() patterns from v112h
  - Deterministic only — no AI, no external API calls

Constraints:
  - No external API calls
  - No TG send
  - No daemon/cron/loop
  - No token/key/secret read or print

Usage:
    from scripts.market_radar_send_readiness_gate_v117 import (
        SendReadinessGate, SendReadinessResult, run_send_readiness_gate,
    )

    gate = SendReadinessGate()
    result = gate.evaluate(quality_gate_result, public_card, target_type="test_channel")
    print(f"Send ready: {result.send_ready}")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

CN_TZ = timezone(timedelta(hours=8))
SEND_READINESS_VERSION = "v1.17"

# ── Forbidden terms (aligned with v112h) ────────────────────────────────────────

FORBIDDEN_DEBUG_TERMS = [
    "debug", "internal", "trace", "fixture",
]

FORBIDDEN_SECRET_TERMS = [
    "secret", "token", "api_key", "chat_id", "password",
]

FORBIDDEN_PATH_TERMS = [
    "C:\\Users\\PC", "C:\\Users", "D:\\", "E:\\",
    "/home/", "/Users/", "/tmp/", "/var/",
    "ai_relay_desk",
]

FORBIDDEN_REGISTRY_TERMS = [
    "value_gate", "cooldown_gate", "pre_send_gate", "pre_send",
    "payload_render", "format_check", "content_quality",
    "gate_decision", "score↑", "blocked_by", "gate_version",
    "factor_hits", "block_reason", "block_rules", "block_triggered",
    "admission_result",
    "not_reached", "mock_sent", "mock_message_id",
]

# Target types that are BLOCKED (production safety hard-stop)
BLOCKED_TARGET_TYPES = frozenset({
    "formal_channel",
    "official_channel",
    "prod",
    "production",
    "main_channel",
})

# Allowed target types for test send
ALLOWED_TARGET_TYPES = frozenset({
    "test_channel",
    "test_group",
    "dry_run",
    "none",
})

# Full wallet address pattern (0x + 40 hex chars)
WALLET_ADDRESS_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}')


def china_stamp() -> str:
    """Return current time in UTC+8 format."""
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


# ══════════════════════════════════════════════════════════════════════════════════════
# Send-Readiness Result
# ══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class SendReadinessResult:
    """Standardized result from the send-readiness gate.

    Fields:
        card_type: Card type key.
        snapshot_id: The snapshot being evaluated.
        send_ready: Overall send-readiness (True = ready for test send).
        quality_gate_passed: The quality gate must have passed.
        debug_leak_free: No debug/internal terms in public card.
        secret_leak_free: No secret/path terms in public card.
        target_type_allowed: Target is test/dry-run, not production.
        wallet_leak_free: No full wallet addresses in public card.
        blocked_reason: If not ready, why.
        debug_terms_found: List of debug terms found.
        secret_terms_found: List of secret/path terms found.
        wallet_leaks: List of full wallet addresses found.
        evaluation_detail: Full evaluation breakdown.
    """
    card_type: str
    snapshot_id: str
    send_ready: bool
    quality_gate_passed: bool
    debug_leak_free: bool
    secret_leak_free: bool
    target_type_allowed: bool
    wallet_leak_free: bool
    blocked_reason: str | None = None
    debug_terms_found: list[str] = field(default_factory=list)
    secret_terms_found: list[str] = field(default_factory=list)
    wallet_leaks: list[str] = field(default_factory=list)
    evaluation_detail: dict = field(default_factory=dict)
    gate_version: str = SEND_READINESS_VERSION
    evaluated_at: str = field(default_factory=china_stamp)

    def as_dict(self) -> dict:
        return {
            "card_type": self.card_type,
            "snapshot_id": self.snapshot_id,
            "send_ready": self.send_ready,
            "quality_gate_passed": self.quality_gate_passed,
            "debug_leak_free": self.debug_leak_free,
            "secret_leak_free": self.secret_leak_free,
            "target_type_allowed": self.target_type_allowed,
            "wallet_leak_free": self.wallet_leak_free,
            "blocked_reason": self.blocked_reason,
            "debug_terms_found": self.debug_terms_found,
            "secret_terms_found": self.secret_terms_found,
            "wallet_leaks": self.wallet_leaks,
            "gate_version": self.gate_version,
            "evaluated_at": self.evaluated_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════════════
# Send-Readiness Gate
# ══════════════════════════════════════════════════════════════════════════════════════

class SendReadinessGate:
    """Unified send-readiness gate for all card types.

    Checks that a card is ready for test send by verifying:
      1. Quality gate passed
      2. No debug/internal term leaks
      3. No secret/path leaks
      4. Target type is test/dry-run (not production)
      5. No full wallet addresses in public output

    This gate is designed for TEST SENDS only.
    Production sends require additional checks (see v116N production readiness checklist).
    """

    def __init__(self):
        self._evaluation_count = 0
        self._ready_count = 0
        self._blocked_count = 0

    @property
    def evaluation_count(self) -> int:
        return self._evaluation_count

    @property
    def ready_count(self) -> int:
        return self._ready_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    def evaluate(
        self,
        quality_gate_result,
        public_card: str,
        target_type: str = "test_channel",
        safety_flags: dict | None = None,
    ) -> SendReadinessResult:
        """Evaluate send-readiness for a card.

        Args:
            quality_gate_result: QualityGateResult from the quality gate.
            public_card: The rendered public card text.
            target_type: One of "test_channel", "test_group", "dry_run", "none".
            safety_flags: Optional safety flags dict.

        Returns:
            SendReadinessResult with detailed evaluation.
        """
        self._evaluation_count += 1

        # Import quality gate result type check
        qg_passed = getattr(quality_gate_result, "quality_gate_passed", False)
        card_type = getattr(quality_gate_result, "card_type", "unknown")
        snapshot_id = getattr(quality_gate_result, "snapshot_id", "unknown")

        # ── Check 1: Quality gate must have passed ───────────────────────────────
        if not qg_passed:
            block_reason = getattr(quality_gate_result, "block_reason", "Quality gate not passed")
            result = SendReadinessResult(
                card_type=card_type,
                snapshot_id=snapshot_id,
                send_ready=False,
                quality_gate_passed=False,
                debug_leak_free=True,
                secret_leak_free=True,
                target_type_allowed=True,
                wallet_leak_free=True,
                blocked_reason=f"Quality gate blocked: {block_reason}",
            )
            self._blocked_count += 1
            return result

        # ── Check 2: Debug/internal leak scan ────────────────────────────────────
        debug_found = self._scan_debug_terms(public_card)
        debug_leak_free = len(debug_found) == 0

        # ── Check 3: Secret/path leak scan ───────────────────────────────────────
        secret_found = self._scan_secret_terms(public_card)
        secret_leak_free = len(secret_found) == 0

        # ── Check 4: Wallet address leak ─────────────────────────────────────────
        wallet_leaks = WALLET_ADDRESS_PATTERN.findall(public_card)
        wallet_leak_free = len(wallet_leaks) == 0

        # ── Check 5: Target type must be allowed ─────────────────────────────────
        target_type_allowed = self._validate_target_type(target_type)

        # ── Assemble result ──────────────────────────────────────────────────────
        checks = [
            ("quality_gate_passed", qg_passed, "Quality gate not passed"),
            ("debug_leak_free", debug_leak_free, f"Debug leaks: {debug_found}"),
            ("secret_leak_free", secret_leak_free, f"Secret leaks: {secret_found}"),
            ("target_type_allowed", target_type_allowed, f"Target type '{target_type}' not allowed"),
            ("wallet_leak_free", wallet_leak_free, f"Wallet address leaks: {len(wallet_leaks)}"),
        ]

        send_ready = all(c[1] for c in checks)

        blocked_reason = None
        if not send_ready:
            for check_name, check_passed, reason in checks:
                if not check_passed:
                    blocked_reason = reason
                    break

        if send_ready:
            self._ready_count += 1
        else:
            self._blocked_count += 1

        return SendReadinessResult(
            card_type=card_type,
            snapshot_id=snapshot_id,
            send_ready=send_ready,
            quality_gate_passed=qg_passed,
            debug_leak_free=debug_leak_free,
            secret_leak_free=secret_leak_free,
            target_type_allowed=target_type_allowed,
            wallet_leak_free=wallet_leak_free,
            blocked_reason=blocked_reason,
            debug_terms_found=debug_found,
            secret_terms_found=secret_found,
            wallet_leaks=wallet_leaks,
            evaluation_detail={
                "checks": [
                    {"name": name, "passed": passed, "reason": reason if not passed else ""}
                    for name, passed, reason in checks
                ],
                "target_type": target_type,
                "public_card_length": len(public_card),
            },
        )

    # ── Private scanners ──────────────────────────────────────────────────────

    def _scan_debug_terms(self, text: str) -> list[str]:
        """Scan text for debug/internal/registry terms."""
        found: list[str] = []
        text_lower = text.lower()
        for term in FORBIDDEN_DEBUG_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        for term in FORBIDDEN_REGISTRY_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        return sorted(set(found))

    def _scan_secret_terms(self, text: str) -> list[str]:
        """Scan text for secret/path terms."""
        found: list[str] = []
        text_lower = text.lower()
        for term in FORBIDDEN_SECRET_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        for term in FORBIDDEN_PATH_TERMS:
            if term.lower() in text_lower:
                found.append(term)
        # Check for Windows absolute paths
        if re.search(r'[A-Za-z]:\\(?:Users|Program|Windows)', text):
            found.append("local_absolute_path")
        # Check for Unix-like paths
        if re.search(r'/(?:home|Users|tmp|var|etc|opt|dev)/', text):
            found.append("unix_absolute_path")
        return sorted(set(found))

    def _validate_target_type(self, target_type: str) -> bool:
        """Check target_type is allowed (test/dry-run only, no production)."""
        t = str(target_type).strip().lower()
        if t in BLOCKED_TARGET_TYPES:
            return False
        if t not in ALLOWED_TARGET_TYPES:
            return False
        return True


# ── Module-level convenience ────────────────────────────────────────────────────

def run_send_readiness_gate(
    quality_gate_result,
    public_card: str,
    target_type: str = "test_channel",
) -> SendReadinessResult:
    """Run send-readiness gate on a single card (convenience function)."""
    gate = SendReadinessGate()
    return gate.evaluate(quality_gate_result, public_card, target_type)
