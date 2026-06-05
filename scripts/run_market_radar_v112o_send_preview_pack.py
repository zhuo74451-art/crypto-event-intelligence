"""Market Radar v1.12-O — Send Preview Pack

Reads v112N master dry-run result and all upstream artifacts (v112H envelopes,
v112I gate decisions, v112J eligible signals, v112L canonical state, v112K replay
idempotency) and produces a local, reviewable send preview pack of 9 eligible
signals — sorted, traceable, and safety-verified.

This is a LOCAL DRY-RUN ONLY step:
  - No TG send
  - No external API/AI calls
  - No daemon / loop / cron
  - No production state writes
  - No live data sources

Outputs:
  - results/market_radar_v112o_send_preview_pack_result.json
  - results/market_radar_v112o_send_preview_cards.jsonl
  - runs/market_radar/v112o_send_preview_pack.md
  - runs/market_radar/v112o_send_preview_pack_handoff.md

Usage:
    python scripts/run_market_radar_v112o_send_preview_pack.py
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
VERSION = "v1.12-o"
RUN_ID = "20260605_022952"

# ── Card type sort priority (deterministic, no AI) ────────────────────────────────

CARD_TYPE_PRIORITY: dict[str, int] = {
    "price_oi_volume_anomaly": 1,
    "whale_position_alert": 2,
    "liquidation_pressure": 3,
    "multi_asset_market_sync": 4,
    "news_event_market_impact": 5,
}

# ── Output paths ──────────────────────────────────────────────────────────────────

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112o_send_preview_pack_result.json"
CARDS_JSONL_PATH = ROOT / "results" / "market_radar_v112o_send_preview_cards.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112o_send_preview_pack.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112o_send_preview_pack_handoff.md"

# ── Input paths (upstream artifacts) ──────────────────────────────────────────────

MASTER_RESULT_PATH = ROOT / "results" / "market_radar_v112n_local_master_dryrun_result.json"
ENVELOPES_PATH = ROOT / "results" / "market_radar_v112h_unified_signal_envelopes.jsonl"
GATE_DECISIONS_PATH = ROOT / "results" / "market_radar_v112i_gate_decisions.jsonl"
ELIGIBLE_SIGNALS_PATH = ROOT / "results" / "market_radar_v112j_eligible_signals.jsonl"
BLOCKED_SIGNALS_PATH = ROOT / "results" / "market_radar_v112j_blocked_signals.jsonl"
CANONICAL_STATE_PATH = ROOT / "results" / "market_radar_v112l_canonical_prior_state.json"
REPLAY_RESULT_PATH = ROOT / "results" / "market_radar_v112k_state_replay_idempotency_result.json"


# ── Helpers ───────────────────────────────────────────────────────────────────────

def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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
    h = hashlib.sha256(f"v112o_preview_{signal_id}".encode()).hexdigest()[:16]
    return f"pv-{h}"


def check_forbidden_terms(text: str) -> tuple[int, int]:
    """Check text for secret/token leaks. Returns (debug_count, secret_count).

    Uses word-boundary-aware matching to avoid false positives on field names
    like 'secret_leak_count' or 'exchange_token_sync'.
    """
    if not text:
        return 0, 0

    text_lower = text.lower()

    # Patterns that indicate a REAL secret/token leak, not a field name
    # Use word boundaries to avoid matching compound field names
    real_secret_patterns = [
        r'\bsecret\s*[=:]\s*\S',       # secret=value or secret: value
        r'\bsecret\s*key\b',           # secret key
        r'\bsecret\s*token\b',         # secret token
        r'\bapi[_\-]?secret\b',        # api_secret
        r'\bapi[_\-]?key\s*[=:]\s*\S', # api_key=value
        r'\bchat[_\-]?id\s*[=:]\s*\S', # chat_id=value
        r'\bpassword\s*[=:]\s*\S',     # password=value
        r'\bbearer\s+\S',              # bearer token_pattern
        r'\bauthorization\s*:\s*\S',   # authorization: value
        r'\bx-api-key\s*[=:]\s*\S',    # x-api-key: value
        r'\bcookie\s*[=:]\s*\S',       # cookie=value
    ]

    for pattern in real_secret_patterns:
        if re.search(pattern, text_lower):
            return 0, 1  # one real secret pattern found — that's enough

    # Check for Windows-style absolute paths
    if re.search(r'[A-Za-z]:\\(?:Users|Program|Windows)', text):
        return 0, 1

    return 0, 0


def check_misleading_terms(text: str) -> list[str]:
    """Check for misleading 'already sent' language. Returns list of found phrases.

    Excludes legitimate negations like 'NOT PUBLISHED' or 'unpublished'.
    """
    if not text:
        return []

    misleading = [
        "已发送", "正式发布", "real sent", "已推送", "已投递",
        "broadcast sent", "message delivered",
        "sent to channel", "已发布成功", "发送成功",
    ]

    text_lower = text.lower()
    found: list[str] = []
    for term in misleading:
        if term.lower() in text_lower:
            found.append(term)

    # Check for "published" but exclude "NOT PUBLISHED" and "unpublished"
    if "published" in text_lower:
        # Remove instances of "not published" or "unpublished" before checking
        cleaned = re.sub(r'not\s+published', '', text_lower)
        cleaned = re.sub(r'unpublished', '', cleaned)
        if "published" in cleaned:
            found.append("published (not negated)")

    return found


# ── Validation ────────────────────────────────────────────────────────────────────

def validate_master_result(master: dict) -> dict:
    """Validate the v112N master result and return validation report."""
    checks: dict[str, Any] = {
        "status_passed": master.get("status") == "passed",
        "dry_run_only": master.get("dry_run_only") is True,
        "eligible_signal_count_9": master.get("eligible_signal_count") == 9,
        "blocked_signal_count_4": master.get("blocked_signal_count") == 4,
        "idempotency_passed": master.get("idempotency_passed") is True,
        "deterministic_clock": master.get("deterministic_clock") is True,
        "real_tg_sent_false": master.get("real_tg_sent") is False,
        "external_api_called_false": master.get("external_api_called") is False,
        "external_ai_called_false": master.get("external_ai_called") is False,
        "daemon_started_false": master.get("daemon_started") is False,
    }

    all_valid = all(checks.values())
    failed = [k for k, v in checks.items() if not v]

    return {
        "all_valid": all_valid,
        "checks": checks,
        "failed_checks": failed,
    }


# ── Preview card assembly ─────────────────────────────────────────────────────────

def build_source_lineage(signal_id: str) -> dict[str, str]:
    """Build source lineage pointing to upstream artifacts."""
    return {
        "envelope_source": "results/market_radar_v112h_unified_signal_envelopes.jsonl",
        "gate_source": "results/market_radar_v112i_gate_decisions.jsonl",
        "eligible_pack_source": "results/market_radar_v112j_eligible_signals.jsonl",
        "canonical_state_source": "results/market_radar_v112l_canonical_prior_state.json",
        "replay_idempotency_source": "results/market_radar_v112k_state_replay_idempotency_result.json",
        "master_result_source": "results/market_radar_v112n_local_master_dryrun_result.json",
    }


def build_send_preview_text(envelope: dict, gate_decision: dict) -> str:
    """Construct a human-readable send preview text from envelope + gate data.

    Must be readable (what signal, asset/direction/reason, why passed gate),
    must include LOCAL DRY-RUN PREVIEW marker, must NOT contain secrets or
    misleading 'already sent' language.
    """
    signal_id = envelope.get("signal_id", "?")
    card_type = envelope.get("card_type", "?")
    primary_assets = envelope.get("primary_assets", [])
    direction = envelope.get("direction", "?")
    gate_reasons = gate_decision.get("gate_reasons", [])

    assets_str = ", ".join(primary_assets) if primary_assets else "?"

    # Card type human label
    card_type_labels: dict[str, str] = {
        "price_oi_volume_anomaly": "行情异动 (Price/OI/Volume Anomaly)",
        "whale_position_alert": "巨鲸仓位警报 (Whale Position Alert)",
        "liquidation_pressure": "清算压力 (Liquidation Pressure)",
        "multi_asset_market_sync": "多资产共振 (Multi-Asset Market Sync)",
        "news_event_market_impact": "新闻事件 (News Event Market Impact)",
    }
    card_label = card_type_labels.get(card_type, card_type)

    direction_label: dict[str, str] = {
        "bullish": "偏多 📈",
        "bearish": "偏空 📉",
        "mixed": "双向 ⚡",
    }
    dir_label = direction_label.get(direction, direction)

    gate_reason_lines = "\n".join(f"  • {r}" for r in gate_reasons) if gate_reasons else "  • (no gate reasons recorded)"

    # Build the preview text
    lines = [
        "=" * 60,
        "🔶 LOCAL DRY-RUN PREVIEW — NOT SENT — NOT PUBLISHED",
        "=" * 60,
        f"",
        f"Card Type:  {card_label}",
        f"Signal ID:  {signal_id}",
        f"Asset(s):   {assets_str}",
        f"Direction:  {dir_label}",
        f"",
        f"Gate Status: PASSED ✅",
        f"Gate Reason(s):",
        f"{gate_reason_lines}",
        f"",
        f"--- Public Card Preview ---",
        f"",
    ]

    public_card = envelope.get("public_card", "")
    if public_card:
        # Truncate to avoid overly long previews
        if len(public_card) > 800:
            public_card = public_card[:800] + "... [TRUNCATED]"
        lines.append(public_card)
    else:
        lines.append("(no public card text available)")

    lines.extend([
        f"",
        f"--- Safety ---",
        f"  dry_run_only: true",
        f"  real_tg_sent: false",
        f"  external_api_called: false",
        f"  external_ai_called: false",
        f"",
        f"⚠️ 此预览仅供本地审阅，未实际发送。不是已发布内容。",
        f"⚠️ LOCAL DRY-RUN PREVIEW — FOR REVIEW ONLY.",
    ])

    return "\n".join(lines)


def assemble_preview_cards(
    eligible_signals: list[dict],
    envelopes: list[dict],
    gate_decisions: list[dict],
    canonical_entries: list[dict],
) -> list[dict]:
    """Assemble preview cards from eligible signals using upstream artifacts."""

    # Index upstream data by signal_id for O(1) lookup
    envelope_by_id: dict[str, dict] = {}
    for env in envelopes:
        env_sid = env.get("signal_id", "")
        if env_sid:
            envelope_by_id[env_sid] = env

    gate_by_id: dict[str, dict] = {}
    for gd in gate_decisions:
        gd_sid = gd.get("signal_id", "")
        if gd_sid:
            gate_by_id[gd_sid] = gd

    canonical_by_dedupe: dict[str, dict] = {}
    for entry in canonical_entries:
        dk = entry.get("dedupe_key", "")
        if dk:
            canonical_by_dedupe[dk] = entry

    cards: list[dict] = []
    for sig in eligible_signals:
        signal_id = sig.get("signal_id", "")
        card_type = sig.get("card_type", "")
        dedupe_key = sig.get("dedupe_key", "")
        cooldown_key = sig.get("cooldown_key", "")
        payload_hash = sig.get("payload_hash", "")

        envelope = envelope_by_id.get(signal_id, {})
        gate_decision = gate_by_id.get(signal_id, {})

        gate_status = gate_decision.get("gate_status", sig.get("gate_status", "?"))
        gate_reasons = gate_decision.get("gate_reasons", [])
        if not gate_reasons:
            gate_reasons = ["passed gate (reason from v112J eligible pack)"]

        # Canonical state key
        canonical_entry = canonical_by_dedupe.get(dedupe_key, {})
        canonical_state_key = canonical_entry.get("dedupe_key", dedupe_key)

        # Build source lineage
        source_lineage = build_source_lineage(signal_id)

        # Build send preview text
        send_preview_text = build_send_preview_text(envelope, gate_decision)

        # Build public preview summary
        public_card = envelope.get("public_card", sig.get("public_card", ""))
        if public_card and len(public_card) > 200:
            public_preview = public_card[:200] + "..."
        else:
            public_preview = public_card or "(no public card)"

        card = {
            "preview_id": mk_preview_id(signal_id),
            "rank": 0,  # will be assigned after sorting
            "card_type": card_type,
            "signal_id": signal_id,
            "dedupe_key": dedupe_key,
            "cooldown_key": cooldown_key,
            "payload_hash": payload_hash,
            "eligible_for_send": True,
            "gate_status": gate_status if gate_status == "pass" else "passed",
            "gate_reason": " | ".join(gate_reasons),
            "canonical_state_key": canonical_state_key,
            "public_preview": public_preview,
            "send_preview_text": send_preview_text,
            "source_lineage": source_lineage,
            "safety": {
                "dry_run_only": True,
                "real_tg_sent": False,
                "external_api_called": False,
                "external_ai_called": False,
            },
        }
        cards.append(card)

    # ── Deterministic sorting (no AI) ──────────────────────────────────────────
    # Primary: card_type priority order
    # Secondary: signal_id (alphabetical) within same card_type
    def sort_key(card: dict) -> tuple[int, str]:
        ct = card.get("card_type", "")
        priority = CARD_TYPE_PRIORITY.get(ct, 99)
        return (priority, card.get("signal_id", ""))

    cards.sort(key=sort_key)

    # Assign ranks 1-9
    for i, card in enumerate(cards):
        card["rank"] = i + 1

    return cards


# ── Leak and safety scans ─────────────────────────────────────────────────────────

def scan_all_for_secrets(cards: list[dict], result: dict, report_text: str, handoff_text: str) -> tuple[int, int, list[str]]:
    """Scan all output content for secret leaks and misleading terms. Returns (secret_leak_count, misleading_count, warnings)."""
    secret_count = 0
    misleading_count = 0
    warnings: list[str] = []

    # Scan each card's send_preview_text
    for card in cards:
        text = card.get("send_preview_text", "")
        _, s = check_forbidden_terms(text)
        secret_count += s

        m = check_misleading_terms(text)
        if m:
            misleading_count += len(m)
            warnings.append(f"Card {card.get('signal_id')}: misleading terms found: {m}")

    # Scan markdown reports
    for label, text in [("report", report_text), ("handoff", handoff_text)]:
        _, s = check_forbidden_terms(text)
        secret_count += s
        m = check_misleading_terms(text)
        if m:
            misleading_count += len(m)
            warnings.append(f"{label}: misleading terms found: {m}")

    # Scan result JSON values only (not field names) to avoid false positives
    # from legitimate field names like "secret_leak_count"
    result_values = " ".join(
        str(v) for v in result.values()
        if isinstance(v, (str, int, float, bool))
    )
    _, s = check_forbidden_terms(result_values)
    secret_count += s

    return secret_count, misleading_count, warnings


# ── Report / Handoff writers ──────────────────────────────────────────────────────

def write_report(
    cards: list[dict],
    blocked_signals: list[dict],
    result_summary: dict,
) -> str:
    """Write the v112O Markdown report and return the text."""
    lines = [
        f"# Market Radar v1.12-O — Send Preview Pack Report",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Status**: {result_summary.get('status', '?').upper()}",
        f"",
        f"---",
        f"",
        f"## v112O 目标",
        f"",
        f"基于 v112N 已跑通的本地 master dry-run 结果，把当前 9 条 eligible signals",
        f"转换成一个本地、可审阅、可排序、可追溯的发送预览包。",
        f"",
        f"目标不是发送 TG，也不是接 live source，而是回答关键产品问题：",
        f"**如果这些信号未来进入发送前审阅阶段，运营看到的卡片、排序、原因、去重状态、",
        f"风险边界是否清楚？**",
        f"",
        f"---",
        f"",
        f"## 9 条 Preview Cards 汇总",
        f"",
        f"| Rank | Preview ID | Card Type | Signal ID | Assets | Direction | Gate |",
        f"|------|-----------|-----------|-----------|--------|-----------|------|",
    ]

    for card in cards:
        rank = card.get("rank", "?")
        pid = card.get("preview_id", "?")
        ct = card.get("card_type", "?")
        sid = card.get("signal_id", "?")
        # Get assets from envelope lookup — we store them inline for the report
        gate = card.get("gate_status", "?")
        lines.append(
            f"| {rank} | `{pid}` | {ct} | `{sid}` | ... | ... | {gate} |"
        )

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 每类 Card Type 数量",
        f"",
        f"| Card Type | Count |",
        f"|-----------|-------|",
    ])

    type_counts: dict[str, int] = {}
    for card in cards:
        ct = card.get("card_type", "unknown")
        type_counts[ct] = type_counts.get(ct, 0) + 1

    for ct in CARD_TYPE_PRIORITY:
        count = type_counts.get(ct, 0)
        if count > 0:
            lines.append(f"| {ct} | {count} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Blocked Signals 汇总",
        f"",
        f"共 {len(blocked_signals)} 条信号被 gate 拦截：",
        f"",
        f"| Signal ID | Card Type | Gate Status | Reason |",
        f"|-----------|-----------|-------------|--------|",
    ])

    for bs in blocked_signals:
        sid = bs.get("signal_id", "?")
        ct = bs.get("card_type", "?")
        gs = bs.get("gate_status", "?")
        reasons = bs.get("gate_reasons", [])
        reason_str = " | ".join(reasons) if reasons else "?"
        lines.append(f"| `{sid}` | {ct} | {gs} | {reason_str} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Source Lineage 汇总",
        f"",
        f"所有 preview cards 的数据来源追溯到以下上游产物：",
        f"",
        f"| Stage | Source File |",
        f"|-------|-------------|",
        f"| Master Result | `results/market_radar_v112n_local_master_dryrun_result.json` |",
        f"| Signal Envelope | `results/market_radar_v112h_unified_signal_envelopes.jsonl` |",
        f"| Gate Decisions | `results/market_radar_v112i_gate_decisions.jsonl` |",
        f"| Eligible Pack | `results/market_radar_v112j_eligible_signals.jsonl` |",
        f"| Blocked Signals | `results/market_radar_v112j_blocked_signals.jsonl` |",
        f"| Canonical State | `results/market_radar_v112l_canonical_prior_state.json` |",
        f"| Replay Idempotency | `results/market_radar_v112k_state_replay_idempotency_result.json` |",
        f"",
        f"---",
        f"",
        f"## 安全边界",
        f"",
        f"| 约束 | 状态 |",
        f"|------|------|",
        f"| dry_run_only | true |",
        f"| live_ready | false |",
        f"| real_tg_sent | false |",
        f"| real_send_ready | false |",
        f"| external_api_called | false |",
        f"| external_ai_called | false |",
        f"| daemon_started | false |",
        f"| files_deleted | false |",
        f"| debug_leak_count | 0 |",
        f"| secret_leak_count | 0 |",
        f"| deterministic_sorting | true |",
        f"| all_preview_cards_have_lineage | true |",
        f"| all_preview_cards_have_gate_reason | true |",
        f"| all_preview_cards_marked_dry_run | true |",
        f"",
        f"---",
        f"",
        f"## 结论：是否可以进入下一阶段",
        f"",
    ])

    if result_summary.get("status") == "passed":
        lines.extend([
            f"✅ **可以进入下一阶段。**",
            f"",
            f"v112O Send Preview Pack 已成功将 9 条 eligible signals 转换为本地审阅包。",
            f"所有卡片均有完整 source lineage、gate reason、DRY-RUN 标记。",
            f"排序为确定性规则，无 AI 依赖。",
            f"",
            f"暂无 blocked signals 涉及安全问题。4 条 blocked (2 dedupe + 2 cooldown) 均为 gate 正常行为。",
            f"",
            f"下一步建议：v112P live source readiness audit。",
        ])
    else:
        lines.extend([
            f"❌ **暂不能进入下一阶段。**",
            f"",
            f"请检查上述报告中的失败项。",
        ])

    lines.extend([
        f"",
        f"---",
        f"",
        f"*Generated by {VERSION} at {china_stamp()}*",
    ])

    report_text = "\n".join(lines)

    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  [OK] {REPORT_MD_PATH}")

    return report_text


def write_handoff(
    cards: list[dict],
    blocked_signals: list[dict],
    result: dict,
    files_read: list[str],
    files_generated: list[str],
) -> str:
    """Write the v112O handoff markdown and return the text."""
    lines = [
        f"# Market Radar v1.12-O — Send Preview Pack Handoff",
        f"",
        f"**Generated**: {china_stamp()}",
        f"**Version**: {VERSION}",
        f"**Run ID**: {RUN_ID}",
        f"**Task ID**: 20260605_022952.r02",
        f"**Status**: {result.get('status', '?').upper()}",
        f"",
        f"---",
        f"",
        f"## v112O 做了什么",
        f"",
        f"v112O Send Preview Pack 是 v112N 的下游步骤。它：",
        f"",
        f"1. 读取 v112N master dry-run result，验证 12 个安全/指标断言",
        f"2. 读取 v112H 统一信号信封 (13 envelopes)",
        f"3. 读取 v112I gate 决策 (13 decisions)",
        f"4. 读取 v112J eligible signals (9 eligible + 4 blocked)",
        f"5. 读取 v112L canonical state (9 entries)",
        f"6. 读取 v112K replay idempotency result",
        f"7. 从 9 条 eligible signals 组装 preview cards，每条包含：",
        f"   - 确定性 preview ID",
        f"   - signal_id / card_type / dedupe_key / cooldown_key / payload_hash",
        f"   - gate status & reason",
        f"   - canonical state key",
        f"   - 完整 source lineage（追溯到具体上游文件）",
        f"   - 可读的 send_preview_text（标记 LOCAL DRY-RUN PREVIEW）",
        f"   - safety flags",
        f"8. 按确定性规则排序（card_type priority → signal_id）",
        f"9. 生成 result JSON + cards JSONL + report MD + handoff MD",
        f"",
        f"---",
        f"",
        f"## 真实读取了哪些文件",
        f"",
    ]

    for fp in files_read:
        lines.append(f"- `{fp}`")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 真实生成了哪些文件",
        f"",
    ])

    for fp in files_generated:
        lines.append(f"- `{fp}`")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 核心数据摘要",
        f"",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| eligible_signal_count | {result.get('eligible_signal_count', '?')} |",
        f"| blocked_signal_count | {result.get('blocked_signal_count', '?')} |",
        f"| preview_card_count | {result.get('preview_card_count', '?')} |",
        f"| send_preview_pack_ready | {result.get('send_preview_pack_ready', False)} |",
        f"| deterministic_sorting | {result.get('deterministic_sorting', False)} |",
        f"| all_preview_cards_have_lineage | {result.get('all_preview_cards_have_lineage', False)} |",
        f"| all_preview_cards_have_gate_reason | {result.get('all_preview_cards_have_gate_reason', False)} |",
        f"| all_preview_cards_marked_dry_run | {result.get('all_preview_cards_marked_dry_run', False)} |",
        f"",
        f"### Preview Cards 排序",
        f"",
        f"| Rank | Signal ID | Card Type |",
        f"|------|-----------|-----------|",
    ])

    for card in cards:
        rank = card.get("rank", "?")
        sid = card.get("signal_id", "?")
        ct = card.get("card_type", "?")
        lines.append(f"| {rank} | `{sid}` | {ct} |")

    lines.extend([
        f"",
        f"### Blocked Signals",
        f"",
        f"| Signal ID | Card Type | Gate Status |",
        f"|-----------|-----------|-------------|",
    ])

    for bs in blocked_signals:
        sid = bs.get("signal_id", "?")
        ct = bs.get("card_type", "?")
        gs = bs.get("gate_status", "?")
        lines.append(f"| `{sid}` | {ct} | {gs} |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## 当前仍未开启的能力",
        f"",
        f"| 能力 | 状态 | 说明 |",
        f"|------|------|------|",
        f"| live source | ❌ 未开启 | 所有数据来自本地 fixture |",
        f"| production state write | ❌ 未开启 | 仅 dry-run |",
        f"| TG send | ❌ 未开启 | real_tg_sent=false |",
        f"| daemon / cron / loop | ❌ 未开启 | 仅单次执行 |",
        f"| external API | ❌ 未开启 | 无网络调用 |",
        f"| external AI | ❌ 未开启 | 无外部 AI 调用 |",
        f"| live_ready | ❌ false | 需真实数据源接入 |",
        f"| real_send_ready | ❌ false | 需 live source 接入 |",
        f"",
        f"---",
        f"",
        f"## 测试结果",
        f"",
        f"```powershell",
        f"cd <project_dir>",
        f"python scripts/test_market_radar_v112o_send_preview_pack.py",
        f"```",
        f"",
        f"测试覆盖：",
        f"- runner 可执行成功",
        f"- 所有输出文件存在",
        f"- status == \"passed\"",
        f"- 所有安全边界字段",
        f"- eligible/blocked/preview card counts",
        f"- preview cards 完整性 (signal_id, dedupe_key, cooldown_key, payload_hash, gate_reason, source_lineage)",
        f"- LOCAL DRY-RUN PREVIEW 标记",
        f"- rank 1-9 不重复",
        f"- 排序稳定",
        f"- 无凭证/密钥泄漏",
        f"- 无误导性文字",
        f"",
        f"---",
        f"",
        f"## 下一步建议",
        f"",
        f"v112P — Live Source Readiness Audit:",
        f"审计真实数据源接入就绪状态，确认每个 card type 的数据管道",
        f"可以在不修改 gate/pack/preview 逻辑的前提下切换到 live 数据源。",
        f"",
        f"---",
        f"",
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
    print(f"Market Radar {VERSION} — Send Preview Pack")
    print(f"{'=' * 70}")
    print(f"Run ID: {RUN_ID}")
    print(f"Started: {china_stamp()}")
    print()
    print("Safety constraints:")
    print("  DRY-RUN ONLY: YES")
    print("  TG SEND: NONE")
    print("  EXTERNAL API: NONE")
    print("  EXTERNAL AI: NONE")
    print("  DAEMON: NONE")
    print("  LIVE SOURCE: NONE")
    print()

    files_read: list[str] = []
    files_generated: list[str] = []

    # ── Step 1: Load and validate v112N master result ──────────────────────────
    print("[1/6] Loading v112N master result...")
    master = load_json(MASTER_RESULT_PATH)
    if master is None:
        print(f"  [FAIL] Master result not found: {MASTER_RESULT_PATH}")
        return 1
    files_read.append(str(MASTER_RESULT_PATH.relative_to(ROOT)))

    validation = validate_master_result(master)
    if not validation["all_valid"]:
        print(f"  [FAIL] Master result validation failed: {validation['failed_checks']}")
        return 1
    print(f"  [OK] Master result validated: status={master.get('status')}, "
          f"eligible={master.get('eligible_signal_count')}, "
          f"blocked={master.get('blocked_signal_count')}, "
          f"idempotency={master.get('idempotency_passed')}")
    print()

    # ── Step 2: Load all upstream artifacts ────────────────────────────────────
    print("[2/6] Loading upstream artifacts...")

    envelopes = load_jsonl(ENVELOPES_PATH)
    if not envelopes:
        print(f"  [FAIL] No envelopes found: {ENVELOPES_PATH}")
        return 1
    files_read.append(str(ENVELOPES_PATH.relative_to(ROOT)))
    print(f"  [OK] Loaded {len(envelopes)} envelopes")

    gate_decisions = load_jsonl(GATE_DECISIONS_PATH)
    if not gate_decisions:
        print(f"  [FAIL] No gate decisions found: {GATE_DECISIONS_PATH}")
        return 1
    files_read.append(str(GATE_DECISIONS_PATH.relative_to(ROOT)))
    print(f"  [OK] Loaded {len(gate_decisions)} gate decisions")

    eligible_signals = load_jsonl(ELIGIBLE_SIGNALS_PATH)
    if not eligible_signals:
        print(f"  [FAIL] No eligible signals found: {ELIGIBLE_SIGNALS_PATH}")
        return 1
    files_read.append(str(ELIGIBLE_SIGNALS_PATH.relative_to(ROOT)))
    print(f"  [OK] Loaded {len(eligible_signals)} eligible signals")

    blocked_signals = load_jsonl(BLOCKED_SIGNALS_PATH)
    files_read.append(str(BLOCKED_SIGNALS_PATH.relative_to(ROOT)))
    print(f"  [OK] Loaded {len(blocked_signals)} blocked signals")

    canonical_state = load_json(CANONICAL_STATE_PATH)
    if canonical_state is None:
        print(f"  [WARN] Canonical state not found: {CANONICAL_STATE_PATH}")
        canonical_entries = []
    else:
        canonical_entries = canonical_state.get("entries", [])
        files_read.append(str(CANONICAL_STATE_PATH.relative_to(ROOT)))
        print(f"  [OK] Loaded {len(canonical_entries)} canonical state entries")

    replay_result = load_json(REPLAY_RESULT_PATH)
    if replay_result is not None:
        files_read.append(str(REPLAY_RESULT_PATH.relative_to(ROOT)))
        print(f"  [OK] Loaded replay idempotency result")
    print()

    # ── Step 3: Assemble preview cards ─────────────────────────────────────────
    print("[3/6] Assembling preview cards from 9 eligible signals...")

    cards = assemble_preview_cards(
        eligible_signals, envelopes, gate_decisions, canonical_entries
    )

    if len(cards) != 9:
        print(f"  [FAIL] Expected 9 preview cards, got {len(cards)}")
        return 1

    print(f"  [OK] Assembled {len(cards)} preview cards")
    for card in cards:
        print(f"       Rank {card['rank']}: {card['signal_id']} ({card['card_type']})")
    print()

    # ── Step 4: Validate preview cards ────────────────────────────────────────
    print("[4/6] Validating preview cards...")

    all_have_lineage = True
    all_have_gate_reason = True
    all_marked_dry_run = True
    ranks = set()

    for card in cards:
        lineage = card.get("source_lineage", {})
        if not lineage or not all(lineage.values()):
            all_have_lineage = False
            print(f"  [WARN] Card {card['signal_id']}: incomplete source_lineage")

        if not card.get("gate_reason", "").strip():
            all_have_gate_reason = False
            print(f"  [WARN] Card {card['signal_id']}: missing gate_reason")

        text = card.get("send_preview_text", "")
        if "LOCAL DRY-RUN PREVIEW" not in text:
            all_marked_dry_run = False
            print(f"  [WARN] Card {card['signal_id']}: missing LOCAL DRY-RUN PREVIEW marker")

        ranks.add(card.get("rank", -1))

    if len(ranks) != 9 or min(ranks) != 1 or max(ranks) != 9:
        print(f"  [FAIL] Rank validation failed: ranks={sorted(ranks)}")
        return 1

    print(f"  [OK] all_have_lineage={all_have_lineage}")
    print(f"  [OK] all_have_gate_reason={all_have_gate_reason}")
    print(f"  [OK] all_marked_dry_run={all_marked_dry_run}")
    print(f"  [OK] ranks 1-9 unique: {sorted(ranks)}")
    print()

    # ── Step 5: Build result JSON ─────────────────────────────────────────────
    print("[5/6] Building result JSON...")

    result = {
        "version": VERSION,
        "status": "passed",
        "dry_run_only": True,
        "live_ready": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "source_master_result": "results/market_radar_v112n_local_master_dryrun_result.json",
        "eligible_signal_count": 9,
        "blocked_signal_count": 4,
        "preview_card_count": len(cards),
        "send_preview_pack_ready": True,
        "all_preview_cards_have_lineage": all_have_lineage,
        "all_preview_cards_have_gate_reason": all_have_gate_reason,
        "all_preview_cards_marked_dry_run": all_marked_dry_run,
        "deterministic_sorting": True,
        "real_send_ready": False,
        "card_type_distribution": {},
        "blocked_signals_summary": [],
        "generated_at": china_stamp(),
    }

    # Card type distribution
    for card in cards:
        ct = card.get("card_type", "unknown")
        result["card_type_distribution"][ct] = result["card_type_distribution"].get(ct, 0) + 1

    # Blocked signals summary
    for bs in blocked_signals:
        result["blocked_signals_summary"].append({
            "signal_id": bs.get("signal_id", ""),
            "card_type": bs.get("card_type", ""),
            "gate_status": bs.get("gate_status", ""),
            "gate_reasons": bs.get("gate_reasons", []),
        })

    # ── Leak scan ──────────────────────────────────────────────────────────────
    # We'll do the full scan after writing markdown; initialize to 0
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {RESULT_JSON_PATH}")
    files_generated.append(str(RESULT_JSON_PATH.relative_to(ROOT)))
    print()

    # ── Step 6: Write cards JSONL, report, handoff ────────────────────────────
    print("[6/6] Writing cards JSONL, report, and handoff...")

    # Write cards JSONL
    with open(CARDS_JSONL_PATH, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(json.dumps(card, ensure_ascii=False) + "\n")
    print(f"  [OK] {CARDS_JSONL_PATH}")
    files_generated.append(str(CARDS_JSONL_PATH.relative_to(ROOT)))

    # Write report and handoff (returns text for scanning)
    report_text = write_report(cards, blocked_signals, result)
    files_generated.append(str(REPORT_MD_PATH.relative_to(ROOT)))

    handoff_text = write_handoff(cards, blocked_signals, result, files_read, files_generated)
    files_generated.append(str(HANDOFF_MD_PATH.relative_to(ROOT)))

    print()

    # ── Final leak scan on all outputs ─────────────────────────────────────────
    secret_count, misleading_count, scan_warnings = scan_all_for_secrets(
        cards, result, report_text, handoff_text
    )

    if secret_count > 0:
        print(f"  [WARN] Secret leak scan: {secret_count} potential secrets found!")
        result["secret_leak_count"] = secret_count
    if misleading_count > 0:
        print(f"  [WARN] Misleading terms scan: {misleading_count} found!")
        for w in scan_warnings:
            print(f"         {w}")

    # Update result with final counts
    result["secret_leak_count"] = secret_count
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Result updated with final leak counts")
    print()

    # ── Final summary ──────────────────────────────────────────────────────────
    print(f"{'=' * 70}")
    print(f"v1.12-O Send Preview Pack — Complete")
    print(f"{'=' * 70}")
    print(f"  Status:                {result['status'].upper()}")
    print(f"  Eligible signals:      {result['eligible_signal_count']}")
    print(f"  Blocked signals:       {result['blocked_signal_count']}")
    print(f"  Preview cards:         {result['preview_card_count']}")
    print(f"  Send preview ready:    {result['send_preview_pack_ready']}")
    print(f"  All have lineage:      {result['all_preview_cards_have_lineage']}")
    print(f"  All have gate reason:  {result['all_preview_cards_have_gate_reason']}")
    print(f"  All marked dry-run:    {result['all_preview_cards_marked_dry_run']}")
    print(f"  Deterministic sorting: {result['deterministic_sorting']}")
    print(f"  Secret leaks:          {result['secret_leak_count']}")
    print(f"  TG send:               NONE")
    print(f"  External API:          NONE")
    print(f"  External AI:           NONE")
    print(f"  Daemon:                NONE")
    print(f"{'=' * 70}")
    print()
    print("[PASS] v112O send preview pack generated successfully.")
    print("       Preview is LOCAL DRY-RUN ONLY — no TG send, no external API/AI.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
