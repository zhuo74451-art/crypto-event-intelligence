import argparse
import hashlib
import logging
import sys
from pathlib import Path

import pandas as pd

try:
    from utils.time_utils import parse_any_time_to_utc_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster duplicate or syndicated event candidates.")
    parser.add_argument("--input", default=str(ROOT / "data" / "event_candidates_v06_enriched.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "event_candidates_v06_deduped.csv"))
    parser.add_argument("--window-hours", type=int, default=2)
    return parser.parse_args()


def normalize_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def parse_time(value: str) -> pd.Timestamp:
    parsed = parse_any_time_to_utc_iso(value)
    if not parsed:
        return pd.NaT
    return pd.to_datetime(parsed, utc=True, errors="coerce")


def cluster_key(row: pd.Series, window_hours: int) -> str:
    entity = str(row.get("primary_entity", "") or row.get("primary_asset_symbol", "") or "unknown").strip().lower()
    event_type = str(row.get("event_type_l1", "") or row.get("candidate_event_type", "") or "unknown").strip().lower()
    timestamp = parse_time(str(row.get("backtest_time_utc", "") or row.get("published_at_utc", "")))
    if pd.isna(timestamp):
        bucket = "unknown_time"
    else:
        seconds = int(timestamp.timestamp())
        bucket_seconds = window_hours * 3600
        bucket = str(seconds // bucket_seconds)
    raw = f"{entity}|{event_type}|{bucket}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"cluster_{digest}"


def choose_primary(group: pd.DataFrame) -> str:
    work = group.copy()
    for col in ["auto_quality_score", "entity_quality_score", "candidate_importance"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0)
        else:
            work[col] = 0
    work["_has_url"] = work.get("url", pd.Series("", index=work.index)).astype(str).str.strip().ne("").astype(int)
    work["_content_len"] = work.get("content", pd.Series("", index=work.index)).astype(str).str.len()
    work = work.sort_values(
        ["auto_quality_score", "entity_quality_score", "candidate_importance", "_has_url", "_content_len"],
        ascending=[False, False, False, False, False],
    )
    return str(work.iloc[0].get("candidate_id", work.index[0]))


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    input_path = normalize_path(args.input)
    output_path = normalize_path(args.output)
    if not input_path.exists():
        logging.error("input file not found: %s", input_path)
        return 1

    df = pd.read_csv(input_path, dtype=str).fillna("")
    df["event_cluster_id"] = df.apply(lambda row: cluster_key(row, args.window_hours), axis=1)

    cluster_rows = []
    for cluster_id, group in df.groupby("event_cluster_id", dropna=False):
        primary_id = choose_primary(group)
        source_count = group.get("source", pd.Series("", index=group.index)).astype(str).replace("", pd.NA).dropna().nunique()
        duplicate_count = max(len(group) - 1, 0)
        titles = " || ".join(group.get("title", pd.Series("", index=group.index)).astype(str).head(5).tolist())
        for idx in group.index:
            cluster_rows.append(
                {
                    "idx": idx,
                    "is_cluster_primary": str(df.loc[idx, "candidate_id"] == primary_id).lower(),
                    "source_count": int(source_count),
                    "duplicate_count": int(duplicate_count),
                    "cluster_titles": titles,
                }
            )
    cluster_df = pd.DataFrame(cluster_rows).set_index("idx")
    for col in ["is_cluster_primary", "source_count", "duplicate_count", "cluster_titles"]:
        df[col] = cluster_df[col]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logging.info("wrote %s deduped candidates to %s", len(df), output_path)
    logging.info("clusters=%s duplicates=%s", df["event_cluster_id"].nunique(), int((df["duplicate_count"].astype(int) > 0).sum()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
