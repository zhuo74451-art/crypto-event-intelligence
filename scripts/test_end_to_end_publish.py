import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local end-to-end publish preview from watcher/ETF candidates without sending Telegram.")
    parser.add_argument("--first-hand", default=str(ROOT / "data" / "v14_first_hand_publish_candidates.csv"))
    parser.add_argument("--etf-digest", default=str(ROOT / "results" / "v14_etf_daily_digest.md"))
    parser.add_argument("--etf-summary", default=str(ROOT / "results" / "v14_etf_daily_digest_summary.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_e2e_publish_preview.md"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_e2e_publish_preview_summary.csv"))
    parser.add_argument("--simulated-now-utc", default="")
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


def parse_utc(value: str):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def money(value) -> str:
    try:
        number = float(str(value or "0").strip())
    except Exception:
        number = 0.0
    if number >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿美元"
    if number >= 10_000:
        return f"{number / 10_000:.2f} 万美元"
    return f"{number:.2f} 美元"


def render_first_hand(rows: list[dict]) -> list[str]:
    lines = []
    publishable = [row for row in rows if row.get("v14_first_hand_route") in {"digest_candidate", "daily_digest_candidate", "intraday_candidate"}]
    if not publishable:
        return ["本轮一手 watcher 没有可发布候选。", ""]
    lines.append("## 一手 Watcher 候选")
    lines.append("")
    for row in publishable:
        source = row.get("watcher_source", "")
        asset = row.get("asset_symbol", "")
        route = row.get("v14_first_hand_route", "")
        reason = row.get("v14_first_hand_reason", "")
        lines.extend(
            [
                f"### {asset}｜{source}",
                f"- 路由：{route}",
                f"- 金额/规模：{money(row.get('amount_usd'))}",
                f"- 观察时间：中国时间 {row.get('observed_at_china','')}",
                f"- 依据：{reason}",
                f"- 验证基础：{row.get('verification_basis','')}",
                "",
            ]
        )
    return lines


def main() -> int:
    args = parse_args()
    first_hand_rows = read_rows(normalize_path(args.first_hand))
    etf_summary = read_rows(normalize_path(args.etf_summary))
    etf_text = normalize_path(args.etf_digest).read_text(encoding="utf-8") if normalize_path(args.etf_digest).exists() else ""
    etf_publishable = bool(etf_summary and str(etf_summary[0].get("publishable_daily_digest") or "").lower() == "true")
    first_hand_publishable = [
        row for row in first_hand_rows
        if row.get("v14_first_hand_route") in {"digest_candidate", "daily_digest_candidate", "intraday_candidate"}
    ]
    simulated_now = parse_utc(args.simulated_now_utc) or datetime.now(timezone.utc)
    latencies = []
    needs_review = 0
    for row in first_hand_publishable:
        observed = parse_utc(row.get("observed_at_utc"))
        if observed:
            latencies.append(max(0.0, (simulated_now - observed).total_seconds() / 60))
        if row.get("v14_first_hand_route") != "intraday_candidate":
            needs_review += 1
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0
    lines = [
        "# v14 End-to-End Publish Preview",
        "",
        f"- generated_at_china: {china_stamp()}",
        "- mode: local_preview_only",
        "- telegram_send: false",
        f"- simulated_now_utc: {simulated_now.replace(microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- avg_latency_minutes: {avg_latency:.1f}",
        f"- max_latency_minutes: {max_latency:.1f}",
        "",
        "## ETF 日频候选",
        "",
        etf_text.strip() if etf_text else "暂无 ETF 日频候选。",
        "",
        *render_first_hand(first_hand_rows),
        "## 发布声明",
        "",
        "本预览仅验证从数据源到候选卡片的本地链路，不自动发送，不构成交易建议。",
        "",
    ]
    normalize_path(args.output).write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "generated_at_china": china_stamp(),
        "etf_publishable": "true" if etf_publishable else "false",
        "first_hand_publishable_rows": len(first_hand_publishable),
        "events_detected": len(first_hand_rows),
        "events_published": len(first_hand_publishable),
        "events_need_review": needs_review,
        "avg_latency_minutes": round(avg_latency, 2),
        "max_latency_minutes": round(max_latency, 2),
        "latency_sla_pass": "true" if max_latency <= 30 else "false",
        "preview_sections": 1 + (1 if first_hand_publishable else 0),
        "telegram_send": "false",
        "status": "pass",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"etf_publishable={summary['etf_publishable']}")
    print(f"first_hand_publishable_rows={summary['first_hand_publishable_rows']}")
    print("status=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
