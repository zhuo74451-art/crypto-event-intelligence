from __future__ import annotations

import re
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional


# ── Redaction Helper ──────────────────────────────────────────────────────


class RedactionHelper:
    """Utility for masking sensitive data in strings."""

    _SENSITIVE_PATTERNS: list[re.Pattern] = [
        re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"(?i)(token|secret|password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE),
        re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
        re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})"),  # OpenAI-style keys
        re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36})"),  # GitHub PAT
        re.compile(r"(?i)(gho_[a-zA-Z0-9]{36})"),  # GitHub OAuth
        re.compile(r"(?i)(ghu_[a-zA-Z0-9]{36})"),  # GitHub user token
        re.compile(r"(?i)(xox[abpors]-[a-zA-Z0-9\-]{10,})"),  # Slack tokens
        re.compile(r"(?i)(AKIA[0-9A-Z]{16})"),  # AWS access key
    ]

    @staticmethod
    def redact_sensitive(text: str) -> str:
        """Replace recognised credential patterns with ``[REDACTED]``."""
        for pattern in RedactionHelper._SENSITIVE_PATTERNS:
            text = pattern.sub(r"\1[REDACTED]", text)
        return text


# ── Envelope ──────────────────────────────────────────────────────────────


@dataclass
class NotificationEnvelope:
    """A self-contained notification payload.

    Must **not** contain raw API keys, tokens, or full raw evidence in any
    field. Use :meth:`redact` to strip sensitive content before sending.
    """
    title: str
    body: str
    source_id: str = ""
    observation_ids: list[str] = field(default_factory=list)
    severity: str = "info"
    max_length: int = 4096

    def redact(self) -> NotificationEnvelope:
        """Return a copy with sensitive fields masked."""
        return NotificationEnvelope(
            title=RedactionHelper.redact_sensitive(self.title),
            body=RedactionHelper.redact_sensitive(self.body),
            source_id=self.source_id,
            observation_ids=list(self.observation_ids),
            severity=self.severity,
            max_length=self.max_length,
        )


# ── Protocol ──────────────────────────────────────────────────────────────


class NotificationClientProtocol(ABC):
    """Abstract interface for an Apprise notification client."""

    @abstractmethod
    def send_notification(self, envelope: NotificationEnvelope) -> bool:
        """Deliver *envelope* and return ``True`` on success."""
        ...


# ── Dry-run client ────────────────────────────────────────────────────────


class DryRunNotificationClient(NotificationClientProtocol):
    """Logs notifications to *stdout* and records them for test inspection.

    Does **not** read any credentials and does **not** send to any external
    service.
    """

    def __init__(self) -> None:
        self._sent: list[NotificationEnvelope] = []

    def send_notification(self, envelope: NotificationEnvelope) -> bool:
        self._sent.append(envelope)
        print(
            f"[DryRun] severity={envelope.severity} "
            f"source_id={envelope.source_id} "
            f"title={envelope.title!r}"
        )
        return True

    @property
    def sent_notifications(self) -> list[NotificationEnvelope]:
        """Return all envelopes sent so far (useful for test assertions)."""
        return list(self._sent)

    def reset(self) -> None:
        """Clear the recorded notification list."""
        self._sent.clear()
