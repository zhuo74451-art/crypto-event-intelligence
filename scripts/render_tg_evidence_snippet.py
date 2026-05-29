import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render evidence snippets for TG cards from quality/effectiveness matrices.")
    parser.add_argument("--alerts", default=str(ROOT / "data" / "tg_alert_ledger.csv"))
    parser.add_argument("--event-matrix", default=str(ROOT / "results" / "event_type_performance_matrix.csv"))
    parser.add_argument("--source-effectiveness", default=str(ROOT / "results" / "source_effectiveness_report.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "tg_evidence_snippets.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "tg_evidence_snippets.md"))
    parser.add_argument("--limit", type=int, default=50)
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


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_float_text(value: str, pct: bool = True) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    try:
        number = float(raw)
    except ValueError:
        return raw
    if pct:
        return f"{number * 100:.2f}%"
    return f"{number:.4f}"


def matrix_index(rows: list[dict]) -> dict[tuple[str, str], dict]:
    output = {}
    for row in rows:
        key = (str(row.get("event_type") or ""), str(row.get("source_type") or ""))
        sample = int(float(row.get("sample_count") or 0))
        current = output.get(key)
        if not current or sample > int(float(current.get("sample_count") or 0)):
            output[key] = row
    return output


def source_index(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("source_type") or ""): row for row in rows}


def sample_label(n: int) -> str:
    if n >= 50:
        return "样本较多"
    if n >= 20:
        return "样本中等"
    if n > 0:
        return "样本偏少"
    return "暂无样本"


def build_snippet(alert: dict, matrix: dict, source: dict) -> tuple[str, str]:
    event_type = str(alert.get("event_type") or "")
    source_type = str(alert.get("source_type") or "")
    mrow = matrix.get((event_type, source_type)) or {}
    srow = source.get(source_type) or {}
    sample = int(float(mrow.get("sample_count") or 0))
    source_status = srow.get("live_effectiveness_status") or srow.get("historical_status") or "未评估"
    route = srow.get("recommended_route") or alert.get("board_label") or "-"
    if sample:
        evidence = (
            f"历史样本：{sample} 条（{sample_label(sample)}）；"
            f"24h 同类异常收益均值 {safe_float_text(mrow.get('avg_abnormal_primary_24h'))}；"
            f"源状态：{source_status}；建议路由：{route}"
        )
    else:
        evidence = f"历史样本：暂无；源状态：{source_status}；建议路由：{route}"
    if sample < 20:
        caution = f"📊 样本偏少（{sample}条），建议结合其他数据源验证。" if sample else "📊 暂无历史样本，建议结合其他数据源验证。"
    elif "noise" in source_status:
        caution = "源质量偏弱，优先降噪或进入摘要。"
    else:
        caution = "基于历史统计展示，不构成交易建议。"
    return evidence, caution


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    alerts = read_rows(normalize_path(args.alerts))[-args.limit :]
    matrix = matrix_index(read_rows(normalize_path(args.event_matrix)))
    sources = source_index(read_rows(normalize_path(args.source_effectiveness)))
    output = []
    for alert in alerts:
        evidence, caution = build_snippet(alert, matrix, sources)
        output.append(
            {
                "alert_id": alert.get("alert_id", ""),
                "published_at_china": alert.get("published_at_china", ""),
                "asset_symbol": alert.get("asset_symbol", ""),
                "event_type": alert.get("event_type", ""),
                "source_type": alert.get("source_type", ""),
                "evidence_snippet": evidence,
                "caution_snippet": caution,
            }
        )

    fields = list(output[0].keys()) if output else ["alert_id", "evidence_snippet"]
    write_rows(normalize_path(args.output), output, fields)
    lines = [
        "# TG Evidence Snippets",
        "",
        "These snippets replace black-box scores with sample-size and source-quality context.",
        "",
        *markdown_table(output[-20:], ["alert_id", "asset_symbol", "event_type", "source_type", "evidence_snippet", "caution_snippet"]),
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"snippet_rows={len(output)}")
    print(f"wrote_output={normalize_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
