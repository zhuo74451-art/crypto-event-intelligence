"""Week 1 manifest validation script.
Run: python -X utf8 research/validate_manifest.py
"""
import json, sys

with open("research/week1_samples_v1.json", "r", encoding="utf-8") as f:
    data = json.load(f)

samples = data["samples"]
errors = []

# Manifest version checks
assert data["manifest"]["manifest_version"] == "v1.1"
assert "correction_commit" in data["manifest"]

nm = data["manifest"]["normalization_mapping"]
assert "A 结构性" in nm["news_quality"]
assert "B 注意力" in nm["news_quality"]
assert "高" in nm["trade_relevance"]
assert "观察" in nm["decision"]
assert "仅风险提示" in nm["decision"]
assert "利空" in nm["direction"]
assert "不确定" in nm["direction"]
assert "高" in nm["pump_risk"]
assert "低" in nm["pump_risk"]

# Verbatim raw summaries
EXPECTED_SUMMARIES = {
    "w1_001": "知名交易员Loracle的HYPE空单浮亏扩大至约3146万美元，持仓规模约1.13亿美元，均价45.35美元，当前币价62.78美元，清算价89.17美元。",
    "w1_002": "麻吉黄立成在HyperLiquid增持ETH多单921.47枚，持仓规模约1355.56万美元，均价2097.23美元，清算价2068.80美元。",
    "w1_003": "分析师称Binance近10天BTC强劲流入，周均流入从378 BTC升至1190 BTC，5月18日单日流入超3600 BTC，储备量增加16000 BTC。",
    "w1_004": "Strategy本周暂停比特币购买，转而购入债券并计划回购近15亿美元可转换债务；Saylor提到未来可能小规模出售部分BTC。",
    "w1_005": "WTI原油期货日内暴跌6%，报90.80美元/桶。",
}

# Expected raw values
EXPECTED_RAW = {
    "w1_001": {"existing_news_quality_raw": "B 注意力", "existing_trade_relevance_raw": "高", "existing_decision_raw": "观察", "existing_direction_raw": "不确定", "existing_pump_risk_raw": "中", "existing_ai_confidence_raw": 78, "notion_page_id": "36b0246231d381ce899becc2bbb1ff7c"},
    "w1_002": {"existing_news_quality_raw": "B 注意力", "existing_trade_relevance_raw": "高", "existing_decision_raw": "仅风险提示", "existing_direction_raw": "不确定", "existing_pump_risk_raw": "中", "existing_ai_confidence_raw": 80, "notion_page_id": "36b0246231d3815ba165d11100396df5"},
    "w1_003": {"existing_news_quality_raw": "A 结构性", "existing_trade_relevance_raw": "高", "existing_decision_raw": "仅风险提示", "existing_direction_raw": "利空", "existing_pump_risk_raw": "低", "existing_ai_confidence_raw": 78, "notion_page_id": "36b0246231d381d29130d2ff58f3efee"},
    "w1_004": {"existing_news_quality_raw": "A 结构性", "existing_trade_relevance_raw": "高", "existing_decision_raw": "观察", "existing_direction_raw": "利空", "existing_pump_risk_raw": "低", "existing_ai_confidence_raw": 75, "notion_page_id": "36b0246231d3810cb1e2d5cf7dceeb90"},
    "w1_005": {"existing_news_quality_raw": "A 结构性", "existing_trade_relevance_raw": "中", "existing_decision_raw": "观察", "existing_direction_raw": "不确定", "existing_pump_risk_raw": "低", "existing_ai_confidence_raw": 76, "notion_page_id": "36b0246231d381faa258d757ca47da18"},
}

# Raw-to-normalized mapping
RAW_TO_NORM = {
    ("existing_news_quality_raw", "B 注意力"): "attention",
    ("existing_news_quality_raw", "A 结构性"): "structural",
    ("existing_trade_relevance_raw", "高"): "high",
    ("existing_trade_relevance_raw", "中"): "medium",
    ("existing_decision_raw", "观察"): "observe",
    ("existing_decision_raw", "仅风险提示"): "risk_tip",
    ("existing_direction_raw", "利空"): "bearish",
    ("existing_direction_raw", "不确定"): "uncertain",
    ("existing_pump_risk_raw", "高"): "high",
    ("existing_pump_risk_raw", "中"): "medium",
    ("existing_pump_risk_raw", "低"): "low",
}

NORM_FIELDS = {
    "existing_news_quality_normalized": "existing_news_quality_raw",
    "existing_trade_relevance_normalized": "existing_trade_relevance_raw",
    "existing_decision_normalized": "existing_decision_raw",
    "existing_direction_normalized": "existing_direction_raw",
    "existing_pump_risk_normalized": "existing_pump_risk_raw",
}

ALIAS_FIELDS = ["existing_news_quality", "existing_trade_relevance", "existing_decision", "existing_direction", "existing_pump_risk"]

for s in samples:
    sid = s["sample_id"]

    # 1. Notion page IDs non-null
    assert s["notion_page_id"] is not None, f"{sid}: notion_page_id is null"
    assert len(s["notion_page_id"]) > 0, f"{sid}: notion_page_id empty"
    assert s["notion_page_url"] is not None, f"{sid}: notion_page_url is null"

    # 2. Verbatim raw summary
    if sid in EXPECTED_SUMMARIES:
        expected = EXPECTED_SUMMARIES[sid]
        assert s["raw_summary"] == expected, f"{sid}: summary MISMATCH"

    # 3. t0 policy
    assert s["event_time_utc"] is None, f"{sid}: event_time_utc must be null"
    assert s["event_time_status"] == "unavailable", f"{sid}: event_time_status must be unavailable"
    assert s["t0_basis"] == "broadcast_time", f"{sid}: t0_basis must be broadcast_time"

    # 4. Raw values match expected
    if sid in EXPECTED_RAW:
        for key, val in EXPECTED_RAW[sid].items():
            assert s[key] == val, f"{sid}: {key} expected={val!r} got={s[key]!r}"

    # 5. Normalized fields derived from raw via mapping
    for norm_field, raw_field in NORM_FIELDS.items():
        raw_val = s[raw_field]
        expected_norm = RAW_TO_NORM.get((raw_field, raw_val))
        assert s[norm_field] == expected_norm, f"{sid}: {norm_field} mismatch: raw={raw_val} -> norm={s[norm_field]} expected={expected_norm}"

    # 6. Deprecated alias fields
    for field in ALIAS_FIELDS:
        assert field in s, f"{sid}: missing deprecated alias {field}"
        assert isinstance(s[field], dict), f"{sid}: {field} must be dict"
        assert s[field].get("deprecated_alias") is True, f"{sid}: {field} missing deprecated_alias=True"

    # 7. No price or attribution data
    text = json.dumps(s, ensure_ascii=False)
    for term in ["price_data", "return_pct", "return_decimal", "abnormal_return"]:
        assert term not in text, f"{sid}: contains price term: {term}"

    # 8. Sample ID format
    assert sid.startswith("w1_"), f"{sid}: must start with w1_"
    num = sid[4:]
    assert num.isdigit(), f"{sid}: suffix must be digits"
    assert 1 <= int(num) <= 5, f"{sid}: id out of range"

    # 9. HYPE provider rationale corrected
    if sid == "w1_001":
        assert "supports both 1m and 15m" in s["price_provider_plan"], f"{sid}: must mention both 1m and 15m"
        assert "retention" in s["price_interval_plan"], f"{sid}: must mention retention-range choice"

    print(f"  {sid}: ALL CHECKS PASSED")

print()
print(f"All {len(samples)} samples validated (0 errors)")
print(f"  notion_page_ids:      5/5 non-null")
print(f"  raw_summaries:         5/5 verbatim")
print(f"  raw_fields:            5/5 preserved")
print(f"  normalized_fields:    5/5 derived via mapping")
print(f"  deprecated_aliases:   25/25 (5 per sample)")
print(f"  event_time_utc:       null for all")
print(f"  t0_basis:             broadcast_time for all")
print(f"  price/attribution:    absent from all")
print(f"  sample_ids:           consistent w1_001-005")
print(f"  HYPE provider:        corrected (mentions 1m+15m, retention choice)")
