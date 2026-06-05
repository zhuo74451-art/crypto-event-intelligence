# Market Radar Sender v1.9A-S2 — 正式发送组件 MVP + 收口补丁

## 概述

v1.9A 将 v1.8H 临时脚本中的可复用逻辑沉淀为正式发送组件，提供统一的候选卡加载、闸门校验、发送模拟和 handoff 输出接口。

v1.9A-S2 补齐了 v1.9A-S1 的最终收口标准：Schema Version、Runtime Source 相对路径、类型和值域校验、PolicyReceipt、Flexible Payload 基础清洗。

**当前阶段：DRY-RUN ONLY**，不调用任何外部 API。

## 文件位置

| 文件 | 路径 | 说明 |
|---|---|---|
| 发送组件 | `scripts/market_radar_sender.py` | 正式发送组件 + Schema + Policy + Sanitization |
| 测试脚本 | `scripts/test_market_radar_sender_v19a.py` | 本地 dry-run + Schema + S2 测试 |
| Schema 契约 | `schemas/market_radar_v19.json` | 单源 Schema 定义 (v1.9A-S2) |
| Sample Manifest | `results/market_radar_v19_manifest_sample.json` | 完整 manifest 示例 |
| 本文档 | `docs/market_radar_sender_v19a.md` | 组件说明 |

## 组件接口

### 核心函数 (v1.9A)

```python
from market_radar_sender import (
    load_candidate,         # 加载候选卡 (md + json)
    load_preview_gate,      # 解析预览报告
    validate_preview_gate,  # 校验所有闸门条件
    build_send_payload,     # 构建发送 payload
    dry_run_send,           # 干跑发送（不调用外部 API）
    write_send_handoff,     # 输出结构化结果
    run_full_dry_run,       # 一键运行完整 pipeline
    GateResult,             # 闸门结果数据类
    SendResult,             # 发送结果数据类
)
```

### Schema 函数 (v1.9A-S1)

```python
from market_radar_sender import (
    load_schema,              # 加载 schema JSON
    validate_manifest,        # 校验 manifest → (is_valid, warnings)
    build_manifest_from_paths,# 从文件路径构建 manifest
)
```

### S2 新增函数 (v1.9A-S2)

```python
from market_radar_sender import (
    # Policy & Receipt
    PolicyReceipt,             # 策略结果数据类
    apply_policy,              # 应用 Lane 1 策略
    validate_and_apply_policy, # 完整 S2 校验+策略 pipeline

    # Validation
    validate_runtime_source_paths,  # Runtime Source 路径校验
    validate_types_and_ranges,      # 类型+值域校验

    # Sanitization
    sanitize_flexible_payload,      # Flexible Payload 清洗
    remove_control_chars,           # 移除控制字符
    sanitize_for_parse_mode,        # parse_mode 特定转义
    escape_html,                    # HTML 转义
    escape_markdown_v2,             # MarkdownV2 转义

    # Normalization
    normalize_parse_mode,           # parse_mode 标准化
    normalize_target_type,          # target_type 标准化
)
```

## v1.9A-S2 收口标准

### 一、Schema Version（Strict Core）

- `schema_version = "1.9A-S2"` 已进入 Strict Core（13 字段）
- 缺失或不匹配时 `validate_and_apply_policy()` 返回 `PolicyReceipt.status = "blocked"`
- Schema 文件版本标识为 `v1.9A-s2`

### 二、Runtime Source 相对路径校验

`candidate_md_path` / `candidate_json_path` / `preview_report_path` 归类为 **Runtime Source**：

| 规则 | 实现 |
|---|---|
| 必须是相对路径 | `os.path.isabs()` 检查 |
| 不允许 `../` 路径逃逸 | `Path.parts` 检查 `..` |
| 允许目录前缀 | `results/`, `runs/`, `schemas/` |
| 违反 → 阻断 | 错误加入 PolicyReceipt.errors |

### 三、类型和值域校验

| 字段 | 类型 | 值域 | 违反行为 |
|---|---|---|---|
| `blocked` | `bool` | — | 错误阻断 |
| `leak_count` | `int` | `>= 0` | 错误阻断 |
| `full_address_count` | `int` | `>= 0` | 错误阻断 |
| `max_send_count` | `int` | `>= 1` | 错误阻断 |
| `parse_mode` | 标准化 | HTML / MarkdownV2 / PlainText | 无法标准化 → 错误 |
| `target_type` | 标准化 | group / supergroup / test_group / fake | 不在集合 → 错误 |

**标准化映射：**
- `"TG群"` → `"group"`, `"TG频道"` → `"supergroup"`, `"dry-run"` → `"test_group"`
- `"Markdown"` → `"MarkdownV2"`, `"plain"` → `"PlainText"`

### 四、Runtime PolicyReceipt

`PolicyReceipt` 数据结构：

```python
@dataclass
class PolicyReceipt:
    status: str           # "ok" | "adjusted" | "blocked"
    warnings: list[str]   # 不阻断，仅记录
    errors: list[str]     # 非空 = 阻断
    adjusted_fields: list[str]    # 被策略修改的字段
    effective_data: dict  # 策略调整后的数据（后续必须使用）
```

**消费规则：**
1. `errors` 非空 → 阻断，不进行下游处理
2. `adjusted_fields` 非空 → 后续必须使用 `effective_data`
3. `warnings` 只记录，不阻断
4. **不允许原地修改 `raw_manifest`** — 所有调整在 `effective_data`（deep copy）上进行

**Lane 1 策略：**
- `max_send_count > 1` → `effective_data` 中修剪为 1，记录 `adjusted_fields = ["max_send_count"]`
- `max_send_count < 1` 或类型错误 → 已在类型校验阶段加入 errors，不重复

### 五、Flexible Payload Sanitization / Escaping

| 字段 | 最大长度 | 清洗规则 |
|---|---|---|
| `token_name` | 32 | 移除控制字符 → 截断 → parse_mode 转义 |
| `symbol` | 16 | 移除控制字符 → 截断 → parse_mode 转义 |
| `wallet_short` | 24 | 移除控制字符 → 截断 → parse_mode 转义 |
| `extra_context` | 280 | 序列化 → 移除控制字符 → 截断 |

**parse_mode 转义规则：**

| parse_mode | 转义行为 |
|---|---|
| `HTML` | 转义 `<` `>` `&` |
| `MarkdownV2` | 转义 `_ * [ ] ( ) ~ \` > # + - = \| { } . !` |
| `PlainText` / 无法识别 | 移除 HTML 标签，替换 Markdown 敏感字符为空格/括号 |

> 原则：宁可失去样式，不允许炸卡。

## 从 v1.8H 沉淀的逻辑

| v1.8H 逻辑 | v1.9A 组件 | 状态 |
|---|---|---|
| `load_token_and_chat_id()` — 凭证加载 | `load_candidate()` — 抽象为通用文件加载器 | ✅ 沉淀为通用接口 |
| `verify_group(token, chat_id)` — TG 目标类型验证 | `validate_preview_gate()` — 闸门#4 类型校验 | ✅ 接口已设计，实现在 v1.9B |
| `send_one_message()` — 单条消息发送 | `dry_run_send()` — 干跑发送模拟 | ✅ 核心逻辑已沉淀 |
| `sent_count <= max_send_count` — 发送上限 | `dry_run_send(sent_count, max_send_count)` | ✅ 已实现 |
| 敏感信息不打印 | `build_send_payload()` — 不包含凭证字段 | ✅ 已实现 |
| 发送结果 handoff JSON 格式 | `write_send_handoff()` + `SendResult.to_dict()` | ✅ 已规范化 |
| `api_call()` — TG Bot API 封装 | 未实现在 dry-run 组件中 | ⏳ v1.9B 实现 |
| 实际 TG `sendMessage` 调用 | 未实现在 dry-run 组件中 | ⏳ v1.9B 实现 |

## 运行测试

```bash
cd C:\Users\PC\Desktop\Projects\事件情报系统
python scripts/test_market_radar_sender_v19a.py
```

**前置条件：**
- `results/static_position_v18g_send_candidate.md` 存在
- `results/static_position_v18g_send_candidate.json` 存在
- `results/static_position_v18h_preview_report.md` 存在
- `results/market_radar_v19_manifest_sample.json` 存在

**测试覆盖 (v1.9A-S2 共 25 个测试)：**

### 原 v1.9A-S1 测试（14 个）
1. ✅ 正常 dry-run 通过
2. ✅ max_send_count=1 生效
3. ✅ blocked=true 时拒绝
4. ✅ leak_count > 0 时拒绝
5. ✅ full_address_count > 0 时拒绝
6. ✅ 不调用外部接口
7. ✅ 空候选卡拒绝
8. ✅ 缺失预览报告处理
9. ✅ Handoff 输出格式完整性
10. ✅ 候选卡正文完整地址检测
11. ✅ Schema 文件可读取 (v1.9A-S2)
12. ✅ 完整 manifest 通过校验 (v1.9A-S2)
13. ✅ 缺失 Strict Core 拒绝 (v1.9A-S2)
14. ✅ 缺失 Flexible Payload 警告 (v1.9A-S2)

### v1.9A-S2 新增测试（11 个）
15. ✅ schema_version 缺失 → 拒绝
16. ✅ schema_version 不匹配 → 拒绝
17. ✅ Runtime Source 绝对路径 → 拒绝
18. ✅ Runtime Source ../ 路径逃逸 → 拒绝
19. ✅ leak_count = -1 → 拒绝（值域）
20. ✅ blocked = "false" (string) → 拒绝（类型）
21. ✅ max_send_count = 2 → policy 修剪为 1，raw_manifest 不被原地修改
22. ✅ Flexible Payload 格式炸弹被清洗
23. ✅ MarkdownV2 特殊字符转义
24. ✅ Parse mode / target type 标准化
25. ✅ 不允许的路径前缀 → 拒绝

**输出文件：**
- `results/market_radar_sender_v19a_dryrun_result.json`
- `results/market_radar_sender_v19a_s2_test_report.md`

## Schema 作为单源契约的工作原理

1. **Sender** 调用 `validate_and_apply_policy()` 完成全部校验+策略+清洗，字段规则全部从 schema JSON 读取
2. **Generator** 使用 `build_manifest_from_paths()` 生成符合 schema 的 manifest，自动包含 `schema_version`
3. **History** 可直接消费 manifest，schema 的 `artifact_id`、`created_at`、`project_label` 提供完整追溯链
4. **未来扩展** — 新增字段只需更新 `schemas/market_radar_v19.json`，所有消费者自动感知

## v1.9B Transport 替换验证 — 已完成

v1.9B 实现了 Transport 可替换验证。同一个 Sender Core，在不改 Schema / Gate / Policy / Payload / Handoff 的前提下，可以接入 FakeTransport 和 TGTransportStub。本轮不发送真实 TG 消息，不调用 TG API，不访问外部网络。

### Transport 接口

```python
from market_radar_sender import (
    BaseTransport,       # 抽象 Transport 基类
    FakeTransport,       # 模拟 Transport（成功/失败）
    TGTransportStub,     # TG API 请求构造 Stub（不发网络）
    MarketRadarSender,   # Sender Core（依赖注入）
    TRANSPORT_FAKE,      # "fake"
    TRANSPORT_TELEGRAM,  # "telegram"
)
```

**BaseTransport** 是抽象接口，`send(payload, target, parse_mode) -> SendResult`。Transport 是哑管道，规则：

1. Transport 只接收 sanitized payload，返回 SendResult
2. Transport 不得重新解析 manifest
3. Transport 不得重新执行 gate / policy
4. Transport 不得读取环境变量
5. Transport 不得修改 payload
6. Transport 不得使用 `_unrecognized_payload` 做发送控制

### FakeTransport

返回模拟成功结果，通过 target 后缀模拟 4 种失败模式：
- `"fake"` → 成功
- `"fake:PROVIDER_REJECTION"` → 400 拒绝
- `"fake:NETWORK_TIMEOUT"` → 超时
- `"fake:AUTH_FAILURE"` → 401 认证失败
- `"fake:RATE_LIMITED"` → 429 限流

### TGTransportStub

构造 TG Bot API `sendMessage` 请求 payload，但不调用网络：
- 纯参数构造（`bot_token="dummy"`, `default_chat_id="dummy"`）
- 不调用 `os.getenv`，不读取 `.env`
- chat_id 在 debug 预览中 REDACTED
- `tg_api_called` 始终为 False

### MarketRadarSender

依赖注入模式的 Sender Core：

```python
sender = MarketRadarSender(transport=FakeTransport())
sender = MarketRadarSender(transport=TGTransportStub(bot_token="dummy", default_chat_id="dummy"))

result = sender.send_from_manifest(manifest)
```

- 禁止全局 `dry_run` 开关
- 禁止运行时动态切换 Transport

### SendResult v1.9B 新增字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `success` | `bool` | 发送是否成功 |
| `status_code` | `int` | HTTP 等效状态码 (200, 400, 401, 429, 0) |
| `error_type` | `str` | PROVIDER_REJECTION / NETWORK_TIMEOUT / AUTH_FAILURE / RATE_LIMITED |
| `error_message` | `str` | 人类可读错误信息 |
| `retry_after` | `int\|None` | RATE_LIMITED 时建议重试秒数 |
| `provider` | `str` | "fake" 或 "telegram" |
| `provider_metadata` | `dict` | `transport_name`, `raw_api_response`, `request_payload_preview` |

### 测试覆盖 (v1.9B)

新增 11 个 Transport 测试 (26-36)，总计 39 个测试全部通过：

| # | 测试 | 验证点 |
|---|---|---|
| 26 | FakeTransport 成功返回标准 SendResult | success, status_code, provider_metadata |
| 27 | TGTransportStub 构造 request payload | 无网络, chat_id REDACTED, raw_api_response=None |
| 28 | FakeTransport 4 种失败模拟 | success=False, error_type, error_message |
| 29 | TGTransportStub RATE_LIMITED | retry_after=30, status_code=429 |
| 30 | Transport 不读环境变量 | spy on os.getenv → 0 calls |
| 31 | Transport 不修改 payload | text_preview == original |
| 32 | Transport 不二次转义 | &lt;Link&gt; 保持原样 |
| 33 | _unrecognized_payload 隔离 | 仅放在 provider_metadata，不参与发送控制 |
| 34 | MarketRadarSender + FakeTransport 集成 | 完整 pipeline 通过 |
| 35 | MarketRadarSender + TGTransportStub 集成 | 完整 pipeline 通过 |
| 36 | MarketRadarSender 拒绝非法 Transport | TypeError |

### v1.9B-final 条件检查

是否可以进入 v1.9B-final 用户授权后的真实 TG 单卡测试：

1. ✅ v1.9B 只替换了 Transport，没有改 Schema / Gate / Policy / Payload 核心流程
2. ✅ FakeTransport 和 TGTransportStub 同构（同接口、同 SendResult）
3. ✅ SendResult 统一了成功和失败（success 字段 + error_type/error_message）
4. ✅ provider_metadata 保存了 raw_api_response 和 request_payload_preview
5. ⏳ 需要用户授权真实 bot_token 和 chat_id 后才能做 v1.9B-final

## 下一步 v1.9B-final — 真实 TGTransport 单卡测试

用户授权后：
1. 实现 `TGTransport(bot_token, default_chat_id)` 真实发送
2. 端到端 fake-send 测试（fake TG server → 验证 payload → 返回 mock message_id）
3. 单卡真实发送验证
4. chat 类型运行时验证
5. 凭证加载模块（从环境变量/config 安全加载，不打印）

## 安全约束

| 约束 | v1.9A-S2 状态 | v1.9B 状态 |
|---|---|---|
| 不调用 TG API | ✅ 所有接口均为 dry-run | ✅ 无真实 API 调用 |
| 不发送任何消息 | ✅ 无网络调用 | ✅ 无消息发送 |
| 不启动 loop/daemon/定时任务 | ✅ 单次执行脚本 | ✅ 单次执行脚本 |
| 不调用付费 API | ✅ 无外部 API | ✅ 无外部 API |
| 不打印 token/chat_id/API key/cookie/密码 | ✅ payload 不含凭证字段 | ✅ chat_id REDACTED, dummy 参数 |
| 不写远程 DB | ✅ 仅本地文件写入 | ✅ 仅本地文件写入 |
| 不写生产环境 | ✅ 输出到 results/ 目录 | ✅ 输出到 results/ 目录 |
| 不删除归档脚本 | ✅ 只读引用 | ✅ 只读引用 |
| 不修改候选卡正文 | ✅ 只读加载 | ✅ 只读加载 |
| raw_manifest 不被原地修改 | ✅ deep copy → effective_data | ✅ deep copy → effective_data |
| Transport 不读环境变量 | — | ✅ spy 验证 0 调用 |
| Transport 不修改 sanitized payload | — | ✅ text 完全一致 |
| Transport 不二次转义 | — | ✅ &lt;Link&gt; 保持 |
| _unrecognized_payload 不参与发送控制 | — | ✅ 仅 provider_metadata |

## v1.9B-final Prep — TGTransport 真实适配器准备 + Mock HTTP 测试

v1.9B-final Prep 实现了真正的 `TGTransport` 适配器代码结构，但所有 HTTP 调用通过注入的 `MockHttpClient` 拦截。本轮不读取真实 token，不读取真实 chat_id，不调用 TG API，不访问外部网络，不发送任何消息。

### HttpClient 抽象

```python
from market_radar_sender import (
    HttpClient,        # 抽象 HTTP 客户端接口
    MockHttpClient,    # Mock HTTP 客户端 (测试用)
    TGTransport,       # 真实 TG API Transport
)
```

**HttpClient** 是抽象接口，定义 `post(url, json, timeout) -> dict` 方法。TGTransport 通过注入的 `http_client` 调用，不直接 `import requests`。

**MockHttpClient** 返回预配置的响应，不访问网络：
- `set_response(status_code, response_json)` — 配置返回的 HTTP 响应
- `set_timeout(True)` — 模拟超时
- `last_request` / `request_count` — 用于断言验证

### TGTransport

**构造参数全部显式：**
```python
transport = TGTransport(
    bot_token="test_token",          # 显式传入，不读环境变量
    default_chat_id="-100123",       # 显式传入
    http_client=MockHttpClient(),    # 注入 HTTP 客户端
    api_base_url="http://dummy.local",  # 测试中必须用 dummy
    timeout_seconds=10,              # 默认 10 秒
)
```

**设计原则（Task Spec v1.9B-final Prep）：**
1. ⛔ 不得读取环境变量（os.getenv）
2. ⛔ 不得读取 .env 文件
3. ⛔ 不得打印 bot_token
4. ⛔ 不得打印 chat_id
5. ⛔ 不得修改 sanitized payload
6. ✅ 所有异常必须返回 `SendResult(success=False, ...)`，不得抛出未捕获异常

### SendResult 标准化

TGTransport 返回标准 SendResult，覆盖 5 种失败模式：

| 错误类型 | HTTP 状态码 | 触发条件 | retry_after |
|---|---|---|---|
| PROVIDER_REJECTION | 400 | TG API 返回 400 | — |
| AUTH_FAILURE | 401 | TG API 返回 401 | — |
| RATE_LIMITED | 429 | TG API 返回 429 | 从 parameters.retry_after 提取 |
| NETWORK_TIMEOUT | 0 | TimeoutError 或 OSError | — |
| UNKNOWN_ERROR | 0 | 未预期的异常 | — |

成功响应：
- `success=True`, `status_code=200`, `message_id=<tg_message_id>`
- `sent_count=1`, `provider="telegram"`
- `provider_metadata.raw_api_response` — 完整 TG API 响应
- `provider_metadata.request_payload_preview` — 脱敏后的请求预览

### 防敏感信息泄露

`provider_metadata.request_payload_preview`:
- `chat_id` → `-100XXXX_REDACTED` / `@XXX_REDACTED` / `TG_TARGET_REDACTED`
- `api_endpoint` → `/bot[REDACTED]/sendMessage`
- bot_token 不出现在任何输出中

### 防二次转义

TGTransport 不修改 payload text：
```
输入: &lt;Link&gt;
请求 body: &lt;Link&gt; (不变)
NOT: &amp;lt;Link&amp;gt;
```

### 测试覆盖 (v1.9B-final Prep)

新增 13 个测试 (37-49)，全部通过：

| # | 测试 | 验证点 |
|---|---|---|
| 37 | TGTransport 纯参数构造 | 不读环境变量 |
| 38 | MockHttpClient 成功响应 | success=True, message_id 正确 |
| 39 | HTTP 400 | PROVIDER_REJECTION |
| 40 | HTTP 401 | AUTH_FAILURE |
| 41 | HTTP 429 | RATE_LIMITED + retry_after 正确 |
| 42 | TimeoutError | NETWORK_TIMEOUT |
| 43 | OSError | NETWORK_TIMEOUT |
| 44 | 敏感信息脱敏 | bot_token/chat_id 不出现在输出 |
| 45 | 防二次转义 | &lt;Link&gt; 保持原样 |
| 46 | 文本透传 | 5 种文本变体均不变 |
| 47 | 拒绝无效构造参数 | 空 token / 空 chat_id / 非 HttpClient |
| 48 | 未预期异常 | UNKNOWN_ERROR，不抛出 |
| 49 | MockHttpClient 请求记录 | 用于断言验证 |

### v1.9B-final 就绪状态

| 条件 | 状态 |
|---|---|
| TGTransport 只替换 Transport，没有改 Schema/Gate/Policy/Payload | ✅ |
| MockHttpClient 如何避免真实网络调用 | ✅ 所有 HTTP 通过注入客户端，测试用 MockHttpClient 拦截 |
| SendResult 统一 TG 成功和失败 | ✅ 5 种错误类型全覆盖 |
| provider_metadata 保存 raw response + request preview | ✅ |
| 所有网络异常标准化为 SendResult(success=False) | ✅ |
| 可进入 v1.9B-final 用户授权后的真实 TG 单卡测试 | ✅ 待用户授权 |

## 下一步 v1.9B-final — 用户授权后的真实 TG 单卡测试

用户授权 bot_token 和 chat_id 后：
1. ✅ **v1.9B-final R1 完成**: 实现 `RealHttpClient`（基于 `requests.post`）
2. 用真实 TG Bot API 做端到端单卡发送测试
3. 验证 chat 类型运行时检查
4. 验证 `published_history.jsonl` 持久化（v1.9C）

## v1.9B-final R1 — RealHttpClient 实现 + Monkeypatch 测试

v1.9B-final R1 实现了 `RealHttpClient` 生产适配器代码结构，但所有测试使用 monkeypatch 拦截 `requests.post`。本轮不读取真实 token，不读取真实 chat_id，不调用 TG API，不访问外部网络，不发送任何消息。

### RealHttpClient

```python
from market_radar_sender import (
    RealHttpClient,    # 生产 HTTP 适配器（基于 requests.post）
)
```

**RealHttpClient** 实现 `HttpClient` 接口的 `post(url, json, timeout)` 方法：

**设计原则：**
1. ⛔ 不读取环境变量（os.getenv）
2. ⛔ 不读取 .env 文件
3. ⛔ 不打印 token / chat_id / URL token
4. ✅ 内部使用 `requests.post`
5. ✅ `requests` 在 `post()` 内延迟导入，测试可提前 monkeypatch
6. ✅ 超时 → `TimeoutError`，连接错误 → `OSError`（TGTransport 统一捕获）

**生产用法：**
```python
client = RealHttpClient(timeout=10)
transport = TGTransport(
    bot_token=user_token,
    default_chat_id=user_chat_id,
    http_client=client,
    # api_base_url 默认 https://api.telegram.org
)
result = transport.send(payload, "group", "HTML")
```

### 异常标准化

RealHttpClient 将 requests 异常映射为标准异常：

| requests 异常 | 抛出 | TGTransport 映射为 |
|---|---|---|
| `requests.exceptions.Timeout` | `TimeoutError` | `NETWORK_TIMEOUT` |
| `requests.exceptions.ConnectionError` | `OSError` | `NETWORK_TIMEOUT` |
| `requests.exceptions.RequestException` | `OSError` | `NETWORK_TIMEOUT` |
| HTTP 400 | 正常返回 `status_code=400` | `PROVIDER_REJECTION` |
| HTTP 401 | 正常返回 `status_code=401` | `AUTH_FAILURE` |
| HTTP 429 | 正常返回 `status_code=429` | `RATE_LIMITED` + retry_after |

### 测试覆盖 (v1.9B-final R1)

新增 8 个 monkeypatch 测试 (50-57)，全部通过（总计 63/63）：

| # | 测试 | 验证点 |
|---|---|---|
| 50 | RealHttpClient injection | 可注入 TGTransport |
| 51 | Monkeypatch success | SendResult.success=True, requests.post 被拦截 |
| 52 | Monkeypatch HTTP 400 | PROVIDER_REJECTION |
| 53 | Monkeypatch HTTP 401 | AUTH_FAILURE |
| 54 | Monkeypatch HTTP 429 | RATE_LIMITED + retry_after=45 |
| 55 | Monkeypatch Timeout + ConnectionError | NETWORK_TIMEOUT（两种异常） |
| 56 | Monkeypatch spy | 确认零真实网络访问（全部 dummy.local） |
| 57 | RealHttpClient no env | spy 确认零 os.getenv 调用 |

### 防真实网络三层保护

1. **monkeypatch**: 所有测试 `requests.post = fake_function`
2. **dummy URL**: `api_base_url="http://dummy.local"` 确保 fallback 安全
3. **spy 验证**: Test 56 显式检查所有 URL 不含 `api.telegram.org`

### v1.9B-final R2 就绪状态

| 条件 | 状态 |
|---|---|
| RealHttpClient 实现 HttpClient 接口 | ✅ |
| RealHttpClient 可注入 TGTransport | ✅ |
| 8 种 monkeypatch 场景全覆盖 | ✅ |
| requests.post 被 monkeypatch | ✅ |
| 零真实网络访问 | ✅ |
| 零环境变量读取 | ✅ |
| 零 .env 读取 | ✅ |
| SendResult 统一真实 HTTP 成功和失败 | ✅ |
| 5 种错误类型全覆盖 | ✅ |
| **可进入 R2：真实 TG 单卡测试** | ✅ (需用户授权) |

### 下一步 v1.9B-final R2

用户授权 bot_token 和 chat_id 后：
1. 将 `api_base_url` 改为真实 TG API（或保留默认）
2. 将 `bot_token` / `default_chat_id` 替换为真值
3. 发送 1 张测试卡
4. 验证 message_id 返回 + chat 类型运行时检查
5. 为 v1.9C published_history.jsonl 做准备

## 安全约束

| 约束 | v1.9A-S2 状态 | v1.9B 状态 | v1.9B-final Prep 状态 | v1.9B-final R1 状态 |
|---|---|---|---|---|
| 不调用 TG API | ✅ 所有接口均为 dry-run | ✅ 无真实 API 调用 | ✅ MockHttpClient 拦截 | ✅ 全部 monkeypatched |
| 不发送任何消息 | ✅ 无网络调用 | ✅ 无消息发送 | ✅ Mock 响应 | ✅ Mock 响应 |
| 不启动 loop/daemon/定时任务 | ✅ 单次执行脚本 | ✅ 单次执行脚本 | ✅ 单次执行脚本 | ✅ 单次执行脚本 |
| 不调用付费 API | ✅ 无外部 API | ✅ 无外部 API | ✅ 无外部 API | ✅ 无外部 API |
| 不打印 token/chat_id/API key/cookie/密码 | ✅ payload 不含凭证字段 | ✅ chat_id REDACTED, dummy 参数 | ✅ REDACTED + api_endpoint 脱敏 | ✅ 零打印 |
| 不写远程 DB | ✅ 仅本地文件写入 | ✅ 仅本地文件写入 | ✅ 仅本地文件写入 | ✅ 仅本地文件写入 |
| 不写生产环境 | ✅ 输出到 results/ 目录 | ✅ 输出到 results/ 目录 | ✅ 输出到 results/ 目录 | ✅ 输出到 results/ 目录 |
| 不删除归档脚本 | ✅ 只读引用 | ✅ 只读引用 | ✅ 只读引用 | ✅ 只读引用 |
| 不修改候选卡正文 | ✅ 只读加载 | ✅ 只读加载 | ✅ 只读加载 | ✅ 只读加载 |
| raw_manifest 不被原地修改 | ✅ deep copy → effective_data | ✅ deep copy → effective_data | ✅ deep copy → effective_data | ✅ deep copy → effective_data |
| Transport 不读环境变量 | — | ✅ spy 验证 0 调用 | ✅ spy 验证 0 调用 | ✅ spy 验证 0 调用 |
| Transport 不修改 sanitized payload | — | ✅ text 完全一致 | ✅ text 完全一致 | ✅ text 完全一致 |
| Transport 不二次转义 | — | ✅ &lt;Link&gt; 保持 | ✅ &lt;Link&gt; 保持 | ✅ &lt;Link&gt; 保持 |
| _unrecognized_payload 不参与发送控制 | — | ✅ 仅 provider_metadata | ✅ 仅 provider_metadata | ✅ 仅 provider_metadata |
| bot_token 不出现在输出中 | — | — | ✅ REDACTED | ✅ REDACTED |
| chat_id 不出现在输出中 | — | — | ✅ REDACTED | ✅ REDACTED |
| RealHttpClient 不读环境变量 | — | — | — | ✅ spy 验证 |
| RealHttpClient 不读 .env | — | — | — | ✅ 无 dotenv |
| RealHttpClient 不打印 token | — | — | — | ✅ 无 print/log |
| requests.post 被 monkeypatch | — | — | — | ✅ 全部测试 |

## v1.9C — published_history.jsonl 持久化 + 脱敏

v1.9C 将 v1.9B-final R2 的真实发送结果沉淀为结构化历史资产库 `published_history.jsonl`，修复 `raw_api_response` 中 `chat.id` / `chat.title` 持久化泄露风险，并补齐 `requirements.txt` 中的 `requests>=2.28.0` 依赖声明。

本轮不发送任何 TG 消息，不调用 TG API，不访问外部网络。

### 新增文件

| 文件 | 说明 |
|---|---|
| `scripts/market_radar_history.py` | 历史记录构建、脱敏、写入、去重模块 |
| `scripts/test_market_radar_history_v19c.py` | 11 项测试（含 6 项核心 + 5 项扩展） |
| `data/market_radar/published_history.jsonl` | 结构化历史资产库（JSONL 格式） |

### 修改文件

| 文件 | 修改内容 |
|---|---|
| `requirements.txt` | `requests` → `requests>=2.28.0`（锚定版本） |

### published_history.jsonl 记录格式 (v1.9C)

每条记录为一行 JSON，包含 27 个字段：

| 字段 | 说明 |
|---|---|
| `history_version` | 历史记录格式版本 (`v1.9C`) |
| `schema_version` | 发送时使用的 schema 版本 (`1.9A-S2`) |
| `project_label` | 项目标签 (`market_radar`) |
| `lane` | 执行通道编号 |
| `artifact_id` | 工件标识符 |
| `created_at` / `published_at` | 时间戳 (UTC+8) |
| `provider` | 发送提供商 (`telegram`) |
| `target_type` | 目标类型 (`group`/`supergroup`) |
| `target_label_redacted` | 脱敏后的目标标签 (`[REDACTED]`) |
| `message_id` | TG 消息 ID |
| `sent_count` | 发送数量 |
| `status_code` | HTTP 状态码 |
| `success` | 发送是否成功 |
| `error_type` / `error_message` / `retry_after` | 错误信息 |
| `parse_mode` | 解析模式 (`HTML`) |
| `candidate_md_path` / `candidate_json_path` | 候选卡路径 |
| `preview_report_path` | 预览报告路径 |
| `send_result_path` | 发送结果路径 |
| `handoff_path` | handoff 路径 |
| `policy_status` / `policy_warnings` / `adjusted_fields` | 策略状态 |
| `provider_metadata_redacted` | 脱敏后的 provider 元数据 |
| `source_result_file` | 源结果文件路径 |

### 脱敏规则

在写入 `published_history.jsonl` 前，`provider_metadata` 经过深度脱敏：

1. `raw_api_response.result.chat.id` → `-REDACTED_CHAT_ID`（保留负号前缀）
2. `raw_api_response.result.chat.title` → `[REDACTED]`
3. `request_payload_preview.api_endpoint` → `/bot[REDACTED]`
4. 任何包含 `token` 关键字的字段值 → `[REDACTED_BOT_TOKEN]`
5. 任何匹配 bot token 格式的字符串（digits:alphanumeric_hash）→ `[REDACTED_BOT_TOKEN]`
6. 递归扫描所有嵌套层级确保无遗漏
7. 写入前执行 `_deep_scan_sensitive()` 验证零泄露，发现敏感信息残留则输出 blocker

### 去重 / 幂等

1. `provider + message_id` 重复 → 跳过（不追加）
2. `artifact_id + message_id` 重复 → 跳过（不追加）
3. 重复运行本任务时，`published_history.jsonl` 行数不增加
4. 去重结果写入 test report / handoff

### 测试覆盖 (v1.9C)

| # | 测试 | 验证点 |
|---|---|---|
| 1 | test_build_history_record_from_r2 | 从 R2 send result 构建完整 history record |
| 2 | test_chat_id_redacted | raw_api_response.result.chat.id 被脱敏 |
| 3 | test_no_token_or_chat_id_leak | provider_metadata 零 token/完整 chat_id |
| 4 | test_write_history_succeeds | published_history.jsonl 写入成功 |
| 5 | test_dedup_same_message_id | 重复写入同一 message_id 不重复追加 |
| 6 | test_different_records_coexist | 不同 message_id 可共存 |
| 7 | test_dedup_by_artifact_message_id | artifact_id + message_id 去重 |
| 8 | test_deep_redact_nested | 深层嵌套 chat 对象脱敏 |
| 9 | test_redact_bot_token_strings | bot token 格式字符串检测和脱敏 |
| 10 | test_is_duplicate_provider_message_id | is_duplicate 逻辑验证 |
| 11 | test_requirements_has_requests | requirements.txt 锚定 requests>=2.28.0 |

### v1.9C 安全约束

| 约束 | 状态 |
|---|---|
| 不调用 TG API | ✅ |
| 不发送任何消息 | ✅ |
| 不访问外部网络 | ✅ |
| 不启动 loop/daemon/定时任务 | ✅ |
| 不调用付费 API | ✅ |
| 不读取/不打印 token/chat_id/API key/cookie/密码 | ✅ |
| 不写远程 DB | ✅ |
| 不写生产环境 | ✅ |
| 不删除文件 | ✅ |
| chat.id 已脱敏 | ✅ `-REDACTED_CHAT_ID` |
| chat.title 已脱敏 | ✅ `[REDACTED]` |
| provider_metadata 零敏感信息 | ✅ deep_scan 通过 |
| 幂等去重 | ✅ provider+message_id, artifact_id+message_id |
| requirements.txt 已锚定 requests | ✅ `requests>=2.28.0` |

### 验证结果

- **R2 真实发送 message_id=2195** 已成功沉淀进 `published_history.jsonl`（1 条记录）
- `raw_api_response.result.chat.id` 脱敏为 `-REDACTED_CHAT_ID`
- `raw_api_response.result.chat.title` 脱敏为 `[REDACTED]`
- 零敏感信息残留（deep scan 0 violations）
- 重复运行不会重复追加（provider=telegram + message_id=2195 已存在 → 跳过）
- 可以进入 v1.10 TTL / 去重 / Buffer 合并设计

### 核心模块接口

```python
from market_radar_history import (
    build_history_record,              # 从 send result 构建记录
    write_published_history,           # 写入 JSONL（带去重）
    is_duplicate,                      # 去重检查
    _deep_redact,                      # 深度脱敏
    _deep_scan_sensitive,              # 深度扫描敏感信息
    _load_existing_records,            # 加载已有记录
    build_and_write_from_send_result,  # 完整 pipeline
)
```
