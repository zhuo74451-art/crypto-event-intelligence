"""Security tests — 15+ scenarios."""
import pytest, os
from market_radar.acquisition.transport.response import redact_headers, redact_sensitive_fields
from market_radar.acquisition.integrations.apprise_client_contract import (
    DryRunNotificationClient, NotificationEnvelope, RedactionHelper,
)
from market_radar.acquisition.contracts.observation import NormalizedObservation


class TestHeaderRedaction:
    def test_authorization_removed(self):
        clean = redact_headers({"authorization": "Bearer tok-123", "content-type": "text/html"})
        assert "authorization" not in clean

    def test_cookie_removed(self):
        clean = redact_headers({"cookie": "session=abc123"})
        assert "cookie" not in clean

    def test_set_cookie_removed(self):
        clean = redact_headers({"set-cookie": "session=abc123"})
        assert "set-cookie" not in clean

    def test_safe_headers_preserved(self):
        clean = redact_headers({"content-type": "text/html", "content-length": "100", "etag": "abc"})
        assert "content-type" in clean
        assert "content-length" in clean
        assert "etag" in clean


class TestSecretRedaction:
    def test_redact_api_key_pattern(self):
        text = "api_key=sk-1234567890abcdef"
        clean = RedactionHelper.redact_sensitive(text)
        assert "sk-" not in clean
        assert "[REDACTED]" in clean

    def test_redact_token_pattern(self):
        text = "token=ghp_abcdefghijklmnop"
        clean = RedactionHelper.redact_sensitive(text)
        assert "[REDACTED]" in clean

    def test_redact_sensitive_fields_dict(self):
        d = {"url": "http://example.com", "password": "secret123"}
        clean = redact_sensitive_fields(d)
        assert "url" in clean
        assert "password" not in clean


class TestDryRunNotification:
    def test_dry_run_does_not_send_external(self):
        client = DryRunNotificationClient()
        env = NotificationEnvelope(title="Test", body="Test body", source_id="test")
        result = client.send_notification(env)
        assert result is True
        assert len(client.sent_notifications) == 1

    def test_notification_envelope_redact(self):
        env = NotificationEnvelope(title="Test", body="api_key=sk-123", source_id="test")
        redacted = env.redact()
        assert "[REDACTED]" in redacted.body
        assert "sk-" not in redacted.body

    def test_dry_run_records_envelopes(self):
        client = DryRunNotificationClient()
        client.send_notification(NotificationEnvelope(title="A", body="B", source_id="s1"))
        client.send_notification(NotificationEnvelope(title="C", body="D", source_id="s2"))
        assert len(client.sent_notifications) == 2


class TestObservationNoMarketDirection:
    def test_no_bullish_bearish(self):
        obs = NormalizedObservation()
        d = obs.to_dict()
        for key in d:
            assert "bullish" not in key.lower()
            assert "bearish" not in key.lower()

    def test_no_signal_score(self):
        obs = NormalizedObservation()
        d = obs.to_dict()
        assert "signal_score" not in d


class TestNoBackgroundProcesses:
    def test_no_infinite_service_loops(self):
        """No daemon-style infinite loops in acquisition code."""
        acq_dir = os.path.join(os.path.dirname(__file__), "..", "..", "market_radar", "acquisition")
        violations = []
        allowed_prefixes = ("rate_limit",)  # blocking acquire uses while True
        for root, dirs, files in os.walk(acq_dir):
            for f in files:
                if not f.endswith(".py") or f == "test_security.py" or "__pycache__" in root:
                    continue
                path = os.path.join(root, f)
                with open(path, "r", encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        stripped = line.strip()
                        if "while True" in stripped or "while 1" in stripped:
                            if not any(f.startswith(p) for p in allowed_prefixes):
                                violations.append(f"{path}:{i}")
        assert len(violations) == 0, f"Found service loop violations: {violations}"
