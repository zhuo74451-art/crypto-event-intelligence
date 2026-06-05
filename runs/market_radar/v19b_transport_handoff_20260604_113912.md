# Market Radar v1.9B Transport — Handoff

Generated: 2026-06-04 11:39:12 UTC+8
Lane: 1
Project: market_radar
Status: done
Task ID: 20260604_105425.r08

## 1. v1.9B 是否只替换 Transport，没有改 Schema / Gate / Policy / Payload 核心流程

**是的。** v1.9B 只新增了 Transport 层和 MarketRadarSender，完全没有修改：

- Schema (`schemas/market_radar_v19.json`) — 未修改
- Gate (`validate_preview_gate`, `GateResult`) — 未修改
- Policy (`apply_policy`, `PolicyReceipt`) — 未修改
- Payload (`build_send_payload`, `sanitize_flexible_payload`) — 未修改
- Handoff (`write_send_handoff`) — 未修改

验证：25 个原有测试全部通过，无任何修改。

## 2. FakeTransport 和 TGTransportStub 是否同构

**是的。** 两者都是 `BaseTransport` 的子类，接口完全一致：

```python
class BaseTransport(ABC):
    @property
    def transport_name(self) -> str: ...
    def send(self, payload: dict, target: str, parse_mode: str) -> SendResult: ...
```

- 相同的方法签名 `send(payload, target, parse_mode) -> SendResult`
- 相同的 `SendResult` 返回结构
- 相同的 `provider_metadata` 字段（transport_name, raw_api_response, request_payload_preview）
- 都不读取环境变量
- 都不修改 payload 文本
- 都不二次转义

差异仅在于：FakeTransport 返回模拟数据，TGTransportStub 构造 TG API 兼容的 request payload。两者都可在 `MarketRadarSender` 中无缝替换。

## 3. SendResult 如何统一成功和失败

`SendResult` 通过 `success` 字段统一成功和失败：

**成功路径：**
```python
SendResult(
    success=True,
    status_code=200,
    sent_count=1,
    message_id="fake-msg-20260604_113912",
    provider="fake",
    provider_metadata={...},
)
```

**失败路径：**
```python
SendResult(
    success=False,
    status="blocked",
    sent_count=0,
    error_type="RATE_LIMITED",
    error_message="Simulated: too many requests, rate limited by provider.",
    retry_after=30,
    status_code=429,
    provider="fake",
    provider_metadata={...},
)
```

所有失败模式统一返回 `SendResult`，不抛出未捕获异常。4 种标准错误类型：
- `PROVIDER_REJECTION`
- `NETWORK_TIMEOUT`
- `AUTH_FAILURE`
- `RATE_LIMITED`

## 4. provider_metadata 如何保存 raw response / request preview

```python
provider_metadata = {
    "transport_name": "fake",           # 或 "telegram"
    "raw_api_response": {               # API 响应（FakeTransport 模拟，TGTransportStub 为 None）
        "ok": True,
        "result": {"message_id": "..."},
    },
    "request_payload_preview": {        # 发送前的 payload 预览
        "text_preview": "<b>...</b>",   # 前 200 字符
        "parse_mode": "HTML",
        "target": "group",
        "char_count": 123,
    },
}
```

`_unrecognized_payload` 仅放入 `provider_metadata["_unrecognized_payload_debug"]`，不参与发送控制。

## 5. 是否可以进入 v1.9B-final 用户授权后的真实 TG 单卡测试

**可以。** 前提条件已满足：

1. ✅ v1.9B Transport 层已验证可替换
2. ✅ FakeTransport + TGTransportStub 同构
3. ✅ SendResult 统一成功/失败
4. ✅ 39/39 测试全部通过
5. ✅ 不调用 TG API、不发送消息、不访问网络
6. ✅ 不读取环境变量、不修改 payload、不二次转义

**进入 v1.9B-final 前需要用户提供：**
- 真实 `bot_token`（从环境变量或安全配置加载）
- 真实 `default_chat_id`（目标群组/频道 ID）
- 测试用候选卡（已有的 static_position_v18g 可复用）

**v1.9B-final 实现要点：**
1. 新建 `TGTransport(BaseTransport)`，接收 `bot_token` 和 `default_chat_id`
2. 实现 `send()` → 调用 TG Bot API `sendMessage`
3. 遵守 `retry_after` 限流
4. 用户授权前不执行任何真实发送

## Modified Files

- `scripts/market_radar_sender.py` — 新增 BaseTransport, FakeTransport, TGTransportStub, MarketRadarSender + SendResult 扩展
- `scripts/test_market_radar_sender_v19a.py` — 新增 11 个 v1.9B 测试 (26-36)
- `docs/market_radar_sender_v19a.md` — 更新 v1.9B 文档

## New Files

- `results/market_radar_sender_v19b_transport_test_report.md`
- `runs/market_radar/v19b_transport_handoff_20260604_113912.md` (本文件)

## Test Results

- Total: 39
- Passed: 39
- Failed: 0
- Skipped: 0

## Compliance

| Constraint | Status |
|---|---|
| TG API called | No |
| Messages sent | No |
| External network calls | No |
| Loop/daemon/timer started | No |
| Paid API called | No |
| Token/chat_id/API key printed | No |
| Remote DB written | No |
| Files deleted | No |
| Scope expanded beyond task | No |

## Warnings

- 无

## Suggestions

- v1.9B-final: 用户提供真实 bot_token 后，实现 `TGTransport(bot_token, chat_id)` 真实发送
- 建议先做 fake TG server（mock HTTP endpoint）E2E 测试，再做真实单卡测试
- 31 号测试中 spy on `os.getenv` 的方式验证了 Transport 不读环境变量，生产环境中 `TGTransport` 应接受显式参数而非从环境读取
