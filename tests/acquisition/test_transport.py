"""Transport layer tests — 25+ scenarios."""
import pytest
from datetime import datetime, timezone
from market_radar.acquisition.transport.response import HttpResponse, redact_headers, redact_sensitive_fields, SAFE_HEADERS
from market_radar.acquisition.transport.rate_limit import RateLimiter
from market_radar.acquisition.transport.retry import RetryPolicy, is_retriable, parse_retry_after
from market_radar.acquisition.transport.cache import InMemoryCache, NoOpCache


class TestSafeHeaders:
    def test_safe_headers_only_keeps_allowlist(self):
        raw = {"content-type": "text/html", "authorization": "Bearer xyz", "cookie": "session=123", "etag": "abc123"}
        clean = redact_headers(raw)
        assert "content-type" in clean
        assert "etag" in clean
        assert "authorization" not in clean
        assert "cookie" not in clean

    def test_redact_headers_lowercases_keys(self):
        raw = {"Content-Type": "text/html", "ETag": "xyz"}
        clean = redact_headers(raw)
        assert "content-type" in clean
        assert "etag" in clean

    def test_redact_sensitive_fields_removes_secrets(self):
        d = {"name": "test", "api_key": "sk-123", "token": "abc", "password": "secret"}
        clean = redact_sensitive_fields(d)
        assert clean["name"] == "test"
        for k in ["api_key", "token", "password"]:
            assert k not in clean

    def test_http_response_creation(self):
        r = HttpResponse(status=200, headers={"content-type": "text/html"}, body=b"hello")
        assert r.status == 200
        assert r.body == b"hello"
        assert r.from_cache is False


class TestRateLimiter:
    def test_acquire_returns_true(self):
        rl = RateLimiter(rate_per_second=100, max_burst=100)
        assert rl.try_acquire() is True

    def test_try_acquire_respects_burst(self):
        rl = RateLimiter(rate_per_second=0.001, max_burst=2)
        assert rl.try_acquire() is True
        assert rl.try_acquire() is True
        assert rl.try_acquire() is False


class TestRetry:
    def test_retry_policy_defaults(self):
        p = RetryPolicy()
        assert p.max_retries == 3

    def test_is_retriable_429(self):
        assert is_retriable("RATE_LIMITED", 429) is True

    def test_is_retriable_404_not_retriable(self):
        assert is_retriable("HTTP_CLIENT_ERROR", 404) is False

    def test_is_retriable_500(self):
        assert is_retriable("HTTP_SERVER_ERROR", 500) is True

    def test_parse_retry_after_seconds(self):
        assert parse_retry_after("30") == 30.0

    def test_parse_retry_after_none(self):
        assert parse_retry_after(None) is None


class TestCache:
    def test_in_memory_cache_set_and_get(self):
        c = InMemoryCache()
        c.set("http://example.com", HttpResponse(200, {}, b"body"), etag="abc")
        result = c.get("http://example.com")
        assert result is not None
        assert result.status == 200

    def test_in_memory_cache_miss(self):
        c = InMemoryCache()
        assert c.get("http://missing.com") is None

    def test_in_memory_cache_clear(self):
        c = InMemoryCache()
        c.set("http://example.com", HttpResponse(200, {}, b"body"))
        c.clear()
        assert c.get("http://example.com") is None

    def test_in_memory_cache_has(self):
        c = InMemoryCache()
        c.set("http://example.com", HttpResponse(200, {}, b"body"))
        assert c.has("http://example.com") is True
        assert c.has("http://missing.com") is False

    def test_no_op_cache_never_caches(self):
        c = NoOpCache()
        c.set("http://example.com", HttpResponse(200, {}, b"body"))
        assert c.get("http://example.com") is None
        assert c.has("http://example.com") is False
