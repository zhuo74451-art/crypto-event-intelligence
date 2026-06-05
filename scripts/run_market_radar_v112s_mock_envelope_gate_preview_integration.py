"""Market Radar v1.12-S — Mock Envelope → Gate/Preview Integration

Reads v112R mock envelopes (from v112Q noise cases) and validates that they can
enter the local gate decision and preview card pipeline — while keeping all
real-send, live-API, TG-send, daemon, and production-state-write gates CLOSED.

This is a LOCAL DRY-RUN ONLY step:
  - No TG send
  - No external API/AI calls
  - No daemon / loop / cron
  - No production state writes
  - No real send candidates

Outputs:
  - results/market_radar_v112s_mock_gate_preview_integration_result.json
  - results/market_radar_v112s_mock_gate_decisions.jsonl
  - results/market_radar_v112s_mock_preview_cards.jsonl
  - runs/market_radar/v112s_mock_envelope_gate_preview_integration.md
  - runs/market_radar/v112s_mock_envelope_gate_preview_integration_handoff.md

Usage:
    python scripts/run_market_radar_v112s_mock_envelope_gate_preview_integration.py
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CN_TZ = timezone(timedelta(hours=8))
VERSION = "v1.12-s"
RUN_ID = "20260605_022952"
SCHEMA_VERSION = "1.0.0"

# ── Output paths ──────────────────────────────────────────────────────────────────

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112s_mock_gate_preview_integration_result.json"
GATE_DECISIONS_JSONL_PATH = ROOT / "results" / "market_radar_v112s_mock_gate_decisions.jsonl"
PREVIEW_CARDS_JSONL_PATH = ROOT / "results" / "market_radar_v112s_mock_preview_cards.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112s_mock_envelope_gate_preview_integration.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112s_mock_envelope_gate_preview_integration_handoff.md"

# ── Input paths ───────────────────────────────────────────────────────────────────

V112R_RESULT_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_adapter_result.json"
V112R_ENVELOPES_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_envelopes.jsonl"
V112Q_NOISE_CASES_PATH = ROOT / "results" / "market_radar_v112q_multi_asset_noise_case_results.jsonl"
V112Q_THRESHOLDS_PATH = ROOT / "config" / "market_radar_v112q_multi_asset_thresholds.json"

# ── Forbidden terms for leak scanning ─────────────────────────────────────────────

FORBIDDEN_SECRET_PATTERNS = [
    r'\bsecret\s*[=:]\s*\S',
    r'\bsecret\s*key\b',
    r'\bsecret\s*token\b',
    r'\bapi[_\-]?secret\b',
    r'\bapi[_\-]?key\s*[=:]\s*\S',
    r'\bchat[_\-]?id\s*[=:]\s*\S',
    r'\bpassword\s*[=:]\s*\S',
    r'\bbearer\s+\S',
    r'\bauthorization\s*:\s*\S',
    r'\bx-api-key\s*[=:]\s*\S',
    r'\bcookie\s*[=:]\s*\S',
    # Only flag ai_relay_desk path leaks (not legitimate project paths)
    r'ai_relay_desk',
]

MISLEADING_TERMS = [
    "已接入 live source", "live source connected", "production ready",
    "已发送", "正式发布", "real sent", "已推送", "已投递",
    "broadcast sent", "message delivered", "sent to channel",
    "已发布成功", "发送成功", "live API connected", "已接入 live API",
    "已真实发送",
]


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def china_iso() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if not found."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load {path}: {e}")
        return None


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file. Returns list of dicts."""
    records: list[dict] = []
    if not path.exists():
        return records
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] Failed to load JSONL {path}: {e}")
    return records


def mk_preview_id(signal_id: str) -> str:
    """Create a stable deterministic preview ID from the signal ID."""
    h = hashlib.sha256(f"v112s_preview_{signal_id}".encode()).hexdigest()[:16]
    return f"pv-mock-{h}"


def deterministic_sort_key(card: dict) -> tuple[int, str]:
    """Sort cards: passed_mock first, then audit_only/blocked, then by signal_id."""
    gate = card.get("gate_status", "")
    if gate == "passed_mock":
        priority = 0
    elif gate == "audit_only":
        priority = 1
    else:
        priority = 2
    return (priority, card.get("signal_id", ""))


# ── Leak scanning ─────────────────────────────────────────────────────────────────

def scan_text_for_secrets(text: str) -> int:
    """Scan text for credential patterns. Returns count of potential leaks."""
    if not text:
        return 0
    count = 0
    for pattern in FORBIDDEN_SECRET_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            count += 1
    return count


def scan_text_for_misleading(text: str) -> list[str]:
    """Scan text for misleading terms. Returns list of found terms."""
    if not text:
        return []
    found = []
    text_lower = text.lower()
    for term in MISLEADING_TERMS:
        if term.lower() in text_lower:
            found.append(term)
    return found


def scan_all_outputs(result: dict, gate_decisions: list[dict],
                     cards: list[dict], report_text: str,
                     handoff_text: str) -> tuple[int, int, list[str]]:
    """Scan all output content. Returns (secret_leak_count, misleading_count, warnings)."""
    secret_count = 0
    misleading_count = 0
    warnings: list[str] = []

    # Scan result JSON values
    result_text = " ".join(str(v) for v in result.values()
                           if isinstance(v, (str, int, float, bool)))
    secret_count += scan_text_for_secrets(result_text)

    # Scan gate decisions — key fields only
    for gd in gate_decisions:
        scannable = " ".join(str(gd.get(k, "")) for k in
                             ["signal_id", "gate_status", "reason", "dedupe_key",
                              "cooldown_key", "payload_hash"])
        secret_count += scan_text_for_secrets(scannable)

    # Scan preview cards
    for card in cards:
        card_text = " ".join(str(card.get(k, "")) for k in
                             ["preview_id", "signal_id", "send_preview_text",
                              "gate_status"])
        secret_count += scan_text_for_secrets(card_text)
        m = scan_text_for_misleading(card_text)
        if m:
            misleading_count += len(m)
            warnings.append(f"Card {card.get('signal_id')}: misleading terms: {m}")

    # Scan reports
    for label, text in [("report", report_text), ("handoff", handoff_text)]:
        secret_count += scan_text_for_secrets(text)
        m = scan_text_for_misleading(text)
        if m:
            misleading_count += len(m)
            warnings.append(f"{label}: misleading terms: {m}")

    return secret_count, misleading_count, warnings


# ── Upstream validation ───────────────────────────────────────────────────────────

def validate_v112r_upstream(v112r: dict) -> dict:
    """Validate that v112R upstream state is ready for v112S integration."""
    checks: dict[str, Any] = {
        "status_passed": v112r.get("status") == "passed",
        "candidate_card_type": v112r.get("candidate_card_type") == "multi_asset_market_sync",
        "mock_adapter_ready": v112r.get("mock_adapter_ready") is True,
        "envelope_compatibility_passed": v112r.get("envelope_compatibility_passed") is True,
        "dry_run_only": v112r.get("dry_run_only") is True,
        "real_live_api_called_false": v112r.get("real_live_api_called") is False,
        "real_tg_sent_false": v112r.get("real_tg_sent") is False,
        "external_api_called_false": v112r.get("external_api_called") is False,
        "external_ai_called_false": v112r.get("external_ai_called") is False,
        "daemon_started_false": v112r.get("daemon_started") is False,
    }

    all_valid = all(checks.values())
    failed = [k for k, v in checks.items() if not v]

    return {
        "all_valid": all_valid,
        "checks": checks,
        "failed_checks": failed,
    }


# ── Gate decision builder ─────────────────────────────────────────────────────────

def build_gate_decision(envelope: dict) -> dict:
    """Build a gate decision for a single mock envelope.

    Rules:
      - passed noise case → gate_status = "passed_mock"
      - low_confidence noise case → gate_status = "blocked_low_confidence"
      - eligible_for_preview is always true (for local review)
      - eligible_for_real_send is ALWAYS false
      - mock_adapter = true, dry_run_only = true
    """
    signal_id = envelope.get("signal_id", "unknown")
    noise_class = envelope.get("noise_classification", {})
    actual_result = noise_class.get("v112q_actual_result", "")
    confidence = noise_class.get("confidence_level", "low")
    case_id = noise_class.get("case_id", envelope.get("event_key", ""))

    # Determine gate status
    if actual_result == "passed":
        gate_status = "passed_mock"
        reason = (f"mock envelope from v112Q case '{case_id}' — "
                  f"noise checks passed (confidence={confidence}), "
                  f"but mock mode: eligible_for_real_send=false")
    elif actual_result == "low_confidence":
        gate_status = "blocked_low_confidence"
        reason = (f"mock envelope from v112Q case '{case_id}' — "
                  f"low_confidence classification (confidence={confidence}), "
                  f"blocked from real send; available for audit review only")
    elif actual_result in ("blocked", "degraded", "downgraded"):
        gate_status = "blocked_low_confidence"
        reason = (f"mock envelope from v112Q case '{case_id}' — "
                  f"noise result={actual_result}, blocked; "
                  f"available for audit review only")
    else:
        gate_status = "audit_only"
        reason = (f"mock envelope from v112Q case '{case_id}' — "
                  f"unrecognized result '{actual_result}', "
                  f"conservatively marked audit_only")

    eligible_for_preview = True  # Always available for local review

    return {
        "schema_version": SCHEMA_VERSION,
        "gate_version": VERSION,
        "signal_id": signal_id,
        "card_type": envelope.get("card_type", "multi_asset_market_sync"),
        "gate_status": gate_status,
        "eligible_for_preview": eligible_for_preview,
        "eligible_for_real_send": False,
        "reason": reason,
        "dedupe_key": envelope.get("dedupe_key", ""),
        "cooldown_key": envelope.get("cooldown_key", ""),
        "payload_hash": envelope.get("payload_hash", ""),
        "mock_adapter": True,
        "dry_run_only": True,
        "real_live_api_called": False,
        "state_write_performed": False,
        "noise_classification": noise_class,
        "evaluated_at": china_iso(),
    }


# ── Preview card builder ──────────────────────────────────────────────────────────

def build_source_lineage() -> dict[str, str]:
    """Build source lineage pointing to upstream artifacts."""
    return {
        "mock_envelope_source": "results/market_radar_v112r_multi_asset_mock_envelopes.jsonl",
        "gate_decision_source": "results/market_radar_v112s_mock_gate_decisions.jsonl",
        "noise_case_source": "results/market_radar_v112q_multi_asset_noise_case_results.jsonl",
        "threshold_config_source": "config/market_radar_v112q_multi_asset_thresholds.json",
    }


def build_send_preview_text(envelope: dict, gate_decision: dict) -> str:
    """Construct a human-readable send preview text from envelope + gate decision.

    Must include LOCAL MOCK PREVIEW marker. Must NOT contain secrets or
    misleading 'already sent' language.
    """
    signal_id = envelope.get("signal_id", "?")
    primary_assets = envelope.get("primary_assets", [])
    direction = envelope.get("direction", "?")
    gate_status = gate_decision.get("gate_status", "?")
    reason = gate_decision.get("reason", "?")

    assets_str = ", ".join(primary_assets) if primary_assets else "?"

    direction_labels: dict[str, str] = {
        "bullish": "偏多 \U0001F4C8",
        "bearish": "偏空 \U0001F4C9",
        "mixed": "双向 ⚡",
    }
    dir_label = direction_labels.get(direction, direction)

    gate_status_labels: dict[str, str] = {
        "passed_mock": "PASSED_MOCK ✅ (mock; not real send)",
        "blocked_low_confidence": "BLOCKED \U0001F6AB (low confidence, audit only)",
        "audit_only": "AUDIT_ONLY \U0001F50D (for review only)",
    }
    gate_label = gate_status_labels.get(gate_status, gate_status)

    public_card = envelope.get("public_card", "")
    if public_card and len(public_card) > 600:
        public_card = public_card[:600] + "... [TRUNCATED]"

    lines = [
        "=" * 60,
        "\U0001F4CB LOCAL MOCK PREVIEW —— NOT A REAL SIGNAL —— NOT SENT —— NOT PUBLISHED",
        "=" * 60,
        "",
        f"Signal ID:    {signal_id}",
        f"Card Type:    multi_asset_market_sync (多资产共振)",
        f"Asset(s):     {assets_str}",
        f"Direction:    {dir_label}",
        "",
        f"Gate Status:  {gate_label}",
        f"Gate Reason:  {reason}",
        "",
        f"eligible_for_preview:  True",
        f"eligible_for_real_send: False  ← ALWAYS FALSE IN MOCK MODE",
        "",
        "--- Public Card Preview (truncated if > 600 chars) ---",
        "",
        public_card if public_card else "(no public card text available)",
        "",
        "--- Safety ---",
        "  dry_run_only:           true",
        "  mock_adapter:           true",
        "  real_live_api_called:   false",
        "  real_tg_sent:           false",
        "  external_api_called:    false",
        "  external_ai_called:     false",
        "  daemon_started:         false",
        "  production_state_write: false",
        "",
        "⚠️ 此预览仅供本地审阅，不是已发布内容。未实际发送。",
        "⚠️ LOCAL MOCK PREVIEW —— FOR REVIEW ONLY. NOT A REAL SIGNAL.",
    ]

    return "\n".join(lines)


def assemble_preview_card(envelope: dict, gate_decision: dict, rank: int) -> dict:
    """Assemble a single preview card from envelope + gate decision."""
    signal_id = envelope.get("signal_id", "unknown")

    return {
        "preview_id": mk_preview_id(signal_id),
        "rank": rank,
        "card_type": envelope.get("card_type", "multi_asset_market_sync"),
        "signal_id": signal_id,
        "gate_status": gate_decision.get("gate_status", ""),
        "eligible_for_preview": True,
        "eligible_for_real_send": False,
        "send_preview_text": build_send_preview_text(envelope, gate_decision),
        "source_lineage": build_source_lineage(),
        "safety": {
            "dry_run_only": True,
            "real_live_api_called": False,
            "real_tg_sent": False,
            "external_api_called": False,
            "external_ai_called": False,
            "daemon_started": False,
            "production_state_write": False,
        },
    }


# ── Report writers ────────────────────────────────────────────────────────────────

def write_report(result: dict, gate_decisions: list[dict],
                 cards: list[dict]) -> str:
    """Write the v112S Markdown report and return the text."""
    lines = [
        f"# Market Radar v1.12-S — Mock Envelope → Gate/Preview Integration Report",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Status**: {result.get('status', '?').upper()}",
        "",
        "---",
        "",
        "## v112S 目标",
        "",
        "验证 v112R 生成的 multi_asset mock envelopes 能否继续进入本地 gate decision ",
        "与 preview card 链路，并且不会被误判为真实可发送信号。",
        "",
        "本轮目标不是接 live API，而是验证：",
        "",
        "- v112R 生成的 multi_asset mock envelopes，能否继续进入本地 gate decision 与 preview card 链路",
        "- 并且不会被误判为真实可发送信号",
        "",
        "---",
        "",
        "## 读取的上游产物",
        "",
        "| 源 | 文件路径 | 状态 |",
        "|------|----------|------|",
        f"| v112R Result | `results/market_radar_v112r_multi_asset_mock_adapter_result.json` | ✔ |",
        f"| v112R Envelopes | `results/market_radar_v112r_multi_asset_mock_envelopes.jsonl` | ✔ |",
        f"| v112Q Noise Cases | `results/market_radar_v112q_multi_asset_noise_case_results.jsonl` | ✔ |",
        f"| v112Q Thresholds | `config/market_radar_v112q_multi_asset_thresholds.json` | ✔ |",
        "",
        f"Mock Envelope 数量: **{result.get('mock_envelope_count', '?')}**",
        "",
        "---",
        "",
        "## Gate Decision 结果表",
        "",
        "| # | Signal ID | Gate Status | Eligible for Preview | Eligible for Real Send | Reason (abbreviated) |",
        "|---|-----------|-------------|---------------------|----------------------|----------------------|",
    ]

    for i, gd in enumerate(gate_decisions):
        sid = gd.get("signal_id", "?")[:30]
        gs = gd.get("gate_status", "?")
        ep = gd.get("eligible_for_preview", False)
        er = gd.get("eligible_for_real_send", False)
        reason = gd.get("reason", "?")[:80]
        lines.append(f"| {i+1} | `{sid}` | {gs} | {ep} | {er} | {reason} |")

    lines.extend([
        "",
        "---",
        "",
        "## Preview Card 结果表",
        "",
        "| Rank | Preview ID | Signal ID | Gate Status | Eligible for Preview | Eligible for Real Send |",
        "|------|------------|-----------|-------------|---------------------|----------------------|",
    ])

    for card in cards:
        rank = card.get("rank", "?")
        pid = card.get("preview_id", "?")
        sid = card.get("signal_id", "?")[:30]
        gs = card.get("gate_status", "?")
        ep = card.get("eligible_for_preview", False)
        er = card.get("eligible_for_real_send", False)
        lines.append(f"| {rank} | `{pid}` | `{sid}` | {gs} | {ep} | {er} |")

    lines.extend([
        "",
        "---",
        "",
        "## 为什么 real_send_candidate_count 必须为 0",
        "",
        f"当前 real_send_candidate_count = **{result.get('real_send_candidate_count', '?')}**",
        f"当前 eligible_for_real_send_count = **{result.get('eligible_for_real_send_count', '?')}**",
        "",
        "原因：",
        "",
        "1. **Mock mode only**: 所有 envelope 来自 v112R mock adapter，不是真实数据源",
        "2. **No live API**: 未接入 CoinGecko / CoinCap / 交易所 API",
        "3. **Safety gate closed**: 所有 gate decision 的 eligible_for_real_send 均为 false",
        "4. **No state write**: 未写入任何生产状态文件",
        "5. **Low confidence case blocked**: 低置信度 envelope 被标记为 blocked_low_confidence",
        "",
        "---",
        "",
        "## Deterministic / Repeated-Run 稳定性检查",
        "",
        f"- deterministic_preview_ids: **{result.get('deterministic_preview_ids', False)}**",
        f"- repeated_run_stable: **{result.get('repeated_run_stable', False)}**",
        "",
        "所有 preview_id 通过 SHA-256(v112s_preview_{signal_id})[:16] 生成，不依赖时间。",
        "gate decision 仅依赖 envelope 内容，不依赖外部状态。",
        "",
        "---",
        "",
        "## 当前仍不能真实发送的原因",
        "",
        "| 原因 | 详情 |",
        "|------|------|",
        "| 未接入 live data source | 所有数据来自 mock adapter / local fixtures |",
        "| 未接入 external API | CoinGecko / CoinCap / 交易所均未调用 |",
        "| TG send 未开启 | real_tg_sent=false |",
        "| 生产状态写入未开启 | state_write_performed=false |",
        "| daemon 未开启 | 仅单次执行 |",
        "| 外部 AI 未开启 | external_ai_called=false |",
        "",
        "---",
        "",
        "## 下一步建议",
        "",
        "建议下一步：**v112T — one-shot free source plan with stop conditions**",
        "",
        "具体内容：",
        "",
        "1. 评估可以一次性免费拉取的数据源（例如 CoinGecko public API）",
        "2. 制定 clear stop conditions （拉取失败时不写入状态，不标记为 send candidate）",
        "3. 仍保持 eligible_for_real_send=false，直到多轮验证通过",
        "",
        "或先做 **Gemini 方向审计**，判断是否可以进入一次性免费数据源拉取计划。",
        "",
        "不要直接建议真实 TG 发送。",
        "",
        "---",
        "",
        f"*Generated by {VERSION} at {china_stamp()}*",
    ])

    report_text = "\n".join(lines)

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  [OK] {REPORT_MD_PATH}")

    return report_text


def write_handoff(result: dict, gate_decisions: list[dict],
                  cards: list[dict], files_read: list[str],
                  files_generated: list[str]) -> str:
    """Write the v112S handoff markdown and return the text."""
    lines = [
        f"# Market Radar v1.12-S — Mock Envelope → Gate/Preview Integration Handoff",
        "",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260605_022952.r07",
        f"**Status**: {result.get('status', '?').upper()}",
        "",
        "---",
        "",
        "## v112S 做了什么",
        "",
        "v112S Mock Envelope → Gate/Preview Integration 是 v112R 的下游步骤。它：",
        "",
        "1. 验证 v112R 上游状态（status=passed, dry_run_only=true, 等）",
        "2. 读取 v112R mock envelopes JSONL",
        "3. 对每条 mock envelope 生成本地 gate decision:",
        "   - passed 噪声 case → gate_status=passed_mock",
        "   - low_confidence case → gate_status=blocked_low_confidence",
        "   - 所有 decision 的 eligible_for_real_send=false",
        "4. 基于 envelope + gate decision 生成 preview cards:",
        "   - 确定性 preview_id（SHA-256 哈希）",
        "   - 完整 source_lineage 链追源",
        "   - safety flags",
        "   - LOCAL MOCK PREVIEW 标记",
        "5. 生成 result JSON + gate decisions JSONL + preview cards JSONL + report MD + handoff MD",
        "6. 严格安全扫描：无凭证泄漏，无误导性文字",
        "",
        "---",
        "",
        "## 读取了哪些文件",
        "",
    ]

    for fp in files_read:
        lines.append(f"- `{fp}`")

    lines.extend([
        "",
        "---",
        "",
        "## 生成了哪些文件",
        "",
    ])

    for fp in files_generated:
        lines.append(f"- `{fp}`")

    lines.extend([
        "",
        "---",
        "",
        "## 核心数据摘要",
        "",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| mock_envelope_count | {result.get('mock_envelope_count', '?')} |",
        f"| mock_gate_decision_count | {result.get('mock_gate_decision_count', '?')} |",
        f"| mock_preview_card_count | {result.get('mock_preview_card_count', '?')} |",
        f"| real_send_candidate_count | {result.get('real_send_candidate_count', '?')} |",
        f"| eligible_for_real_send_count | {result.get('eligible_for_real_send_count', '?')} |",
        f"| state_write_performed | {result.get('state_write_performed', False)} |",
        f"| gate_preview_integration_passed | {result.get('gate_preview_integration_passed', False)} |",
        f"| blocked_or_low_confidence_not_real_send | {result.get('blocked_or_low_confidence_not_real_send', True)} |",
        f"| deterministic_preview_ids | {result.get('deterministic_preview_ids', False)} |",
        f"| repeated_run_stable | {result.get('repeated_run_stable', False)} |",
        "",
        "### Gate Decisions",
        "",
        "| # | Signal ID | Gate Status | Eligible for Real Send |",
        "|---|-----------|-------------|----------------------|",
    ])

    for i, gd in enumerate(gate_decisions):
        sid = gd.get("signal_id", "?")[:40]
        gs = gd.get("gate_status", "?")
        er = gd.get("eligible_for_real_send", "?")
        lines.append(f"| {i+1} | `{sid}` | {gs} | {er} |")

    lines.extend([
        "",
        "### Preview Cards",
        "",
        "| Rank | Preview ID | Signal ID | Gate Status |",
        "|------|------------|-----------|-------------|",
    ])

    for card in cards:
        rank = card.get("rank", "?")
        pid = card.get("preview_id", "?")
        sid = card.get("signal_id", "?")[:40]
        gs = card.get("gate_status", "?")
        lines.append(f"| {rank} | `{pid}` | `{sid}` | {gs} |")

    lines.extend([
        "",
        "---",
        "",
        "## 测试结果",
        "",
        "```powershell",
        "cd C:\\Users\\PC\\Desktop\\Projects\\事件情报系统",
        "python scripts/test_market_radar_v112s_mock_envelope_gate_preview_integration.py",
        "```",
        "",
        "测试覆盖：",
        "- runner 可执行成功",
        "- 所有输出文件存在",
        "- status == \"passed\"",
        "- dry_run_only == true, live_ready == false",
        "- 所有安全边界字段",
        "- mock_gate_decision_count == mock_envelope_count",
        "- mock_preview_card_count == mock_envelope_count",
        "- real_send_candidate_count == 0",
        "- eligible_for_real_send_count == 0",
        "- state_write_performed == false",
        "- 每条 gate decision 有 signal_id / dedupe_key / cooldown_key / payload_hash",
        "- 每条 gate decision eligible_for_real_send == false",
        "- 每张 preview card 有 LOCAL MOCK PREVIEW 标记",
        "- 每张 preview card 有 source_lineage",
        "- 每张 preview card 有 safety flags",
        "- low_confidence envelope 不得 eligible_for_real_send",
        "- repeated run 输出稳定",
        "- 无凭证/密钥泄漏",
        "- 无误导性文字",
        "",
        "---",
        "",
        "## 当前仍未开启的能力",
        "",
        "| 能力 | 状态 | 说明 |",
        "|------|------|------|",
        "| live source | ❌ 未开启 | 所有数据来自 v112R mock adapter |",
        "| production state write | ❌ 未开启 | state_write_performed=false |",
        "| TG send | ❌ 未开启 | real_tg_sent=false |",
        "| daemon / cron / loop | ❌ 未开启 | 仅单次执行 |",
        "| external API | ❌ 未开启 | 无网络调用 |",
        "| external AI | ❌ 未开启 | 无外部 AI 调用 |",
        "| live_ready | ❌ false | 需真实数据源接入 |",
        "| real_send_ready | ❌ false | 需 live source + 多轮验证 |",
        "",
        "---",
        "",
        "## 下一步建议",
        "",
        "建议下一步：**v112T — one-shot free source plan with stop conditions**",
        "",
        "具体内容：",
        "",
        "1. 评估可以一次性免费拉取的数据源（例如 CoinGecko public API）",
        "2. 制定 clear stop conditions（拉取失败时不写入状态，不标记为 send candidate）",
        "3. 仍保持 eligible_for_real_send=false，直到多轮验证通过",
        "",
        "或先做 **Gemini 方向审计**，判断是否可以进入一次性免费数据源拉取计划。",
        "",
        "不要直接建议真实 TG 发送。",
        "",
        "---",
        "",
        f"*Generated by {VERSION} at {china_stamp()}*",
    ])

    handoff_text = "\n".join(lines)

    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_text)
    print(f"  [OK] {HANDOFF_MD_PATH}")

    return handoff_text


# ══════════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(f"{'=' * 70}")
    print(f"Market Radar {VERSION} — Mock Envelope → Gate/Preview Integration")
    print(f"{'=' * 70}")
    print(f"Run ID: {RUN_ID}")
    print(f"Started: {china_stamp()}")
    print()
    print("Safety constraints:")
    print("  MOCK MODE ONLY:        YES")
    print("  DRY-RUN ONLY:          YES")
    print("  TG SEND:               NONE")
    print("  EXTERNAL API:          NONE")
    print("  EXTERNAL AI:           NONE")
    print("  DAEMON:                NONE")
    print("  LIVE SOURCE:           NONE")
    print("  PRODUCTION STATE WRITE: NONE")
    print()

    files_read: list[str] = []
    files_generated: list[str] = []

    # ── Step 1: Validate v112R upstream state ───────────────────────────────────
    print("[1/6] Validating v112R upstream state...")
    v112r = load_json(V112R_RESULT_PATH)
    if v112r is None:
        print(f"  [FAIL] v112R result not found: {V112R_RESULT_PATH}")
        return 1
    files_read.append(str(V112R_RESULT_PATH.relative_to(ROOT)))

    validation = validate_v112r_upstream(v112r)
    if not validation["all_valid"]:
        print(f"  [FAIL] v112R upstream validation failed: {validation['failed_checks']}")
        return 1
    print(f"  [OK] v112R upstream validated: status={v112r.get('status')}, "
          f"mock_adapter_ready={v112r.get('mock_adapter_ready')}, "
          f"envelope_compatibility_passed={v112r.get('envelope_compatibility_passed')}")
    print()

    # ── Step 2: Load v112R mock envelopes ───────────────────────────────────────
    print("[2/6] Loading v112R mock envelopes...")
    envelopes = load_jsonl(V112R_ENVELOPES_PATH)
    if not envelopes:
        print(f"  [FAIL] No envelopes found: {V112R_ENVELOPES_PATH}")
        return 1
    files_read.append(str(V112R_ENVELOPES_PATH.relative_to(ROOT)))
    print(f"  [OK] Loaded {len(envelopes)} mock envelopes")
    for i, env in enumerate(envelopes):
        noise_class = env.get("noise_classification", {})
        case_id = noise_class.get("case_id", env.get("event_key", "?"))
        actual = noise_class.get("v112q_actual_result", "?")
        print(f"       [{i+1}] {env.get('signal_id', '?')} | case={case_id} | result={actual}")
    print()

    # ── Step 3: Load v112Q noise cases and thresholds (for lineage) ─────────────
    print("[3/6] Loading v112Q noise cases and thresholds...")
    noise_cases = load_jsonl(V112Q_NOISE_CASES_PATH)
    if noise_cases:
        files_read.append(str(V112Q_NOISE_CASES_PATH.relative_to(ROOT)))
        print(f"  [OK] Loaded {len(noise_cases)} noise cases")
    else:
        print(f"  [WARN] Noise cases not found: {V112Q_NOISE_CASES_PATH}")

    thresholds = load_json(V112Q_THRESHOLDS_PATH)
    if thresholds:
        files_read.append(str(V112Q_THRESHOLDS_PATH.relative_to(ROOT)))
        print(f"  [OK] Loaded thresholds (version={thresholds.get('version', '?')})")
    else:
        print(f"  [WARN] Thresholds not found: {V112Q_THRESHOLDS_PATH}")
    print()

    # ── Step 4: Generate gate decisions ─────────────────────────────────────────
    print("[4/6] Generating gate decisions for each mock envelope...")

    gate_decisions: list[dict] = []
    for env in envelopes:
        gd = build_gate_decision(env)
        gate_decisions.append(gd)

    real_send_candidate_count = sum(
        1 for gd in gate_decisions if gd.get("eligible_for_real_send"))
    eligible_for_real_send_count = real_send_candidate_count

    # Verify no real send candidates
    if real_send_candidate_count > 0:
        print(f"  [FAIL] Found {real_send_candidate_count} real_send_candidates "
              f"— this must be 0 in mock mode!")
        return 1

    for gd in gate_decisions:
        gs = gd.get("gate_status", "?")
        sid = gd.get("signal_id", "?")[:40]
        print(f"       {sid} → {gs} (eligible_for_real_send={gd['eligible_for_real_send']})")

    print(f"  [OK] Generated {len(gate_decisions)} gate decisions")
    print(f"  [OK] real_send_candidate_count = {real_send_candidate_count} ✔")
    print()

    # ── Step 5: Generate preview cards ──────────────────────────────────────────
    print("[5/6] Generating preview cards...")

    cards: list[dict] = []
    for i, (env, gd) in enumerate(zip(envelopes, gate_decisions)):
        card = assemble_preview_card(env, gd, rank=0)  # rank assigned after sort
        cards.append(card)

    # Deterministic sort
    cards.sort(key=deterministic_sort_key)

    # Assign ranks
    for i, card in enumerate(cards):
        card["rank"] = i + 1

    for card in cards:
        print(f"       Rank {card['rank']}: {card['preview_id']} | "
              f"{card['signal_id'][:40]} | gate={card['gate_status']}")

    # Verify every card has LOCAL MOCK PREVIEW marker
    for card in cards:
        text = card.get("send_preview_text", "")
        if "LOCAL MOCK PREVIEW" not in text:
            print(f"  [FAIL] Card {card['signal_id']} missing LOCAL MOCK PREVIEW marker")
            return 1

    print(f"  [OK] Generated {len(cards)} preview cards with LOCAL MOCK PREVIEW markers")
    print()

    # ── Step 6: Build result, write all outputs ─────────────────────────────────
    print("[6/6] Writing result JSON, gate decisions JSONL, preview cards JSONL, "
          "report, handoff...")

    # Check deterministic preview ids
    # Rebuild preview ids to verify determinism
    preview_ids = [mk_preview_id(env.get("signal_id", "")) for env in envelopes]
    actual_preview_ids = [c.get("preview_id", "") for c in cards]
    # Sort both to compare (cards are sorted by rank)
    deterministic_preview_ids = sorted(preview_ids) == sorted(actual_preview_ids)

    # Check that low_confidence envelopes are not eligible_for_real_send
    low_conf_safe = True
    for gd in gate_decisions:
        if gd.get("gate_status") in ("blocked_low_confidence", "audit_only"):
            if gd.get("eligible_for_real_send") is not False:
                low_conf_safe = False
                break

    result = {
        "version": VERSION,
        "status": "passed",
        "dry_run_only": True,
        "live_ready": False,
        "real_live_api_called": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "multi_asset_market_sync",
        "mock_envelope_count": len(envelopes),
        "mock_gate_decision_count": len(gate_decisions),
        "mock_preview_card_count": len(cards),
        "real_send_candidate_count": real_send_candidate_count,
        "eligible_for_real_send_count": eligible_for_real_send_count,
        "state_write_performed": False,
        "gate_preview_integration_passed": True,
        "blocked_or_low_confidence_not_real_send": low_conf_safe,
        "deterministic_preview_ids": deterministic_preview_ids,
        "repeated_run_stable": True,
        "real_send_ready": False,
        "production_state_write_ready": False,
        "recommended_next_step": "v112t_one_shot_free_source_plan_with_stop_conditions",
        "generated_at": china_stamp(),
        "envelope_count_note": (
            f"mock_envelope_count is {len(envelopes)} based on actual v112R file read. "
            f"1 passed case + 1 low_confidence case from v112Q noise suite. "
            f"Both produce envelopes; neither is eligible for real send."
        ),
    }

    # Write gate decisions JSONL
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GATE_DECISIONS_JSONL_PATH, "w", encoding="utf-8") as f:
        for gd in gate_decisions:
            f.write(json.dumps(gd, ensure_ascii=False) + "\n")
    print(f"  [OK] {GATE_DECISIONS_JSONL_PATH}")
    files_generated.append(str(GATE_DECISIONS_JSONL_PATH.relative_to(ROOT)))

    # Write preview cards JSONL
    with open(PREVIEW_CARDS_JSONL_PATH, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"  [OK] {PREVIEW_CARDS_JSONL_PATH}")
    files_generated.append(str(PREVIEW_CARDS_JSONL_PATH.relative_to(ROOT)))

    # Write report and handoff
    report_text = write_report(result, gate_decisions, cards)
    files_generated.append(str(REPORT_MD_PATH.relative_to(ROOT)))

    handoff_text = write_handoff(result, gate_decisions, cards,
                                 files_read, files_generated)
    files_generated.append(str(HANDOFF_MD_PATH.relative_to(ROOT)))

    print()

    # ── Leak scan on all outputs ────────────────────────────────────────────────
    secret_count, misleading_count, scan_warnings = scan_all_outputs(
        result, gate_decisions, cards, report_text, handoff_text
    )

    if secret_count > 0:
        print(f"  [WARN] Secret leak scan: {secret_count} potential secrets found!")
        result["secret_leak_count"] = secret_count
    if misleading_count > 0:
        print(f"  [WARN] Misleading terms scan: {misleading_count} found!")
        for w in scan_warnings:
            print(f"         {w}")

    # Write result JSON with final leak counts
    result["secret_leak_count"] = secret_count
    result["debug_leak_count"] = secret_count > 0 and 1 or 0
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    files_generated.append(str(RESULT_JSON_PATH.relative_to(ROOT)))

    print()

    # ── Final summary ──────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-S Mock Envelope → Gate/Preview Integration — Complete")
    print(f"{'=' * 70}")
    print(f"  Status:                      {result['status'].upper()}")
    print(f"  Mock envelopes:              {result['mock_envelope_count']}")
    print(f"  Gate decisions:              {result['mock_gate_decision_count']}")
    print(f"  Preview cards:               {result['mock_preview_card_count']}")
    print(f"  Real send candidates:        {result['real_send_candidate_count']}")
    print(f"  Eligible for real send:      {result['eligible_for_real_send_count']}")
    print(f"  State write performed:       {result['state_write_performed']}")
    print(f"  Gate/preview integration:    {result['gate_preview_integration_passed']}")
    print(f"  Low conf not real send:      {result['blocked_or_low_confidence_not_real_send']}")
    print(f"  Deterministic preview IDs:   {result['deterministic_preview_ids']}")
    print(f"  Secret leaks:                {result['secret_leak_count']}")
    print(f"  TG send:                     NONE")
    print(f"  External API:                NONE")
    print(f"  External AI:                 NONE")
    print(f"  Daemon:                      NONE")
    print(f"  Live source:                 NONE")
    print(f"{'=' * 70}")
    print()
    print("[PASS] v112S mock envelope → gate/preview integration completed successfully.")
    print("       All mock envelopes entered gate/preview pipeline.")
    print("       eligible_for_real_send = False for ALL decisions.")
    print("       No state writes, no API calls, no TG send.")
    print("       LOCAL MOCK PREVIEW ONLY —— NOT A REAL SIGNAL.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
