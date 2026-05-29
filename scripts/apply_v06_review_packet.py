import argparse
import logging
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

MANUAL_COLS = [
    "manual_decision",
    "manual_event_type_l1",
    "manual_event_type_l2",
    "manual_primary_asset_symbol",
    "manual_channel_route",
    "manual_useful_for_research",
    "manual_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply reviewed packet edits back to v0.6 manual label sheet.")
    parser.add_argument("--sheet", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--packet", default=str(ROOT / "data" / "v06_manual_label_batch_review.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "v06_manual_label_sheet.csv"))
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument("--summary", default=str(ROOT / "results" / "v06_review_packet_apply_summary.csv"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def as_str(value: object) -> str:
    return str(value if value is not None else "").strip()


def is_blank(value: object) -> bool:
    return as_str(value) == ""


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    sheet_path = normalize_path(args.sheet)
    packet_path = normalize_path(args.packet)
    output_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)

    if not sheet_path.exists():
        logging.error("sheet not found: %s", sheet_path)
        return 1
    if not packet_path.exists():
        logging.error("packet not found: %s", packet_path)
        return 1

    sheet = pd.read_csv(sheet_path, dtype=str).fillna("")
    packet = pd.read_csv(packet_path, dtype=str).fillna("")
    if "candidate_id" not in sheet.columns or "candidate_id" not in packet.columns:
        logging.error("candidate_id is required in both sheet and packet")
        return 1

    for col in MANUAL_COLS:
        if col not in sheet.columns:
            sheet[col] = ""
        if col not in packet.columns:
            packet[col] = ""
    if "manual_review_required" not in sheet.columns:
        sheet["manual_review_required"] = ""
    if "label_origin" not in sheet.columns:
        sheet["label_origin"] = ""

    sheet = sheet.set_index("candidate_id", drop=False)
    packet = packet.drop_duplicates(subset=["candidate_id"], keep="last")

    changed_rows = 0
    skipped_rows = 0

    for _, prow in packet.iterrows():
        cid = as_str(prow.get("candidate_id"))
        if not cid or cid not in sheet.index:
            continue
        touched = False
        for col in MANUAL_COLS:
            new_val = as_str(prow.get(col))
            cur_val = as_str(sheet.at[cid, col])
            if is_blank(new_val):
                continue
            if not args.allow_overwrite and not is_blank(cur_val):
                continue
            if new_val != cur_val:
                sheet.at[cid, col] = new_val
                touched = True
        if touched:
            sheet.at[cid, "manual_review_required"] = "false"
            origin = as_str(sheet.at[cid, "label_origin"])
            if origin == "auto_provisional":
                sheet.at[cid, "label_origin"] = "human_verified"
            changed_rows += 1
        else:
            skipped_rows += 1

    out = sheet.reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    pd.DataFrame(
        [
            {
                "sheet_rows": len(out),
                "packet_rows": len(packet),
                "changed_rows": changed_rows,
                "skipped_rows": skipped_rows,
                "allow_overwrite": args.allow_overwrite,
            }
        ]
    ).to_csv(summary_path, index=False)
    logging.info("applied packet to %s", output_path)
    logging.info("wrote apply summary to %s", summary_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
