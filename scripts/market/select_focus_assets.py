import argparse
import csv
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


COLUMNS = [
    "asset_symbol",
    "tier",
    "selected",
    "selection_reason",
    "price_change_pct_24h",
    "open_interest_change_pct_24h",
    "funding_rate",
    "market_state_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select digest focus assets from market-state rows using asset tiers.")
    parser.add_argument("--market-state", default=str(ROOT / "results" / "v14_market_state_snapshot.csv"))
    parser.add_argument("--asset-tiers", default=str(ROOT / "config" / "asset_tiers.yaml"))
    parser.add_argument("--output", default=str(ROOT / "results" / "v14_focus_assets.csv"))
    parser.add_argument("--summary", default=str(ROOT / "results" / "v14_focus_assets_summary.csv"))
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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return default


def load_simple_yaml(path: Path) -> dict:
    data: dict[str, Any] = {}
    current_key = ""
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current_key = line[:-1].strip()
            data[current_key] = []
            continue
        if line.startswith("  - ") and current_key:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(line.strip()[2:].strip())
            continue
        if line.startswith("  ") and ":" in line and current_key:
            if not isinstance(data.get(current_key), dict):
                data[current_key] = {}
            key, value = line.strip().split(":", 1)
            data[current_key][key.strip()] = value.strip()
    return data


def asset_tier(asset: str, cfg: dict) -> str:
    asset_u = str(asset or "").strip().upper()
    for tier in ("tier_1", "tier_2", "tier_3"):
        if asset_u in {str(item).upper() for item in cfg.get(tier, [])}:
            return tier
    return "other"


def rule_float(rules: dict, key: str, default: float) -> float:
    return safe_float(rules.get(key), default)


def select_row(row: dict, cfg: dict) -> tuple[bool, str, str]:
    asset = str(row.get("asset_symbol") or "").strip().upper()
    tier = asset_tier(asset, cfg)
    rules = cfg.get("focus_rules", {}) if isinstance(cfg.get("focus_rules"), dict) else {}
    price_abs = abs(safe_float(row.get("price_change_pct_24h")))
    oi_abs = abs(safe_float(row.get("open_interest_change_pct_24h")))

    if tier == "tier_1":
        return True, tier, "tier_1_always"
    if tier == "tier_2":
        if price_abs >= rule_float(rules, "tier_2_min_abs_price_change_pct", 5) or oi_abs >= rule_float(rules, "tier_2_min_abs_oi_change_pct", 10):
            return True, tier, "tier_2_threshold_met"
        return False, tier, "tier_2_below_threshold"
    if tier == "tier_3":
        if price_abs >= rule_float(rules, "tier_3_min_abs_price_change_pct", 15) or oi_abs >= rule_float(rules, "tier_3_min_abs_oi_change_pct", 20):
            return True, tier, "tier_3_extreme_threshold_met"
        return False, tier, "tier_3_below_extreme_threshold"
    return False, tier, "not_in_focus_tiers"


def main() -> int:
    args = parse_args()
    cfg = load_simple_yaml(normalize_path(args.asset_tiers))
    rules = cfg.get("focus_rules", {}) if isinstance(cfg.get("focus_rules"), dict) else {}
    max_focus = int(rule_float(rules, "max_focus_assets", 4))
    input_rows = [row for row in read_rows(normalize_path(args.market_state)) if str(row.get("quality_status", "")).lower() == "ok"]
    output = []
    selected = []
    for row in input_rows:
        is_selected, tier, reason = select_row(row, cfg)
        item = {
            "asset_symbol": row.get("asset_symbol", ""),
            "tier": tier,
            "selected": "true" if is_selected else "false",
            "selection_reason": reason,
            "price_change_pct_24h": row.get("price_change_pct_24h", ""),
            "open_interest_change_pct_24h": row.get("open_interest_change_pct_24h", ""),
            "funding_rate": row.get("funding_rate", ""),
            "market_state_reason": row.get("market_state_reason", ""),
        }
        output.append(item)
        if is_selected:
            selected.append(item)
    tier_rank = {"tier_1": 0, "tier_2": 1, "tier_3": 2, "other": 3}
    selected = sorted(
        selected,
        key=lambda row: (
            tier_rank.get(row.get("tier", "other"), 9),
            -abs(safe_float(row.get("price_change_pct_24h"))),
            -abs(safe_float(row.get("open_interest_change_pct_24h"))),
        ),
    )[:max_focus]
    selected_assets = {row["asset_symbol"] for row in selected}
    for row in output:
        row["selected"] = "true" if row["asset_symbol"] in selected_assets else "false"
        if row["asset_symbol"] not in selected_assets and row["selection_reason"].endswith("_met"):
            row["selection_reason"] = "trimmed_by_max_focus_assets"

    write_rows(normalize_path(args.output), output, COLUMNS)
    summary = {
        "input_rows": len(input_rows),
        "selected_count": len(selected_assets),
        "selected_assets": ";".join(row["asset_symbol"] for row in selected),
        "tier_1_selected": sum(1 for row in selected if row.get("tier") == "tier_1"),
        "tier_2_selected": sum(1 for row in selected if row.get("tier") == "tier_2"),
        "tier_3_selected": sum(1 for row in selected if row.get("tier") == "tier_3"),
        "status": "pass" if selected_assets else "warning",
    }
    write_rows(normalize_path(args.summary), [summary], list(summary.keys()))
    print(f"selected_count={summary['selected_count']} assets={summary['selected_assets']}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
