import argparse
import csv
import hashlib
import json
from pathlib import Path

try:
    from utils.time_utils import parse_any_time_to_utc_iso
except ModuleNotFoundError:
    from scripts.utils.time_utils import parse_any_time_to_utc_iso


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = [
    "unlock_id",
    "asset_symbol",
    "unlock_time_utc",
    "unlock_name",
    "unlock_amount_usd",
    "unlock_pct_circulating",
    "source",
    "url",
    "enabled",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize raw token-unlock CSV exports into token_unlock_calendar.csv format.")
    parser.add_argument("--input", default=str(ROOT / "data" / "raw_token_unlocks_template.csv"))
    parser.add_argument("--output", default=str(ROOT / "data" / "token_unlock_calendar_imported.csv"))
    parser.add_argument("--mapping", default=str(ROOT / "data" / "token_unlock_column_mapping.json"))
    parser.add_argument("--symbol-map", default=str(ROOT / "data" / "symbol_map.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v081_token_unlock_import_summary.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v081_token_unlock_import_report.md"))
    parser.add_argument("--default-source", default="manual_unlock_csv")
    parser.add_argument("--default-timezone", default="Asia/Shanghai")
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


def read_mapping(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_value(row: dict, aliases: list[str]) -> str:
    lower_to_key = {str(key).strip().lower(): key for key in row.keys()}
    for alias in aliases:
        key = lower_to_key.get(str(alias).strip().lower())
        if key is not None:
            value = str(row.get(key, "") or "").strip()
            if value:
                return value
    return ""


def safe_float_text(value: str) -> str:
    raw = str(value or "").strip().replace(",", "").replace("$", "").replace("%", "")
    if not raw:
        return ""
    try:
        return f"{float(raw):.6f}".rstrip("0").rstrip(".")
    except Exception:
        return ""


def truthy_text(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"", "1", "true", "yes", "y", "active", "enabled"}:
        return "true"
    if raw in {"0", "false", "no", "n", "disabled", "inactive"}:
        return "false"
    return "true"


def load_symbol_map(path: Path) -> set[str]:
    return {str(row.get("asset_symbol", "") or "").strip().upper() for row in read_rows(path) if str(row.get("asset_symbol", "") or "").strip()}


def make_unlock_id(raw_id: str, asset: str, unlock_time_utc: str, name: str, source: str) -> str:
    if raw_id:
        return str(raw_id).strip()
    material = "|".join([asset, unlock_time_utc, name, source])
    digest = hashlib.sha1(material.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"unlock_{digest}"


def is_sample(row: dict) -> bool:
    text = " ".join(str(row.get(key, "") or "") for key in ["unlock_id", "unlock_name", "source", "notes"]).lower()
    return "sample" in text or "template" in text


def markdown_table(rows: list[dict], columns: list[str]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return lines


def main() -> int:
    args = parse_args()
    input_path = normalize_path(args.input)
    mapping = read_mapping(normalize_path(args.mapping))
    symbols = load_symbol_map(normalize_path(args.symbol_map))
    raw_rows = read_rows(input_path)

    rows = []
    skipped_rows = 0
    invalid_time_rows = 0
    missing_symbol_rows = 0
    unsupported_symbol_rows = 0
    missing_amount_rows = 0
    missing_pct_rows = 0
    duplicate_rows = 0
    seen = set()

    for raw in raw_rows:
        raw_id = first_value(raw, mapping.get("raw_id", ["raw_id", "id"]))
        asset = first_value(raw, mapping.get("asset_symbol", ["asset_symbol", "symbol", "token"])).upper()
        timezone_name = first_value(raw, mapping.get("timezone", ["timezone"])) or args.default_timezone
        raw_time = first_value(raw, mapping.get("unlock_time", ["unlock_time", "date", "time"]))
        unlock_time_utc = parse_any_time_to_utc_iso(raw_time, default_timezone=timezone_name)
        name = first_value(raw, mapping.get("unlock_name", ["unlock_name", "title", "name"]))
        amount = safe_float_text(first_value(raw, mapping.get("unlock_amount_usd", ["unlock_amount_usd", "amount_usd", "value_usd"])))
        pct = safe_float_text(first_value(raw, mapping.get("unlock_pct_circulating", ["unlock_pct_circulating", "pct", "percentage"])))
        source = first_value(raw, mapping.get("source", ["source", "provider"])) or args.default_source
        url = first_value(raw, mapping.get("url", ["url", "link"]))
        enabled = truthy_text(first_value(raw, mapping.get("enabled", ["enabled"])))
        notes = first_value(raw, mapping.get("notes", ["notes", "note"]))
        flags = []

        if not asset:
            missing_symbol_rows += 1
            flags.append("missing_symbol")
        elif asset not in symbols:
            unsupported_symbol_rows += 1
            flags.append("unsupported_symbol")
        if not unlock_time_utc:
            invalid_time_rows += 1
            flags.append("invalid_time")
        if not amount:
            missing_amount_rows += 1
            flags.append("missing_amount_usd")
        if not pct:
            missing_pct_rows += 1
            flags.append("missing_pct_circulating")
        if is_sample({"unlock_id": raw_id, "unlock_name": name, "source": source, "notes": notes}):
            flags.append("sample_row")

        unlock_id = make_unlock_id(raw_id, asset, unlock_time_utc, name, source)
        dedupe = (asset, unlock_time_utc, name, source)
        if dedupe in seen:
            duplicate_rows += 1
            skipped_rows += 1
            continue
        seen.add(dedupe)

        if not asset or not unlock_time_utc:
            skipped_rows += 1
            continue

        merged_notes = notes
        if flags:
            merged_notes = (merged_notes + "; " if merged_notes else "") + "import_flags=" + ",".join(flags)
        rows.append(
            {
                "unlock_id": unlock_id,
                "asset_symbol": asset,
                "unlock_time_utc": unlock_time_utc,
                "unlock_name": name or f"{asset} token unlock",
                "unlock_amount_usd": amount,
                "unlock_pct_circulating": pct,
                "source": source,
                "url": url,
                "enabled": enabled,
                "notes": merged_notes,
            }
        )

    output_path = normalize_path(args.output)
    write_rows(output_path, rows, OUTPUT_COLUMNS)
    real_rows = sum(1 for row in rows if not is_sample(row))
    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "raw_rows": len(raw_rows),
        "output_rows": len(rows),
        "real_rows": real_rows,
        "sample_rows": len(rows) - real_rows,
        "skipped_rows": skipped_rows,
        "duplicate_rows": duplicate_rows,
        "invalid_time_rows": invalid_time_rows,
        "missing_symbol_rows": missing_symbol_rows,
        "unsupported_symbol_rows": unsupported_symbol_rows,
        "missing_amount_rows": missing_amount_rows,
        "missing_pct_rows": missing_pct_rows,
        "status": "pass" if rows else "no_output_rows",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))

    preview = rows[:20]
    lines = [
        "# v0.8.1 Token Unlock Import Report",
        "",
        f"- input: `{input_path}`",
        f"- output: `{output_path}`",
        f"- raw_rows: {len(raw_rows)}",
        f"- output_rows: {len(rows)}",
        f"- real_rows: {real_rows}",
        f"- sample_rows: {len(rows) - real_rows}",
        f"- invalid_time_rows: {invalid_time_rows}",
        f"- unsupported_symbol_rows: {unsupported_symbol_rows}",
        "",
        "## Preview",
        "",
        *markdown_table(preview, ["unlock_id", "asset_symbol", "unlock_time_utc", "unlock_amount_usd", "unlock_pct_circulating", "source"]),
        "",
        "## Usage",
        "",
        "Default output is non-destructive. After reviewing quality, rerun with `--output data/token_unlock_calendar.csv` to replace the live calendar.",
        "",
    ]
    normalize_path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"output_rows={len(rows)}")
    print(f"real_rows={real_rows}")
    print(f"wrote_output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
