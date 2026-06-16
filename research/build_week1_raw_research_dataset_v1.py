#!/usr/bin/env python3
"""Build Week 1 Raw Research Dataset v1.

Assembles the unified research dataset from two approved source files:
  - research/week1_samples_v1.json (event Manifest)
  - research/week1_price_backfill_raw_v1.json (Price Results)

No network access. No recomputation. No attribution.
Deterministic: same inputs produce identical outputs.
"""

import hashlib
import json
import os
import sys
from copy import deepcopy

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJ, "research")
DOCS_DIR = os.path.join(PROJ, "docs", "research")
os.makedirs(DOCS_DIR, exist_ok=True)

MANIFEST_PATH = os.path.join(OUTPUT_DIR, "week1_samples_v1.json")
PRICE_PATH = os.path.join(OUTPUT_DIR, "week1_price_backfill_raw_v1.json")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "week1_raw_research_dataset_v1.json")
DOCS_PATH = os.path.join(DOCS_DIR, "week1_raw_research_dataset_v1.md")

MAIN_BASELINE = "9c28c9308e42ea8ef822f7eff8a20c4b0e827290"
MANIFEST_COMMIT = "1f332992b2938a355e43f566d8901f00d01d842c"
PRICE_CODE_COMMIT = "d7b908d868957e0165924598e6058fef27eb0b3d"
PRICE_DATA_COMMIT = "7188a52dedb54955cd41b187821081e1945c8706"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_dataset() -> dict:
    manifest = load_json(MANIFEST_PATH)
    price_data = load_json(PRICE_PATH)

    manifest_sha = sha256_file(MANIFEST_PATH)
    price_sha = sha256_file(PRICE_PATH)

    # A. Event Samples from Manifest
    samples = manifest.get("samples", [])
    samples_by_id: dict[str, dict] = {s["sample_id"]: s for s in samples}

    # B. Unique Price Observations from Price Results
    price_results = price_data.get("results", [])
    obs_by_key: dict[str, dict] = {}
    for r in price_results:
        pok = r.get("price_observation_key", "")
        if pok and pok not in obs_by_key:
            obs_by_key[pok] = r

    # C. Sample-to-Observation Links
    links = []
    for r in price_results:
        links.append({
            "sample_id": r.get("sample_id", ""),
            "result_id": r.get("result_id", ""),
            "price_observation_key": r.get("price_observation_key", ""),
            "subject_asset": r.get("subject_asset", ""),
            "observed_asset": r.get("observed_asset", ""),
            "observation_reused": r.get("observation_reused", False),
            "reused_from_result_id": r.get("reused_from_result_id"),
        })

    now = price_data.get("generated_at", "")

    dataset = {
        "dataset_name": "Week 1 Raw Research Dataset",
        "dataset_version": "v1",
        "dataset_status": "raw_no_attribution",
        "generated_at": now,
        "main_baseline_commit": MAIN_BASELINE,
        "manifest_commit": MANIFEST_COMMIT,
        "price_code_commit": PRICE_CODE_COMMIT,
        "price_data_commit": PRICE_DATA_COMMIT,
        "manifest_file_sha256": manifest_sha,
        "price_file_sha256": price_sha,
        "samples_count": len(samples),
        "sample_links_count": len(links),
        "unique_price_observations_count": len(obs_by_key),
        "t0_policy": "broadcast_time",
        "contains_attribution": False,
        "contains_trading_advice": False,
        "samples": samples,
        "price_observations": {k: deepcopy(v) for k, v in obs_by_key.items()},
        "sample_price_links": links,
    }
    return dataset


def save_dataset(dataset: dict):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    return OUTPUT_PATH


def save_docs(dataset: dict):
    lines = [
        "# Week 1 Raw Research Dataset v1",
        "",
        "## Purpose",
        "",
        "This dataset packages Week 1 event samples with their corresponding raw price",
        "backfill results. It is the foundation for downstream attribution analysis.",
        "",
        "## Dataset Structure",
        "",
        "| Layer | Count | Description |",
        "|-------|-------|-------------|",
        f"| Event Samples | {dataset['samples_count']} | 5 event facts from the manifest |",
        f"| Unique Price Observations | {dataset['unique_price_observations_count']} | 5 deduplicated price backfill results |",
        f"| Sample-to-Observation Links | {dataset['sample_links_count']} | 6 links connecting samples to observations |",
        "",
        "## Event Samples",
        "",
        "| ID | Title | Subject | Broadcast (UTC) |",
        "|----|-------|---------|-----------------|",
    ]
    for s in dataset["samples"]:
        lines.append(
            f"| {s['sample_id']} | {s.get('title', '?')} | "
            f"{s.get('subject_asset', '?')} | {s.get('broadcast_time_utc', '?')} |"
        )

    lines += [
        "",
        "## Price Observations",
        "",
        "| Key | Observed Asset | Provider | Interval | Policy | Signed Lag |",
        "|-----|---------------|----------|----------|--------|------------|",
    ]
    for pok, obs in dataset["price_observations"].items():
        lines.append(
            f"| `{pok}` | {obs.get('observed_asset', '?')} | "
            f"{obs.get('provider', '?')} | {obs.get('interval', '?')} | "
            f"{obs.get('selection_policy', '?')} | {obs.get('signed_lag_seconds', '?')}s |"
        )

    lines += [
        "",
        "## Sample Links",
        "",
        "| Sample | Result ID | Observation Key | Reused |",
        "|--------|-----------|-----------------|--------|",
    ]
    for link in dataset["sample_price_links"]:
        reused = f"yes (from {link['reused_from_result_id']})" if link.get("observation_reused") else "no"
        lines.append(
            f"| {link['sample_id']} | {link['result_id']} | "
            f"`{link['price_observation_key']}` | {reused} |"
        )

    lines += [
        "",
        "## Key Design Decisions",
        "",
        "1. **t0 = broadcast_time**: All price snapshots use the event broadcast",
        "   time as t0, not event time or edit time.",
        "",
        "2. **HYPE 15m / BTC,ETH 1m**: HYPE uses Hyperliquid 15m candles with",
        "   nearest_candle_open selection (450s max lag). BTC and ETH use Binance",
        "   1m klines with first_after_target selection (120s max lag).",
        "",
        "3. **w1_003 / w1_004 share observation**: Both samples reference the same",
        "   BTC price at 2026-05-25T16:12:00Z. The price was fetched once and",
        "   reused via run-level SnapshotCache. w1_004 is marked observation_reused.",
        "",
        "4. **Price response != event attribution**: The observed price movement",
        "   may be influenced by confounding factors. This dataset provides raw",
        "   returns only — it does not assign causality.",
        "",
        "## Known Limitations",
        "",
        "- HYPE data uses 15m candles (not 1m). Signed lag of -120s means the",
        "  nearest candle open is 2 minutes before broadcast time.",
        "- 24h windows may be pending if data was generated before full maturity.",
        "- Some samples may have duplicate broadcast times (e.g., w1_003/w1_004).",
        "- No attribution score or confidence is calculated at this layer.",
        "",
        "## Downstream Consumption",
        "",
        "Attribution analysis should use `sample_price_links` to join samples",
        "with their observations. Use `price_observations` as the canonical",
        "price data. The `price_observation_key` ensures dedup across samples.",
        "",
        f"*Generated: {dataset['generated_at']}*",
        "*Version: v1 | Status: raw_no_attribution*",
    ]

    with open(DOCS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return DOCS_PATH


def main():
    print(f"Building dataset from:\n  Manifest: {MANIFEST_PATH}\n  Price:    {PRICE_PATH}")
    dataset = build_dataset()
    jp = save_dataset(dataset)
    dp = save_docs(dataset)
    print(f"Output:   {jp}")
    print(f"Docs:     {dp}")
    print(f"Samples: {dataset['samples_count']}")
    print(f"Unique obs: {dataset['unique_price_observations_count']}")
    print(f"Links: {dataset['sample_links_count']}")
    print("Build complete — no network, no recomputation, no attribution")


if __name__ == "__main__":
    main()
