import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


REVIEW_COLUMNS = [
    "candidate_id",
    "raw_id",
    "published_at",
    "published_at_utc",
    "published_at_china",
    "backtest_time",
    "backtest_time_utc",
    "backtest_time_china",
    "source_timezone",
    "source_timezone_assumption",
    "title",
    "content",
    "source",
    "url",
    "primary_asset_symbol",
    "primary_entity",
    "primary_entity_type",
    "detected_entity_names",
    "event_type_l1",
    "event_type_l2",
    "event_scope",
    "publish_decision",
    "research_priority",
    "relevance_score_realtime",
    "impact_score",
    "certainty_score",
    "timeliness_score",
    "entity_quality_score",
    "source_count",
    "duplicate_count",
    "discard_reason",
    "primary_discard_reason",
    "secondary_discard_reasons",
    "tradability_tier",
    "tradability_tier_reason",
    "channel_route",
    "entity_flags",
    "quality_flags",
    "recommended_benchmark",
    "benchmark_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export v0.6 review queues and a markdown summary.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data" / "event_candidates_v06_relevance_scored.csv"),
    )
    parser.add_argument(
        "--review-output",
        default=str(ROOT / "data" / "event_candidates_v06_publish_review_queue.csv"),
    )
    parser.add_argument(
        "--other-output",
        default=str(ROOT / "data" / "event_candidates_v06_other_review_queue.csv"),
    )
    parser.add_argument(
        "--discard-output",
        default=str(ROOT / "data" / "event_candidates_v06_discard_audit_sample.csv"),
    )
    parser.add_argument(
        "--report",
        default=str(ROOT / "results" / "v061_review_queue_report.md"),
    )
    parser.add_argument("--discard-sample-size", type=int, default=80)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = [col for col in REVIEW_COLUMNS if col in df.columns]
    out = df[cols].copy()
    out["manual_decision"] = ""
    out["manual_event_type_l1"] = ""
    out["manual_event_type_l2"] = ""
    out["manual_primary_asset_symbol"] = ""
    out["manual_notes"] = ""
    return out


def markdown_table(df: pd.DataFrame, columns: list[str], max_rows: int = 20) -> str:
    df = df.head(max_rows)
    if df.empty:
        return "_No rows._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        cells = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                cells.append(f"{value:.2f}")
            else:
                cells.append(str(value).replace("\n", " ")[:140])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def count_table(series: pd.Series) -> str:
    counts = series.fillna("").astype(str).value_counts()
    lines = ["| value | count |", "|---|---:|"]
    for value, count in counts.items():
        lines.append(f"| {value or '(blank)'} | {count} |")
    return "\n".join(lines)


def write_report(df: pd.DataFrame, report_path: Path, review: pd.DataFrame, other: pd.DataFrame, discard: pd.DataFrame) -> None:
    lines = [
        "# v0.6.1 Review Queue Report",
        "",
        "This report is for manual QA before any TG publishing is connected.",
        "",
        "## Counts",
        f"- total: {len(df)}",
        f"- publish review queue: {len(review)}",
        f"- other review queue: {len(other)}",
        f"- discard audit sample: {len(discard)}",
        "",
        "## Publish Decision Distribution",
        count_table(df.get("publish_decision", pd.Series("", index=df.index))),
        "",
        "## Event Type L1 Distribution",
        count_table(df.get("event_type_l1", pd.Series("", index=df.index))),
        "",
        "## Discard Reason Distribution",
        count_table(df.get("discard_reason", pd.Series("", index=df.index))),
        "",
        "## Top Publish Review Rows",
        markdown_table(
            review,
            [
                "candidate_id",
                "title",
                "primary_asset_symbol",
                "event_type_l1",
                "publish_decision",
                "relevance_score_realtime",
                "source_count",
            ],
            25,
        ),
        "",
        "## Top Other Review Rows",
        markdown_table(
            other,
            [
                "candidate_id",
                "title",
                "detected_entity_names",
                "primary_asset_symbol",
                "discard_reason",
            ],
            25,
        ),
        "",
        "## Manual Review Instructions",
        "- Fill `manual_decision` with `approve_publish`, `keep_review`, `discard`, or `fix_taxonomy`.",
        "- Fill manual taxonomy fields only when the automatic L1/L2/asset is wrong.",
        "- Do not connect TG publishing until false positives in this queue are reviewed.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    input_path = normalize_path(args.input)
    review_path = normalize_path(args.review_output)
    other_path = normalize_path(args.other_output)
    discard_path = normalize_path(args.discard_output)
    report_path = normalize_path(args.report)

    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    df["relevance_score_realtime_num"] = pd.to_numeric(df.get("relevance_score_realtime", ""), errors="coerce").fillna(0)
    df["duplicate_count_num"] = pd.to_numeric(df.get("duplicate_count", ""), errors="coerce").fillna(0)

    publish_queue = df[df["publish_decision"].isin(["auto_publish", "human_review"])].copy()
    publish_queue = publish_queue.sort_values(
        ["publish_decision", "relevance_score_realtime_num", "duplicate_count_num"],
        ascending=[True, False, False],
    )

    other_queue = df[df.get("event_type_l1", "") == "other_review"].copy()
    other_queue = other_queue.sort_values(["duplicate_count_num", "relevance_score_realtime_num"], ascending=False)

    discard = df[df["publish_decision"] == "discard"].copy()
    discard = discard.sort_values(["relevance_score_realtime_num", "duplicate_count_num"], ascending=False).head(args.discard_sample_size)

    for path, out_df in [
        (review_path, select_columns(publish_queue)),
        (other_path, select_columns(other_queue)),
        (discard_path, select_columns(discard)),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(path, index=False)
        logging.info("wrote %s rows to %s", len(out_df), path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(df, report_path, publish_queue, other_queue, discard)
    logging.info("wrote report to %s", report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
