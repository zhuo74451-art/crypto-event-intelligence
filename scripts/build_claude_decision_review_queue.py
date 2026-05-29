import argparse
import hashlib
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

ACTION_KEYWORDS = [
    "recommend",
    "should",
    "must",
    "do not",
    "don't",
    "action",
    "priority",
    "gate",
    "split",
    "separate",
    "route",
    "policy",
    "decision",
    "建议",
    "应该",
    "必须",
    "不要",
    "优先",
    "拆分",
    "分流",
    "策略",
    "决策",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a human-reviewable decision queue from local Claude responses without auto-applying advice."
    )
    parser.add_argument("--index", default=str(ROOT / "results" / "claude_response_index.csv"))
    parser.add_argument("--existing", default=str(ROOT / "data" / "claude_decision_review_queue.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "claude_decision_review_queue.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "docs" / "CLAUDE_DECISION_REVIEW.md"))
    parser.add_argument("--limit-per-file", type=int, default=80)
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_existing(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        return {}
    if "content_sha256_16" not in df.columns:
        return {}
    return {str(row["content_sha256_16"]): row.to_dict() for _, row in df.iterrows()}


def line_type(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith(("-", "*")):
        return "bullet"
    if re.match(r"^\d+[\.)]\s+", stripped):
        return "numbered"
    if stripped.startswith("|"):
        return "table_row"
    return "sentence"


def clean_line(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^\d+[\.)]\s+", "", text)
    text = text.strip().strip("|").strip()
    return re.sub(r"\s+", " ", text)


def looks_actionable(text: str) -> bool:
    lowered = text.lower()
    if len(text) < 18:
        return False
    if text.startswith("---"):
        return False
    return any(keyword in lowered for keyword in ACTION_KEYWORDS)


def classify_scope(text: str, section: str) -> str:
    lowered = f"{section} {text}".lower()
    checks = [
        ("tg", ["tg", "telegram", "draft", "publish", "auto_publish", "auto-send"]),
        ("taxonomy", ["taxonomy", "event_type", "l1", "l2", "bucket", "classification", "分类"]),
        ("asset_attribution", ["asset", "symbol", "btc", "eth", "hype", "primary asset", "归因"]),
        ("macro_policy", ["macro", "market-wide", "regulation", "policy", "fed", "cpi", "宏观"]),
        ("qa", ["audit", "false positive", "false negative", "gate", "rollback", "验证", "回滚"]),
        ("data", ["source", "timezone", "csv", "dataset", "label", "样本", "数据"]),
        ("backtest", ["backtest", "benchmark", "abnormal", "return", "回测"]),
        ("product", ["product", "stream", "channel", "用户", "产品"]),
    ]
    for scope, keywords in checks:
        if any(keyword in lowered for keyword in keywords):
            return scope
    return "unknown"


def extract_items(path: Path, response_type: str, limit: int) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    section = ""
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("#").strip()
            continue
        item_text = clean_line(stripped)
        if not looks_actionable(item_text):
            continue
        item_hash = hashlib.sha256(
            f"{safe_rel(path)}\n{section}\n{item_text}".encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        rows.append(
            {
                "item_id": f"claude_{item_hash}",
                "source_file": safe_rel(path),
                "response_type": response_type,
                "line_number": lineno,
                "section_heading": section,
                "line_type": line_type(stripped),
                "suggested_scope": classify_scope(item_text, section),
                "recommendation_text": item_text,
                "decision_status": "pending",
                "decision_id": "",
                "implementation_status": "not_started",
                "review_notes": "",
                "content_sha256_16": item_hash,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def merge_existing(rows: list[dict], existing: dict[str, dict]) -> list[dict]:
    preserved_columns = ["decision_status", "decision_id", "implementation_status", "review_notes"]
    merged = []
    for row in rows:
        old = existing.get(row["content_sha256_16"], {})
        for col in preserved_columns:
            if old.get(col, ""):
                row[col] = old[col]
        merged.append(row)
    return merged


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Claude Decision Review",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        "This queue extracts possible decision/action items from Claude responses. It is a review aid only.",
        "",
        "Rules:",
        "",
        "- `pending` means not accepted.",
        "- `accepted` requires a matching entry in `docs/DECISIONS.md`.",
        "- `implementation_status=done` requires code/docs/tests to prove the change.",
        "- Do not implement direction-level recommendations directly from this queue.",
        "",
    ]
    if not rows:
        lines.append("No actionable Claude decision items found.")
        return "\n".join(lines) + "\n"

    df = pd.DataFrame(rows)
    lines.extend(["## Status Counts", "", "| decision_status | count |", "|---|---:|"])
    for key, count in df["decision_status"].value_counts().to_dict().items():
        lines.append(f"| {key} | {count} |")
    lines.extend(["", "## Scope Counts", "", "| suggested_scope | count |", "|---|---:|"])
    for key, count in df["suggested_scope"].value_counts().to_dict().items():
        lines.append(f"| {key} | {count} |")

    preview = df[df["decision_status"].astype(str).eq("pending")].head(25)
    lines.extend(
        [
            "",
            "## Pending Preview",
            "",
            "| item_id | scope | source | recommendation |",
            "|---|---|---|---|",
        ]
    )
    for _, row in preview.iterrows():
        rec = str(row["recommendation_text"]).replace("|", "\\|")
        if len(rec) > 180:
            rec = rec[:177] + "..."
        lines.append(f"| `{row['item_id']}` | {row['suggested_scope']} | `{row['source_file']}` | {rec} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    index_path = normalize_path(args.index)
    output_path = normalize_path(args.output)
    md_output = normalize_path(args.md_output)
    existing_path = normalize_path(args.existing)

    if not index_path.exists():
        print(f"Claude response index not found: {index_path}")
        return 1
    index_df = pd.read_csv(index_path, dtype=str).fillna("")
    existing = load_existing(existing_path)

    rows: list[dict] = []
    for _, index_row in index_df.iterrows():
        source_file = str(index_row.get("file", ""))
        if not source_file:
            continue
        path = normalize_path(source_file)
        if not path.exists():
            continue
        rows.extend(extract_items(path, str(index_row.get("response_type", "unknown")), args.limit_per_file))

    rows = merge_existing(rows, existing)
    rows = sorted(rows, key=lambda row: (row["decision_status"] != "pending", row["source_file"], int(row["line_number"])))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    md_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"wrote {len(rows)} Claude decision review items to {output_path}")
    print(f"wrote Markdown review to {md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
