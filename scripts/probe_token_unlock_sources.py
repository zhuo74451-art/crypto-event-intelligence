import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36",
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://coinmarketcap.com/token-unlocks/",
    "Origin": "https://coinmarketcap.com",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe public token-unlock data APIs/pages.")
    parser.add_argument("--output", default=str(ROOT / "results" / "v081_token_unlock_api_probe.csv"))
    parser.add_argument("--report", default=str(ROOT / "results" / "v081_token_unlock_api_probe.md"))
    parser.add_argument("--timeout", type=float, default=15)
    return parser.parse_args()


def normalize_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def fetch(url: str, timeout: float) -> tuple[int, str, str, str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        ctype = response.headers.get("content-type", "")
        text = response.text or ""
        return response.status_code, ctype, text, ""
    except Exception as exc:
        return 0, "", "", f"{type(exc).__name__}: {exc}"


def short(value: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def extract_script_urls(html: str) -> list[str]:
    urls = []
    for match in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, flags=re.I):
        src = match.group(1)
        if "_next/static" in src:
            urls.append(urljoin("https://coinmarketcap.com", src))
    return sorted(set(urls))


def extract_api_hints(text: str) -> list[str]:
    hints = set()
    patterns = [
        r"https://api\.coinmarketcap\.com/data-api/[^\"'`\\\s]+",
        r"/data-api/v\d+/[^\"'`\\\s]+",
        r"data-api/v\d+/[^\"'`\\\s]+",
        r"token[-_]?unlock[^\"'`\\\s]{0,140}",
        r"unlock[^\"'`\\\s]{0,140}",
        r"vesting[^\"'`\\\s]{0,140}",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            item = match.group(0).replace("\\u002F", "/").replace("\\/", "/")
            hints.add(item)
    return sorted(hints)


def json_summary(text: str) -> str:
    try:
        data = json.loads(text)
    except Exception:
        return ""
    if isinstance(data, dict):
        keys = ",".join(list(data.keys())[:20])
        return f"dict_keys={keys}"
    if isinstance(data, list):
        return f"list_len={len(data)}"
    return type(data).__name__


def main() -> int:
    args = parse_args()
    rows = []
    candidates = [
        "https://api.llama.fi/emissions",
        "https://api.llama.fi/api/emissions",
        "https://api.coinmarketcap.com/data-api/v3/token-unlocks",
        "https://api.coinmarketcap.com/data-api/v3/token-unlock",
        "https://api.coinmarketcap.com/data-api/v3/token-unlock/list",
        "https://api.coinmarketcap.com/data-api/v3/token-unlock/calendar",
        "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/token-unlocks",
        "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/unlock/list",
        "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/vesting",
        "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit=100&sortBy=market_cap&sortType=desc&convert=USD&cryptoType=all&tagType=all&audited=false&aux=ath,atl,high24h,low24h,num_market_pairs,cmc_rank,date_added,max_supply,circulating_supply,total_supply,volume_7d,volume_30d",
    ]

    page_url = "https://coinmarketcap.com/token-unlocks/"
    status, ctype, html, error = fetch(page_url, args.timeout)
    rows.append(
        {
            "source": "coinmarketcap_page",
            "url": page_url,
            "status": status,
            "content_type": ctype,
            "bytes": len(html),
            "json_summary": json_summary(html),
            "snippet": short(error or html),
        }
    )

    page_hints = extract_api_hints(html)
    for hint in page_hints:
        if "data-api" in hint.lower():
            if hint.startswith("http"):
                candidates.append(hint)
            elif hint.startswith("/"):
                candidates.append(urljoin("https://api.coinmarketcap.com", hint))
            else:
                candidates.append(urljoin("https://api.coinmarketcap.com/", hint))

    script_urls = extract_script_urls(html)
    searched_scripts = 0
    script_hints = []
    for script_url in script_urls[:80]:
        status, ctype, text, error = fetch(script_url, args.timeout)
        hints = extract_api_hints(text)
        if hints:
            searched_scripts += 1
            script_hints.extend(hints)
            rows.append(
                {
                    "source": "coinmarketcap_script_hint",
                    "url": script_url,
                    "status": status,
                    "content_type": ctype,
                    "bytes": len(text),
                    "json_summary": "",
                    "snippet": " | ".join(hints[:8]),
                }
            )
    for hint in script_hints:
        if "data-api" in hint.lower():
            if hint.startswith("http"):
                candidates.append(hint)
            elif hint.startswith("/"):
                candidates.append(urljoin("https://api.coinmarketcap.com", hint))
            else:
                candidates.append(urljoin("https://api.coinmarketcap.com/", hint))

    unique_candidates = []
    seen = set()
    for url in candidates:
        clean_url = url.strip().strip('"').strip("'")
        clean_url = clean_url.replace("\\u002F", "/").replace("\\/", "/")
        if clean_url and clean_url not in seen:
            seen.add(clean_url)
            unique_candidates.append(clean_url)

    for url in unique_candidates:
        status, ctype, text, error = fetch(url, args.timeout)
        rows.append(
            {
                "source": "api_probe",
                "url": url,
                "status": status,
                "content_type": ctype,
                "bytes": len(text),
                "json_summary": json_summary(text),
                "snippet": short(error or text),
            }
        )

    output_path = normalize_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["source", "url", "status", "content_type", "bytes", "json_summary", "snippet"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    useful = [
        row
        for row in rows
        if int(row.get("status") or 0) == 200
        and ("json" in str(row.get("content_type", "")).lower() or row.get("json_summary"))
    ]
    report_lines = [
        "# Token Unlock API Probe",
        "",
        f"- coinmarketcap_script_count: {len(script_urls)}",
        f"- scripts_with_unlock_hints: {searched_scripts}",
        f"- probed_api_candidates: {len(unique_candidates)}",
        f"- useful_json_200_count: {len(useful)}",
        f"- csv: `{output_path}`",
        "",
        "## Useful 200 JSON Responses",
        "",
        "| status | url | json_summary | snippet |",
        "| --- | --- | --- | --- |",
    ]
    for row in useful[:30]:
        report_lines.append(
            f"| {row['status']} | {row['url']} | {row['json_summary']} | {str(row['snippet']).replace('|', '/')} |"
        )
    report_lines.extend(["", "## Best Hints", ""])
    for row in rows:
        if "unlock" in str(row.get("snippet", "")).lower() or "vesting" in str(row.get("snippet", "")).lower():
            report_lines.append(f"- `{row['source']}` `{row['status']}` `{row['url']}`: {row['snippet']}")
    normalize_path(args.report).write_text("\n".join(report_lines), encoding="utf-8")
    print(f"wrote_probe_csv={output_path}")
    print(f"useful_json_200_count={len(useful)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
