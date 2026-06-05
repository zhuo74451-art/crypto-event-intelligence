# Market Radar v1.9B-final R1 — RealHttpClient Physical-Network Pre-Adapter Layer Handoff

Generated: 2026-06-04 12:15 UTC+8
Task: RealHttpClient hardening for real-network readiness
Source: Gemini audit acceptance → executor implementation

---

## 1. Binding Info

- **result_source**: claude_code_executor
- **executor_lane**: market_radar
- **task_id**: 20260604_121532.r01
- **project_dir**: C:\Users\PC\Desktop\Projects\事件情报系统
- **component**: scripts/market_radar_sender.py

---

## 2. What Was Done

v1.9B-final R1 hardens `RealHttpClient` as a physical-network pre-adapter layer
without introducing async, httpx, or connection-pool complexity. The scope
matches the user's directive: "R1 只做真实网络前的最小硬化：timeout、proxy、
异常包裹、monkeypatch、固定 handoff。"

### 2.1 Default Timeout Hardened

- Changed `RealHttpClient.__init__` default timeout from `10` to `5` seconds.
- Every `requests.post` call now carries `timeout=effective_timeout` where the
  effective value is the per-call override or the constructor default.
- No bare `requests.post(...)` calls exist — timeout is always explicit.

### 2.2 proxy_url Parameter Reserved

- Added `proxy_url: Optional[str] = None` to `RealHttpClient.__init__`.
- When set, builds `proxies = {"http": proxy_url, "https": proxy_url}` and
  passes it to `requests.post(proxies=proxies)`.
- `proxy_url` is an EXPLICIT constructor parameter only.
  - Does NOT read `os.environ`, `os.getenv`, `.env`, or any config file.
  - Default is `None` (direct connection).
- Compatible with the existing pattern in `scripts/get_tg_chat_id.py`.

### 2.3 HTTP 403 Mapping Added

- Added `status_code == 403 → error_type = "PROVIDER_REJECTION"` in
  `TGTransport._handle_api_error()`.
- 403 from Telegram API means the bot was blocked, not a member of the chat,
  or the chat access is forbidden — correctly classified as a provider-level
  rejection (not an auth failure, since the token itself may be valid).

### 2.4 Monkeypatch Test Coverage Extended

- **Test 58 (new)**: `test_58_real_httpclient_proxy_url` — verifies:
  - `proxy_url=None` → `proxies=None` passed to `requests.post`
  - `proxy_url="http://127.0.0.1:7897"` → `proxies={"http": ..., "https": ...}` passed
  - `proxy_url` is stored as `self._proxy_url`
  - No `os.getenv` calls for proxy resolution

- **Test 59 (new)**: `test_59_monkeypatch_http_403` — verifies:
  - Monkeypatched `requests.post` returning 403
  - `SendResult.error_type == "PROVIDER_REJECTION"`
  - `SendResult.status_code == 403`
  - `error_message` contains "Forbidden"

### 2.5 Fixed Handoff File

- This file: `runs/market_radar/v19b_real_httpclient_handoff.md`
- Exists at a fixed, predictable path for downstream automated reading.
- Timestamped copies can still be generated separately.

---

## 3. Error Type Coverage Matrix

| Condition | RealHttpClient | TGTransport | SendResult.error_type |
|---|---|---|---|
| `requests.exceptions.Timeout` | Raises `TimeoutError` | Catches → `NETWORK_TIMEOUT` | `NETWORK_TIMEOUT` |
| `requests.exceptions.ConnectionError` | Raises `OSError` | Catches → `NETWORK_TIMEOUT` | `NETWORK_TIMEOUT` |
| `requests.exceptions.RequestException` | Raises `OSError` | Catches → `NETWORK_TIMEOUT` | `NETWORK_TIMEOUT` |
| HTTP 200 + `ok: true` | Returns response dict | Returns success `SendResult` | *(success)* |
| HTTP 400 | Returns response dict | `_handle_api_error` | `PROVIDER_REJECTION` |
| HTTP 401 | Returns response dict | `_handle_api_error` | `AUTH_FAILURE` |
| HTTP 403 | Returns response dict | `_handle_api_error` | `PROVIDER_REJECTION` |
| HTTP 429 | Returns response dict | `_handle_api_error` | `RATE_LIMITED` |
| HTTP other (5xx, etc.) | Returns response dict | `_handle_api_error` | `UNKNOWN_ERROR` |
| Non-JSON response body | Wraps as `{"_raw_body": text}` | *(forwarded)* | *(as mapped above)* |

---

## 4. Design Principles Compliance

| Principle | Status |
|---|---|
| Timeout enforced on every request | ✅ Default 5s, always passed explicitly |
| proxy_url explicit parameter | ✅ Accepted, never read from env |
| No environment variable reading | ✅ Verified by test_57 |
| No .env file reading | ✅ No .env logic exists |
| No token/chat_id in output | ✅ Redaction via `_redact_chat_id()` |
| All exceptions → SendResult | ✅ Full coverage (Timeout, ConnectionError, 400, 401, **403**, 429, unknown) |
| Monkeypatch proves no real network | ✅ Verified by test_56 (spy) |
| Fixed handoff file exists | ✅ This file |
| No async/httpx/connection-pool complexity | ✅ Kept at `requests.post + timeout + proxy` |

---

## 5. Modified Files

| File | Change |
|---|---|
| `scripts/market_radar_sender.py` | `RealHttpClient.__init__`: default timeout 10→5, add `proxy_url` param |
| `scripts/market_radar_sender.py` | `RealHttpClient.post()`: build `proxies` dict, pass to `requests.post` |
| `scripts/market_radar_sender.py` | `TGTransport._handle_api_error()`: add HTTP 403 → `PROVIDER_REJECTION` |
| `scripts/test_market_radar_sender_v19a.py` | Add `test_58_real_httpclient_proxy_url` (proxy_url acceptance) |
| `scripts/test_market_radar_sender_v19a.py` | Add `test_59_monkeypatch_http_403` (403 monkeypatch) |
| `scripts/test_market_radar_sender_v19a.py` | Update main() to run tests 58-59 |
| `runs/market_radar/v19b_real_httpclient_handoff.md` | This handoff file (created) |

---

## 6. Commands Executed

```bash
# Install test dependency
python -m pip install requests

# Run new tests
python -c "from test_market_radar_sender_v19a import test_58_real_httpclient_proxy_url, test_59_monkeypatch_http_403; test_58_real_httpclient_proxy_url(); test_59_monkeypatch_http_403()"

# Run full v1.9B-final R1 test suite (tests 50-59)
python -c "..."  # all 10 tests
```

---

## 7. Test Results

All 10 v1.9B-final R1 tests (50–59) pass:

| Test | Status | Description |
|---|---|---|
| 50 | ✅ PASS | RealHttpClient injection into TGTransport |
| 51 | ✅ PASS | Monkeypatch success → SendResult.success=True |
| 52 | ✅ PASS | Monkeypatch HTTP 400 → PROVIDER_REJECTION |
| 53 | ✅ PASS | Monkeypatch HTTP 401 → AUTH_FAILURE |
| 54 | ✅ PASS | Monkeypatch HTTP 429 → RATE_LIMITED + retry_after |
| 55 | ✅ PASS | Monkeypatch Timeout / ConnectionError → NETWORK_TIMEOUT |
| 56 | ✅ PASS | Monkeypatch spy confirms no real network |
| 57 | ✅ PASS | RealHttpClient does NOT read env vars |
| 58 | ✅ PASS | RealHttpClient proxy_url accepted and passed |
| 59 | ✅ PASS | Monkeypatch HTTP 403 → PROVIDER_REJECTION |

---

## 8. Completion Status

**Status: done**

All 5 accepted Gemini audit recommendations are implemented:

1. ✅ **timeout=5** — Default timeout hardened from 10s to 5s
2. ✅ **proxy_url** — Explicit constructor parameter, passed to requests.post, never from env
3. ✅ **Handoff filename fixed** — `runs/market_radar/v19b_real_httpclient_handoff.md`
4. ✅ **SendResult wraps all exceptions** — Timeout, ConnectionError, 400, 401, **403**, 429 all mapped
5. ✅ **Monkeypatch proves no real network** — Spy confirms zero calls to api.telegram.org

---

## 9. Unfinished Items / Risks

- **None.** R1 scope is complete.
- Deferred to later rounds:
  - `httpx.Client()` / async / connection-pool (explicitly rejected for R1)
  - Session-level `close()` lifecycle management (not needed for single-request TG pattern)
  - Retry logic with backoff (currently single-attempt; retry can be added in a later round)
  - Real TG test-group single-card send (next round after user authorization)

---

## 10. Next Round (Gemini Audit)

Suggested audit questions for Gemini on R1:

1. Does `RealHttpClient` now have the minimum engineering robustness for real-network readiness?
2. Is `timeout` enforced on every `requests.post` call?
3. Is `proxy_url` an explicit parameter (no env reading)?
4. Are all `requests.post` calls fully intercepted by monkeypatch?
5. Does `SendResult` cover Timeout / ConnectionError / 400 / 401 / 403 / 429?
6. Does the fixed handoff file exist at `runs/market_radar/v19b_real_httpclient_handoff.md`?

---

## 11. Security Boundaries

- ✅ No TG sent
- ✅ No Telegram API called (all requests monkeypatched)
- ✅ No background loops/daemons/cron started
- ✅ No paid external APIs called
- ✅ No server or remote database written
- ✅ No sensitive credentials output
- ✅ No trading actions
- ✅ No env var reading (verified by test_57)
