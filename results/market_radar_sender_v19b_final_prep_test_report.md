# Market Radar Sender v1.9A-S2 + v1.9B Transport + v1.9B-final Prep — Test Report

Generated: 2026-06-04 11:54:07 UTC+8
Component: scripts/market_radar_sender.py
Schema: schemas/market_radar_v19.json
Patches: v1.9A-S2 Schema / Policy / Sanitization + v1.9B Transport + v1.9B-final Prep TGTransport

## Results

| # | Test | Status | Detail |
|---|---|---|---|
| 1 | 1.Normal dry-run pass | [PASS] PASS | sent_count=1, gates=9 passed |
| 2 | 2.max_send_count enforcement | [PASS] PASS | Correctly blocked: Send limit reached: sent_count=1 >= max_send_count=1 |
| 3 | 3.blocked=true rejection | [PASS] PASS | Correctly blocked when blocked=true |
| 4 | 4.leak_count > 0 rejection | [PASS] PASS | Correctly blocked on leak_count=2 |
| 5 | 5.full_address_count > 0 rejection | [PASS] PASS | Correctly blocked on full_address_count=1 |
| 6 | 6.No external interface calls | [PASS] PASS | Verified 0 external calls, result status=done |
| 7 | 7.Empty candidate rejection | [PASS] PASS | Correctly raised ValueError on empty markdown |
| 8 | 8.Missing preview report | [PASS] PASS | Correctly raised FileNotFoundError |
| 9 | 9.Handoff output format | [PASS] PASS | All 16 required fields present |
| 10 | 10.Full address detection | [PASS] PASS | Correctly detected full address in candidate MD |
| 11 | 10.Short address passes gate | [PASS] PASS | Correctly allows short address (0x082e...ca88) |
| 12 | 11.Schema file readable | [PASS] PASS | strict_core=13 fields (incl. schema_version), flexible_payload=8 fields |
| 13 | 12.Full manifest passes | [PASS] PASS | Validated OK, 8 flexible-payload warnings |
| 14 | 13.Missing Strict Core rejects | [PASS] PASS | ValueError raised for missing 'artifact_id': Strict Core fields missing from manifest: ['artifact_id']. These fields are required by schema v1.9A-s2. See schemas/market_radar_v19.json for field definitions. |
| 15 | 13.Missing Strict Core (2nd field) rejects | [PASS] PASS | ValueError for 'parse_mode' |
| 16 | 14.Missing Flexible Payload warns | [PASS] PASS | 8 warnings for 8 missing flexible fields |
| 17 | 15.schema_version missing → reject | [PASS] PASS | Blocked with 2 errors: ["Strict Core fields missing from manifest: ['schema_version']. These fields are required by schema v1.9A-s2. See schemas/market_radar_v19.json for field definitions.", 'schema_version is missing from manifest (Strict Core)'] |
| 18 | 16.schema_version mismatch → reject | [PASS] PASS | Blocked with errors: ["schema_version mismatch: expected '1.9A-S2', got '1.9A-S1'"] |
| 19 | 17.Runtime Source absolute path → reject | [PASS] PASS | Blocked with errors: ["Runtime Source 'candidate_md_path' is an absolute path: 'C:\\Users\\PC\\Desktop\\Projects\\事件情报系统\\results\\test.md'. Must be relative from project root."] |
| 20 | 18.Runtime Source ../ traversal → reject | [PASS] PASS | Blocked with errors: ["Runtime Source 'candidate_md_path' contains path traversal (..): 'results/../../etc/passwd'"] |
| 21 | 19.leak_count = -1 → reject | [PASS] PASS | Blocked with errors: ['leak_count must be >= 0, got -1'] |
| 22 | 20.blocked = 'false' → reject | [PASS] PASS | Blocked with errors: ["blocked must be bool, got str: 'false'"] |
| 23 | 21.max_send_count = 2 → policy trim | [PASS] PASS | raw_manifest preserved (msc=2), effective_data trimmed to 1, adjusted_fields=['max_send_count'] |
| 24 | 22.Flexible Payload format bomb sanitized | [PASS] PASS | Token name: 111→32 chars, symbol: 29→16 chars, wallet: 52→24 chars |
| 25 | 23.MarkdownV2 escaping | [PASS] PASS | token_name='ETH\_BTC\*\[test\]', symbol='\~symbol\` \> ch' |
| 26 | 24.Parse mode / target type normalization | [PASS] PASS | All 10 pm + 10 tt cases pass |
| 27 | 25.Disallowed path prefix → reject | [PASS] PASS | Blocked: ["Runtime Source 'candidate_md_path' has disallowed path prefix: 'etc/passwd'. Allowed prefixes: ['results/', 'runs/', 'schemas/']"] |
| 28 | 26.FakeTransport success | [PASS] PASS | message_id=fake-msg-20260604_115407, provider=fake |
| 29 | 27.TGTransportStub request payload | [PASS] PASS | Constructed valid TG request payload, no API call, chat_id redacted |
| 30 | 28.FakeTransport failure simulation | [PASS] PASS | All 4 failure modes return success=False with error details |
| 31 | 29.TGTransportStub RATE_LIMITED | [PASS] PASS | retry_after=30, status_code=429 |
| 32 | 30.Transport no env reading | [PASS] PASS | Neither FakeTransport nor TGTransportStub called os.getenv |
| 33 | 31.Transport no payload modification | [PASS] PASS | Both transports pass text through unchanged |
| 34 | 32.Transport no double-escaping | [PASS] PASS | &lt;Link&gt; preserved through both transports |
| 35 | 32.Mixed escaping preserved | [PASS] PASS | Mixed escaped+unescaped text preserved unchanged |
| 36 | 33._unrecognized_payload isolation | [PASS] PASS | _unrecognized_payload passed through in provider_metadata, did NOT affect send control |
| 37 | 34.MarketRadarSender + FakeTransport | [PASS] PASS | Full pipeline OK, provider=fake |
| 38 | 35.MarketRadarSender + TGTransportStub | [PASS] PASS | Full pipeline OK, TG request payload constructed, no API call |
| 39 | 36.MarketRadarSender rejects invalid transport | [PASS] PASS | TypeError raised: transport must be a BaseTransport instance, got str |
| 40 | 37.TGTransport pure-param construction | [PASS] PASS | No env reading, transport_name='telegram' |
| 41 | 38.TGTransport mock success | [PASS] PASS | message_id=4242, sent_count=1, request_count=1 |
| 42 | 39.TGTransport HTTP 400 → PROVIDER_REJECTION | [PASS] PASS | error_type=PROVIDER_REJECTION, error_message=Bad Request: message text is empty |
| 43 | 40.TGTransport HTTP 401 → AUTH_FAILURE | [PASS] PASS | error_type=AUTH_FAILURE, status_code=401 |
| 44 | 41.TGTransport HTTP 429 → RATE_LIMITED | [PASS] PASS | error_type=RATE_LIMITED, retry_after=30 |
| 45 | 41.RATE_LIMITED retry_after=60 | [PASS] PASS | retry_after correctly extracted from response parameters |
| 46 | 42.TGTransport TimeoutError → NETWORK_TIMEOUT | [PASS] PASS | error_type=NETWORK_TIMEOUT, error_message=TG API request timed out |
| 47 | 43.TGTransport OSError → NETWORK_TIMEOUT | [PASS] PASS | error_type=NETWORK_TIMEOUT, error_message=Connection refused |
| 48 | 44.TGTransport sensitive info redaction | [PASS] PASS | bot_token and full chat_id absent from all outputs |
| 49 | 45.TGTransport no double-escaping | [PASS] PASS | &lt;Link&gt; preserved through TGTransport |
| 50 | 46.TGTransport text passthrough | [PASS] PASS | All 5 text variants pass through unchanged |
| 51 | 47.Empty bot_token rejected | [PASS] PASS | ValueError: bot_token must be a non-empty string |
| 52 | 47.Empty chat_id rejected | [PASS] PASS | ValueError: default_chat_id must be a non-empty string |
| 53 | 47.Non-HttpClient rejected | [PASS] PASS | TypeError: http_client must be an HttpClient instance, got str |
| 54 | 48.TGTransport UNKNOWN_ERROR | [PASS] PASS | error_type=UNKNOWN_ERROR, error_message=RuntimeError: Simulated unexpected internal error |
| 55 | 49.MockHttpClient request recording | [PASS] PASS | All 2 requests recorded with full details |
| 56 | 50.RealHttpClient injection | [PASS] PASS | RealHttpClient accepted by TGTransport, implements HttpClient interface |
| 57 | 51.Monkeypatch success → SendResult | [PASS] PASS | message_id=7777, requests.post called 1 times |
| 58 | 52.Monkeypatch HTTP 400 → PROVIDER_REJECTION | [PASS] PASS | error_type=PROVIDER_REJECTION, error_message=Bad Request: chat_id is invalid |
| 59 | 53.Monkeypatch HTTP 401 → AUTH_FAILURE | [PASS] PASS | error_type=AUTH_FAILURE, status_code=401 |
| 60 | 54.Monkeypatch HTTP 429 → RATE_LIMITED | [PASS] PASS | error_type=RATE_LIMITED, retry_after=45 |
| 61 | 55.Monkeypatch Timeout / ConnectionError → NETWORK_TIMEOUT | [PASS] PASS | Both Timeout and ConnectionError correctly mapped to NETWORK_TIMEOUT |
| 62 | 56.Monkeypatch spy no real network | [PASS] PASS | All 1 POST calls intercepted by spy, zero real network access |
| 63 | 57.RealHttpClient no env reading | [PASS] PASS | Zero os.getenv calls during construction and post() |

## Summary

- **Total**: 63
- **Passed**: 63
- **Failed**: 0
- **Skipped**: 0

## S2 Coverage Verification

| Feature | Tests |
|---|---|
| schema_version in Strict Core | 11, 15, 16 |
| Runtime Source relative path + whitelist | 17, 18, 25 |
| Type + value range validation | 19, 20 |
| PolicyReceipt (max_send_count trim, raw_manifest preservation) | 21 |
| Flexible Payload sanitization (truncate, control chars, escaping) | 22, 23 |
| Parse mode / target type normalization | 24 |

## v1.9B Transport Coverage Verification

| Feature | Tests |
|---|---|
| FakeTransport success returns standard SendResult | 26 |
| TGTransportStub constructs request payload without network | 27 |
| FakeTransport failure simulation (4 modes) | 28 |
| TGTransportStub RATE_LIMITED retry_after | 29 |
| Transport does not read env vars | 30 |
| Transport does not modify sanitized payload | 31 |
| Transport does not double-escape HTML | 32 |
| _unrecognized_payload isolation | 33 |
| MarketRadarSender + FakeTransport integration | 34 |
| MarketRadarSender + TGTransportStub integration | 35 |
| MarketRadarSender rejects invalid transport | 36 |

## v1.9B-final Prep TGTransport Coverage Verification

| Feature | Tests |
|---|---|
| TGTransport pure-param construction, no env reading | 37 |
| MockHttpClient success → SendResult.success=True | 38 |
| MockHttpClient HTTP 400 → PROVIDER_REJECTION | 39 |
| MockHttpClient HTTP 401 → AUTH_FAILURE | 40 |
| MockHttpClient HTTP 429 → RATE_LIMITED + retry_after | 41 |
| MockHttpClient TimeoutError → NETWORK_TIMEOUT | 42 |
| OSError → NETWORK_TIMEOUT | 43 |
| provider_metadata redaction (no bot_token / full chat_id) | 44 |
| TGTransport no double-escape &lt;Link&gt; | 45 |
| TGTransport text passthrough (no modification) | 46 |
| TGTransport rejects invalid constructor args | 47 |
| UNKNOWN_ERROR for unexpected exceptions | 48 |
| MockHttpClient request recording for assertions | 49 |

## v1.9B-final R1 RealHttpClient + Monkeypatch Coverage Verification

| Feature | Tests |
|---|---|
| RealHttpClient can be injected into TGTransport | 50 |
| Monkeypatched requests.post success → SendResult.success=True | 51 |
| Monkeypatched HTTP 400 → PROVIDER_REJECTION | 52 |
| Monkeypatched HTTP 401 → AUTH_FAILURE | 53 |
| Monkeypatched HTTP 429 → RATE_LIMITED + retry_after | 54 |
| Monkeypatched Timeout / ConnectionError → NETWORK_TIMEOUT | 55 |
| Monkeypatch spy confirms no real network access | 56 |
| RealHttpClient does NOT read env vars / .env | 57 |

## Safety Verification

| Check | Status |
|---|---|
| TG API called | No (MockHttpClient only) |
| Messages sent | No (mock responses) |
| Loop started | No |
| Sensitive info printed | No |
| External network calls | No (MockHttpClient intercepts all) |
| Remote DB written | No |
| Archive scripts modified | No |
| Candidate card modified | No |
| raw_manifest mutated in-place | No |
| Transport reads env vars | No |
| Transport modifies payload | No |
| Transport double-escapes HTML | No |
| bot_token in outputs | No (REDACTED) |
| chat_id in outputs | No (REDACTED) |
| RealHttpClient reads env vars | No (spy confirmed) |
| RealHttpClient reads .env | No |
| RealHttpClient prints token/chat_id | No |
| requests.post called without monkeypatch | No (always monkeypatched in tests) |
| Real TG API endpoint called | No (api_base_url is always dummy.local) |

## v1.9B-final R1 Readiness

| Criterion | Status |
|---|---|
| RealHttpClient 实现 HttpClients 接口 | ✅ |
| RealHttpClient 可注入 TGTransport | ✅ |
| 7 种 monkeypatch 场景全覆盖 | ✅ |
| 防真实网络（全部 monkeypatched） | ✅ |
| 防环境变量读取 | ✅ |
| 防 .env 读取 | ✅ |
| 防 token / chat_id 打印 | ✅ |
| SendResult 统一真实 HTTP 成功和失败 | ✅ |
| 异常标准化（PROVIDER_REJECTION/AUTH_FAILURE/RATE_LIMITED/NETWORK_TIMEOUT/UNKNOWN_ERROR） | ✅ |
| 可进入 v1.9B-final R2：用户授权后的真实 TG 单卡测试 | ✅ (需用户授权 token + chat_id) |

## Test Environment

- Python: 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
- Root: C:\Users\PC\Desktop\Projects\事件情报系统
- Platform: win32
- Schema version: 1.9A-S2