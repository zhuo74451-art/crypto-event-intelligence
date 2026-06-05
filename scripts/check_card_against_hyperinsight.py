"""v1.6E: Benchmark Market Radar cards against HyperInsight standards."""
import csv, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = [
    "long\n", "short\n", "buy_ratio", "current_side", "profile_enabled",
    "size-based Delta", "active_behavior_card", "conflict_semantics_card",
    "该消息具备观察价值", "建议关注后续", "看多", "看空", "利好", "利空",
    "吸筹", "出货", "战神", "聪明钱", "胜率",
]

def score_card(text: str) -> dict:
    scores = {}
    # 1. Title clarity (15): must have asset + action
    has_asset = bool(re.search(r'(HYPE|BTC|ETH|SOL|BNB|DOGE|XRP|TON|AVAX|LINK)', text))
    has_action = bool(re.search(r'(买入|卖出|加仓|减仓|爆仓|平仓|减持|增持|连续买入|连续卖出|反手|提取)', text))
    scores["title_clarity"] = 15 if (has_asset and has_action) else (8 if has_asset else 0)

    # 2. Identity (15): must have address/trader/pool label
    has_identity = bool(re.search(r'(0x[a-fA-F0-9]{8,}|loraclexyz|Abras|Loracle|监控池|TOP\s*\d)', text, re.IGNORECASE))
    scores["identity"] = 15 if has_identity else 5

    # 3. Action clarity (20): human action words
    action_words = ["加仓", "减仓", "爆仓", "平仓", "提取保证金", "反手", "连续买入", "连续卖出",
                    "减持", "增持", "净买入", "净卖出"]
    action_count = sum(1 for a in action_words if a in text)
    scores["action_clarity"] = min(20, action_count * 7)

    # 4. Key numbers (20): at least 3 specific numbers
    num_count = len(re.findall(r'\d+[\.\d]*\s*(万|枚|笔|美元|M|K|%|亿)', text))
    num_count += len(re.findall(r'\$\d+', text))
    scores["key_numbers"] = min(20, num_count * 5)

    # 5. Annotation (15): must have background note
    has_note = bool(re.search(r'(注[：:]|背景[：:]|🔥)', text))
    scores["annotation"] = 15 if has_note else 0

    # 6. No machine/forbidden words (15)
    machine_hits = sum(1 for kw in FORBIDDEN if kw in text)
    scores["clean_language"] = max(0, 15 - machine_hits * 3)

    total = sum(scores.values())
    return {"total": total, "breakdown": scores, "passes": total >= 80}


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=str(ROOT / "results" / "hyperinsight_style_card_preview_v1.md"))
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        # Try v2
        alt = ROOT / "results" / "address_behavior_card_preview_v2.md"
        if alt.exists():
            input_path = alt
            print(f"Using fallback: {input_path}")
        else:
            return 1

    text = input_path.read_text(encoding="utf-8")
    # Split into per-card sections
    cards = re.split(r'\n## ', text)
    results = []
    for card_text in cards:
        if not card_text.strip(): continue
        title_match = re.match(r'([^\n]+)', card_text)
        card_title = title_match.group(1) if title_match else "unknown"
        s = score_card(card_text)
        results.append({"card": card_title[:60], "score": s["total"], "passes": s["passes"],
                        "breakdown": str(s["breakdown"])})

    csv_path = ROOT / "results" / "card_benchmark_score.csv"
    md_path = ROOT / "results" / "card_benchmark_score.md"

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["card", "score", "passes", "breakdown"])
        w.writeheader(); w.writerows(results)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Card Benchmark Scores (vs HyperInsight)\n\n")
        f.write("| card | score | passes (>=80) |\n|---|---:|---|\n")
        for r in results:
            f.write(f"| {r['card'][:50]} | {r['score']} | {r['passes']} |\n")
        avg = sum(r["score"] for r in results) / max(len(results), 1)
        all_pass = all(r["passes"] for r in results)
        f.write(f"\n- average_score: {avg:.0f}\n")
        f.write(f"- all_pass: {all_pass}\n")

    for r in results:
        print(f"  [{r['score']}/100] {'PASS' if r['passes'] else 'FAIL'} | {r['card'][:60]}")
    print(f"CSV: {csv_path}\nMD: {md_path}")
    return 0 if all(r["passes"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
