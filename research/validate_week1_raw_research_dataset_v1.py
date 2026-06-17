#!/usr/bin/env python3
"""Validate Week 1 Raw Research Dataset v1.

Usage: python -X utf8 research/validate_week1_raw_research_dataset_v1.py <dataset.json>
Exit 0 = pass, 1 = fail.
"""

import hashlib
import json
import sys


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


PRICE_FILE = "research/week1_price_backfill_raw_v1.json"
MANIFEST_FILE = "research/week1_samples_v1.json"
EXPECTED_PRICE_COMMIT = "d7b908d868957e0165924598e6058fef27eb0b3d"
EXPECTED_DATA_COMMIT = "7188a52dedb54955cd41b187821081e1945c8706"
FORBIDDEN_TERMS = ["attribution_confidence", "causal_score", "buy_signal",
                   "sell_signal", "win_rate", "causality"]


def validate(data: dict, proj_dir: str) -> tuple[bool, list[str]]:
    violations = []

    # 1. Count checks
    if data.get("samples_count") != 5:
        violations.append(f"samples_count={data.get('samples_count')} != 5")
    if data.get("sample_links_count") != 6:
        violations.append(f"sample_links_count={data.get('sample_links_count')} != 6")
    if data.get("unique_price_observations_count") != 5:
        violations.append(f"unique_price_observations={data.get('unique_price_observations_count')} != 5")

    # 2. All 5 sample IDs exist
    samples = data.get("samples", [])
    sample_ids = {s.get("sample_id") for s in samples}
    for sid in ("w1_001", "w1_002", "w1_003", "w1_004", "w1_005"):
        if sid not in sample_ids:
            violations.append(f"sample_id '{sid}' missing from samples")

    # 3. Each link's sample_id exists in samples
    links = data.get("sample_price_links", [])
    for link in links:
        lsid = link.get("sample_id", "")
        if lsid not in sample_ids:
            violations.append(f"link sample_id '{lsid}' not found in samples")

    # 4. Each link's price_observation_key exists in observations
    obs = data.get("price_observations", {})
    for link in links:
        pok = link.get("price_observation_key", "")
        if pok not in obs:
            violations.append(f"link price_observation_key '{pok}' not found in observations")

    # 5. w1_003 and w1_004 share same observation key
    link_by_sid = {}
    for link in links:
        lsid = link.get("sample_id", "")
        if lsid not in link_by_sid:
            link_by_sid[lsid] = []
        link_by_sid[lsid].append(link)
    w3_keys = {l["price_observation_key"] for l in link_by_sid.get("w1_003", [])}
    w4_keys = {l["price_observation_key"] for l in link_by_sid.get("w1_004", [])}
    if w3_keys != w4_keys:
        violations.append(f"w1_003 keys {w3_keys} != w1_004 keys {w4_keys} (should share)")

    # 6. w1_003 and w1_004 are still independent samples
    if len(link_by_sid.get("w1_003", [])) != 1:
        violations.append("w1_003 should have exactly 1 link")
    if len(link_by_sid.get("w1_004", [])) != 1:
        violations.append("w1_004 should have exactly 1 link")

    # 7. w1_005 has BTC and ETH links
    w5_links = link_by_sid.get("w1_005", [])
    w5_obs = {l.get("observed_asset") for l in w5_links}
    if w5_obs != {"BTC", "ETH"}:
        violations.append(f"w1_005 observed assets {w5_obs} != {{BTC, ETH}}")

    # 8. raw_summary not modified (compare to source)
    manifest_path = f"{proj_dir}/{MANIFEST_FILE}"
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            src_manifest = json.load(f)
        src_samples = {s["sample_id"]: s for s in src_manifest.get("samples", [])}
        for s in samples:
            sid = s.get("sample_id", "")
            src = src_samples.get(sid, {})
            if s.get("raw_summary") != src.get("raw_summary"):
                violations.append(f"{sid}: raw_summary differs from manifest source")
            if s.get("tags_raw") != src.get("tags_raw"):
                violations.append(f"{sid}: tags_raw differs from manifest source")
    except (IOError, json.JSONDecodeError) as e:
        violations.append(f"Cannot read manifest source: {e}")

    # 9. Price observations match price source file
    price_path = f"{proj_dir}/{PRICE_FILE}"
    try:
        with open(price_path, "r", encoding="utf-8") as f:
            src_price = json.load(f)
        src_results = {r.get("price_observation_key", ""): r for r in src_price.get("results", [])}
        for pok, entry in obs.items():
            src_entry = src_results.get(pok)
            if src_entry is None:
                violations.append(f"observation '{pok}' not found in price source")
                continue
            # Compare full payload (skip metadata that differs for shared obs)
            skip_keys = {"calculated_at", "sample_id", "result_id",
                         "observation_reused", "reused_from_result_id"}
            for key in src_entry:
                if key in skip_keys:
                    continue
                sv = src_entry[key]
                ev = entry.get(key)
                if isinstance(sv, dict) and isinstance(ev, dict):
                    for k in sv:
                        if k in skip_keys:
                            continue
                        if sv.get(k) != ev.get(k):
                            violations.append(f"{pok}/{key}.{k}: price source mismatch")
                elif key in ("return_1h", "return_4h", "return_24h"):
                    pass
                elif sv != ev:
                    violations.append(f"{pok}/{key}: {sv} != {ev}")
    except (IOError, json.JSONDecodeError) as e:
        violations.append(f"Cannot read price source: {e}")

    # 10. checksums
    try:
        manifest_sha = sha256_file(manifest_path)
        if data.get("manifest_file_sha256") != manifest_sha:
            violations.append("manifest_file_sha256 mismatch")
    except IOError:
        violations.append("Cannot compute manifest sha256")
    try:
        price_sha = sha256_file(price_path)
        if data.get("price_file_sha256") != price_sha:
            violations.append("price_file_sha256 mismatch")
    except IOError:
        violations.append("Cannot compute price sha256")

    # 11. Commit values
    cc = data.get("price_code_commit", "")
    if cc != EXPECTED_PRICE_COMMIT:
        violations.append(f"price_code_commit '{cc}' != {EXPECTED_PRICE_COMMIT}")
    dc = data.get("price_data_commit", "")
    if dc != EXPECTED_DATA_COMMIT:
        violations.append(f"price_data_commit '{dc}' != {EXPECTED_DATA_COMMIT}")

    # 12. No attribution or trading advice
    if data.get("contains_attribution") is not False:
        violations.append("contains_attribution should be false")
    if data.get("contains_trading_advice") is not False:
        violations.append("contains_trading_advice should be false")

    text = json.dumps(data, ensure_ascii=False).lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            violations.append(f"forbidden term '{term}' found in dataset")

    # 13. No fixture sources
    if "fixture" in text:
        violations.append("fixture source found in dataset")

    passed = len(violations) == 0
    return passed, violations


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_week1_raw_research_dataset_v1.py <dataset.json>")
        sys.exit(1)
    path = sys.argv[1]
    proj_dir = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    passed, violations = validate(data, proj_dir)
    print(f"File: {path}")
    print(f"Samples: {data.get('samples_count', '?')}")
    print(f"Links: {data.get('sample_links_count', '?')}")
    print(f"Unique obs: {data.get('unique_price_observations_count', '?')}")
    print(f"Passed: {passed}")
    if violations:
        print(f"\nViolations ({len(violations)}):")
        for v in violations:
            print(f"  [FAIL] {v}")
        sys.exit(1)
    else:
        print("[PASS] All dataset consistency checks passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
