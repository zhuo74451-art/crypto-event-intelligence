"""Market Radar v117 — Sender Contract (Shared Pipeline).

TGTestGroupSender: sends rendered cards to TG test group.

Requirements:
  - Only test group allowed
  - Reuse existing safe TG test send tools from project
  - Never print token/chat_id/message_id plaintext
  - Output redacted result
  - production_send must be False
  - If safe TG config is missing, output tg_test_send_skipped_missing_safe_config
    and do NOT fail the entire pipeline

v117F: Enhanced network failure classification with granular error types:
  network_timeout, dns_error, connection_refused, proxy_required_or_unreachable,
  http_status_error, unknown_transport_error.
  Proxy env detection records boolean presence only (no proxy address logging).
"""

from __future__ import annotations

import hashlib
import os
import socket
from typing import Any, Optional

from market_radar.shared.models import (
    RenderedCard,
    SendReadinessDecision,
    TGTestSendResult,
    china_now,
    PIPELINE_VERSION,
    sha256_short,
)

# v117F: Granular network failure types
NETWORK_ERROR_CLASSIFICATIONS = [
    "network_timeout",
    "dns_error",
    "connection_refused",
    "proxy_required_or_unreachable",
    "http_status_error",
    "unknown_transport_error",
]

# v117F: Proxy environment variable names (presence only, never log values)
PROXY_ENV_VARS = ["HTTP_PROXY", "HTTPS_PROXY", "TELEGRAM_PROXY_URL", "ALL_PROXY"]


def _detect_proxy_env() -> dict[str, bool]:
    """Detect proxy environment variables. Returns boolean presence ONLY.

    NEVER logs or saves proxy addresses/URLs — only True/False per var.
    """
    result = {}
    for var in PROXY_ENV_VARS:
        val = os.environ.get(var, "")
        result[var] = bool(val and val.strip())
    result["any_proxy_detected"] = any(v for k, v in result.items() if k != "any_proxy_detected")
    return result


def _classify_network_error(error_message: str) -> str:
    """Classify a network error into a granular failure type.

    Examines the error message string for DNS, connection, timeout,
    and proxy-related keywords. Never examines raw credentials.
    """
    msg_lower = error_message.lower()

    # Check for proxy-specific indicators
    if any(kw in msg_lower for kw in ["proxy", "socks", "tunnel", "407"]):
        return "proxy_required_or_unreachable"

    # Check for DNS resolution failures
    if any(kw in msg_lower for kw in ["dns", "getaddrinfo", "name resolution",
                                        "nodename nor servname", "no address",
                                        "unknown host", "resolve", "gai_error"]):
        return "dns_error"

    # Check for connection refused (server reachable but rejecting)
    if any(kw in msg_lower for kw in ["connection refused", "refused", "errno 61",
                                        "errno 111", "ecONNRESET",
                                        "cannot connect to host"]):
        return "connection_refused"

    # Check for timeout (distinct from DNS/connect)
    if any(kw in msg_lower for kw in ["timeout", "timed out", "time out",
                                        "ssl: wrong_version"]):
        return "network_timeout"

    # Check for HTTP status errors embedded in message
    if any(kw in msg_lower for kw in ["http error", "status code", "403", "404",
                                        "500", "502", "503", "504"]):
        return "http_status_error"

    return "unknown_transport_error"


def _redact_url_host(url: str) -> str:
    """Return only the host[:port] of a URL, redacted of any token/path parts.

    Example: 'https://api.telegram.org/botTOKEN/sendMessage' → 'api.telegram.org'
    """
    if not url:
        return "unknown"
    # Simple extraction: just the hostname
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or "unknown"
        if parsed.port and parsed.port not in (443, 80):
            host = f"{host}:{parsed.port}"
        return host
    except Exception:
        # Fallback: return first segment after protocol
        parts = url.replace("https://", "").replace("http://", "").split("/")[0]
        return parts[:60]  # Safe truncation


class TGTestGroupSender:
    """Sends cards to TG test group using safe project-internal tools.

    CRITICAL SAFETY:
      - Only sends to test_group target
      - Never prints or logs raw token/chat_id/message_id
      - All outputs are redacted (SHA-256 fingerprints only)
      - production_send is always False
      - If env vars are missing, returns skipped (not failed)

    v117F: Enhanced network failure classification. Detects proxy env presence
    (boolean only). Classifies failures into granular types: network_timeout,
    dns_error, connection_refused, proxy_required_or_unreachable,
    http_status_error, unknown_transport_error.
    """

    def __init__(self):
        self._version = PIPELINE_VERSION

    def _read_credentials(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Read TG credentials from environment (safe pattern — boolean presence only).

        NEVER prints, logs, or stores raw values. Values stay in local scope only.
        Returns (bot_token, chat_id, proxy_url) or (None, None, None).
        """
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        proxy_url = os.environ.get("TELEGRAM_PROXY_URL", None)
        return (
            bot_token if bot_token else None,
            chat_id if chat_id else None,
            proxy_url,
        )

    def _check_safe_config(self) -> tuple[bool, str]:
        """Check if safe TG config is available. Returns (ready, reason)."""
        bot_token, chat_id, _ = self._read_credentials()
        if not bot_token or not chat_id:
            return False, "tg_test_send_skipped_missing_safe_config: TELEGRAM_BOT_TOKEN and/or TELEGRAM_CHAT_ID not set"
        return True, "safe_config_available"

    def _build_network_diagnostics(
        self,
        error_msg: str,
        timeout_secs: int,
    ) -> dict[str, Any]:
        """Build redacted network diagnostic info.

        NEVER includes raw token, chat_id, proxy address, or URL path.
        Only records: error_class, redacted_host, timeout_secs, proxy_detected (bool).
        """
        proxy_env = _detect_proxy_env()
        error_class = _classify_network_error(error_msg)

        return {
            "network_error_class": error_class,
            "redacted_api_host": "api.telegram.org",
            "timeout_seconds": timeout_secs,
            "proxy_env_detected": proxy_env["any_proxy_detected"],
            "proxy_env_vars_set": [k for k, v in proxy_env.items()
                                   if v and k != "any_proxy_detected"],
            "diagnostics_redacted": True,
            "error_excerpt": error_msg[:120] if error_msg else "",
        }

    def send(
        self,
        card: RenderedCard,
        readiness: SendReadinessDecision,
        parse_mode: Optional[str] = "HTML",
    ) -> TGTestSendResult:
        """Attempt to send a rendered card to TG test group.

        Args:
            card: Rendered card to send.
            readiness: Send-readiness decision.
            parse_mode: TG parse_mode. Default "HTML" for backward compatibility.
                Pass None or "" for plain text (no HTML/MarkdownV2 parsing).
                Pass "HTML" or "MarkdownV2" for formatted messages.

        Returns TGTestSendResult with all sensitive data redacted.
        Never raises — all errors become result entries.
        """
        # Pre-check: test group only
        if not readiness.allow_test_group:
            return TGTestSendResult(
                attempted=False,
                success=False,
                status="blocked",
                reason=f"Send-readiness gate blocked test_group send: {readiness.reason}",
                target_type="test_group",
                one_shot=True,
                production_send=False,
            )

        # Check safe config
        safe_ready, safe_reason = self._check_safe_config()
        if not safe_ready:
            return TGTestSendResult(
                attempted=False,
                success=False,
                status="skipped",
                reason=safe_reason,
                target_type="test_group",
                one_shot=True,
                production_send=False,
                credentials_printed=False,
            )

        bot_token, chat_id, proxy_url = self._read_credentials()
        if not bot_token or not chat_id:
            return TGTestSendResult(
                attempted=False,
                success=False,
                status="skipped",
                reason="tg_test_send_skipped_missing_safe_config",
                target_type="test_group",
                one_shot=True,
                production_send=False,
            )

        # Compute redacted proofs BEFORE any send attempt
        token_proof = sha256_short(bot_token) if bot_token else None
        chat_id_proof = sha256_short(chat_id) if chat_id else None

        # Attempt to use the existing project sender
        try:
            from scripts.market_radar_sender import TGTransport, RealHttpClient

            if proxy_url:
                http_client = RealHttpClient(timeout=10, proxy_url=proxy_url)
            else:
                http_client = RealHttpClient(timeout=10)

            transport = TGTransport(
                bot_token=bot_token,
                default_chat_id=chat_id,
                http_client=http_client,
                timeout_seconds=10,
            )

            # v118C: support plain text mode — when parse_mode is None
            # or empty, OMIT parse_mode from the TG API request body
            # entirely. Telegram treats messages without parse_mode as
            # plain text and renders emoji/Unicode natively without
            # HTML entity parsing. This avoids the v118B "Bad Request:
            # can't parse entities" error.
            use_plain_text = not parse_mode

            if use_plain_text:
                # Plain text: send directly without parse_mode field
                # (TGTransport always inserts parse_mode, so we go
                # direct via the HTTP client for plain text mode)
                import requests as _requests
                api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                request_body = {
                    "chat_id": chat_id,
                    "text": card.full_text,
                    "disable_web_page_preview": True,
                    # NO parse_mode — TG defaults to plain text
                }
                # Build redacted preview for diagnostics
                _req_preview = {
                    "chat_id_redacted": sha256_short(chat_id) if chat_id else None,
                    "text_length": len(card.full_text),
                    "parse_mode": None,
                    "disable_web_page_preview": True,
                }
                try:
                    http_resp = _requests.post(
                        api_url, json=request_body, timeout=10,
                    )
                    _status = http_resp.status_code
                    _body = http_resp.json() if http_resp.text else {}
                except Exception as _e:
                    _status = 0
                    _e_str = str(_e)
                    if bot_token and bot_token in _e_str:
                        _e_str = _e_str.replace(bot_token, "[REDACTED_TOKEN]")
                    _body = {"ok": False, "description": f"{type(_e).__name__}: {_e_str[:200]}"}

                if _status == 200 and _body.get("ok") is True:
                    _result_data = _body.get("result", {})
                    _mid = str(_result_data.get("message_id", ""))
                    message_id_proof = sha256_short(_mid) if _mid else None
                    return TGTestSendResult(
                        attempted=True,
                        success=True,
                        status="sent",
                        reason="TG test group one-shot sent successfully (plain text, no parse_mode)",
                        target_type="test_group",
                        one_shot=True,
                        production_send=False,
                        message_id_proof=message_id_proof,
                        token_proof=token_proof,
                        chat_id_proof=chat_id_proof,
                        credentials_printed=False,
                    )
                else:
                    error_desc = _body.get("description", f"HTTP {_status}")
                    if bot_token and bot_token in error_desc:
                        error_desc = error_desc.replace(bot_token, "[REDACTED_TOKEN]")
                    if chat_id and chat_id in error_desc:
                        error_desc = error_desc.replace(chat_id, "[REDACTED_CHAT_ID]")
                    proxy_env = _detect_proxy_env()
                    proxy_detected = proxy_env["any_proxy_detected"]
                    reason = (
                        f"TG send failed (plain text, no parse_mode): "
                        f"[http_status_error] {error_desc[:200]} "
                        f"(host=api.telegram.org, timeout=10s, "
                        f"proxy_detected={proxy_detected})"
                    )
                    return TGTestSendResult(
                        attempted=True,
                        success=False,
                        status="failed",
                        reason=reason[:400],
                        target_type="test_group",
                        one_shot=True,
                        production_send=False,
                        token_proof=token_proof,
                        chat_id_proof=chat_id_proof,
                        credentials_printed=False,
                    )

            # HTML/MarkdownV2 mode: use existing TGTransport path
            send_payload = {
                "text": card.full_text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }

            result = transport.send(send_payload, target="test_group", parse_mode=parse_mode)

            # Redact message_id
            message_id_proof = None
            if result.message_id:
                raw_mid = str(result.message_id)
                if not raw_mid.startswith("dry-run") and not raw_mid.startswith("tg-stub"):
                    message_id_proof = sha256_short(raw_mid)

            # Sanitize error message (strip any possible credential leak)
            error_msg = result.error_message or ""
            if bot_token and bot_token in error_msg:
                error_msg = error_msg.replace(bot_token, "[REDACTED_TOKEN]")
            if chat_id and chat_id in error_msg:
                error_msg = error_msg.replace(chat_id, "[REDACTED_CHAT_ID]")

            if result.success:
                return TGTestSendResult(
                    attempted=True,
                    success=True,
                    status="sent",
                    reason="TG test group one-shot sent successfully",
                    target_type="test_group",
                    one_shot=True,
                    production_send=False,
                    message_id_proof=message_id_proof,
                    token_proof=token_proof,
                    chat_id_proof=chat_id_proof,
                    credentials_printed=False,
                )
            else:
                # v117F: Enhanced failure classification
                failure_class = result.error_type or "unknown_transport_error"
                if failure_class == "NETWORK_TIMEOUT":
                    failure_class_norm = "network_timeout"
                elif failure_class == "AUTH_FAILURE":
                    failure_class_norm = "http_status_error"
                elif failure_class == "PROVIDER_REJECTION":
                    failure_class_norm = "http_status_error"
                elif failure_class == "RATE_LIMITED":
                    failure_class_norm = "http_status_error"
                else:
                    failure_class_norm = "unknown_transport_error"

                proxy_env = _detect_proxy_env()
                proxy_detected = proxy_env["any_proxy_detected"]

                reason = (
                    f"TG send failed: [{failure_class_norm}] "
                    f"(transport_error_type={failure_class}) "
                    f"{error_msg[:150]} "
                    f"(host=api.telegram.org, timeout=10s, "
                    f"proxy_detected={proxy_detected})"
                )
                return TGTestSendResult(
                    attempted=True,
                    success=False,
                    status="failed",
                    reason=reason[:400],
                    target_type="test_group",
                    one_shot=True,
                    production_send=False,
                    token_proof=token_proof,
                    chat_id_proof=chat_id_proof,
                    credentials_printed=False,
                )

        except ImportError as e:
            diag = self._build_network_diagnostics(
                f"ImportError: {e}", timeout_seconds=10,
            )
            return TGTestSendResult(
                attempted=False,
                success=False,
                status="skipped",
                reason=f"tg_test_send_skipped_import_error: cannot import market_radar_sender: {e}",
                target_type="test_group",
                one_shot=True,
                production_send=False,
                token_proof=token_proof,
                chat_id_proof=chat_id_proof,
                credentials_printed=False,
            )
        except Exception as e:
            error_str = str(e)
            if bot_token and bot_token in error_str:
                error_str = error_str.replace(bot_token, "[REDACTED_TOKEN]")
            if chat_id and chat_id in error_str:
                error_str = error_str.replace(chat_id, "[REDACTED_CHAT_ID]")

            # v117F: Enhanced network failure classification
            diag = self._build_network_diagnostics(
                error_str, timeout_seconds=10,
            )
            failure_class = diag["network_error_class"]
            proxy_detected = diag["proxy_env_detected"]

            reason = (
                f"TG send exception: [{failure_class}] "
                f"{type(e).__name__}: {error_str[:150]} "
                f"(host=api.telegram.org, timeout=10s, "
                f"proxy_detected={proxy_detected})"
            )
            return TGTestSendResult(
                attempted=True,
                success=False,
                status="failed",
                reason=reason[:400],
                target_type="test_group",
                one_shot=True,
                production_send=False,
                token_proof=token_proof,
                chat_id_proof=chat_id_proof,
                credentials_printed=False,
            )


def create_tg_sender() -> TGTestGroupSender:
    """Factory: create the TG test group sender."""
    return TGTestGroupSender()
