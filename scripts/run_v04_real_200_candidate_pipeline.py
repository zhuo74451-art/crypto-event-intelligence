import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

try:
    from summarize_event_candidates import build_overall_summary, grouped_summary
except ModuleNotFoundError:
    from scripts.summarize_event_candidates import build_overall_summary, grouped_summary


ROOT = Path(__file__).resolve().parents[1]

STANDARD_FIELDS = [
    "raw_id",
    "published_at",
    "source_published_at",
    "source_timezone",
    "title",
    "content",
    "source",
    "url",
    "language",
    "author",
    "category",
    "tags",
]

FIELD_ALIASES = {
    "raw_id": ["raw_id", "id", "tweet_id", "post_id", "message_id", "news_id"],
    "published_at": ["published_at", "created_at", "publish_time", "time", "timestamp", "date"],
    "source_published_at": ["source_published_at", "source_time", "original_published_at", "article_published_at", "news_published_at"],
    "source_timezone": ["source_timezone", "timezone", "tz", "source_tz"],
    "title": ["title", "headline", "title_hint", "short_title"],
    "content": ["content", "text", "body", "summary", "summary_hint", "message"],
    "source": ["source", "source_type", "source_type_hint", "platform", "channel"],
    "url": ["url", "link", "source_url"],
    "language": ["language", "lang"],
    "author": ["author", "username", "user", "screen_name"],
    "category": ["category", "type", "priority"],
    "tags": ["tags", "tag", "tags_json", "labels"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v0.4 real 200-news candidate import pipeline.")
    parser.add_argument("--raw-input", default=str(ROOT / "data" / "raw_news_real_200.csv"))
    parser.add_argument("--mapping", default=str(ROOT / "data" / "raw_news_column_mapping.json"))
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--normalized-output", default=str(ROOT / "data" / "raw_news_real_200_normalized.csv"))
    parser.add_argument("--candidates-output", default=str(ROOT / "data" / "event_candidates_real_200_review.csv"))
    parser.add_argument("--inspection-output", default="")
    parser.add_argument("--summary-prefix", default="v04")
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def infer_mapping(columns: List[str]) -> Dict[str, str]:
    lower_to_original = {column.lower(): column for column in columns}
    mapping: Dict[str, str] = {}
    for target, aliases in FIELD_ALIASES.items():
        source = ""
        for alias in aliases:
            if alias.lower() in lower_to_original:
                source = lower_to_original[alias.lower()]
                break
        mapping[target] = source
    return mapping


def load_or_create_mapping(mapping_path: Path, columns: List[str]) -> Dict[str, str]:
    inferred = infer_mapping(columns)
    if not mapping_path.exists():
        ensure_parent(mapping_path)
        mapping_path.write_text(
            json.dumps(inferred, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logging.warning("mapping file was missing; wrote inferred mapping to %s", mapping_path)
        return inferred

    with mapping_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    mapping = {field: str(loaded.get(field, inferred.get(field, "")) or "") for field in STANDARD_FIELDS}
    changed = False
    for field in STANDARD_FIELDS:
        if not mapping[field] and inferred.get(field):
            mapping[field] = inferred[field]
            changed = True
    if changed:
        mapping_path.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logging.info("updated missing mapping fields in %s", mapping_path)
    return mapping


def normalize_raw_news(df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
    normalized = pd.DataFrame()
    for target in STANDARD_FIELDS:
        source = mapping.get(target, "")
        if source and source in df.columns:
            normalized[target] = df[source].fillna("").astype(str)
        else:
            normalized[target] = ""

    if (normalized["raw_id"].str.strip() == "").any():
        missing_mask = normalized["raw_id"].str.strip() == ""
        normalized.loc[missing_mask, "raw_id"] = [
            f"real_{idx + 1:05d}" for idx in normalized.index[missing_mask]
        ]
    return normalized[STANDARD_FIELDS]


def write_inspection(
    raw_df: pd.DataFrame,
    normalized: pd.DataFrame,
    mapping: Dict[str, str],
    output_path: Path,
) -> None:
    rows = []
    row_count = len(normalized)
    for field in STANDARD_FIELDS:
        source = mapping.get(field, "")
        present = bool(source and source in raw_df.columns)
        non_empty_count = int((normalized[field].fillna("").astype(str).str.strip() != "").sum())
        sample_value = ""
        if non_empty_count:
            sample_value = normalized.loc[
                normalized[field].fillna("").astype(str).str.strip() != "", field
            ].iloc[0]
        notes = []
        if not present:
            notes.append("source_column_missing")
        if non_empty_count == 0:
            notes.append("all_empty")
        rows.append(
            {
                "row_count": row_count,
                "standard_field": field,
                "source_column": source,
                "source_column_present": str(present).lower(),
                "non_empty_count": non_empty_count,
                "empty_count": row_count - non_empty_count,
                "sample_value": sample_value[:200],
                "notes": ",".join(notes),
            }
        )
    ensure_parent(output_path)
    pd.DataFrame(rows).to_csv(output_path, index=False)


def run_step(name: str, command: list) -> None:
    logging.info("starting step: %s", name)
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")
    logging.info("finished step: %s", name)


def write_candidate_summaries(candidates_path: Path, output_dir: Path, prefix: str) -> None:
    df = pd.read_csv(candidates_path, dtype=str).fillna("")
    overall = build_overall_summary(df)
    by_event_type = grouped_summary(df, "candidate_event_type")
    by_scope = grouped_summary(df, "event_scope")

    overall.to_csv(output_dir / f"{prefix}_candidate_import_summary.csv", index=False)
    by_event_type.to_csv(output_dir / f"{prefix}_candidate_summary_by_event_type.csv", index=False)
    by_scope.to_csv(output_dir / f"{prefix}_candidate_summary_by_scope.csv", index=False)


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    raw_input = normalize_path(args.raw_input)
    mapping_path = normalize_path(args.mapping)
    symbol_map = normalize_path(args.symbol_map)
    normalized_output = normalize_path(args.normalized_output)
    candidates_output = normalize_path(args.candidates_output)
    inspection_output = (
        normalize_path(args.inspection_output)
        if args.inspection_output
        else ROOT / "results" / f"{args.summary_prefix}_real_news_export_inspection.csv"
    )
    output_dir = ROOT / "results"

    if not raw_input.exists():
        logging.error("raw input not found: %s", raw_input)
        logging.error("export recent 30-90 day news to data/raw_news_real_200.csv first")
        return 1

    raw_df = pd.read_csv(raw_input, dtype=str).fillna("")
    if args.limit and args.limit > 0:
        raw_df = raw_df.head(args.limit)
    logging.info("loaded %s raw rows from %s", len(raw_df), raw_input)

    mapping = load_or_create_mapping(mapping_path, list(raw_df.columns))
    normalized = normalize_raw_news(raw_df, mapping)
    ensure_parent(normalized_output)
    normalized.to_csv(normalized_output, index=False)
    logging.info("wrote normalized raw news to %s", normalized_output)

    write_inspection(raw_df, normalized, mapping, inspection_output)
    logging.info("wrote export inspection to %s", inspection_output)

    try:
        run_step(
            "import candidates",
            [
                sys.executable,
                "scripts/import_raw_news_to_event_candidates.py",
                "--input",
                str(normalized_output),
                "--output",
                str(candidates_output),
                "--symbol-map",
                str(symbol_map),
                "--limit",
                str(args.limit),
            ],
        )
        write_candidate_summaries(candidates_output, output_dir, args.summary_prefix)
        logging.info("wrote candidate summaries with prefix %s to %s", args.summary_prefix, output_dir)
    except Exception as exc:
        logging.error("v0.4 candidate pipeline failed: %s", exc)
        return 1

    logging.info("v0.4 candidate pipeline completed; review %s before 50-sample backtest", candidates_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
