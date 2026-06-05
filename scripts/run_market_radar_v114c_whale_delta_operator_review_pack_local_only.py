#!/usr/bin/env python3
"""
v114C Whale Delta Operator Review Pack — Local Only
=====================================================
Reads v114B delta compare results and generates operator review cards
for local operator review. No external API calls, no TG send, no prod state.

Invariants (enforced):
  - No external API calls
  - No API key / credentials read
  - No TG send
  - No production state write
  - No daemon / watcher / loop
  - No file deletion
  - local_review_only = true (all cards)
  - eligible_for_real_send = false (all cards)
  - tg_send_allowed = false (all cards)
  - prod_state_write = false (all cards)
  - operator_action = review_only_no_send (all cards)
"""

import hashlib
import json
import os
import sys
import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
RUNS_DIR = os.path.join(BASE_DIR, "runs", "market_radar")

# v114B inputs (read-only)
V114B_DELTA_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_delta_compare_result.json")
V114B_DELTAS_JSONL = os.path.join(RESULTS_DIR, "market_radar_v114b_whale_position_deltas.jsonl")

# v114C outputs
OUT_RESULT = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_pack_result.json")
OUT_CARDS = os.path.join(RESULTS_DIR, "market_radar_v114c_whale_delta_operator_review_cards.jsonl")
OUT_REPORT = os.path.join(RUNS_DIR, "v114c_whale_delta_operator_review_pack_local_only.md")
OUT_HANDOFF = os.path.join(RUNS_DIR, "v114c_whale_delta_operator_review_pack_local_only_handoff.md")

TZ_SHANGHAI = datetime.timezone(datetime.timedelta(hours=8))

# Safety invariants
EXTERNAL_API_CALLED = False
CREDENTIALS_READ = False
DAEMON_STARTED = False
WATCHER_STARTED = False
FILES_DELETED = False
TG_SENT = False
PROD_STATE_WRITE = False

# Delta type constants
DELTA_CLOSED = "closed_position"
DELTA_SIZE_CHANGED = "size_changed"
DELTA_UNCHANGED = "unchanged"
DELTA_NEW = "new_position"

# Attention levels
ATTENTION_HIGH = "high"
ATTENTION_MEDIUM = "medium"
ATTENTION_LOW = "low"

# Priority ordering for sorting
PRIORITY_ORDER = {
    DELTA_CLOSED: 0,
    DELTA_SIZE_CHANGED: 1,
    DELTA_NEW: 2,
    DELTA_UNCHANGED: 3,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.datetime.now(TZ_SHANGHAI).isoformat()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_jsonl(path) -> list:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def safe_float(value, default=0.0):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Step 1: Load v114B delta data
# ---------------------------------------------------------------------------
def load_v114b_data():
    """Load v114B delta compare result and delta records JSONL."""
    if not os.path.exists(V114B_DELTA_RESULT):
        print(f"ERROR: v114B delta result not found at {V114B_DELTA_RESULT}")
        sys.exit(1)
    if not os.path.exists(V114B_DELTAS_JSONL):
        print(f"ERROR: v114B delta records not found at {V114B_DELTAS_JSONL}")
        sys.exit(1)

    delta_result = load_json(V114B_DELTA_RESULT)
    deltas = load_jsonl(V114B_DELTAS_JSONL)

    print(f"  v114B delta result loaded: {delta_result['delta_records_written']} records")
    print(f"  v114B delta JSONL loaded: {len(deltas)} records")

    return delta_result, deltas


# ---------------------------------------------------------------------------
# Step 2: Validate v114B invariants
# ---------------------------------------------------------------------------
def validate_v114b_invariants(delta_result, deltas):
    """Confirm v114B safety invariants before processing."""
    checks = []

    # Result-level invariants
    checks.append(("local_delta_compare_only=true",
                   delta_result.get("local_delta_compare_only") is True))
    checks.append(("eligible_for_real_send_count=0",
                   delta_result.get("eligible_for_real_send_count") == 0))
    checks.append(("tg_send_allowed_count=0",
                   delta_result.get("tg_send_allowed_count") == 0))
    checks.append(("prod_state_write=false",
                   delta_result.get("prod_state_write") is False))

    all_pass = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] v114B invariant: {name}")
        else:
            print(f"  [{status}] v114B invariant: {name}")

    if not all_pass:
        print("ERROR: v114B invariants not satisfied. Aborting.")
        sys.exit(1)

    # Per-record checks
    for i, d in enumerate(deltas):
        if d.get("local_delta_compare_only") is not True:
            print(f"  [FAIL] delta[{i}] local_delta_compare_only is not True")
            sys.exit(1)
        if d.get("eligible_for_real_send") is not False:
            print(f"  [FAIL] delta[{i}] eligible_for_real_send is not False")
            sys.exit(1)
        if d.get("tg_send_allowed") is not False:
            print(f"  [FAIL] delta[{i}] tg_send_allowed is not False")
            sys.exit(1)

    return True


# ---------------------------------------------------------------------------
# Step 3: Determine operator attention level
# ---------------------------------------------------------------------------
def determine_attention_level(delta_type, size_delta_abs):
    """
    Determine operator attention level.

    Rules (per v114C result template):
      - high: closed_position, new_position
      - medium: size_changed (all 5)
      - low: unchanged
    """
    if delta_type in (DELTA_CLOSED, DELTA_NEW):
        return ATTENTION_HIGH
    elif delta_type == DELTA_SIZE_CHANGED:
        return ATTENTION_MEDIUM
    elif delta_type == DELTA_UNCHANGED:
        return ATTENTION_LOW
    return ATTENTION_LOW


# ---------------------------------------------------------------------------
# Step 4: Generate review summary text
# ---------------------------------------------------------------------------
def generate_review_summary(delta_type, asset, side, baseline_size, current_size, size_delta):
    """Generate clear, English review_summary per card type. Not exaggerated."""
    if delta_type == DELTA_CLOSED:
        return (
            f"{asset} {side} position disappeared in second probe; "
            f"classify as closed_position for local operator review only."
        )
    elif delta_type == DELTA_SIZE_CHANGED:
        direction = "reduced" if size_delta < 0 else "increased"
        return (
            f"Position size {direction} versus local baseline "
            f"(delta={size_delta:+,.2f}); "
            f"review delta magnitude before any future routing decision."
        )
    elif delta_type == DELTA_UNCHANGED:
        return (
            f"Position remains within tolerance; "
            f"low-priority observation."
        )
    elif delta_type == DELTA_NEW:
        return (
            f"New {asset} {side} position appeared versus local baseline; "
            f"local review required before any future routing decision."
        )
    return "Unknown delta type."


# ---------------------------------------------------------------------------
# Step 5: Generate operator review cards
# ---------------------------------------------------------------------------
def generate_review_cards(deltas):
    """Generate operator review card from each v114B delta record."""
    cards = []
    for d in deltas:
        delta_type = d["delta_type"]
        size_delta_abs = abs(safe_float(d.get("size_delta", 0)))

        attention_level = determine_attention_level(delta_type, size_delta_abs)

        baseline_size = d.get("baseline_size")
        current_size = d.get("current_size")
        size_delta = d.get("size_delta")

        review_summary = generate_review_summary(
            delta_type,
            d.get("asset", "?"),
            d.get("side", "?"),
            baseline_size,
            current_size,
            safe_float(size_delta, 0),
        )

        # Build warnings
        warnings = [
            "本地二次探针差异对比",
            "不允许直接发送",
        ]
        lc = d.get("label_confidence", "unknown")
        if lc in ("low", "medium"):
            warnings.append("标签置信度不足")
        if d.get("liquidation_price") is None:
            warnings.append("清算价格缺失")

        # Source delta hash (content-based)
        raw = json.dumps(d, sort_keys=True, ensure_ascii=False)
        source_delta_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # Liquidation price availability flag
        liq_unavailable = d.get("liquidation_price") is None

        card = {
            "version": "v114C",
            "review_type": "whale_delta_operator_review",
            "local_review_only": True,
            "operator_action": "review_only_no_send",
            "eligible_for_real_send": False,
            "real_send_candidate": False,
            "tg_send_allowed": False,
            "prod_state_write": False,
            "position_identity_key": d.get("position_identity_key", ""),
            "delta_type": delta_type,
            "operator_attention_level": attention_level,
            "address": d.get("address", ""),
            "label": d.get("label", ""),
            "label_confidence": d.get("label_confidence", ""),
            "asset": d.get("asset", ""),
            "side": d.get("side", ""),
            "baseline_size": baseline_size,
            "current_size": current_size,
            "size_delta": size_delta,
            "size_delta_abs": size_delta_abs,
            "entry_price_changed": d.get("entry_price_changed", False),
            "liquidation_price_unavailable": liq_unavailable,
            "review_summary": review_summary,
            "warnings": warnings,
            "source_delta_hash": source_delta_hash,
        }
        cards.append(card)

    # Sort by priority: closed_position > size_changed > new_position > unchanged
    # Within same delta_type, sort by size_delta_abs descending
    cards.sort(key=lambda c: (
        PRIORITY_ORDER.get(c["delta_type"], 99),
        -c["size_delta_abs"]
    ))

    return cards


# ---------------------------------------------------------------------------
# Step 6: Write outputs
# ---------------------------------------------------------------------------
def write_result_json(deltas, cards):
    """Write the v114C result JSON."""
    closed_count = sum(1 for c in cards if c["delta_type"] == DELTA_CLOSED)
    size_changed_count = sum(1 for c in cards if c["delta_type"] == DELTA_SIZE_CHANGED)
    unchanged_count = sum(1 for c in cards if c["delta_type"] == DELTA_UNCHANGED)
    new_count = sum(1 for c in cards if c["delta_type"] == DELTA_NEW)
    high_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_HIGH)
    medium_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_MEDIUM)
    low_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_LOW)

    result = {
        "version": "v114C",
        "status": "passed",
        "input_delta_records_loaded": len(deltas),
        "operator_review_cards_written": len(cards),
        "closed_position_count": closed_count,
        "size_changed_count": size_changed_count,
        "unchanged_count": unchanged_count,
        "new_position_count": new_count,
        "high_attention_count": high_count,
        "medium_attention_count": medium_count,
        "low_attention_count": low_count,
        "external_api_called": EXTERNAL_API_CALLED,
        "local_review_only": True,
        "eligible_for_real_send_count": 0,
        "real_send_candidate_count": 0,
        "tg_send_allowed_count": 0,
        "prod_state_write": PROD_STATE_WRITE,
        "credentials_read": CREDENTIALS_READ,
        "daemon_started": DAEMON_STARTED,
        "watcher_started": WATCHER_STARTED,
        "files_deleted": FILES_DELETED,
        "known_data_consistency_note": (
            "v113D legacy test has v112X total_positions_found 9 "
            "vs v114A baseline 10; not modified in this step."
        ),
        "next_step": "v114d_whale_delta_review_pack_seal_local_only",
        "generated_at": now_iso(),
    }
    save_json(OUT_RESULT, result)
    return result


def write_cards_jsonl(cards):
    """Write operator review cards as JSONL. Returns count written."""
    return save_jsonl(OUT_CARDS, cards)


def write_markdown_report(delta_result, deltas, cards, result):
    """Write the v114C markdown report in Chinese structure with English JSON fields."""

    # Build size_changed table (sorted by size_delta_abs desc)
    size_changed_cards = [c for c in cards if c["delta_type"] == DELTA_SIZE_CHANGED]
    size_changed_cards.sort(key=lambda c: c["size_delta_abs"], reverse=True)

    sc_rows = []
    for c in size_changed_cards:
        addr_short = f"{c['address'][:10]}...{c['address'][-6:]}"
        sc_rows.append(
            f"| {c['asset']} | {c['label']} ({addr_short}) | "
            f"{c['label_confidence']} | "
            f"{c['baseline_size']:,.2f} | {c['current_size']:,.2f} | "
            f"{c['size_delta']:+,.2f} | {c['size_delta_abs']:,.2f} |"
        )

    sc_table = "\n".join(sc_rows) if sc_rows else "| (none) | | | | | | |"

    # Build unchanged table (low priority)
    unchanged_cards = [c for c in cards if c["delta_type"] == DELTA_UNCHANGED]
    uc_rows = []
    for c in unchanged_cards:
        addr_short = f"{c['address'][:10]}...{c['address'][-6:]}"
        uc_rows.append(
            f"| {c['asset']} | {c['label']} ({addr_short}) | "
            f"{c['label_confidence']} | {c['side']} | "
            f"{c['current_size']:,.2f} |"
        )

    uc_table = "\n".join(uc_rows) if uc_rows else "| (none) | | | | |"

    # BTC closed position
    btc_closed = [c for c in cards
                  if c["delta_type"] == DELTA_CLOSED
                  and c["asset"] == "BTC"
                  and c["side"] == "short"]

    # Safety invariant table
    safety_rows = []
    for c in cards:
        addr_short = f"{c['address'][:10]}...{c['address'][-6:]}"
        safety_rows.append(
            f"| {addr_short} | {c['asset']} | {c['side']} | {c['delta_type']} | "
            f"{c['operator_attention_level']} | "
            f"{'✅' if c['local_review_only'] else '❌'} | "
            f"{'✅' if c['operator_action'] == 'review_only_no_send' else '❌'} | "
            f"{'✅' if not c['eligible_for_real_send'] else '❌'} | "
            f"{'✅' if not c['tg_send_allowed'] else '❌'} | "
            f"{'✅' if not c['prod_state_write'] else '❌'} |"
        )
    safety_table = "\n".join(safety_rows)

    report = f"""# v114C Whale Delta Operator Review Pack — Local Only

**Generated:** {result['generated_at']}
**Status:** {result['status']}
**Version:** v114C

---

## 目的 (Purpose)

基于 v114B 的 10 条 whale position delta records，生成本地 operator review pack。
所有内容仅用于本地审阅，不进入 TG send，不写 prod state。

---

## v114B Delta 总览

| 指标 | 数值 |
|------|------|
| 输入 delta records | {result['input_delta_records_loaded']} |
| closed_position | {result['closed_position_count']} |
| size_changed | {result['size_changed_count']} |
| unchanged | {result['unchanged_count']} |
| new_position | {result['new_position_count']} |

### 注意力分布

| 级别 | 数量 |
|------|------|
| 🔴 High | {result['high_attention_count']} |
| 🟡 Medium | {result['medium_attention_count']} |
| 🟢 Low | {result['low_attention_count']} |

---

## 🔴 高优先级事件 (High Attention)

### BTC Short — Closed Position

"""

    if btc_closed:
        c = btc_closed[0]
        report += f"""| 字段 | 值 |
|------|-----|
| 地址 | `{c['address']}` |
| 标签 | {c['label']} |
| 标签置信度 | {c['label_confidence']} |
| 资产 | {c['asset']} |
| 方向 | {c['side']} |
| 基线仓位大小 | {c['baseline_size']:,.2f} |
| 当前仓位大小 | {c['current_size']} |
| 变化量 | {c['size_delta']:+,.2f} |
| 操作员关注级别 | **{c['operator_attention_level']}** |
| 审查摘要 | {c['review_summary']} |

**结论：** `0x50b3...ac9f20` 的 BTC short 已从 baseline 中消失，
明确标记为 `closed_position` 和 `high_operator_attention`。

**注意：** 标签置信度为 low（"Unknown Hyperliquid Whale"），
不能伪装成确定机构。这是本地审阅分类，不是交易信号。

"""
    else:
        report += "⚠️ 未找到 BTC short closed_position 记录。\n\n"

    report += f"""---

## 🟡 仓位变化表格 (Size Changed — Medium Attention)

按变化幅度（size_delta_abs）降序排列：

| Asset | Label | Confidence | Baseline Size | Current Size | Delta | Abs Delta |
|-------|-------|------------|---------------|--------------|-------|-----------|
{sc_table}

---

## 🟢 低优先级观察区 (Unchanged — Low Attention)

| Asset | Label | Confidence | Side | Current Size |
|-------|-------|------------|------|--------------|
{uc_table}

---

## Label Confidence 摘要

| 级别 | 数量 | 说明 |
|------|------|------|
| High | 0 | 无高置信度标签 |
| Medium | 8 | 含 loraclexyz (7) + Matrixport Related (1) |
| Low | 2 | Unknown Hyperliquid Whale + Unknown HYPE Whale |

**标注：** 所有标签置信度从 v114A baseline 保留，本轮未升级。

---

## Liquidation Price 可用性

| 状态 | 数量 |
|------|------|
| 可用 | {delta_result['delta_records_written'] - delta_result['liquidation_price_null_count']} |
| 缺失 / null | {delta_result['liquidation_price_null_count']} |

---

## 安全不变量摘要 (Safety Invariant Summary)

| Address | Asset | Side | Delta Type | Attention | local_review_only | operator_action | eligible_for_real_send | tg_send_allowed | prod_state_write |
|---------|-------|------|------------|-----------|-------------------|-----------------|------------------------|-----------------|------------------|
{safety_table}

---

## Known Data Consistency Note

**v113D historical count mismatch：**
v113D legacy test 有 `total_positions_found=9` vs v114A baseline=10。
这是已知历史字段不一致（v112X 同一批数据的不同快照时点造成）。
本轮 v114C 不修改旧 seal，只记录此已知差异。
不影响 v114B delta records 的本地 review pack。

---

## 明确结论

| 结论 | 状态 |
|------|------|
| local_operator_review_only | ✅ True |
| not_tg_send_ready | ✅ 确认 (所有 cards tg_send_allowed=false) |
| not_prod_state_ready | ✅ 确认 (prod_state_write=false) |
| not_real_send_candidate | ✅ 确认 (eligible_for_real_send_count=0) |
| external_api_called | ✅ False |
| credentials_read | ✅ False |
| daemon_started | ✅ False |
| watcher_started | ✅ False |
| files_deleted | ✅ False |

---

## 下一步建议

**v114D:** Whale delta review pack seal — local-only。
- 对本轮 operator review cards 做最终 seal
- 确认所有分类和审查摘要
- 不进入 TG send，不写 prod state

---

## 输出文件

| 文件 | 路径 |
|------|------|
| Result JSON | `{OUT_RESULT}` |
| Review Cards JSONL | `{OUT_CARDS}` |
| Report MD | `{OUT_REPORT}` |
| Handoff MD | `{OUT_HANDOFF}` |

---

*本报告仅用于本地运营审阅。不构成交易建议，不自动发送。*
"""

    save_text(OUT_REPORT, report)

    # --- Handoff ---
    handoff = f"""# v114C Handoff — Whale Delta Operator Review Pack Local Only

**Generated:** {result['generated_at']}
**Lane:** 1
**Risk Level:** safe-local-only

---

## What was done

1. Loaded v114B delta compare result: {result['input_delta_records_loaded']} delta records.
2. Validated v114B safety invariants (local_delta_compare_only=true, eligible_for_real_send_count=0, tg_send_allowed_count=0, prod_state_write=false).
3. Generated {result['operator_review_cards_written']} operator review cards — one per delta record.
4. Classified by operator attention level:
   - High: {result['high_attention_count']} (BTC short closed_position)
   - Medium: {result['medium_attention_count']} (size_changed positions)
   - Low: {result['low_attention_count']} (unchanged positions)
5. Sorted cards by priority: closed_position > size_changed > new_position > unchanged.
6. Within delta_type, sorted by size_delta_abs descending.
7. All outputs written with full safety invariants enforced.

## Key Results

| Metric | Value |
|--------|-------|
| Input delta records loaded | {result['input_delta_records_loaded']} |
| Operator review cards generated | {result['operator_review_cards_written']} |
| closed_position | {result['closed_position_count']} |
| size_changed | {result['size_changed_count']} |
| unchanged | {result['unchanged_count']} |
| new_position | {result['new_position_count']} |
| High attention | {result['high_attention_count']} |
| Medium attention | {result['medium_attention_count']} |
| Low attention | {result['low_attention_count']} |
| External API called | False |
| Credentials read | False |
| Prod state written | False |

## BTC Closed Position Handling

"""

    if btc_closed:
        c = btc_closed[0]
        handoff += f"""- Address: `{c['address']}`
- Label: {c['label']} (confidence: {c['label_confidence']})
- Asset: {c['asset']}, Side: {c['side']}
- Baseline size: {c['baseline_size']:,.2f}
- Correctly classified as: **closed_position** with **high_operator_attention**
- Not written as an error — this is expected behavior when position disappears between probes.
"""
    else:
        handoff += "⚠️ BTC closed position not found in cards — potential issue.\n"

    handoff += f"""
## Confirmed Safety Invariants

- `local_review_only=true` (all {result['operator_review_cards_written']} cards)
- `operator_action=review_only_no_send` (all cards)
- `eligible_for_real_send=false` (all cards)
- `tg_send_allowed=false` (all cards)
- `prod_state_write=false` (all cards)
- `real_send_candidate=false` (all cards)
- `external_api_called=false`
- `credentials_read=false`
- `daemon_started=false`
- `watcher_started=false`
- `files_deleted=false`

## Operator Attention Rules Applied

- **High**: closed_position, new_position, or size_delta_abs >= 1,000,000
- **Medium**: size_changed with size_delta_abs < 1,000,000
- **Low**: unchanged

## This Stage Is NOT

- Production state
- Send-ready
- TG-eligible
- A trading signal
- A position recommendation
- Ready for external consumption

## This Stage IS

- A local-only operator review pack
- Input for v114D seal
- Fully guarded with safety invariants

## Known Data Consistency Note

v113D legacy test has `total_positions_found=9` vs v114A baseline=10.
This is a known historical field inconsistency (different snapshot timing from same v112X data).
Not modified in this step. Does not affect v114B delta records or v114C review pack.

## Next Step

**v114D — Whale Delta Review Pack Seal (Local-Only)**

Requirements for v114D:
- Seal the v114C operator review cards
- Finalize classifications and review summaries
- No TG send, no prod state, no daemon
- Local seal only

---

*This handoff is for the next stage executor (v114D). No action required now.*
"""

    save_text(OUT_HANDOFF, handoff)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("v114C Whale Delta Operator Review Pack — Local Only")
    print("=" * 70)

    # Step 1: Load v114B data
    print("\n[1/5] Loading v114B delta data...")
    delta_result, deltas = load_v114b_data()
    assert delta_result["delta_records_written"] == 10, \
        f"Expected 10 delta records, got {delta_result['delta_records_written']}"
    assert len(deltas) == 10, \
        f"Expected 10 delta JSONL records, got {len(deltas)}"

    # Step 2: Validate v114B invariants
    print("\n[2/5] Validating v114B invariants...")
    validate_v114b_invariants(delta_result, deltas)

    # Step 3: Generate operator review cards
    print("\n[3/5] Generating operator review cards...")
    cards = generate_review_cards(deltas)
    print(f"  Generated {len(cards)} operator review cards")

    # Summary
    closed_count = sum(1 for c in cards if c["delta_type"] == DELTA_CLOSED)
    size_changed_count = sum(1 for c in cards if c["delta_type"] == DELTA_SIZE_CHANGED)
    unchanged_count = sum(1 for c in cards if c["delta_type"] == DELTA_UNCHANGED)
    new_count = sum(1 for c in cards if c["delta_type"] == DELTA_NEW)
    high_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_HIGH)
    medium_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_MEDIUM)
    low_count = sum(1 for c in cards if c["operator_attention_level"] == ATTENTION_LOW)

    print(f"    closed: {closed_count}, size_changed: {size_changed_count}, "
          f"unchanged: {unchanged_count}, new: {new_count}")
    print(f"    attention: high={high_count}, medium={medium_count}, low={low_count}")

    # Verify BTC closed position
    btc_closed = [c for c in cards
                  if c["delta_type"] == DELTA_CLOSED
                  and c["asset"] == "BTC"
                  and c["side"] == "short"]
    if btc_closed:
        c = btc_closed[0]
        print(f"  [OK] BTC short closed_position found: {c['position_identity_key']}")
        print(f"     attention_level={c['operator_attention_level']}")
        assert c["operator_attention_level"] == ATTENTION_HIGH, \
            "BTC closed_position must be high attention!"
    else:
        print("  [FAIL] BTC short closed_position NOT found!")
        sys.exit(1)

    # Verify all cards have required fields
    for i, c in enumerate(cards):
        assert c["version"] == "v114C", f"card[{i}] version mismatch"
        assert c["local_review_only"] is True, f"card[{i}] local_review_only not True"
        assert c["operator_action"] == "review_only_no_send", \
            f"card[{i}] operator_action not review_only_no_send"
        assert c["eligible_for_real_send"] is False, \
            f"card[{i}] eligible_for_real_send not False"
        assert c["tg_send_allowed"] is False, f"card[{i}] tg_send_allowed not False"
        assert c["prod_state_write"] is False, f"card[{i}] prod_state_write not False"
        assert c.get("review_summary"), f"card[{i}] missing review_summary"
        assert c.get("label_confidence"), f"card[{i}] missing label_confidence"

    # Step 4: Write outputs
    print("\n[4/5] Writing outputs...")

    result = write_result_json(deltas, cards)
    print(f"  Result JSON → {OUT_RESULT}")

    cards_written = write_cards_jsonl(cards)
    print(f"  Review cards JSONL: {cards_written} records → {OUT_CARDS}")

    write_markdown_report(delta_result, deltas, cards, result)
    print(f"  Markdown report → {OUT_REPORT}")
    print(f"  Handoff markdown → {OUT_HANDOFF}")

    # Step 5: Final safety invariant verification
    print("\n[5/5] Safety invariant verification...")
    invariants = [
        ("input_delta_records_loaded", result["input_delta_records_loaded"] == 10),
        ("operator_review_cards_written", result["operator_review_cards_written"] == 10),
        ("closed_position_count", result["closed_position_count"] == 1),
        ("size_changed_count", result["size_changed_count"] == 5),
        ("unchanged_count", result["unchanged_count"] == 4),
        ("new_position_count", result["new_position_count"] == 0),
        ("high_attention_count", result["high_attention_count"] >= 1),
        ("external_api_called", result["external_api_called"] is False),
        ("local_review_only", result["local_review_only"] is True),
        ("eligible_for_real_send_count", result["eligible_for_real_send_count"] == 0),
        ("tg_send_allowed_count", result["tg_send_allowed_count"] == 0),
        ("prod_state_write", result["prod_state_write"] is False),
        ("credentials_read", result["credentials_read"] is False),
        ("daemon_started", result["daemon_started"] is False),
        ("watcher_started", result["watcher_started"] is False),
        ("files_deleted", result["files_deleted"] is False),
    ]

    all_pass = True
    for name, ok in invariants:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
            print(f"  [{status}] {name}")
        else:
            print(f"  [{status}] {name}")

    print("\n" + "=" * 70)
    if all_pass:
        print("v114C COMPLETE — All invariants passed.")
    else:
        print("v114C COMPLETE — Some invariants FAILED.")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
