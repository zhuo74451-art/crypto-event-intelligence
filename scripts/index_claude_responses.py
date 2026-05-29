import argparse
import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index local Claude response Markdown files for Project OS tracking.")
    parser.add_argument("--results-dir", default=str(ROOT / "results"))
    parser.add_argument("--csv-output", default=str(ROOT / "results" / "claude_response_index.csv"))
    parser.add_argument("--md-output", default=str(ROOT / "docs" / "CLAUDE_RESPONSE_INDEX.md"))
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


def classify_response(path: Path, text: str) -> str:
    name = path.name.lower()
    lowered = text.lower()
    if "manual_reduction" in name:
        return "manual_reduction"
    if "question_backlog" in name:
        return "question_backlog"
    if "engineering_direction" in name:
        return "engineering_direction"
    if "tg_pilot" in name:
        return "tg_pilot"
    if "macro_holdout" in name:
        return "macro_holdout"
    if "release_rules" in name:
        return "release_rules"
    if "claude_next_response" in name or "claude response" in lowered[:200]:
        return "next_consultation"
    return "other"


def first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def metadata_value(text: str, key: str) -> str:
    prefix = f"- {key}:"
    for line in text.splitlines()[:30]:
        if line.strip().lower().startswith(prefix.lower()):
            return line.split(":", 1)[1].strip()
    return ""


def index_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    stat = path.stat()
    return {
        "file": safe_rel(path),
        "response_type": classify_response(path, text),
        "title": first_heading(text),
        "generated_at": metadata_value(text, "generated_at"),
        "model": metadata_value(text, "model"),
        "prompt": metadata_value(text, "prompt"),
        "prompt_sha256_16": metadata_value(text, "prompt_sha256_16"),
        "size_bytes": stat.st_size,
        "line_count": len(text.splitlines()),
        "modified_at_china": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "content_sha256_16": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16],
    }


def render_markdown(rows: list[dict]) -> str:
    lines = [
        "# Claude Response Index",
        "",
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}",
        "",
        "This index tracks local Claude responses stored under `results/`. It does not mark advice as accepted; accepted project decisions still belong in `docs/DECISIONS.md`.",
        "",
    ]
    if not rows:
        lines.append("No Claude response files found.")
        return "\n".join(lines) + "\n"

    df = pd.DataFrame(rows)
    type_counts = df["response_type"].value_counts().to_dict()
    lines.extend(["## Counts", "", "| response_type | count |", "|---|---:|"])
    for key, count in type_counts.items():
        lines.append(f"| {key} | {count} |")

    latest = df.sort_values("modified_at_china", ascending=False).head(12)
    lines.extend(
        [
            "",
            "## Latest Responses",
            "",
            "| file | type | modified_at_china | title |",
            "|---|---|---|---|",
        ]
    )
    for _, row in latest.iterrows():
        title = str(row.get("title", "")).replace("|", "\\|")
        lines.append(
            f"| `{row['file']}` | {row['response_type']} | {row['modified_at_china']} | {title} |"
        )

    lines.extend(
        [
            "",
            "## Operating Rule",
            "",
            "- Store raw Claude responses in `results/`.",
            "- Run `python scripts/index_claude_responses.py` after adding a response.",
            "- Convert accepted recommendations into `docs/DECISIONS.md` before changing product direction.",
            "- Do not treat unreviewed Claude text as implementation authority.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    results_dir = normalize_path(args.results_dir)
    csv_output = normalize_path(args.csv_output)
    md_output = normalize_path(args.md_output)

    rows = []
    if results_dir.exists():
        for path in sorted(results_dir.glob("*claude*.md")):
            rows.append(index_file(path))

    csv_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(csv_output, index=False)
    md_output.write_text(render_markdown(rows), encoding="utf-8")
    print(f"indexed {len(rows)} Claude response files")
    print(f"wrote CSV index to {csv_output}")
    print(f"wrote Markdown index to {md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
