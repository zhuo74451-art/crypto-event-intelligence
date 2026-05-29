import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate v0.7 first-hand watcher watchlists.")
    parser.add_argument("--addresses", default=str(ROOT / "data" / "watchlist_addresses.csv"))
    parser.add_argument("--stablecoins", default=str(ROOT / "data" / "stablecoin_watchlist.csv"))
    parser.add_argument("--hyperliquid", default=str(ROOT / "data" / "hyperliquid_watchlist.csv"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v07_watchlist_validation_report.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v07_watchlist_validation_summary.csv"))
    parser.add_argument("--markdown-output", default=str(ROOT / "results" / "v07_watchlist_validation_report.md"))
    return parser.parse_args()


def normalize_path(value: str) -> Path:
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


def is_enabled(row: dict) -> bool:
    return str(row.get("enabled", "")).strip().lower() in {"1", "true", "yes", "y"}


def number(value: str) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError:
        return 0.0


def check_address_rows(rows: list[dict]) -> list[dict]:
    checks = []
    seen = {}
    for idx, row in enumerate(rows, start=2):
        address = str(row.get("address", "")).strip()
        key = address.lower()
        flags = []
        if not ADDRESS_RE.match(address):
            flags.append("invalid_address")
        if key in seen:
            flags.append("duplicate_address")
        seen[key] = idx
        if not str(row.get("blockchain", "")).strip():
            flags.append("missing_blockchain")
        if str(row.get("blockchain", "")).strip().lower() != "ethereum":
            flags.append("unsupported_blockchain_for_v07")
        if not str(row.get("label", "")).strip():
            flags.append("missing_label")
        if not str(row.get("entity", "")).strip():
            flags.append("missing_entity")
        if not str(row.get("category", "")).strip():
            flags.append("missing_category")
        if is_enabled(row) and number(row.get("alert_threshold_usd")) <= 0:
            flags.append("invalid_threshold")
        checks.append(
            {
                "source_file": "watchlist_addresses.csv",
                "row_number": idx,
                "address": address,
                "label": row.get("label", ""),
                "category": row.get("category", ""),
                "enabled": row.get("enabled", ""),
                "status": "fail" if flags else "pass",
                "flags": ",".join(flags),
            }
        )
    return checks


def check_stablecoin_rows(rows: list[dict]) -> list[dict]:
    checks = []
    seen = {}
    for idx, row in enumerate(rows, start=2):
        token = str(row.get("token_symbol", "")).strip().upper()
        token_address = str(row.get("token_address", "")).strip()
        treasury = str(row.get("treasury_address", "")).strip()
        key = token or token_address.lower()
        flags = []
        if not token:
            flags.append("missing_token_symbol")
        if key in seen:
            flags.append("duplicate_stablecoin")
        seen[key] = idx
        if not ADDRESS_RE.match(token_address):
            flags.append("invalid_token_address")
        if not ADDRESS_RE.match(treasury):
            flags.append("invalid_treasury_address")
        if number(row.get("decimals")) <= 0:
            flags.append("invalid_decimals")
        if is_enabled(row) and number(row.get("mint_threshold_usd")) <= 0:
            flags.append("invalid_mint_threshold")
        if is_enabled(row) and number(row.get("burn_threshold_usd")) <= 0:
            flags.append("invalid_burn_threshold")
        checks.append(
            {
                "source_file": "stablecoin_watchlist.csv",
                "row_number": idx,
                "address": token_address,
                "label": row.get("issuer_label", ""),
                "category": "stablecoin",
                "enabled": row.get("enabled", ""),
                "status": "fail" if flags else "pass",
                "flags": ",".join(flags),
            }
        )
    return checks


def check_hyperliquid_rows(rows: list[dict]) -> list[dict]:
    checks = []
    seen = {}
    for idx, row in enumerate(rows, start=2):
        account = str(row.get("address", "")).strip()
        key = account.lower()
        flags = []
        if not ADDRESS_RE.match(account):
            flags.append("invalid_address")
        if key in seen:
            flags.append("duplicate_hyperliquid_account")
        seen[key] = idx
        if not str(row.get("label", "")).strip():
            flags.append("missing_label")
        if not str(row.get("entity", "")).strip():
            flags.append("missing_entity")
        if is_enabled(row) and number(row.get("alert_threshold_usd")) <= 0:
            flags.append("invalid_threshold")
        checks.append(
            {
                "source_file": "hyperliquid_watchlist.csv",
                "row_number": idx,
                "address": account,
                "label": row.get("label", ""),
                "category": row.get("category", "hyperliquid_whale"),
                "enabled": row.get("enabled", ""),
                "status": "fail" if flags else "pass",
                "flags": ",".join(flags),
            }
        )
    return checks


def render_markdown(rows: list[dict], summary: dict) -> str:
    lines = [
        "# v0.7 Watchlist Validation",
        "",
        "| field | value |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Failed Rows", "", "| source | row | label | flags |", "|---|---:|---|---|"])
    failed = [row for row in rows if row["status"] == "fail"]
    if not failed:
        lines.append("| none |  |  |  |")
    else:
        for row in failed:
            lines.append(f"| {row['source_file']} | {row['row_number']} | {row['label']} | {row['flags']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    address_rows = read_rows(normalize_path(args.addresses))
    stablecoin_rows = read_rows(normalize_path(args.stablecoins))
    hyperliquid_rows = read_rows(normalize_path(args.hyperliquid))
    checks = check_address_rows(address_rows) + check_stablecoin_rows(stablecoin_rows) + check_hyperliquid_rows(hyperliquid_rows)
    fail_count = sum(1 for row in checks if row["status"] == "fail")
    enabled_address_count = sum(1 for row in address_rows if is_enabled(row))
    enabled_stablecoin_count = sum(1 for row in stablecoin_rows if is_enabled(row))
    summary = {
        "address_rows": len(address_rows),
        "enabled_address_rows": enabled_address_count,
        "stablecoin_rows": len(stablecoin_rows),
        "enabled_stablecoin_rows": enabled_stablecoin_count,
        "hyperliquid_rows": len(hyperliquid_rows),
        "enabled_hyperliquid_rows": sum(1 for row in hyperliquid_rows if is_enabled(row)),
        "check_rows": len(checks),
        "fail_count": fail_count,
        "status": "pass" if fail_count == 0 else "fail",
    }
    report_path = normalize_path(args.output)
    summary_path = normalize_path(args.summary)
    markdown_path = normalize_path(args.markdown_output)
    write_rows(report_path, checks, ["source_file", "row_number", "address", "label", "category", "enabled", "status", "flags"])
    write_rows(summary_path, [summary], list(summary.keys()))
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(checks, summary), encoding="utf-8")
    print(f"watchlist_status={summary['status']}")
    print(f"fail_count={fail_count}")
    print(f"wrote_report={report_path}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
