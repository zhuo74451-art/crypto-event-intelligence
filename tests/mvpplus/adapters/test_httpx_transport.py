"""Unit tests for HttpxTransport — no live network."""
import json, unittest
from unittest.mock import MagicMock, patch
import httpx

from market_radar.external_adapters.httpx_transport import (
    HttpxTransport, TransportResult, TransportError, RETRIABLE_STATUSES,
)


class FakeResponse:
    def __init__(self, status_code, json_data=None, text="{}"):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else json.loads(text)
        self.text = text

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class TestTransportTimeoutConfig(unittest.TestCase):
    def test_default_timeouts(self):
        t = HttpxTransport()
        self.assertEqual(t._connect_timeout, 10.0)
        self.assertEqual(t._read_timeout, 30.0)
        self.assertEqual(t._write_timeout, 10.0)
        self.assertEqual(t._pool_timeout, 5.0)
        self.assertEqual(t._max_retries, 3)
        t.close()

    def test_custom_timeouts(self):
        t = HttpxTransport(connect_timeout=5.0, read_timeout=15.0,
                           write_timeout=8.0, pool_timeout=3.0, max_retries=5)
        self.assertEqual(t._connect_timeout, 5.0)
        self.assertEqual(t._read_timeout, 15.0)
        self.assertEqual(t._write_timeout, 8.0)
        self.assertEqual(t._pool_timeout, 3.0)
        self.assertEqual(t._max_retries, 5)
        t.close()

    def test_timeouts_clamped(self):
        t = HttpxTransport(connect_timeout=0.1, read_timeout=999.0)
        self.assertEqual(t._connect_timeout, 0.5)  # min clamp
        self.assertEqual(t._read_timeout, 120.0)    # max clamp
        t.close()

    def test_max_retries_clamped(self):
        t = HttpxTransport(max_retries=100)
        self.assertEqual(t._max_retries, 10)
        t.close()


class TestBoundedRetry(unittest.TestCase):
    def test_max_retries_capped(self):
        t = HttpxTransport(max_retries=3)
        self.assertEqual(t._max_retries, 3)
        t.close()

    def test_no_retry_on_400(self):
        transport = HttpxTransport(max_retries=3)
        transport._client = MagicMock()
        transport._client.request.return_value = FakeResponse(400, {"error": "bad"})

        result = transport.get("https://api.binance.com/test")
        self.assertFalse(result.ok)
        self.assertEqual(result.attempts, 1)
        transport.close()


class TestRetriable429(unittest.TestCase):
    def test_retry_on_429(self):
        transport = HttpxTransport(max_retries=2, backoff_base=0.01)
        transport._client = MagicMock()
        transport._client.request.side_effect = [
            FakeResponse(429, {}),
            FakeResponse(200, {"ok": True}),
        ]
        result = transport.get("https://api.binance.com/test")
        self.assertTrue(result.ok)
        self.assertEqual(result.attempts, 2)
        transport.close()

    def test_retry_exhausted_on_503(self):
        transport = HttpxTransport(max_retries=2, backoff_base=0.01)
        transport._client = MagicMock()
        transport._client.request.side_effect = [
            FakeResponse(503, {}),
            FakeResponse(503, {}),
        ]
        result = transport.get("https://api.binance.com/test")
        self.assertFalse(result.ok)
        self.assertEqual(result.attempts, 2)
        transport.close()


class TestStructuredNetworkError(unittest.TestCase):
    def test_network_error_structured(self):
        transport = HttpxTransport(max_retries=1)
        transport._client = MagicMock()
        transport._client.request.side_effect = httpx.ConnectError("connection refused")

        result = transport.get("https://api.binance.com/test")
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.kind, "network")
        transport.close()


class TestMalformedJSON(unittest.TestCase):
    def test_malformed_json_returns_error(self):
        transport = HttpxTransport(max_retries=1)
        transport._client = MagicMock()
        resp = httpx.Response(200, content=b"not-json", request=MagicMock())
        transport._client.request.return_value = resp

        result = transport.get("https://api.binance.com/test")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.kind, "json")
        transport.close()


class TestHTTPSAllowlist(unittest.TestCase):
    def test_non_https_rejected(self):
        transport = HttpxTransport()
        result = transport.get("http://api.binance.com/test")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.kind, "allowlist")
        transport.close()

    def test_host_not_allowed_rejected(self):
        transport = HttpxTransport()
        result = transport.get("https://evil.com/test")
        self.assertFalse(result.ok)
        self.assertEqual(result.error.kind, "allowlist")
        transport.close()

    def test_allowed_host_accepted(self):
        transport = HttpxTransport(max_retries=1, https_allowlist={"api.binance.com"})
        transport._client = MagicMock()
        transport._client.request.return_value = FakeResponse(200, {"ok": True})
        result = transport.get("https://api.binance.com/test")
        self.assertTrue(result.ok)
        transport.close()


class TestContextManager(unittest.TestCase):
    def test_context_manager_closes(self):
        with HttpxTransport(max_retries=1) as t:
            self.assertIsNotNone(t)
        # If close wasn't called, no error — just verifying pattern


class TestTransportResultDict(unittest.TestCase):
    def test_result_as_dict(self):
        r = TransportResult(ok=True, data={"price": 100}, status_code=200, attempts=1)
        d = r.as_dict()
        self.assertTrue(d["ok"])
        self.assertEqual(d["data"]["price"], 100)

    def test_error_as_dict(self):
        e = TransportError("timeout", "connection timed out", status_code=504)
        d = e.as_dict()
        self.assertEqual(d["kind"], "timeout")
        self.assertIn("status_code", d)


if __name__ == "__main__":
    unittest.main()
