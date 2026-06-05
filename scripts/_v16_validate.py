"""v16 final acceptance validation script."""
import csv

print("=" * 60)
print("1. raw_signals.csv VERIFICATION")
print("=" * 60)

rows = list(csv.DictReader(open("data/raw_signals.csv", encoding="utf-8-sig")))
print(f"Data rows: {len(rows)}")
strengths = [float(r["magnitude"]) for r in rows]
strengths.sort()
print(f"strength min: {min(strengths)}")
print(f"strength max: {max(strengths)}")
print(f"strength avg: {sum(strengths)/len(strengths):.1f}")
print(f"strength > 100: {sum(1 for s in strengths if s > 100)}")
print(f"strength < 0: {sum(1 for s in strengths if s < 0)}")
empty_asset = sum(1 for r in rows if not r.get("asset", "").strip())
empty_ts = sum(1 for r in rows if not r.get("timestamp_china", "").strip())
print(f"empty asset: {empty_asset}")
print(f"empty timestamp_china: {empty_ts}")

print()
print("TOP 10 STRENGTH:")
print(f"{'asset':<8} {'category':<32} {'strength':>8} {'conf':>6} {'ts_china':<24} {'fh':>5}")
print("-" * 90)
ranked = sorted(rows, key=lambda r: -float(r["magnitude"]))[:10]
for r in ranked:
    print(f"{r['asset']:<8} {r['signal_category']:<32} {r['magnitude']:>8} {r['confidence']:>6} {r['timestamp_china']:<24} {r['is_first_hand']:>5}")

print()
print("=" * 60)
print("2. aggregated_events.csv VERIFICATION")
print("=" * 60)

ev_rows = list(csv.DictReader(open("data/aggregated_events.csv", encoding="utf-8-sig")))
print(f"event_count: {len(ev_rows)}")
assets = set(r["asset"] for r in ev_rows)
print(f"asset_count: {len(assets)}")
fh_events = sum(1 for r in ev_rows if int(float(r.get("first_hand_count", 0))) > 0)
pure_data = sum(1 for r in ev_rows if int(float(r.get("first_hand_count", 0))) == 0)
print(f"first_hand_event_count: {fh_events}")
print(f"pure_data_event_count: {pure_data}")
has_fh_field = "has_first_hand_signal" in ev_rows[0] if ev_rows else False
print(f"has_first_hand_signal field: {has_fh_field}")
fh_tagged = sum(1 for r in ev_rows if "含一手监控信号" in r.get("summary", ""))
pure_tagged = sum(1 for r in ev_rows if "纯数据信号" in r.get("summary", ""))
print(f"summary [含一手监控信号]: {fh_tagged}")
print(f"summary [纯数据信号]: {pure_tagged}")
has_fh_true = sum(1 for r in ev_rows if r.get("has_first_hand_signal", "") in ("True", "true", "1"))
has_fh_false = sum(1 for r in ev_rows if r.get("has_first_hand_signal", "") in ("False", "false", "0", ""))
print(f"has_first_hand_signal=True: {has_fh_true}")
print(f"has_first_hand_signal=False: {has_fh_false}")

print()
print("=" * 60)
print("3. v16_asset_event_cards.md VERIFICATION")
print("=" * 60)

with open("results/v16_asset_event_cards.md", encoding="utf-8") as f:
    content = f.read()
card_count = content.count("## ") - content.count("## 说明") - content.count("## MARKET")
print(f"card_count: {card_count}")
fh_badge = "一手监控" in content
print(f"[一手监控] badge present: {fh_badge}")
disclaimer = "不构成任何交易建议" in content
print(f"Disclaimer present: {disclaimer}")
liq_wall = "清算墙" in content
print(f"'清算墙' in user-visible text: {liq_wall}")
liq_disclaimer = "不代表全市场清算密集区" in content
print(f"'不代表全市场清算密集区' present: {liq_disclaimer}")

print()
print("=" * 60)
print("4. v16_asset_event_cards_summary.csv VERIFICATION")
print("=" * 60)

import os
path = "results/v16_asset_event_cards_summary.csv"
print(f"File exists: {os.path.exists(path)}")
if os.path.exists(path):
    s_rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    for s in s_rows:
        for k, v in s.items():
            print(f"  {k}: {v}")
