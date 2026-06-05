"""Market Radar v1.11-N — SafeTelegramTestSender (safe single-card sender)

A safety-hardened Telegram sender that enforces:
  - target_type="test_channel" ONLY — blocks formal/official/prod
  - signal_id="H6-07" ONLY (this round)
  - asset="ARB" ONLY — blocks ETH
  - Max 1 card per send call
  - No .env file reading
  - No interactive input (Read-Host)
  - No printing or saving token/chat_id
  - Credentials from runtime environment only (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
  - Blocked with clear reason if credentials missing

Usage:
    from scripts.market_radar_safe_sender_v111n import SafeTelegramTestSender

    sender = SafeTelegramTestSender()
    result = sender.safe_send_single(
        payload_text="...",
        parse_mode="MarkdownV2",
        signal_id="H6-07",
        asset="ARB",
        target_type="test_channel",
    )
    if result["status"] == "sent":
        print(f"Sent: message_id={result['message_id']}")
    else:
        print(f"Blocked: {result['reason']}")
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
SAFE_SENDER_VERSION = "v1.11-n"

# ── Blocked target types ─────────────────────────────────────────────────────────
BLOCKED_TARGET_TYPES = frozenset({
    "formal_channel",
    "official_channel",
    "prod",
    "production",
    "main_channel",
})

# ── Allowed parse modes ──────────────────────────────────────────────────────────
VALID_PARSE_MODES = frozenset({
    "MarkdownV2",
    "Markdown",
    "HTML",
    None,
})

# ── Debug / gate terms that must NOT appear in public card text ──────────────────
# Note: "mock_message_id" and "mock_sent" are NOT in this set —
# they are checked separately in Gate 7 (mock_terms_in_payload)
# to produce a distinct block reason.
FORBIDDEN_DEBUG_TERMS = frozenset({
    "value_gate", "cooldown_gate", "pre_send_gate", "signal_trust_gate",
    "mock_v111j",
    "价值:", "冷却:", "安全:", "价值：", "冷却：", "安全：",
    "value:", "cooldown:", "upgrade_override",
    "allow",  # in gate context — detected by companion terms
    "block",  # gate context
    "debug_leak", "internal_",
    "token", "chat_id", "bot_token",
})

# ── Helpers ──────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """Return current ISO timestamp in CN_TZ."""
    return datetime.now(CN_TZ).isoformat()


def _sha256_hex(text: str) -> str:
    """Return SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _has_forbidden_terms(text: str) -> tuple[bool, list[str]]:
    """Check if text contains any forbidden debug/gate/secret terms.

    Returns (has_any, found_terms).
    """
    text_lower = text.lower()
    found = []
    for term in FORBIDDEN_DEBUG_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return len(found) > 0, found


# ── Safe Telegram Test Sender ────────────────────────────────────────────────────

class SafeTelegramTestSender:
    """Safety-hardened Telegram sender for test-channel delivery only.

    Security guarantees:
      - Only target_type="test_channel" is allowed
      - Only signal_id="H6-07" (this round)
      - Only asset="ARB" — ETH is blocked
      - Max 1 card per send call (safe_send_single)
      - No .env file reading
      - No interactive input (Read-Host)
      - Never prints or saves token/chat_id
      - Credentials from os.environ only
      - Blocked result if credentials missing (no crash, no prompt)
      - Debug/gate terms in payload trigger block

    Modes:
      - Real send: When TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID are set in env
      - Mock send: For testing without real credentials — always returns
        safe fake message_id with explicit mock marking
    """

    def __init__(self, http_client=None):
        """Initialize the safe sender.

        Args:
            http_client: Optional RealHttpClient for dependency injection (testing).
                         If None, will be created from env when needed for real send.
        """
        self._http_client = http_client
        self._sent_count = 0
        self._blocked_count = 0
        self._official_channel_touched = False
        self._secret_printed = False

    # ── Public properties ────────────────────────────────────────────────────

    @property
    def sent_count(self) -> int:
        return self._sent_count

    @property
    def blocked_count(self) -> int:
        return self._blocked_count

    # ── Credential loading (safe — no .env, no printing) ─────────────────────

    def _load_credentials(self) -> dict:
        """Load TG credentials from os.environ ONLY.

        Never reads .env files. Never prints or logs token/chat_id values.

        Returns:
            Dict with bot_token, chat_id, proxy_url (all str, may be empty).
        """
        return {
            "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
            "proxy_url": os.environ.get("TELEGRAM_PROXY_URL", None),
        }

    def _credentials_present(self, creds: dict) -> bool:
        """Check if both bot_token and chat_id are present (non-empty)."""
        return bool(creds.get("bot_token") and creds.get("chat_id"))

    # ── Main send method ─────────────────────────────────────────────────────

    def safe_send_single(
        self,
        payload_text: str,
        parse_mode: str | None,
        signal_id: str,
        asset: str,
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
        pre_send_gate_result: dict | None = None,
    ) -> dict:
        """Send exactly ONE card through the full safety validation pipeline.

        Args:
            payload_text: The rendered public card text (must be non-empty).
            parse_mode: TG parse_mode (MarkdownV2, HTML, None).
            signal_id: Must be "H6-07" (this round).
            asset: Must be "ARB" — ETH is blocked.
            target_type: Must be "test_channel".
            target_alias: Logical alias for logging.
            pre_send_gate_result: Optional pre_send_gate check result.

        Returns:
            Dict with keys:
              - status: "sent" | "blocked"
              - reason: str | None (blocked reason)
              - message_id: str (real TG message_id if sent, else "")
              - signal_id: str
              - asset: str
              - target_type: str
              - payload_text_sha256: str
              - payload_length: int
              - sent_at: str (ISO timestamp)
              - real_tg_sent: bool
              - official_channel_touched: bool
              - secret_printed: bool
              - sender_version: str
        """
        sent_at = _now_iso()

        # ── Gate 1: Target type MUST be test_channel ──
        if not target_type:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type or "(empty)",
                "missing_runtime_test_channel_credentials",
                "target_type is empty or None",
                sent_at, payload_text,
            )

        t = str(target_type).strip().lower()
        if t in BLOCKED_TARGET_TYPES:
            self._blocked_count += 1
            if t in ("formal_channel", "official_channel", "prod", "production"):
                self._official_channel_touched = True
            return self._build_blocked(
                signal_id, asset, target_type,
                "formal_channel_blocked",
                f"target_type '{target_type}' is blocked (formal/prod)",
                sent_at, payload_text,
            )

        if t != "test_channel":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "invalid_target_type",
                f"target_type '{target_type}' is not 'test_channel'",
                sent_at, payload_text,
            )

        # ── Gate 2: Asset MUST be ARB — ETH is blocked ──
        asset_upper = str(asset).strip().upper() if asset else ""
        if asset_upper == "ETH":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "eth_blocked",
                "ETH is blocked this round — only ARB H6-07 is allowed",
                sent_at, payload_text,
            )

        if asset_upper != "ARB":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "asset_not_allowed",
                f"asset '{asset}' is not in allowlist (only ARB this round)",
                sent_at, payload_text,
            )

        # ── Gate 3: Signal ID MUST be H6-07 ──
        if signal_id != "H6-07":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "signal_not_allowed",
                f"signal_id '{signal_id}' is not in allowlist (only H6-07 this round)",
                sent_at, payload_text,
            )

        # ── Gate 4: Payload validation ──
        if not payload_text or not isinstance(payload_text, str):
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "empty_payload",
                "payload_text is empty or not a string",
                sent_at, payload_text if isinstance(payload_text, str) else "",
            )

        if not payload_text.strip():
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "empty_payload",
                "payload_text is whitespace-only",
                sent_at, payload_text,
            )

        # ── Gate 5: Parse mode validation ──
        if parse_mode is not None and parse_mode not in VALID_PARSE_MODES:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "invalid_parse_mode",
                f"parse_mode '{parse_mode}' is not valid",
                sent_at, payload_text,
            )

        # ── Gate 6: Forbidden terms check ──
        has_forbidden, found_terms = _has_forbidden_terms(payload_text)
        if has_forbidden:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "debug_terms_in_payload",
                f"Payload contains forbidden terms: {found_terms}",
                sent_at, payload_text,
            )

        # ── Gate 7: mock_message_id / mock_sent must not appear ──
        payload_lower = payload_text.lower()
        if "mock_message_id" in payload_lower or "mock_sent" in payload_lower:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "mock_terms_in_payload",
                "Payload contains mock_message_id or mock_sent references",
                sent_at, payload_text,
            )

        # ── Gate 8: pre_send_gate check ──
        if pre_send_gate_result is not None:
            gate_decision = pre_send_gate_result.get("decision", "")
            if gate_decision != "pass":
                self._blocked_count += 1
                return self._build_blocked(
                    signal_id, asset, target_type,
                    "pre_send_gate_failed",
                    f"pre_send_gate decision={gate_decision}, expected=pass",
                    sent_at, payload_text,
                )

        # ── Gate 9: Credential check ──
        creds = self._load_credentials()
        if not self._credentials_present(creds):
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "missing_runtime_test_channel_credentials",
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in runtime environment",
                sent_at, payload_text,
            )

        # ── Send via real TG API ──
        send_result = self._do_real_send(payload_text, parse_mode, creds)

        if send_result["success"]:
            self._sent_count += 1
            return {
                "status": "sent",
                "reason": None,
                "message_id": str(send_result["message_id"]),
                "signal_id": signal_id,
                "asset": asset,
                "target_type": target_type,
                "payload_text_sha256": _sha256_hex(payload_text),
                "payload_length": len(payload_text),
                "sent_at": sent_at,
                "real_tg_sent": True,
                "official_channel_touched": False,
                "secret_printed": False,
                "sender_version": SAFE_SENDER_VERSION,
            }
        else:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                f"tg_send_failed: {send_result.get('error_type', 'UNKNOWN')}",
                f"TG API send failed: {send_result.get('error_message', '')[:200]}",
                sent_at, payload_text,
            )

    # ── Real send ────────────────────────────────────────────────────────────

    def _do_real_send(self, payload_text: str, parse_mode: str | None,
                      creds: dict) -> dict:
        """Perform real TG API send. Does NOT print token/chat_id."""
        try:
            from scripts.market_radar_sender import TGTransport, RealHttpClient
        except ImportError as e:
            return {
                "success": False,
                "message_id": "",
                "error_type": "IMPORT_ERROR",
                "error_message": f"Cannot import TGTransport: {e}",
            }

        bot_token = creds["bot_token"]
        chat_id = creds["chat_id"]
        proxy_url = creds.get("proxy_url")

        try:
            http_client = self._http_client
            if http_client is None:
                http_client = RealHttpClient(
                    timeout=10,
                    proxy_url=proxy_url if proxy_url else None,
                )

            transport = TGTransport(
                bot_token=bot_token,
                default_chat_id=chat_id,
                http_client=http_client,
                timeout_seconds=10,
            )

            payload = {
                "text": payload_text,
                "parse_mode": parse_mode or "MarkdownV2",
                "disable_web_page_preview": True,
                "char_count": len(payload_text),
                "has_html_tags": False,
            }

            result = transport.send(payload, "test_group", parse_mode or "MarkdownV2")

            return {
                "success": result.success,
                "message_id": result.message_id if result.success else "",
                "error_type": result.error_type,
                "error_message": result.error_message or "",
                "status_code": getattr(result, "status_code", 0),
            }

        except Exception as e:
            return {
                "success": False,
                "message_id": "",
                "error_type": type(e).__name__,
                "error_message": str(e),
            }

    # ── Mock send (for testing without credentials) ──────────────────────────

    def mock_send_single(
        self,
        payload_text: str,
        parse_mode: str | None,
        signal_id: str,
        asset: str,
        target_type: str = "test_channel",
        target_alias: str = "market_radar_test_channel",
        pre_send_gate_result: dict | None = None,
    ) -> dict:
        """Test-only mock send — validates everything but never calls TG API.

        Passes through the exact same validation gates as safe_send_single,
        but skips credential check and real network call. Returns a fake
        message_id with explicit mock_ marking — does NOT impersonate real send.

        Returns:
            Dict with same shape as safe_send_single, plus:
              - real_tg_sent: False (always)
              - mock_mode: True
              - mock_message_id: str (deterministic, mock_v111n_XXX)
        """
        sent_at = _now_iso()

        # Reuse validation via internal check — but without credential gate
        # Target check
        if not target_type:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type or "(empty)",
                "missing_runtime_test_channel_credentials",
                "target_type is empty or None",
                sent_at, payload_text,
            )

        t = str(target_type).strip().lower()
        if t in BLOCKED_TARGET_TYPES:
            self._blocked_count += 1
            if t in ("formal_channel", "official_channel", "prod", "production"):
                self._official_channel_touched = True
            return self._build_blocked(
                signal_id, asset, target_type,
                "formal_channel_blocked",
                f"target_type '{target_type}' is blocked (formal/prod)",
                sent_at, payload_text,
            )

        if t != "test_channel":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "invalid_target_type",
                f"target_type '{target_type}' is not 'test_channel'",
                sent_at, payload_text,
            )

        # Asset check
        asset_upper = str(asset).strip().upper() if asset else ""
        if asset_upper == "ETH":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "eth_blocked",
                "ETH is blocked this round — only ARB H6-07 is allowed",
                sent_at, payload_text,
            )

        if asset_upper != "ARB":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "asset_not_allowed",
                f"asset '{asset}' is not in allowlist (only ARB this round)",
                sent_at, payload_text,
            )

        # Signal ID check
        if signal_id != "H6-07":
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "signal_not_allowed",
                f"signal_id '{signal_id}' is not in allowlist (only H6-07 this round)",
                sent_at, payload_text,
            )

        # Payload validation
        if not payload_text or not isinstance(payload_text, str):
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "empty_payload",
                "payload_text is empty or not a string",
                sent_at, "",
            )

        if not payload_text.strip():
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "empty_payload",
                "payload_text is whitespace-only",
                sent_at, payload_text,
            )

        # Parse mode
        if parse_mode is not None and parse_mode not in VALID_PARSE_MODES:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "invalid_parse_mode",
                f"parse_mode '{parse_mode}' is not valid",
                sent_at, payload_text,
            )

        # Forbidden terms
        has_forbidden, found_terms = _has_forbidden_terms(payload_text)
        if has_forbidden:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "debug_terms_in_payload",
                f"Payload contains forbidden terms: {found_terms}",
                sent_at, payload_text,
            )

        # Mock terms
        payload_lower = payload_text.lower()
        if "mock_message_id" in payload_lower or "mock_sent" in payload_lower:
            self._blocked_count += 1
            return self._build_blocked(
                signal_id, asset, target_type,
                "mock_terms_in_payload",
                "Payload contains mock_message_id or mock_sent references",
                sent_at, payload_text,
            )

        # pre_send_gate
        if pre_send_gate_result is not None:
            gate_decision = pre_send_gate_result.get("decision", "")
            if gate_decision != "pass":
                self._blocked_count += 1
                return self._build_blocked(
                    signal_id, asset, target_type,
                    "pre_send_gate_failed",
                    f"pre_send_gate decision={gate_decision}, expected=pass",
                    sent_at, payload_text,
                )

        # All validations passed — generate mock message_id
        mock_id = f"mock_v111n_{self._sent_count + self._blocked_count + 1:03d}"
        self._sent_count += 1

        return {
            "status": "sent",
            "reason": None,
            "message_id": mock_id,
            "signal_id": signal_id,
            "asset": asset,
            "target_type": target_type,
            "payload_text_sha256": _sha256_hex(payload_text),
            "payload_length": len(payload_text),
            "sent_at": sent_at,
            "real_tg_sent": False,
            "mock_mode": True,
            "mock_message_id": mock_id,
            "official_channel_touched": False,
            "secret_printed": False,
            "sender_version": SAFE_SENDER_VERSION,
        }

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_blocked(
        self,
        signal_id: str,
        asset: str,
        target_type: str,
        reason: str,
        detail: str,
        sent_at: str,
        payload_text: str = "",
    ) -> dict:
        """Build a standard blocked result dict."""
        return {
            "status": "blocked",
            "reason": reason,
            "detail": detail,
            "message_id": "",
            "signal_id": signal_id,
            "asset": asset,
            "target_type": target_type,
            "payload_text_sha256": _sha256_hex(payload_text) if payload_text else "",
            "payload_length": len(payload_text) if payload_text else 0,
            "sent_at": sent_at,
            "real_tg_sent": False,
            "official_channel_touched": self._official_channel_touched,
            "secret_printed": self._secret_printed,
            "sender_version": SAFE_SENDER_VERSION,
        }


# ── Module-level convenience ────────────────────────────────────────────────────

def create_safe_sender(http_client=None) -> SafeTelegramTestSender:
    """Factory function — creates a fresh SafeTelegramTestSender."""
    return SafeTelegramTestSender(http_client=http_client)
