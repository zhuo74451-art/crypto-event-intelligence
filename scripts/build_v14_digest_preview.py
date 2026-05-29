import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a strict v14 morning/evening digest preview from quality-gated rows.")
    parser.add_argument("--etf", default=str(ROOT / "data" / "etf_fund_flow_filtered.csv"))
    parser.add_argument("--exploit", default=str(ROOT / "data" / "active_exploit_verified.csv"))
    parser.add_argument("--policy", default=str(ROOT / "data" / "v14_publish_policy_candidates.csv"))
    parser.add_argument("--source-scores", default=str(ROOT / "data" / "source_scores_v14_webhook_split.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_digest_preview.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_digest_preview_summary.csv"))
    parser.add_argument("--min-source-score", type=float, default=50.0)
    parser.add_argument("--max-security", type=int, default=3)
    parser.add_argument("--max-fund-flow", type=int, default=3)
    parser.add_argument("--max-upgrade", type=int, default=5)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_float(value) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return 0.0


def short_text(value: str, limit: int = 58) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def money_cn(value) -> str:
    number = safe_float(value)
    if number >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿美元"
    if number >= 10_000:
        return f"{number / 10_000:.2f} 万美元"
    if number > 0:
        return f"{number:.2f} 美元"
    return "未解析"


def pct(value) -> str:
    number = safe_float(value)
    return f"{number * 100:+.2f}%"


def source_score_map(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for row in rows:
        key = str(row.get("subsource") or "").strip()
        if key:
            output[key] = row
    return output


def source_allowed(row: dict, scores: dict[str, dict], min_score: float) -> tuple[bool, float, str]:
    source = str(row.get("source") or "").strip()
    score_row = scores.get(source)
    if not score_row:
        return False, 0.0, "missing_source_score"
    score = safe_float(score_row.get("score"))
    action = str(score_row.get("recommended_action") or "")
    if score < min_score or action == "block":
        return False, score, f"source_score_below_{min_score:g}"
    return True, score, action


def build_security_rows(rows: list[dict], scores: dict[str, dict], args: argparse.Namespace) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("urgent_eligible") or "").lower() != "true":
            continue
        allowed, score, source_status = source_allowed(row, scores, args.min_source_score)
        if not allowed:
            continue
        item = dict(row)
        item["source_score"] = score
        item["source_status"] = source_status
        output.append(item)
    return sorted(output, key=lambda item: safe_float(item.get("estimated_amount_usd")), reverse=True)[: args.max_security]


def build_fund_rows(rows: list[dict], scores: dict[str, dict], args: argparse.Namespace) -> list[dict]:
    output = []
    for row in rows:
        if str(row.get("v14_etf_filter_decision") or "") != "keep":
            continue
        allowed, score, source_status = source_allowed(row, scores, args.min_source_score)
        if not allowed:
            continue
        item = dict(row)
        item["source_score"] = score
        item["source_status"] = source_status
        output.append(item)
    return sorted(
        output,
        key=lambda item: (safe_float(item.get("parsed_flow_amount_usd")), safe_float(item.get("abnormal_vs_btc_24h"))),
        reverse=True,
    )[: args.max_fund_flow]


def rows_from_policy(policy_rows: list[dict], etf_rows: list[dict], exploit_rows: list[dict], args: argparse.Namespace) -> tuple[list[dict], list[dict], list[dict]]:
    etf_by_id = {str(row.get("event_id") or "").strip(): row for row in etf_rows}
    exploit_by_id = {str(row.get("event_id") or "").strip(): row for row in exploit_rows}
    security_rows = []
    fund_rows = []
    upgrade_rows = []
    for row in policy_rows:
        if str(row.get("v14_policy_route") or "") != "digest":
            continue
        event_id = str(row.get("event_id") or "").strip()
        subtype = str(row.get("event_subtype") or "").strip()
        item = dict(row)
        if subtype == "exploit_or_theft":
            item.update(exploit_by_id.get(event_id, {}))
            security_rows.append(item)
        elif subtype == "etf_or_fund_flow":
            item.update(etf_by_id.get(event_id, {}))
            fund_rows.append(item)
        elif subtype == "upgrade_or_fork":
            upgrade_rows.append(item)
    security_rows = sorted(security_rows, key=lambda item: safe_float(item.get("estimated_amount_usd")), reverse=True)
    fund_rows = sorted(
        fund_rows,
        key=lambda item: (safe_float(item.get("parsed_flow_amount_usd")), safe_float(item.get("v14_publish_score"))),
        reverse=True,
    )
    upgrade_rows = sorted(upgrade_rows, key=lambda item: (item.get("upgrade_route") != "digest", -safe_float(item.get("v14_publish_score"))))
    deduped_upgrades = []
    seen_upgrade_keys = set()
    for item in upgrade_rows:
        key = (str(item.get("asset_symbol") or ""), str(item.get("upgrade_type") or ""))
        if key in seen_upgrade_keys:
            continue
        seen_upgrade_keys.add(key)
        deduped_upgrades.append(item)
    return security_rows[: args.max_security], fund_rows[: args.max_fund_flow], deduped_upgrades[: args.max_upgrade]


def render_digest(security_rows: list[dict], fund_rows: list[dict], upgrade_rows: list[dict], summary: dict) -> str:
    lines = [
        f"🧭 <b>市场情报摘要测试版</b>",
        f"时间：{summary['generated_at_china']}",
        "",
        "本摘要只展示已过质量闸门的候选事件；未通过来源分、金额语境或资产一致性检查的内容不展示。",
        "",
    ]
    if security_rows:
        lines.append("🛡️ <b>安全事件</b>")
        for idx, row in enumerate(security_rows, 1):
            lines.append(
                f"{idx}. {short_text(row.get('title'))}｜金额 {money_cn(row.get('estimated_amount_usd'))}｜已过安全事件闸门"
            )
        lines.append("")
    if fund_rows:
        lines.append("🏦 <b>ETF/基金流</b>")
        for idx, row in enumerate(fund_rows, 1):
            amount = money_cn(row.get("parsed_flow_amount_usd"))
            abn = pct(row.get("abnormal_vs_btc_24h"))
            lines.append(f"{idx}. {short_text(row.get('title'))}｜金额 {amount}｜24h相对BTC {abn}｜已过来源/语境闸门")
        lines.append("")
    if upgrade_rows:
        lines.append("🧱 <b>主网/协议升级</b>")
        for idx, row in enumerate(upgrade_rows, 1):
            upgrade_type = str(row.get("upgrade_type") or "upgrade")
            lines.append(f"{idx}. {short_text(row.get('title'))}｜资产 {row.get('asset_symbol','')}｜类型 {upgrade_type}｜事件提醒")
        lines.append("")
    if not security_rows and not fund_rows and not upgrade_rows:
        lines.append("本轮没有满足 v14 质量闸门的可展示事件。")
        lines.append("")
    lines.extend(
        [
            "🔎 阅读方式：优先看事件是否有明确来源、金额和上下文；相对BTC仅用于复盘观察，不代表结论。",
            "⚠️ 仅作市场结构与链上情报观察，不构成任何交易建议。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    scores = source_score_map(read_rows(normalize_path(args.source_scores)))
    policy_rows = read_rows(normalize_path(args.policy))
    etf_rows = read_rows(normalize_path(args.etf))
    exploit_rows = read_rows(normalize_path(args.exploit))
    if policy_rows:
        security_rows, fund_rows, upgrade_rows = rows_from_policy(policy_rows, etf_rows, exploit_rows, args)
    else:
        security_rows = build_security_rows(exploit_rows, scores, args)
        fund_rows = build_fund_rows(etf_rows, scores, args)
        upgrade_rows = []
    summary = {
        "generated_at_china": china_stamp(),
        "security_rows": len(security_rows),
        "fund_flow_rows": len(fund_rows),
        "upgrade_rows": len(upgrade_rows),
        "min_source_score": args.min_source_score,
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    normalize_path(args.output).parent.mkdir(parents=True, exist_ok=True)
    normalize_path(args.output).write_text(render_digest(security_rows, fund_rows, upgrade_rows, summary), encoding="utf-8")
    print(f"security_rows={len(security_rows)}")
    print(f"fund_flow_rows={len(fund_rows)}")
    print(f"upgrade_rows={len(upgrade_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
