import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHINA_TZ = timezone(timedelta(hours=8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize LLM/OpenRouter usage ledger.")
    parser.add_argument("--input", default=str(ROOT / "data" / "llm_usage_ledger.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "llm_usage_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "llm_usage_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "llm_usage_report.md"))
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


def china_stamp() -> str:
    return datetime.now(CHINA_TZ).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def safe_int(value) -> int:
    try:
        return int(float(str(value or "0").strip() or 0))
    except ValueError:
        return 0


def safe_float(value) -> float:
    try:
        return float(str(value or "0").strip() or 0)
    except ValueError:
        return 0.0


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    rows = read_rows(normalize_path(args.input))
    grouped = defaultdict(list)
    for row in rows:
        key = (row.get("task_type") or "unknown", row.get("model") or "unknown", row.get("status") or "unknown")
        grouped[key].append(row)

    output = []
    for (task_type, model, status), items in grouped.items():
        output.append(
            {
                "task_type": task_type,
                "model": model,
                "status": status,
                "call_count": len(items),
                "prompt_tokens": sum(safe_int(row.get("prompt_tokens")) for row in items),
                "completion_tokens": sum(safe_int(row.get("completion_tokens")) for row in items),
                "total_tokens": sum(safe_int(row.get("total_tokens")) for row in items),
                "estimated_cost_usd": round(sum(safe_float(row.get("estimated_cost_usd")) for row in items), 6),
            }
        )
    output.sort(key=lambda row: (-safe_float(row["estimated_cost_usd"]), row["task_type"], row["model"]))
    write_rows(normalize_path(args.output), output, list(output[0].keys()) if output else ["task_type", "call_count"])

    summary = {
        "status": "pass",
        "generated_at_china": china_stamp(),
        "call_count": len(rows),
        "ok_count": sum(1 for row in rows if row.get("status") == "ok"),
        "fail_count": sum(1 for row in rows if row.get("status") == "fail"),
        "total_tokens": sum(safe_int(row.get("total_tokens")) for row in rows),
        "estimated_cost_usd": round(sum(safe_float(row.get("estimated_cost_usd")) for row in rows), 6),
        "output": str(normalize_path(args.output)),
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    lines = [
        "# LLM Usage Report",
        "",
        f"- generated_at_china: {summary['generated_at_china']}",
        f"- call_count: {summary['call_count']}",
        f"- total_tokens: {summary['total_tokens']}",
        f"- estimated_cost_usd: {summary['estimated_cost_usd']}",
        "",
        "## By Task / Model",
        "",
        *markdown_table(output, ["task_type", "model", "status", "call_count", "total_tokens", "estimated_cost_usd"]),
        "",
        "Usage is estimated from provider-reported tokens when available. Secrets are never recorded here.",
        "",
    ]
    normalize_path(args.markdown_output).write_text("\n".join(lines), encoding="utf-8")
    print(f"call_count={len(rows)}")
    print(f"estimated_cost_usd={summary['estimated_cost_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
