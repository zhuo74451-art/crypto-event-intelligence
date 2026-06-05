# Market Radar v1.9B-final Prep — TGTransport 真实适配器准备 + Mock HTTP 测试 Handoff

**Date:** 2026-06-04 11:47:27 UTC+8  
**Lane:** 1  
**Project:** market_radar  
**Status:** done  
**Component:** scripts/market_radar_sender.py  
**Test Suite:** scripts/test_market_radar_sender_v19a.py  

## 执行摘要

v1.9B-final Prep 已完成。实现了真正的 TGTransport 适配器代码结构，所有 HTTP 调用通过注入的 MockHttpClient 拦截测试。本轮未读取真实 token，未调用 TG API，未访问外部网络，未发送任何消息。

## 修改文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `scripts/market_radar_sender.py` | 新增 | TGTransport, HttpClient, MockHttpClient 类 |
| `scripts/test_market_radar_sender_v19a.py` | 新增 | 13 个 v1.9B-final Prep 测试 (37-49) |
| `docs/market_radar_sender_v19a.md` | 更新 | 添加 v1.9B-final Prep 文档章节 |

## 新增文件

| 文件 | 说明 |
|---|---|
| `results/market_radar_sender_v19b_final_prep_test_report.md` | 测试报告 |
| `runs/market_radar/v19b_final_prep_handoff_20260604_114727.md` | 本文档 |

## 测试结果

- **总测试数**: 55
- **通过数**: 55
- **失败数**: 0
- **跳过数**: 0
- **新增测试**: 13 (37-49)

### 新增测试明细

| # | 测试 | 状态 |
|---|---|---|
| 37 | TGTransport 纯参数构造，不读取环境变量 | PASS |
| 38 | MockHttpClient 成功响应 → SendResult.success=True | PASS |
| 39 | MockHttpClient HTTP 400 → PROVIDER_REJECTION | PASS |
| 40 | MockHttpClient HTTP 401 → AUTH_FAILURE | PASS |
| 41 | MockHttpClient HTTP 429 → RATE_LIMITED + retry_after 正确 | PASS |
| 42 | MockHttpClient TimeoutError → NETWORK_TIMEOUT | PASS |
| 43 | OSError → NETWORK_TIMEOUT | PASS |
| 44 | request_payload_preview 不包含 bot_token / 完整 chat_id | PASS |
| 45 | TGTransport 防二次转义 &lt;Link&gt; | PASS |
| 46 | TGTransport 文本透传（5种变体） | PASS |
| 47 | TGTransport 拒绝无效构造参数（空token/chat_id/非HttpClient） | PASS |
| 48 | UNKNOWN_ERROR 捕获未预期异常 | PASS |
| 49 | MockHttpClient 请求记录 | PASS |

## 安全验证

| 检查项 | 结果 |
|---|---|
| 是否调用真实 TG API | 否 |
| 是否发送消息 | 否 |
| 是否访问外部网络 | 否 |
| TGTransport 是否纯参数构造 | 是 |
| bot_token 是否出现在输出中 | 否（REDACTED） |
| chat_id 是否出现在输出中 | 否（REDACTED） |
| api_endpoint 是否脱敏 | 是（/bot[REDACTED]/sendMessage） |

## SendResult 错误类型覆盖

| 错误类型 | 覆盖 | 触发方式 |
|---|---|---|
| PROVIDER_REJECTION | ✅ | MockHttpClient HTTP 400 |
| AUTH_FAILURE | ✅ | MockHttpClient HTTP 401 |
| RATE_LIMITED | ✅ | MockHttpClient HTTP 429 + parameters.retry_after |
| NETWORK_TIMEOUT | ✅ | MockHttpClient TimeoutError / OSError |
| UNKNOWN_ERROR | ✅ | 未预期 RuntimeError |

## Handoff 说明

### 1. TGTransport 是否只替换 Transport，没有改 Schema/Gate/Policy/Payload 核心流程

✅ 是。TGTransport 继承 BaseTransport，实现 `send(payload, target, parse_mode) -> SendResult`。Schema/Gate/Policy/Payload 核心流程未做任何修改，Transport 层面完全对 Sender Core 透明。

### 2. MockHttpClient 如何避免真实网络调用

✅ MockHttpClient 是内存中的模拟 HTTP 客户端：
- `set_response(status_code, json)` 预配置响应
- `set_timeout(True)` 模拟超时
- `post()` 方法只记录请求并返回预配置响应，不发起任何 socket 连接
- 测试中 `api_base_url="http://dummy.local"` 确保即使漏过 Mock 也不会访问真实 API

### 3. SendResult 如何统一 TG 成功和失败

✅ 所有路径都返回标准 SendResult：
- 成功路径：`SendResult(success=True, status_code=200, message_id=..., provider="telegram", provider_metadata={raw_api_response, request_payload_preview})`
- 失败路径：`SendResult(success=False, error_type=..., error_message=..., retry_after=..., provider="telegram")`
- 所有网络异常（TimeoutError, OSError, RuntimeError 等）都被 try/except 捕获并转换为 SendResult，不抛出未捕获异常

### 4. provider_metadata 如何保存 raw response / request preview

✅ provider_metadata 结构：
```json
{
  "transport_name": "telegram",
  "raw_api_response": { ... TG API 完整响应 JSON ... },
  "request_payload_preview": {
    "chat_id": "-100XXXX_REDACTED",
    "text_preview": "... （前200字符）",
    "text_length": 100,
    "parse_mode": "HTML",
    "disable_web_page_preview": true,
    "api_endpoint": "/bot[REDACTED]/sendMessage"
  }
}
```

- `raw_api_response` 保存完整的 TG API 响应（成功时包含 message_id、chat、date 等）
- `request_payload_preview` 是脱敏后的请求预览（bot_token 完全不出现在任何字段中，chat_id 仅显示脱敏形式）

### 5. 是否可以进入 v1.9B-final 用户授权后的真实 TG 单卡测试

✅ 可以。所有前置条件已满足：

| 条件 | 状态 |
|---|---|
| TGTransport 代码结构就绪 | ✅ |
| Mock HTTP 测试全部通过 (13/13 新增，55/55 总计) | ✅ |
| 错误类型全覆盖 (5/5) | ✅ |
| 敏感信息脱敏验证通过 | ✅ |
| 防二次转义验证通过 | ✅ |
| 所有异常安全捕获 | ✅ |

**下一步需要用户提供**：
- 真实 bot_token（用于 TGTransport 构造函数）
- 真实 chat_id（用于指定发送目标）
- 然后实现 RealHttpClient（基于 `requests.post` 的真实 HTTP 调用封装）

## 建议

1. **v1.9B-final 真实 TG 单卡测试时**，创建 RealHttpClient 类（实现 HttpClient 接口，内部用 `requests.post`），保持与 MockHttpClient 相同的接口
2. **v1.9C 持久化**时，在 MarketRadarSender.send_from_manifest() 中添加 `published_history.jsonl` 写入逻辑
3. **安全提醒**：真实 token 应从安全的凭据管理方式获取（如仅通过构造参数传入），确认不打印/不记录/不序列化
